from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict

from PySide6.QtCore import QObject, QThread, QTime, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from direct_api_capture import (
    DirectApiCaptureError,
    DirectApiLoginRequiredError,
    capture_with_direct_api,
    format_cookie_diagnostics,
    migrate_direct_api_cookie_config,
    summarize_cookie,
    update_direct_api_cookie,
)
from external_capture import LoginRequiredError, capture_with_external_chrome, inspect_existing_shadow_browser_state, inspect_external_page_state
from login_accounts import add_login_account, build_account_state, capture_enabled_accounts, ensure_login_accounts
from shadow_browser import (
    ChromeNotFoundError,
    PortOccupiedError,
    ShadowBrowserError,
    default_shadow_profile_dir,
    show_shadow_browser_for_login,
    shutdown_shadow_browser,
)
from single_instance import SingleInstanceManager
from spider_core import EMPLOYEE_TARGET_URL, format_employee_summary, payload_signature
from startup_manager import ensure_autostart, is_autostart_enabled
from upload_client import UploadClientError, upload_employee_payload

APP_NAME = "远盛数据助手"
DEFAULT_SERVER_URL = "http://120.27.22.50"  # 如需安全传输，服务端启用 HTTPS 后将此改为 https://


def direct_api_cookie_state_label(status: str) -> str:
    return f"接口 Cookie：{status}"


def cookie_has_direct_api_markers(cookie: str) -> bool:
    summary = summarize_cookie(cookie)
    return bool(summary["hasMtopToken"] and (summary["hasSn"] or summary["hasUnb"] or summary["hasTbToken"]))


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def app_data_dir() -> Path:
    import os
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "YuanshengDataAssistant" / "data"


def _default_state() -> Dict[str, Any]:
    shadow_dir = str(default_shadow_profile_dir())
    return {
        "dataVersion": 1,
        "captureEngine": "external",
        "directApiPreferred": False,
        "directApiConfigPath": "",
        "chromePath": "",
        "chromePort": 9222,
        "chromeUserDataDir": shadow_dir,
        "shadowChromeProfileDir": shadow_dir,
        "shadowChromeStartupUrl": EMPLOYEE_TARGET_URL,
        "lastKnownLoginAccount": "",
        "scheduleEnabled": True,
        "scheduleTime": "09:00",
        "lastRunDate": "",
        "lastRunAt": "",
        "lastCaptureDate": "",
        "lastCaptureAt": "",
        "lastUploadDate": "",
        "lastUploadAt": "",
        "lastPayloadSignature": "",
        "lastPayloadSummary": "",
        "closeToTray": True,
        "autoStartEnabled": True,
        "shadowChromeAutoLaunch": False,
        "exitRequiresConfirm": True,
        "shadowChromePid": 0,
        "serverUrl": DEFAULT_SERVER_URL,
        "uploadTimeoutSeconds": 10,
        "uploadHistory": {},
    }


def _upload_payload_with_state(
    state: Dict[str, Any],
    payload: Dict[str, Any],
    signature: str,
    capture_reason: str,
) -> tuple[str, Dict[str, Any] | None]:
    server_url = str(state.get("serverUrl") or "").strip()
    if not server_url:
        return "未配置服务端地址，本次仅保留本地结果。", None

    upload_history = state.get("uploadHistory")
    if not isinstance(upload_history, dict):
        upload_history = {}

    if signature in upload_history and capture_reason != "手动采集":
        history = upload_history.get(signature) or {}
        uploaded_at = history.get("uploadedAt") or "未知时间"
        return f"本次数据已上传过，跳过重复上传。上次上传时间：{uploaded_at}。", None

    timeout_seconds = float(state.get("uploadTimeoutSeconds") or 10)
    try:
        result = upload_employee_payload(server_url, payload, timeout_seconds=timeout_seconds)
    except UploadClientError as exc:
        return f"服务端上传失败：{exc}", None

    upload_record = {
        "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "serverUrl": server_url.rstrip("/"),
        "recordDate": payload.get("recordDate"),
        "subAccount": payload.get("subAccount"),
    }
    return f"服务端上传成功：{result['message']}。", upload_record


class CaptureWorker(QObject):
    log_message = Signal(str)
    finished = Signal(object)

    def __init__(self, state: Dict[str, Any], reason: str):
        super().__init__()
        self.state = state
        self.reason = reason

    @Slot()
    def run(self) -> None:
        try:
            if self._has_login_accounts():
                results = self._capture_batch_results()
                self.finished.emit({"ok": True, "reason": self.reason, "batch": True, "results": results})
                return

            payload = self._capture_payload()
            signature = payload_signature(payload)
            upload_message, upload_record = _upload_payload_with_state(self.state, payload, signature, self.reason)
            self.finished.emit(
                {
                    "ok": True,
                    "reason": self.reason,
                    "payload": payload,
                    "signature": signature,
                    "uploadMessage": upload_message,
                    "uploadRecord": upload_record,
                }
            )
        except LoginRequiredError as exc:
            self.finished.emit({"ok": False, "reason": self.reason, "errorType": "login_required", "message": str(exc)})
        except DirectApiLoginRequiredError as exc:
            self.finished.emit({"ok": False, "reason": self.reason, "errorType": "login_required", "message": str(exc)})
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            self.finished.emit({"ok": False, "reason": self.reason, "errorType": "browser", "message": str(exc)})
        except Exception as exc:
            self.finished.emit({"ok": False, "reason": self.reason, "errorType": "generic", "message": str(exc)})

    CONFIG_ERROR_MARKERS = ("配置文件", "合法 JSON", "未启用", "缺少", "根节点", "config")

    def _capture_payload(self) -> Dict[str, Any]:
        if bool(self.state.get("directApiPreferred", True)):
            try:
                self.log_message.emit("开始接口直采，读取本地 F12 配置。")
                self._refresh_cookie_from_existing_shadow_for_capture()
                return capture_with_direct_api(self.state, self.log_message.emit)
            except DirectApiCaptureError as exc:
                message = str(exc)
                if any(marker in message for marker in self.CONFIG_ERROR_MARKERS):
                    self.log_message.emit(f"接口直采配置错误，请检查 F12 配置文件：{exc}")
                else:
                    self.log_message.emit(f"接口直采未完成：{exc}，回退到影子浏览器表格采集。")
            except Exception as exc:
                self.log_message.emit(f"接口直采异常：{exc}，回退到影子浏览器表格采集。")

        return capture_with_external_chrome(self.state, self.log_message.emit)

    def _has_login_accounts(self) -> bool:
        accounts = self.state.get("loginAccounts")
        return isinstance(accounts, list) and bool(accounts)

    def _capture_batch_results(self) -> list[Dict[str, Any]]:
        accounts = self.state.get("loginAccounts")
        if not isinstance(accounts, list):
            return []
        return capture_enabled_accounts(
            self.state,
            accounts,
            reason=self.reason,
            capture_func=capture_with_external_chrome,
            upload_func=_upload_payload_with_state,
            log=self.log_message.emit,
        )

    def _refresh_cookie_from_existing_shadow_for_capture(self) -> None:
        config_path_text = str(self.state.get("directApiConfigPath") or "").strip()
        if not config_path_text:
            return
        try:
            state = inspect_existing_shadow_browser_state(self.state, lambda _message: None)
        except ShadowBrowserError:
            self.log_message.emit("采集前未检测到已打开的影子浏览器，继续使用本地 Cookie。")
            return
        except Exception as exc:
            self.log_message.emit(f"采集前刷新影子浏览器 Cookie 跳过：{exc}")
            return

        cookie_header = str(state.get("cookieHeader") or "").strip()
        if not cookie_header or not cookie_has_direct_api_markers(cookie_header):
            return
        try:
            update_direct_api_cookie(Path(config_path_text), cookie_header)
        except DirectApiCaptureError as exc:
            self.log_message.emit(f"采集前刷新接口 Cookie 失败：{exc}")
            return

        self.log_message.emit(f"采集前已从已打开的影子浏览器刷新 Cookie：{format_cookie_diagnostics(cookie_header)}")


class CleanupWorker(QObject):
    log_message = Signal(str)
    finished = Signal()

    def __init__(self, target: Path):
        super().__init__()
        self.target = target

    @Slot()
    def run(self) -> None:
        try:
            if self.target.exists():
                shutil.rmtree(self.target)
                self.log_message.emit(f"已删除影子目录：{self.target}")
        except Exception as exc:
            self.log_message.emit(f"删除影子目录失败，可稍后手动清理：{exc}")
        self.finished.emit()


class YuanshengMainWindow(QMainWindow):
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.data_dir = app_data_dir()
        self.state_path = self.data_dir / "app_state.json"
        self.icon_path = self.base_dir / "resources" / "yuansheng_logo.png"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.state = self._load_json(self.state_path, _default_state())
        self.state["directApiConfigPath"] = str(self.data_dir / "direct_api_capture.json")
        ensure_login_accounts(self.state, self.data_dir)
        self.cookie_security_migration_message = self._migrate_direct_api_cookie_config()
        self._migrate_state_defaults()
        self.logged_in = False
        self.capture_in_progress = False
        self.capture_reason = ""
        self.pending_login_recovery = False
        self.pending_login_account_id = ""
        self.exit_requested = False
        self._last_log_message = ""
        self.capture_thread: QThread | None = None
        self.capture_worker: CaptureWorker | None = None

        self.setWindowTitle(APP_NAME)
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))
        self.resize(980, 860)

        self._build_ui()
        self._build_tray()
        self._bind_events()
        self._apply_state_to_ui()
        QTimer.singleShot(0, self._initialize_runtime)

    def _make_section_header(self, title_text: str, subtitle_text: str = "") -> QWidget:
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        if subtitle_text:
            subtitle = QLabel(subtitle_text)
            subtitle.setObjectName("mutedText")
            layout.addWidget(subtitle)

        return header

    def _make_info_tile(self, title_text: str, value_label: QLabel) -> QFrame:
        tile = QFrame()
        tile.setObjectName("infoTile")
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title = QLabel(title_text)
        title.setObjectName("tileCaption")
        value_label.setObjectName("tileValue")
        value_label.setWordWrap(title_text in {"Chrome 路径", "影子目录"})
        value_label.setToolTip(value_label.text())

        layout.addWidget(title)
        layout.addWidget(value_label)
        return tile

    def _set_info_text(self, label: QLabel, text: str) -> None:
        label.setText(text)
        if hasattr(label, "setToolTip"):
            label.setToolTip(text)

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(16, 14, 16, 14)
        page.setSpacing(12)

        header = QFrame()
        header.setObjectName("heroCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        title = QLabel(APP_NAME)
        title.setObjectName("titleText")
        subtitle = QLabel("接口直采优先；Cookie 失效时打开影子 Chrome 刷新登录态")
        subtitle.setObjectName("mutedText")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        status_box = QVBoxLayout()
        status_box.setSpacing(6)
        status_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_pill = QLabel("初始化中")
        self.status_pill.setObjectName("statusPill")
        self.next_run_label = QLabel("下次计划：--")
        self.next_run_label.setObjectName("mutedText")
        self.last_run_label = QLabel("最近执行：--")
        self.last_run_label.setObjectName("mutedText")
        status_box.addWidget(self.status_pill, alignment=Qt.AlignmentFlag.AlignRight)
        status_box.addWidget(self.next_run_label, alignment=Qt.AlignmentFlag.AlignRight)
        status_box.addWidget(self.last_run_label, alignment=Qt.AlignmentFlag.AlignRight)

        header_layout.addLayout(title_box)
        header_layout.addStretch(1)
        header_layout.addLayout(status_box)
        page.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tabWidget")

        tab_data = QWidget()
        tab_data_layout = QVBoxLayout(tab_data)
        tab_data_layout.setContentsMargins(0, 0, 0, 0)
        tab_data_layout.setSpacing(12)

        tab_users = QWidget()
        tab_users_layout = QVBoxLayout(tab_users)
        tab_users_layout.setContentsMargins(0, 0, 0, 0)
        tab_users_layout.setSpacing(12)

        self.tab_widget.addTab(tab_data, "数据采集")
        self.tab_widget.addTab(tab_users, "用户管理")
        page.addWidget(self.tab_widget, stretch=1)

        control_card = QFrame()
        control_card.setObjectName("card")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(18, 16, 18, 16)
        control_layout.setSpacing(14)

        control_layout.addWidget(self._make_section_header(
            "采集控制台",
            "查看登录态、配置自动采集，并手动触发客服绩效采集。",
        ))

        self.login_state_label = QLabel("检查中")
        self.account_label = QLabel("--")
        self.result_summary_label = QLabel("尚未采集")
        self.chrome_path_label = QLabel("检测中")
        self.shadow_dir_label = QLabel("检测中")

        status_grid = QGridLayout()
        status_grid.setContentsMargins(0, 0, 0, 0)
        status_grid.setHorizontalSpacing(10)
        status_grid.setVerticalSpacing(10)
        status_grid.addWidget(self._make_info_tile("登录状态", self.login_state_label), 0, 0)
        status_grid.addWidget(self._make_info_tile("当前账号", self.account_label), 0, 1)
        status_grid.addWidget(self._make_info_tile("最近结果", self.result_summary_label), 0, 2)
        status_grid.addWidget(self._make_info_tile("Chrome 路径", self.chrome_path_label), 1, 0)
        status_grid.addWidget(self._make_info_tile("影子目录", self.shadow_dir_label), 1, 1, 1, 2)
        status_grid.setColumnStretch(0, 1)
        status_grid.setColumnStretch(1, 1)
        status_grid.setColumnStretch(2, 1)
        control_layout.addLayout(status_grid)

        settings_grid = QGridLayout()
        settings_grid.setContentsMargins(0, 0, 0, 0)
        settings_grid.setHorizontalSpacing(12)
        settings_grid.setVerticalSpacing(12)

        schedule_panel = QFrame()
        schedule_panel.setObjectName("softPanel")
        schedule_layout = QVBoxLayout(schedule_panel)
        schedule_layout.setContentsMargins(14, 12, 14, 12)
        schedule_layout.setSpacing(10)
        schedule_layout.addWidget(self._make_section_header("自动采集", "设置每日采集时间和服务端上传地址。"))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.schedule_time = QTimeEdit()
        self.schedule_time.setDisplayFormat("HH:mm")
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://服务器IP:8080 或 https://api.xxx.com")
        self.schedule_checkbox = QCheckBox("启用每日自动采集")
        self.auto_start_checkbox = QCheckBox("登录 Windows 后自动启动")
        self.shadow_launch_checkbox = QCheckBox("启动主程序时自动拉起影子浏览器")
        self.exit_confirm_checkbox = QCheckBox("托盘退出前二次确认")

        form.addRow("每日执行时间", self.schedule_time)
        form.addRow("服务端地址", self.server_url_input)
        schedule_layout.addLayout(form)
        schedule_layout.addWidget(self.schedule_checkbox)

        preference_panel = QFrame()
        preference_panel.setObjectName("softPanel")
        preference_layout = QVBoxLayout(preference_panel)
        preference_layout.setContentsMargins(14, 12, 14, 12)
        preference_layout.setSpacing(10)
        preference_layout.addWidget(self._make_section_header("运行偏好", "控制程序启动、影子浏览器和托盘退出行为。"))
        preference_layout.addWidget(self.auto_start_checkbox)
        preference_layout.addWidget(self.shadow_launch_checkbox)
        preference_layout.addWidget(self.exit_confirm_checkbox)
        preference_layout.addStretch(1)

        settings_grid.addWidget(schedule_panel, 0, 0)
        settings_grid.addWidget(preference_panel, 0, 1)
        settings_grid.setColumnStretch(0, 3)
        settings_grid.setColumnStretch(1, 2)
        control_layout.addLayout(settings_grid)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.login_button = QPushButton("重新登录")
        self.login_button.setObjectName("primaryButton")
        self.manual_crawl_button = QPushButton("采集全部启用账号")
        self.manual_crawl_button.setObjectName("accentButton")
        self.hide_button = QPushButton("缩到托盘")
        self.hide_button.setObjectName("secondaryButton")
        action_row.addWidget(self.login_button)
        action_row.addWidget(self.manual_crawl_button)
        action_row.addStretch(1)
        action_row.addWidget(self.hide_button)
        control_layout.addLayout(action_row)

        self.capture_progress = QProgressBar()
        self.capture_progress.setObjectName("captureProgress")
        self.capture_progress.setRange(0, 0)
        self.capture_progress.setTextVisible(False)
        self.capture_progress.hide()
        control_layout.addWidget(self.capture_progress)

        self.hint_label = QLabel("程序会优先接管本机影子 Chrome；未登录时请点击“重新登录”打开扫码窗口。")
        self.hint_label.setObjectName("mutedText")
        control_layout.addWidget(self.hint_label)
        tab_data_layout.addWidget(control_card)

        account_card = QFrame()
        account_card.setObjectName("card")
        account_layout = QVBoxLayout(account_card)
        account_layout.setContentsMargins(18, 16, 18, 16)
        account_layout.setSpacing(12)

        account_header = QHBoxLayout()
        account_header.setSpacing(12)
        account_header.addWidget(self._make_section_header(
            "登录账户管理",
            "维护多账号登录、采集和最近状态。",
        ))
        account_header.addStretch(1)

        self.add_account_button = QPushButton("新增登录账户")
        self.edit_account_button = QPushButton("编辑选中账户")
        self.delete_account_button = QPushButton("删除选中账户")
        self.login_selected_button = QPushButton("登录/重新登录选中账户")
        self.capture_selected_button = QPushButton("采集选中账号")
        self.delete_account_button.setObjectName("dangerButton")
        self.capture_selected_button.setObjectName("accentButton")
        self.login_selected_button.setObjectName("secondaryButton")
        for button in (
            self.add_account_button,
            self.edit_account_button,
            self.delete_account_button,
            self.login_selected_button,
            self.capture_selected_button,
        ):
            account_header.addWidget(button)
        account_layout.addLayout(account_header)

        self.login_accounts_table = QTableWidget(0, 8)
        self.login_accounts_table.setObjectName("loginAccountsTable")
        self.login_accounts_table.setHorizontalHeaderLabels(["启用", "账户备注", "登录识别名", "端口", "登录状态", "最近采集", "最近结果", "操作"])
        self.login_accounts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.login_accounts_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.login_accounts_table.verticalHeader().setVisible(False)
        self.login_accounts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.login_accounts_table.setAlternatingRowColors(True)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.login_accounts_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.login_accounts_table.setColumnWidth(7, 176)
        self.login_accounts_table.verticalHeader().setDefaultSectionSize(48)
        account_layout.addWidget(self.login_accounts_table)
        tab_users_layout.addWidget(account_card)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(18, 16, 18, 16)
        log_layout.setSpacing(12)
        log_layout.addWidget(self._make_section_header("运行日志", "记录影子浏览器、登录和采集过程。"))
        self.log_output = QPlainTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("这里会显示影子浏览器状态、登录提示和本地采集结果。")
        self.log_output.setMaximumBlockCount(500)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(self.log_output, stretch=1)
        tab_data_layout.addWidget(log_card, stretch=1)

        self._load_stylesheet()

        self.schedule_timer = QTimer(self)
        self.schedule_timer.setInterval(30_000)
        self.schedule_timer.timeout.connect(self._check_schedule)
        self.schedule_timer.start()

        self.login_poll_timer = QTimer(self)
        self.login_poll_timer.setInterval(3_000)
        self.login_poll_timer.timeout.connect(self._poll_login_state)

    def _load_stylesheet(self, dark: bool = False) -> None:
        filename = "style_dark.qss" if dark else "style.qss"
        qss_path = self.base_dir / "resources" / filename
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        self.dark_mode = dark

    def _login_accounts(self) -> list[Dict[str, Any]]:
        return ensure_login_accounts(self.state, self.data_dir)

    def _selected_login_account(self) -> Dict[str, Any] | None:
        accounts = self._login_accounts()
        selected = self.login_accounts_table.selectionModel().selectedRows() if hasattr(self, "login_accounts_table") else []
        if selected:
            row = selected[0].row()
            if 0 <= row < len(accounts):
                return accounts[row]
        return accounts[0] if accounts else None

    def _find_login_account(self, account_id: str) -> Dict[str, Any] | None:
        for account in self._login_accounts():
            if str(account.get("id") or "") == str(account_id):
                return account
        return None

    def _refresh_login_accounts_table(self) -> None:
        if not hasattr(self, "login_accounts_table"):
            return
        accounts = self._login_accounts()
        self.login_accounts_table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            values = [
                "是" if account.get("enabled", True) else "否",
                str(account.get("displayName") or ""),
                str(account.get("loginHint") or account.get("lastKnownLoginAccount") or ""),
                str(account.get("chromePort") or ""),
                str(account.get("loginStatus") or "待验证"),
                str(account.get("lastCaptureAt") or "--"),
                str(account.get("lastResult") or account.get("lastError") or "--"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.login_accounts_table.setItem(row, column, item)
            action_cell = QWidget()
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(6, 0, 6, 0)
            action_layout.setSpacing(6)
            login_button = QPushButton("登录")
            capture_button = QPushButton("采集")
            delete_button = QPushButton("删除")
            login_button.setObjectName("inlineActionButton")
            capture_button.setObjectName("inlineActionButton")
            delete_button.setObjectName("inlineDangerButton")
            for button in (login_button, capture_button, delete_button):
                button.setMinimumWidth(48)
                button.setMaximumWidth(48)
            account_id = str(account.get("id") or "")
            login_button.clicked.connect(lambda _checked=False, value=account_id: self.open_login_dialog(value))
            capture_button.clicked.connect(lambda _checked=False, value=account_id: self.start_selected_account_capture(value))
            delete_button.clicked.connect(lambda _checked=False, value=account_id: self._delete_login_account(value))
            action_layout.addWidget(login_button)
            action_layout.addWidget(capture_button)
            action_layout.addWidget(delete_button)
            self.login_accounts_table.setCellWidget(row, 7, action_cell)
        self.login_accounts_table.resizeRowsToContents()

    def _account_dialog(self, title: str, account: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        display_input = QLineEdit(str((account or {}).get("displayName") or ""))
        display_input.setPlaceholderText("例如：张三")
        hint_input = QLineEdit(str((account or {}).get("loginHint") or ""))
        hint_input.setPlaceholderText("可选，用于备注淘宝登录识别名")
        profile_input = QLineEdit(str((account or {}).get("profileDir") or ""))
        port_input = QLineEdit(str((account or {}).get("chromePort") or ""))
        enabled_input = QCheckBox("启用该账号参与一键采集")
        enabled_input.setChecked(bool((account or {}).get("enabled", True)))

        form.addRow("账户备注", display_input)
        form.addRow("登录识别名", hint_input)
        form.addRow("影子目录", profile_input)
        form.addRow("调试端口", port_input)
        form.addRow("", enabled_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            port = int(port_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "端口无效", "调试端口必须是数字。")
            return None
        display_name = display_input.text().strip()
        if not display_name:
            QMessageBox.warning(self, "账户备注必填", "请填写账户备注，方便区分多个登录账户。")
            return None
        return {
            "displayName": display_name,
            "loginHint": hint_input.text().strip(),
            "profileDir": profile_input.text().strip(),
            "chromePort": port,
            "enabled": enabled_input.isChecked(),
        }

    def _add_login_account(self) -> None:
        account = add_login_account(self.state, self.data_dir, display_name="新登录账户")
        edited = self._account_dialog("新增登录账户", account)
        if edited is None:
            self._login_accounts().remove(account)
            self._refresh_login_accounts_table()
            return
        account.update(edited)
        self._save_state()
        self._refresh_login_accounts_table()

    def _edit_selected_login_account(self) -> None:
        account = self._selected_login_account()
        if account is None:
            QMessageBox.information(self, "未选择账户", "请先选择一个登录账户。")
            return
        edited = self._account_dialog("编辑登录账户", account)
        if edited is None:
            return
        account.update(edited)
        self._save_state()
        self._refresh_login_accounts_table()

    def _delete_selected_login_account(self) -> None:
        account = self._selected_login_account()
        if account is None:
            QMessageBox.information(self, "未选择账户", "请先选择一个登录账户。")
            return
        self._delete_login_account(str(account.get("id") or ""))

    def _delete_login_account(self, account_id: str) -> None:
        account = self._find_login_account(account_id)
        if account is None:
            return
        answer = QMessageBox.question(
            self,
            "删除登录账户",
            f"确定删除登录账户“{account.get('displayName') or account_id}”吗？这不会删除服务端数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        profile_dir = str(account.get("profileDir") or "")
        self.state["loginAccounts"] = [item for item in self._login_accounts() if str(item.get("id") or "") != account_id]
        cleanup = QMessageBox.question(
            self,
            "清理本地登录档案",
            "是否同时删除该账号的本地影子 Chrome 档案目录？删除后该账号需要重新扫码登录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if cleanup == QMessageBox.StandardButton.Yes:
            self._delete_profile_dir_if_safe(profile_dir)
        self._save_state()
        self._refresh_login_accounts_table()

    def _delete_profile_dir_if_safe(self, profile_dir: str) -> None:
        if not profile_dir:
            return
        target = Path(profile_dir).resolve()
        allowed_root = (self.data_dir / "profiles").resolve()
        try:
            target.relative_to(allowed_root)
        except ValueError:
            self._log(f"跳过删除影子目录：{target} 不在本程序 profiles 目录下。")
            return
        if not target.exists():
            return
        cleanup_thread = QThread(self)
        cleanup_worker = CleanupWorker(target)
        cleanup_worker.moveToThread(cleanup_thread)
        cleanup_thread.started.connect(cleanup_worker.run)
        cleanup_worker.log_message.connect(self._log)
        cleanup_worker.finished.connect(cleanup_thread.quit)
        cleanup_worker.finished.connect(cleanup_worker.deleteLater)
        cleanup_thread.finished.connect(cleanup_thread.deleteLater)
        cleanup_thread.start()

    def _build_tray(self) -> None:
        self.normal_tray_icon = self.windowIcon() if not self.windowIcon().isNull() else self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.alert_tray_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.normal_tray_icon)

        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self._restore_from_tray)
        login_action = tray_menu.addAction("重新登录")
        login_action.triggered.connect(self.open_login_dialog)
        crawl_action = tray_menu.addAction("采集全部启用账号")
        crawl_action.triggered.connect(lambda: self.start_capture(manual=True, reason="托盘手动采集"))
        exit_action = tray_menu.addAction("退出程序")
        exit_action.triggered.connect(self._exit_from_tray)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._handle_tray_activated)
        self.tray.messageClicked.connect(self._handle_tray_message_clicked)
        self.tray.show()

    def _bind_events(self) -> None:
        self.login_button.clicked.connect(self.open_login_dialog)
        self.manual_crawl_button.clicked.connect(lambda: self.start_capture(manual=True, reason="手动采集"))
        self.add_account_button.clicked.connect(self._add_login_account)
        self.edit_account_button.clicked.connect(self._edit_selected_login_account)
        self.delete_account_button.clicked.connect(self._delete_selected_login_account)
        self.login_selected_button.clicked.connect(self.open_login_dialog)
        self.capture_selected_button.clicked.connect(self.start_selected_account_capture)
        self.hide_button.clicked.connect(self._hide_to_tray)
        self.schedule_checkbox.toggled.connect(self._persist_settings)
        self.schedule_time.timeChanged.connect(self._persist_settings)
        self.server_url_input.textChanged.connect(self._persist_settings)
        self.auto_start_checkbox.toggled.connect(self._sync_autostart_setting)
        self.shadow_launch_checkbox.toggled.connect(self._persist_settings)
        self.exit_confirm_checkbox.toggled.connect(self._persist_settings)

    def _initialize_runtime(self) -> None:
        self._sync_autostart_setting(announce=False)
        self._persist_settings()
        if self.cookie_security_migration_message:
            self._log(self.cookie_security_migration_message)
            if self.cookie_security_migration_message.startswith("Cookie 安全迁移失败"):
                self._set_status("Cookie 迁移失败", danger=True)
        if bool(self.state.get("loginAccounts")):
            self._set_status("待命")
            self.hint_label.setText("可一键采集全部启用账号；未登录账号会标记为需要登录并继续采集其他账号。")
            self._log("已启用本机多登录账户采集，接口直采暂不作为多账号主路径。")
            self._refresh_login_accounts_table()
            return
        if bool(self.state.get("directApiPreferred", True)) and not self.shadow_launch_checkbox.isChecked():
            self._log("接口直采模式已启用，启动时不拉起影子浏览器。")
            self._apply_login_state(False)
            return

        self._log("正在初始化影子浏览器运行环境。")
        if self.shadow_launch_checkbox.isChecked():
            try:
                session = ensure_shadow_browser(self.state, self._log)
                self._remember_shadow_session(session.chrome_path, session.profile_dir, session.pid)
                self._log("影子浏览器已就绪，程序将接管该实例。")
            except ShadowBrowserError as exc:
                self._remember_shadow_session(self.state.get("chromePath") or "", self._shadow_profile_dir(), self.state.get("shadowChromePid") or 0)
                self._set_status("浏览器未就绪", danger=True)
                self._set_alert_mode(True)
                self._log(str(exc))
        self._check_login_state(announce=False)

    def _migrate_direct_api_cookie_config(self) -> str:
        config_path = Path(str(self.state.get("directApiConfigPath") or self.data_dir / "direct_api_capture.json"))
        try:
            migrated = migrate_direct_api_cookie_config(config_path)
        except DirectApiCaptureError as exc:
            return f"Cookie 安全迁移失败：{exc}。请点击“重新登录”刷新 Cookie。"
        if migrated:
            return "接口 Cookie 已迁移为本机加密存储。"
        return ""

    def _apply_state_to_ui(self) -> None:
        schedule_str = self.state.get("scheduleTime", "09:00")
        schedule_time = QTime.fromString(schedule_str, "HH:mm")
        self.schedule_time.setTime(schedule_time if schedule_time.isValid() else QTime(9, 0))
        self.server_url_input.setText(str(self.state.get("serverUrl") or DEFAULT_SERVER_URL))
        self.schedule_checkbox.setChecked(bool(self.state.get("scheduleEnabled", True)))
        self.auto_start_checkbox.setChecked(bool(self.state.get("autoStartEnabled", True) or is_autostart_enabled(APP_NAME)))
        self.shadow_launch_checkbox.setChecked(bool(self.state.get("shadowChromeAutoLaunch", False)))
        self.exit_confirm_checkbox.setChecked(bool(self.state.get("exitRequiresConfirm", True)))
        self._set_account_text(self.state.get("lastKnownLoginAccount") or "")
        summary = self.state.get("lastPayloadSummary") or "尚未采集"
        self._set_info_text(self.result_summary_label, summary)
        self._set_info_text(self.chrome_path_label, str(self.state.get("chromePath") or "待检测"))
        self._set_info_text(self.shadow_dir_label, str(self._shadow_profile_dir()))
        self._refresh_login_accounts_table()
        self._refresh_schedule_hint()

    def _shadow_profile_dir(self) -> str:
        return str(self.state.get("shadowChromeProfileDir") or self.state.get("chromeUserDataDir") or default_shadow_profile_dir())

    def _persist_settings(self, *_args: object) -> None:
        self.state["captureEngine"] = "external"
        self.state["scheduleEnabled"] = self.schedule_checkbox.isChecked()
        self.state["scheduleTime"] = self.schedule_time.time().toString("HH:mm")
        self.state["serverUrl"] = self.server_url_input.text().strip()
        self.state["autoStartEnabled"] = self.auto_start_checkbox.isChecked()
        self.state["shadowChromeAutoLaunch"] = self.shadow_launch_checkbox.isChecked()
        self.state["exitRequiresConfirm"] = self.exit_confirm_checkbox.isChecked()
        self.state["shadowChromeStartupUrl"] = EMPLOYEE_TARGET_URL
        self.state["closeToTray"] = True
        if not str(self.state.get("shadowChromeProfileDir") or "").strip():
            self.state["shadowChromeProfileDir"] = str(default_shadow_profile_dir())
        self.state["chromeUserDataDir"] = self.state["shadowChromeProfileDir"]
        self._save_state()
        self._refresh_schedule_hint()

    def _sync_autostart_setting(self, *_args: object, announce: bool = True) -> None:
        self.state["autoStartEnabled"] = self.auto_start_checkbox.isChecked()
        try:
            ensure_autostart(self.auto_start_checkbox.isChecked(), app_name=APP_NAME, base_dir=self.base_dir)
        except Exception as exc:
            self._set_status("自启配置失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"更新开机自启失败：{exc}")
        else:
            if announce:
                state_text = "已开启" if self.auto_start_checkbox.isChecked() else "已关闭"
                self._log(f"登录后自启{state_text}。")
        self._save_state()

    def _check_login_state(self, announce: bool) -> None:
        if bool(self.state.get("directApiPreferred", True)) and not self.shadow_launch_checkbox.isChecked():
            self.logged_in = False
            self._apply_direct_api_cookie_state("待验证", hint="接口 Cookie 可用时可以立即采集；Cookie 过期时请点击“重新登录”刷新。")
            if announce:
                self._log("接口直采模式不自动检查影子浏览器登录态。")
            return

        try:
            state = inspect_external_page_state(
                self.state,
                self._log if announce else (lambda _message: None),
                ensure_browser=self.shadow_launch_checkbox.isChecked(),
            )
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            self.logged_in = False
            self._apply_login_state(False)
            self._set_status("浏览器未就绪", danger=True)
            self._set_alert_mode(True)
            if announce:
                self._log(str(exc))
            return

        self._remember_shadow_session(
            state.get("chromePath") or self.state.get("chromePath") or "",
            state.get("shadowChromeProfileDir") or self._shadow_profile_dir(),
            state.get("shadowChromePid") or 0,
        )
        if state.get("loggedIn"):
            self.logged_in = True
            self.pending_login_recovery = False
            self._remember_login_account(state.get("currentNick") or "")
            self._apply_login_state(True)
            self._set_alert_mode(False)
            if announce:
                self._log("影子浏览器登录态有效，可直接采集。")
            return

        was_logged_in = self.logged_in
        self.logged_in = False
        self._apply_login_state(False)
        if was_logged_in:
            self._handle_login_expired("检测到千牛登录已过期，请重新扫码。")
        elif announce:
            self._log("当前影子浏览器未登录千牛，请点击“重新登录”。")

    def _open_employee_target_page(self, session: Any, failure_prefix: str) -> bool:
        try:
            session.page.get(EMPLOYEE_TARGET_URL)
        except Exception as exc:
            self._log(f"{failure_prefix}：{exc}")
            return False
        return True

    def open_login_dialog(self, account_id: str = "") -> None:
        account = self._find_login_account(account_id) if account_id else self._selected_login_account()
        if account is not None:
            return self._open_login_dialog_for_account(account)

        try:
            session = show_shadow_browser_for_login(self.state, self._log)
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            self._set_status("浏览器未就绪", danger=True)
            self._set_alert_mode(True)
            self._log(str(exc))
            return

        self._remember_shadow_session(session.chrome_path, session.profile_dir, session.pid)
        self.pending_login_recovery = True
        if bool(self.state.get("directApiPreferred", True)):
            self._apply_direct_api_cookie_state("等待刷新", hint="请在影子 Chrome 中确认千牛已登录，程序会自动读取新 Cookie。")
        else:
            self._set_status("等待登录")
        self._set_alert_mode(True)
        if self._open_employee_target_page(session, "打开绩效考核页面失败"):
            self._log("已打开影子浏览器绩效考核页，请在该窗口完成千牛扫码登录。")
        self._log("已打开影子浏览器，请在浏览器窗口完成千牛扫码登录。")
        if not self.login_poll_timer.isActive():
            self.login_poll_timer.start()

    def _open_login_dialog_for_account(self, account: Dict[str, Any]) -> None:
        account_state = build_account_state(self.state, account)
        display_name = str(account.get("displayName") or account.get("id") or "").strip()
        try:
            session = show_shadow_browser_for_login(account_state, self._log)
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            account["loginStatus"] = "浏览器未就绪"
            account["lastError"] = str(exc)
            self._refresh_login_accounts_table()
            self._set_status("浏览器未就绪", danger=True)
            self._set_alert_mode(True)
            self._log(str(exc))
            self._save_state()
            return

        account["loginStatus"] = "等待登录"
        self.pending_login_account_id = str(account.get("id") or "")
        self.pending_login_recovery = True
        self._remember_shadow_session(session.chrome_path, session.profile_dir, session.pid)
        self._set_status("等待登录")
        self._set_alert_mode(True)
        self._refresh_login_accounts_table()
        if self._open_employee_target_page(session, "打开绩效考核页面失败"):
            self._log(f"已打开“{display_name or '--'}”的独立影子浏览器，请在该窗口完成千牛扫码登录。")
        if not self.login_poll_timer.isActive():
            self.login_poll_timer.start()

    def _poll_login_state(self) -> None:
        if self.pending_login_account_id:
            self._poll_login_account_state()
            return

        if bool(self.state.get("directApiPreferred", True)):
            if not self.pending_login_recovery:
                self.login_poll_timer.stop()
                return
            try:
                state = inspect_existing_shadow_browser_state(self.state, lambda _message: None)
                self._poll_error_count = 0
            except ShadowBrowserError as exc:
                self.login_poll_timer.stop()
                self.pending_login_recovery = False
                self._set_status("等待登录中断", danger=True)
                self._set_alert_mode(True)
                self._log(f"登录窗口连接已断开：{exc}")
                return
            except Exception:
                self._poll_error_count = getattr(self, "_poll_error_count", 0) + 1
                if self._poll_error_count >= 10:
                    self.login_poll_timer.stop()
                    self._log("登录状态轮询连续异常过多，已自动停止轮询，请手动点击重新登录。")
                    self._poll_error_count = 0
                return

            self._remember_shadow_session(
                state.get("chromePath") or self.state.get("chromePath") or "",
                state.get("shadowChromeProfileDir") or self._shadow_profile_dir(),
                state.get("shadowChromePid") or 0,
            )
            cookie_header = str(state.get("cookieHeader") or "").strip()
            if (not state.get("loggedIn") and not cookie_has_direct_api_markers(cookie_header)) or not cookie_header:
                return

            if self._refresh_direct_api_cookie_from_shadow_state(state):
                self.login_poll_timer.stop()
            return

        try:
            state = inspect_external_page_state(self.state, lambda _message: None, ensure_browser=False)
            self._poll_error_count = 0
        except ShadowBrowserError:
            return
        except Exception as exc:
            self.login_poll_timer.stop()
            self._log(f"登录状态轮询异常，已停止：{exc}")
            return

        self._remember_shadow_session(
            state.get("chromePath") or self.state.get("chromePath") or "",
            state.get("shadowChromeProfileDir") or self._shadow_profile_dir(),
            state.get("shadowChromePid") or 0,
        )
        if not state.get("loggedIn"):
            return

        self.login_poll_timer.stop()
        self.logged_in = True
        self.pending_login_recovery = False
        self._remember_login_account(state.get("currentNick") or "")
        self._apply_login_state(True)
        self._set_alert_mode(False)
        self._log("千牛登录成功，影子浏览器将保持可见，可以点击“立即采集”。")

    def _poll_login_account_state(self) -> None:
        account = self._find_login_account(self.pending_login_account_id)
        if account is None:
            self.pending_login_account_id = ""
            self.pending_login_recovery = False
            self.login_poll_timer.stop()
            return
        try:
            state = inspect_existing_shadow_browser_state(build_account_state(self.state, account), lambda _message: None)
        except ShadowBrowserError as exc:
            self.login_poll_timer.stop()
            self.pending_login_account_id = ""
            self.pending_login_recovery = False
            account["loginStatus"] = "登录中断"
            account["lastError"] = str(exc)
            self._set_status("等待登录中断", danger=True)
            self._set_alert_mode(True)
            self._log(f"登录窗口连接已断开：{exc}")
            self._save_state()
            self._refresh_login_accounts_table()
            return
        except Exception:
            return

        cookie_header = str(state.get("cookieHeader") or "").strip()
        if not state.get("loggedIn") and not cookie_has_direct_api_markers(cookie_header):
            return

        self.login_poll_timer.stop()
        self.pending_login_account_id = ""
        self.pending_login_recovery = False
        account["loginStatus"] = "已登录"
        account["lastError"] = ""
        current_account = str(state.get("currentNick") or "").strip()
        if current_account:
            account["lastKnownLoginAccount"] = current_account
            if not str(account.get("loginHint") or "").strip():
                account["loginHint"] = current_account
            self._remember_login_account(current_account)
        self._remember_shadow_session(
            state.get("chromePath") or self.state.get("chromePath") or "",
            state.get("shadowChromeProfileDir") or str(account.get("profileDir") or ""),
            state.get("shadowChromePid") or 0,
        )
        self._set_status("已登录")
        self._set_alert_mode(False)
        self._save_state()
        self._refresh_login_accounts_table()
        self._log(f"登录账户“{account.get('displayName') or account.get('id')}”已登录，可以采集。")

    def _refresh_direct_api_cookie_from_shadow_state(self, state: Dict[str, Any]) -> bool:
        cookie_header = str(state.get("cookieHeader") or "").strip()
        if not cookie_header or not cookie_has_direct_api_markers(cookie_header):
            return False

        config_path = Path(str(self.state.get("directApiConfigPath") or self.data_dir / "direct_api_capture.json"))
        try:
            update_direct_api_cookie(config_path, cookie_header)
        except DirectApiCaptureError as exc:
            self.pending_login_recovery = False
            self._set_status("Cookie 更新失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"刷新接口 Cookie 失败：{exc}")
            return False

        self.pending_login_recovery = False
        self.logged_in = True
        self.state["directApiConfigPath"] = str(config_path)
        self._remember_login_account(state.get("currentNick") or self.state.get("lastKnownLoginAccount") or "")
        self._apply_direct_api_cookie_state("已刷新", hint="Cookie 已更新，可以点击“立即采集”。")
        self._set_alert_mode(False)
        self._save_state()
        self._log(f"已从影子浏览器刷新接口 Cookie：{format_cookie_diagnostics(cookie_header)}，可以点击“立即采集”。")
        return True

    def start_capture(self, manual: bool, reason: str, override_accounts: list | None = None) -> None:
        if self.capture_in_progress:
            self._log("已有采集任务正在执行，跳过新的触发。")
            return

        self.manual_crawl_button.setEnabled(False)
        self.capture_selected_button.setEnabled(False)
        self.login_button.setEnabled(False)
        self.login_selected_button.setEnabled(False)

        has_login_accounts = bool(override_accounts) if override_accounts is not None else bool(self.state.get("loginAccounts"))
        direct_api_preferred = bool(self.state.get("directApiPreferred", True)) and not has_login_accounts
        if not has_login_accounts and not self.logged_in and not direct_api_preferred:
            self._check_login_state(announce=False)
            if not self.logged_in:
                self._restore_capture_buttons()
                self._set_status("请先登录", danger=True)
                self._log("当前未登录千牛，请先点击“重新登录”。")
                return

        self._persist_settings()
        self._begin_capture_ui(reason)
        self._set_alert_mode(False)
        if has_login_accounts:
            self._log(f"开始{reason}，将按登录账户列表顺序采集全部启用账号。")
        elif direct_api_preferred:
            self._log(f"开始{reason}，当前优先使用接口直采；失败后回退到影子浏览器表格采集。")
        else:
            self._log(f"开始{reason}，当前使用外置影子浏览器采集。")

        state_snapshot = json.loads(json.dumps(self.state, ensure_ascii=False))
        if override_accounts is not None:
            state_snapshot["loginAccounts"] = override_accounts
        self.capture_thread = QThread(self)
        self.capture_worker = CaptureWorker(state_snapshot, reason)
        self.capture_worker.moveToThread(self.capture_thread)
        self.capture_thread.started.connect(self.capture_worker.run)
        self.capture_worker.log_message.connect(self._log)
        self.capture_worker.finished.connect(self._handle_capture_worker_finished)
        self.capture_worker.finished.connect(self.capture_thread.quit)
        self.capture_worker.finished.connect(self.capture_worker.deleteLater)
        self.capture_thread.finished.connect(self.capture_thread.deleteLater)
        self.capture_thread.finished.connect(self._clear_capture_worker_refs)
        self.capture_thread.start()

    def start_selected_account_capture(self, account_id: str = "") -> None:
        account = self._find_login_account(account_id) if account_id else self._selected_login_account()
        if account is None:
            QMessageBox.information(self, "未选择账户", "请先选择一个登录账户。")
            return
        self.start_capture(manual=True, reason=f"采集账号：{account.get('displayName') or account.get('id')}", override_accounts=[dict(account)])

    def _begin_capture_ui(self, reason: str) -> None:
        self.capture_in_progress = True
        self.capture_reason = reason
        self._set_status("采集中...")
        self.manual_crawl_button.setEnabled(False)
        self.manual_crawl_button.setText("采集中...")
        self.login_button.setEnabled(False)
        self.capture_selected_button.setEnabled(False)
        self.login_selected_button.setEnabled(False)
        self.capture_progress.show()
        if bool(self.state.get("loginAccounts")):
            self.hint_label.setText("正在按登录账户列表顺序采集并上传数据，请不要关闭正在使用的影子浏览器窗口。")
        elif bool(self.state.get("directApiPreferred", True)):
            self.hint_label.setText("正在通过接口直采并上传数据；Cookie 过期时会提示重新登录。")
        else:
            self.hint_label.setText("正在接管影子浏览器采集并上传数据，请不要关闭影子浏览器窗口。")

    def _end_capture_ui(self) -> None:
        self.capture_in_progress = False
        self.manual_crawl_button.setEnabled(True)
        self.manual_crawl_button.setText("采集全部启用账号")
        self.login_button.setEnabled(True)
        self.capture_selected_button.setEnabled(True)
        self.login_selected_button.setEnabled(True)
        self.capture_progress.hide()
        if bool(self.state.get("loginAccounts")):
            self.hint_label.setText("可一键采集全部启用账号；未登录账号会标记为需要登录并继续采集其他账号。")
        elif bool(self.state.get("directApiPreferred", True)):
            self.hint_label.setText("接口 Cookie 可用时可以立即采集；Cookie 过期时请点击“重新登录”刷新。")
        elif self.logged_in:
            self.hint_label.setText("影子浏览器登录态有效，可以立即采集，也会按计划自动采集。")
        else:
            self.hint_label.setText("当前未检测到有效千牛登录态，请点击“重新登录”打开影子浏览器扫码。")

    def _restore_capture_buttons(self) -> None:
        self.manual_crawl_button.setEnabled(True)
        self.manual_crawl_button.setText("采集全部启用账号")
        self.login_button.setEnabled(True)
        self.capture_selected_button.setEnabled(True)
        self.login_selected_button.setEnabled(True)

    def _clear_capture_worker_refs(self) -> None:
        self.capture_thread = None
        self.capture_worker = None

    def _handle_capture_worker_finished(self, result: object) -> None:
        if not isinstance(result, dict):
            self._set_status("采集失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"{self.capture_reason}失败：后台采集线程返回了无效结果。")
            self._finish_capture(None, aborted=True)
            return

        reason = str(result.get("reason") or self.capture_reason)
        if result.get("batch"):
            self._finish_batch_capture(result.get("results") if isinstance(result.get("results"), list) else [])
            return

        if not result.get("ok"):
            message = str(result.get("message") or "未知错误")
            error_type = str(result.get("errorType") or "generic")
            if error_type == "login_required":
                self._handle_login_expired(f"{reason}失败：{message}")
                self._finish_capture(None, aborted=True)
                return
            elif error_type == "browser":
                self._set_status("浏览器未就绪", danger=True)
                self._set_alert_mode(True)
                self._log(f"{reason}失败：{message}")
            else:
                self._set_status("采集失败", danger=True)
                self._set_alert_mode(True)
                self._log(f"{reason}失败：{message}")
            self._finish_capture(None, aborted=True)
            return

        self._finish_capture(
            result.get("payload") if isinstance(result.get("payload"), dict) else None,
            aborted=False,
            signature=str(result.get("signature") or ""),
            upload_message=str(result.get("uploadMessage") or ""),
            upload_record=result.get("uploadRecord") if isinstance(result.get("uploadRecord"), dict) else None,
        )

    def _finish_batch_capture(self, results: list[Dict[str, Any]]) -> None:
        self._end_capture_ui()
        accounts_by_id = {str(item.get("id") or ""): item for item in self._login_accounts()}
        success_results = [item for item in results if isinstance(item, dict) and item.get("ok")]
        upload_success = False

        for item in results:
            if not isinstance(item, dict):
                continue
            account = accounts_by_id.get(str(item.get("accountId") or ""))
            if account is not None:
                for key in ("loginStatus", "lastCaptureAt", "lastResult", "lastError", "lastKnownLoginAccount", "lastUploadAt"):
                    if key in item:
                        account[key] = item.get(key) or ""
            upload_record = item.get("uploadRecord")
            signature = str(item.get("signature") or "")
            if signature and isinstance(upload_record, dict):
                self._add_upload_record(signature, upload_record)
                upload_success = True

        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_text = datetime.now().strftime("%Y-%m-%d")
        self.state["lastRunAt"] = now_text
        self.state["lastCaptureAt"] = now_text
        self.state["lastCaptureDate"] = today_text
        if upload_success:
            self.state["lastRunDate"] = today_text
            self.state["lastUploadDate"] = today_text
            self.state["lastUploadAt"] = now_text

        if success_results:
            last_success = success_results[-1]
            summary = str(last_success.get("summary") or "")
            signature = str(last_success.get("signature") or "")
            if summary:
                self.state["lastPayloadSummary"] = summary
                self._set_info_text(self.result_summary_label, summary)
            if signature:
                self.state["lastPayloadSignature"] = signature
            payload = last_success.get("payload")
            if isinstance(payload, dict):
                self._remember_login_account(payload.get("loginAccount") or payload.get("subAccount") or "")
            self._set_status("待命")
            self._set_alert_mode(False)
        else:
            self._set_status("采集失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"{self.capture_reason}没有成功采集任何账号。")

        failed_count = len(results) - len(success_results)
        self._log(f"{self.capture_reason}结束：成功 {len(success_results)} 个，失败 {failed_count} 个。")
        self._save_state()
        self._refresh_login_accounts_table()
        self._refresh_schedule_hint()

    def _finish_capture(
        self,
        payload: Dict[str, Any] | None,
        aborted: bool,
        signature: str = "",
        upload_message: str = "",
        upload_record: Dict[str, Any] | None = None,
    ) -> None:
        self._end_capture_ui()
        if aborted:
            self._log(f"{self.capture_reason}结束。")
            return
        if not payload:
            self._set_status("采集失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"{self.capture_reason}失败：本次没有拿到任何员工绩效数据。")
            self._log(f"{self.capture_reason}结束。")
            return

        current_signature = signature or payload_signature(payload)
        previous_signature = self.state.get("lastPayloadSignature", "")
        summary = format_employee_summary(payload)

        if current_signature == previous_signature and self.capture_reason != "手动采集":
            self._log("本次数据与上次一致，已完成本地校验。")
        else:
            self._log(f"采集成功：{summary}")

        if upload_message:
            self._log(upload_message)
        if upload_record is not None:
            self._add_upload_record(current_signature, upload_record)

        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_text = datetime.now().strftime("%Y-%m-%d")
        self.state["lastRunAt"] = now_text
        self.state["lastCaptureAt"] = now_text
        self.state["lastCaptureDate"] = today_text
        if upload_record is not None:
            self.state["lastRunDate"] = today_text
            self.state["lastUploadDate"] = today_text
            self.state["lastUploadAt"] = now_text
        self.state["lastPayloadSignature"] = current_signature
        self.state["lastPayloadSummary"] = summary
        self._remember_login_account(payload.get("loginAccount") or payload.get("subAccount") or "")
        self._set_info_text(self.result_summary_label, summary)
        self._set_status("待命")
        self._save_state()
        self._refresh_schedule_hint()
        self._log(f"{self.capture_reason}结束。")

    def _upload_payload(self, payload: Dict[str, Any], signature: str) -> str:
        upload_message, upload_record = _upload_payload_with_state(self.state, payload, signature, self.capture_reason)
        if upload_record is not None:
            self._add_upload_record(signature, upload_record)
        return upload_message

    def _check_schedule(self) -> None:
        if self.capture_in_progress or not self.schedule_checkbox.isChecked():
            return
        if not bool(self.state.get("loginAccounts")) and not self.logged_in and not bool(self.state.get("directApiPreferred", True)):
            return
        now = datetime.now()
        schedule_str = self.schedule_time.time().toString("HH:mm")
        today = now.strftime("%Y-%m-%d")
        if self.state.get("lastRunDate") == today:
            return
        if now.strftime("%H:%M") >= schedule_str:
            self.start_capture(manual=False, reason="每日自动采集")

    def _refresh_schedule_hint(self) -> None:
        schedule_str = self.schedule_time.time().toString("HH:mm")
        enabled = self.schedule_checkbox.isChecked()
        self.next_run_label.setText(f"下次计划：{'每日 ' + schedule_str if enabled else '已关闭'}")
        self.last_run_label.setText(f"最近执行：{self.state.get('lastRunAt') or '--'}")

    def _remember_shadow_session(self, chrome_path: str, profile_dir: str, pid: int | None) -> None:
        if chrome_path:
            self.state["chromePath"] = chrome_path
        if profile_dir:
            self.state["shadowChromeProfileDir"] = profile_dir
            self.state["chromeUserDataDir"] = profile_dir
        if pid:
            self.state["shadowChromePid"] = pid
        self._set_info_text(self.chrome_path_label, str(self.state.get("chromePath") or "待检测"))
        self._set_info_text(self.shadow_dir_label, str(self._shadow_profile_dir()))
        self._save_state()

    def _remember_login_account(self, account: str) -> None:
        clean_account = str(account or "").strip()
        if not clean_account:
            return
        self.state["lastKnownLoginAccount"] = clean_account
        self._set_account_text(clean_account)
        self._save_state()

    def _set_account_text(self, account: str) -> None:
        clean_account = str(account or "").strip()
        self._set_info_text(self.account_label, clean_account or "--")

    def _apply_direct_api_cookie_state(self, status: str, danger: bool = False, hint: str = "") -> None:
        self._set_info_text(self.login_state_label, direct_api_cookie_state_label(status))
        self.login_button.setText("重新登录")
        self.hint_label.setText(hint or "接口 Cookie 可用时可以立即采集；Cookie 过期时请点击“重新登录”刷新。")
        self._set_status(f"Cookie {status}", danger=danger)

    def _apply_login_state(self, logged_in: bool) -> None:
        if bool(self.state.get("directApiPreferred", True)):
            if logged_in:
                self._apply_direct_api_cookie_state("已刷新", hint="Cookie 已更新，可以点击“立即采集”。")
            else:
                self._apply_direct_api_cookie_state("待验证", hint="接口 Cookie 可用时可以立即采集；Cookie 过期时请点击“重新登录”刷新。")
            return
        if logged_in:
            self._set_info_text(self.login_state_label, "已登录")
            self.hint_label.setText("影子浏览器登录态有效，可以立即采集，也会按计划自动采集。")
            self.login_button.setText("重新登录")
            self._set_status("已登录")
            return
        self._set_info_text(self.login_state_label, "请先登录")
        self.hint_label.setText("当前未检测到有效千牛登录态，请点击“重新登录”打开影子浏览器扫码。")
        self.login_button.setText("重新登录")
        self._set_status("请先登录", danger=True)

    def _handle_login_expired(self, message: str) -> None:
        self.login_poll_timer.stop()
        self.logged_in = False
        self.pending_login_recovery = False
        if bool(self.state.get("directApiPreferred", True)):
            self._apply_direct_api_cookie_state(
                "已过期，请点击重新登录",
                danger=True,
                hint="接口 Cookie 已过期，请点击“重新登录”刷新 Cookie。",
            )
        else:
            self._apply_login_state(False)
        self._set_alert_mode(True)
        self._log(message)
        self.tray.showMessage(
            APP_NAME,
            "接口 Cookie 已过期，请在主窗口手动点击“重新登录”。",
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )

    def _set_status(self, text: str, danger: bool = False) -> None:
        self.status_pill.setText(text)
        new_name = "statusPillDanger" if danger else "statusPill"
        if self.status_pill.objectName() != new_name:
            self.status_pill.setObjectName(new_name)
            self.status_pill.style().unpolish(self.status_pill)
            self.status_pill.style().polish(self.status_pill)

    def _set_alert_mode(self, active: bool) -> None:
        self.tray.setIcon(self.alert_tray_icon if active else self.normal_tray_icon)

    def _log(self, message: str) -> None:
        if message == self._last_log_message:
            return
        self._last_log_message = message
        now = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{now}] {message}")

    def _hide_to_tray(self) -> None:
        self.hide()
        self.tray.showMessage(APP_NAME, "程序已缩到托盘，将继续在后台运行。", QSystemTrayIcon.MessageIcon.Information, 3000)

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _handle_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._restore_from_tray()

    def _handle_tray_message_clicked(self) -> None:
        self._restore_from_tray()

    def _exit_from_tray(self) -> None:
        if self.capture_in_progress:
            QMessageBox.information(self, "正在采集", "当前采集任务正在执行，请等待采集结束后再退出程序。")
            return
        if self.exit_confirm_checkbox.isChecked():
            answer = QMessageBox.question(
                self,
                "退出程序",
                "确认退出后会同时停止后台采集和影子浏览器。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.exit_requested = True
        self.login_poll_timer.stop()
        try:
            killed = 0
            if self.state.get("loginAccounts"):
                for account in self._login_accounts():
                    try:
                        killed += shutdown_shadow_browser(build_account_state(self.state, account), self._log)
                    except ShadowBrowserError as exc:
                        self._log(f"停止账号“{account.get('displayName') or account.get('id')}”影子浏览器时出现异常：{exc}")
            else:
                killed = shutdown_shadow_browser(self.state, self._log)
            if killed:
                self._log("已停止影子浏览器。")
        except ShadowBrowserError as exc:
            self._log(f"停止影子浏览器时出现异常：{exc}")
        self.tray.hide()
        self.close()

    def handle_external_activation(self, _payload: str) -> None:
        self._restore_from_tray()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_settings()
        if not self.exit_requested:
            event.ignore()
            self._hide_to_tray()
            return
        super().closeEvent(event)

    def _add_upload_record(self, signature: str, upload_record: Dict[str, Any]) -> None:
        upload_history = self.state.setdefault("uploadHistory", {})
        if not isinstance(upload_history, dict):
            upload_history = {}
        upload_history[signature] = upload_record
        if len(upload_history) > 500:
            excess = len(upload_history) - 500
            for key in list(upload_history.keys())[:excess]:
                del upload_history[key]
        self.state["uploadHistory"] = upload_history

    def _save_state(self) -> None:
        self._write_json(self.state_path, self.state)

    def _migrate_state_defaults(self) -> None:
        server_url = str(self.state.get("serverUrl") or "").strip().rstrip("/")
        if not server_url:
            self.state["serverUrl"] = DEFAULT_SERVER_URL

        if self.state.get("loginAccounts"):
            self.state["directApiPreferred"] = False

        if bool(self.state.get("directApiPreferred", True)):
            self.state["shadowChromeAutoLaunch"] = False

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            backup = path.with_suffix(".json.bak")
            if backup.exists():
                try:
                    loaded = json.loads(backup.read_text(encoding="utf-8"))
                except Exception:
                    return dict(default)
            else:
                return dict(default)
        merged = dict(default)
        if isinstance(loaded, dict):
            merged.update(loaded)
        return merged

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
            tmp_path.replace(path)
            backup = path.with_suffix(".json.bak")
            try:
                backup.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
            except Exception:
                pass
        except Exception as exc:
            self._log(f"保存状态文件失败，请检查磁盘空间和权限：{exc}")
            self._set_status("保存失败", danger=True)
            self._set_alert_mode(True)


def run() -> int:
    app = QApplication([])
    icon_path = Path(__file__).resolve().parent / "resources" / "yuansheng_logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    instance_name = "YuanshengDataAssistantDesktop"
    instance_manager = SingleInstanceManager(instance_name, app)
    if not instance_manager.acquire():
        return 0

    window = YuanshengMainWindow(app_base_dir())
    instance_manager.set_activation_callback(window.handle_external_activation)
    app.instance_manager = instance_manager  # type: ignore[attr-defined]
    app.aboutToQuit.connect(lambda: instance_manager.lock.unlock())
    window.show()
    return app.exec()
