from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict

from PySide6.QtCore import QTime, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStyle,
    QSystemTrayIcon,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from external_capture import LoginRequiredError, capture_with_external_chrome, inspect_external_page_state
from shadow_browser import (
    ChromeNotFoundError,
    PortOccupiedError,
    ShadowBrowserError,
    default_shadow_profile_dir,
    ensure_shadow_browser,
    show_shadow_browser_for_login,
    shutdown_shadow_browser,
)
from single_instance import SingleInstanceManager
from spider_core import EMPLOYEE_TARGET_URL, format_employee_summary, payload_signature
from startup_manager import ensure_autostart, is_autostart_enabled

APP_NAME = "远盛数据助手"


def _default_state() -> Dict[str, Any]:
    shadow_dir = str(default_shadow_profile_dir())
    return {
        "captureEngine": "external",
        "chromePath": "",
        "chromePort": 9222,
        "chromeUserDataDir": shadow_dir,
        "shadowChromeProfileDir": shadow_dir,
        "lastKnownLoginAccount": "",
        "scheduleEnabled": True,
        "scheduleTime": "09:00",
        "lastRunDate": "",
        "lastRunAt": "",
        "lastPayloadSignature": "",
        "lastPayloadSummary": "",
        "closeToTray": True,
        "autoStartEnabled": True,
        "shadowChromeAutoLaunch": True,
        "exitRequiresConfirm": True,
        "shadowChromePid": 0,
    }


class YuanshengMainWindow(QMainWindow):
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.data_dir = self.base_dir / "data"
        self.state_path = self.data_dir / "app_state.json"
        self.icon_path = self.base_dir / "resources" / "yuansheng_logo.png"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.state = self._load_json(self.state_path, _default_state())
        self.logged_in = False
        self.capture_in_progress = False
        self.capture_reason = ""
        self.pending_login_recovery = False
        self.exit_requested = False
        self._last_log_message = ""

        self.setWindowTitle(APP_NAME)
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))
        self.resize(780, 720)

        self._build_ui()
        self._build_tray()
        self._bind_events()
        self._apply_state_to_ui()
        QTimer.singleShot(0, self._initialize_runtime)

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(16, 16, 16, 16)
        page.setSpacing(12)

        header = QFrame()
        header.setObjectName("card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("titleText")
        subtitle = QLabel("默认接管本机影子 Chrome，在后台采集当前登录客服员工本人的绩效数据")
        subtitle.setObjectName("mutedText")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        status_box = QVBoxLayout()
        status_box.setSpacing(4)
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

        control_card = QFrame()
        control_card.setObjectName("card")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(16, 14, 16, 14)
        control_layout.setSpacing(12)

        self.login_state_label = QLabel("登录状态：检查中")
        self.login_state_label.setObjectName("sectionTitle")
        self.account_label = QLabel("当前账号：--")
        self.account_label.setObjectName("mutedText")
        self.result_summary_label = QLabel("最近结果：尚未采集")
        self.result_summary_label.setObjectName("mutedText")
        self.chrome_path_label = QLabel("Chrome 路径：检测中")
        self.chrome_path_label.setObjectName("mutedText")
        self.shadow_dir_label = QLabel("影子目录：检测中")
        self.shadow_dir_label.setObjectName("mutedText")
        control_layout.addWidget(self.login_state_label)
        control_layout.addWidget(self.account_label)
        control_layout.addWidget(self.result_summary_label)
        control_layout.addWidget(self.chrome_path_label)
        control_layout.addWidget(self.shadow_dir_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.schedule_time = QTimeEdit()
        self.schedule_time.setDisplayFormat("HH:mm")
        self.schedule_checkbox = QCheckBox("启用每日自动采集")
        self.auto_start_checkbox = QCheckBox("登录 Windows 后自动启动")
        self.shadow_launch_checkbox = QCheckBox("启动主程序时自动拉起影子浏览器")
        self.exit_confirm_checkbox = QCheckBox("托盘退出前二次确认")

        form.addRow("每日执行时间", self.schedule_time)
        form.addRow("", self.schedule_checkbox)
        form.addRow("", self.auto_start_checkbox)
        form.addRow("", self.shadow_launch_checkbox)
        form.addRow("", self.exit_confirm_checkbox)
        control_layout.addLayout(form)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.login_button = QPushButton("重新登录")
        self.login_button.setObjectName("primaryButton")
        self.manual_crawl_button = QPushButton("立即采集")
        self.manual_crawl_button.setObjectName("primaryButton")
        self.hide_button = QPushButton("缩到托盘")
        action_row.addWidget(self.login_button)
        action_row.addWidget(self.manual_crawl_button)
        action_row.addStretch(1)
        action_row.addWidget(self.hide_button)
        control_layout.addLayout(action_row)

        self.hint_label = QLabel("程序会优先接管本机影子 Chrome；未登录时请点击“重新登录”打开扫码窗口。")
        self.hint_label.setObjectName("mutedText")
        control_layout.addWidget(self.hint_label)
        page.addWidget(control_card)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 14)
        log_layout.setSpacing(10)
        log_title = QLabel("运行日志")
        log_title.setObjectName("sectionTitle")
        self.log_output = QPlainTextEdit(self)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("这里会显示影子浏览器状态、登录提示和本地采集结果。")
        self.log_output.setMaximumBlockCount(500)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_output, stretch=1)
        page.addWidget(log_card, stretch=1)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
              background: #f5f7fb;
              color: #1f2937;
              font-family: "Microsoft YaHei UI";
              font-size: 13px;
            }
            QFrame#card {
              background: white;
              border: 1px solid #e5ebf5;
              border-radius: 12px;
            }
            QLabel#titleText {
              color: #0f172a;
              font-size: 22px;
              font-weight: 700;
            }
            QLabel#sectionTitle {
              color: #0f172a;
              font-size: 16px;
              font-weight: 700;
            }
            QLabel#mutedText {
              color: #64748b;
              font-size: 12px;
            }
            QLabel#statusPill {
              color: #0f172a;
              background: #eef4ff;
              border: 1px solid #d7e5ff;
              border-radius: 12px;
              padding: 6px 12px;
              font-weight: 700;
            }
            QTimeEdit {
              min-height: 38px;
              border: 1px solid #d6dce8;
              border-radius: 10px;
              padding: 0 12px;
              background: white;
            }
            QTimeEdit:focus {
              border: 1px solid #246bfd;
            }
            QPushButton {
              min-height: 38px;
              padding: 0 14px;
              border-radius: 10px;
              border: 1px solid #d6dce8;
              background: white;
            }
            QPushButton:hover {
              border-color: #246bfd;
              color: #246bfd;
            }
            QPushButton#primaryButton {
              background: #246bfd;
              color: white;
              border: none;
              font-weight: 700;
            }
            QPushButton#primaryButton:hover {
              background: #1d57d0;
              color: white;
            }
            QCheckBox {
              spacing: 8px;
              color: #334155;
            }
            QPlainTextEdit#logOutput {
              border: 1px solid #e7ecf5;
              border-radius: 12px;
              background: #111827;
              color: #dbe4ff;
              padding: 10px;
              font-family: "Cascadia Mono";
            }
            """
        )

        self.schedule_timer = QTimer(self)
        self.schedule_timer.setInterval(30_000)
        self.schedule_timer.timeout.connect(self._check_schedule)
        self.schedule_timer.start()

        self.login_poll_timer = QTimer(self)
        self.login_poll_timer.setInterval(3_000)
        self.login_poll_timer.timeout.connect(self._poll_login_state)

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
        crawl_action = tray_menu.addAction("立即采集")
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
        self.hide_button.clicked.connect(self._hide_to_tray)
        self.schedule_checkbox.toggled.connect(self._persist_settings)
        self.schedule_time.timeChanged.connect(self._persist_settings)
        self.auto_start_checkbox.toggled.connect(self._sync_autostart_setting)
        self.shadow_launch_checkbox.toggled.connect(self._persist_settings)
        self.exit_confirm_checkbox.toggled.connect(self._persist_settings)

    def _initialize_runtime(self) -> None:
        self._sync_autostart_setting(announce=False)
        self._persist_settings()
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

    def _apply_state_to_ui(self) -> None:
        schedule_str = self.state.get("scheduleTime", "09:00")
        schedule_time = QTime.fromString(schedule_str, "HH:mm")
        self.schedule_time.setTime(schedule_time if schedule_time.isValid() else QTime(9, 0))
        self.schedule_checkbox.setChecked(bool(self.state.get("scheduleEnabled", True)))
        self.auto_start_checkbox.setChecked(bool(self.state.get("autoStartEnabled", True) or is_autostart_enabled(APP_NAME)))
        self.shadow_launch_checkbox.setChecked(bool(self.state.get("shadowChromeAutoLaunch", True)))
        self.exit_confirm_checkbox.setChecked(bool(self.state.get("exitRequiresConfirm", True)))
        self._set_account_text(self.state.get("lastKnownLoginAccount") or "")
        summary = self.state.get("lastPayloadSummary") or "尚未采集"
        self.result_summary_label.setText(f"最近结果：{summary}")
        self.chrome_path_label.setText(f"Chrome 路径：{self.state.get('chromePath') or '待检测'}")
        self.shadow_dir_label.setText(f"影子目录：{self._shadow_profile_dir()}")
        self._refresh_schedule_hint()

    def _shadow_profile_dir(self) -> str:
        return str(self.state.get("shadowChromeProfileDir") or self.state.get("chromeUserDataDir") or default_shadow_profile_dir())

    def _persist_settings(self, *_args: object) -> None:
        self.state["captureEngine"] = "external"
        self.state["scheduleEnabled"] = self.schedule_checkbox.isChecked()
        self.state["scheduleTime"] = self.schedule_time.time().toString("HH:mm")
        self.state["autoStartEnabled"] = self.auto_start_checkbox.isChecked()
        self.state["shadowChromeAutoLaunch"] = self.shadow_launch_checkbox.isChecked()
        self.state["exitRequiresConfirm"] = self.exit_confirm_checkbox.isChecked()
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

    def open_login_dialog(self) -> None:
        try:
            session = show_shadow_browser_for_login(self.state, self._log)
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            self._set_status("浏览器未就绪", danger=True)
            self._set_alert_mode(True)
            self._log(str(exc))
            return

        self._remember_shadow_session(session.chrome_path, session.profile_dir, session.pid)
        self.pending_login_recovery = True
        self._set_status("等待登录")
        self._set_alert_mode(True)
        try:
            session.page.get(EMPLOYEE_TARGET_URL)
        except Exception as exc:
            self._log(f"打开绩效考核页面失败：{exc}")
        else:
            self._log("已打开影子浏览器绩效考核页，请在该窗口完成千牛扫码登录。")
        self._log("已打开影子浏览器，请在浏览器窗口完成千牛扫码登录。")
        if not self.login_poll_timer.isActive():
            self.login_poll_timer.start()

    def _poll_login_state(self) -> None:
        try:
            state = inspect_external_page_state(self.state, lambda _message: None, ensure_browser=False)
        except ShadowBrowserError:
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
        self._log("千牛登录成功，正在切回后台影子浏览器。")
        try:
            session = ensure_shadow_browser(self.state, lambda _message: None, force_restart=True, visible=False)
            self._remember_shadow_session(session.chrome_path, session.profile_dir, session.pid)
        except ShadowBrowserError as exc:
            self._log(f"影子浏览器切回后台失败，但登录态已保留：{exc}")
        self.start_capture(manual=False, reason="登录后自动采集")

    def start_capture(self, manual: bool, reason: str) -> None:
        if self.capture_in_progress:
            self._log("已有采集任务正在执行，跳过新的触发。")
            return

        if not self.logged_in:
            self._check_login_state(announce=False)
            if not self.logged_in:
                self._set_status("请先登录", danger=True)
                self._log("当前未登录千牛，请先点击“重新登录”。")
                return

        self.capture_in_progress = True
        self.capture_reason = reason
        self._set_status(f"{reason}中")
        self._set_alert_mode(False)
        self._log(f"开始{reason}，当前使用外置影子浏览器采集。")
        try:
            payload = capture_with_external_chrome(self.state, self._log)
        except LoginRequiredError as exc:
            self._handle_login_expired(f"{reason}失败：{exc}")
            self._finish_capture(None, aborted=True)
            return
        except (ChromeNotFoundError, PortOccupiedError, ShadowBrowserError) as exc:
            self._set_status("浏览器未就绪", danger=True)
            self._set_alert_mode(True)
            self._log(f"{reason}失败：{exc}")
            self._finish_capture(None, aborted=True)
            return
        except Exception as exc:
            self._set_status("采集失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"{reason}失败：{exc}")
            self._finish_capture(None, aborted=True)
            return

        self._finish_capture(payload, aborted=False)

    def _finish_capture(self, payload: Dict[str, Any] | None, aborted: bool) -> None:
        self.capture_in_progress = False
        if aborted:
            self._log(f"{self.capture_reason}结束。")
            return
        if not payload:
            self._set_status("采集失败", danger=True)
            self._set_alert_mode(True)
            self._log(f"{self.capture_reason}失败：本次没有拿到任何员工绩效数据。")
            return

        current_signature = payload_signature(payload)
        previous_signature = self.state.get("lastPayloadSignature", "")
        summary = format_employee_summary(payload)

        if current_signature == previous_signature and self.capture_reason != "手动采集":
            self._log("本次数据与上次一致，已完成本地校验。")
        else:
            self._log(f"采集成功：{summary}")
            self._log(json.dumps(payload, ensure_ascii=False, indent=2))

        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.state["lastRunAt"] = now_text
        self.state["lastRunDate"] = datetime.now().strftime("%Y-%m-%d")
        self.state["lastPayloadSignature"] = current_signature
        self.state["lastPayloadSummary"] = summary
        self._remember_login_account(payload.get("loginAccount") or payload.get("subAccount") or "")
        self.result_summary_label.setText(f"最近结果：{summary}")
        self._set_status("待命")
        self._save_state()
        self._refresh_schedule_hint()
        self._log(f"{self.capture_reason}结束。")

    def _check_schedule(self) -> None:
        if self.capture_in_progress or not self.schedule_checkbox.isChecked() or not self.logged_in:
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
        self.chrome_path_label.setText(f"Chrome 路径：{self.state.get('chromePath') or '待检测'}")
        self.shadow_dir_label.setText(f"影子目录：{self._shadow_profile_dir()}")
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
        self.account_label.setText(f"当前账号：{clean_account or '--'}")

    def _apply_login_state(self, logged_in: bool) -> None:
        if logged_in:
            self.login_state_label.setText("登录状态：已登录")
            self.hint_label.setText("影子浏览器登录态有效，可以立即采集，也会按计划自动采集。")
            self.login_button.setText("重新登录")
            self._set_status("已登录")
            return
        self.login_state_label.setText("登录状态：请先登录")
        self.hint_label.setText("当前未检测到有效千牛登录态，请点击“重新登录”打开影子浏览器扫码。")
        self.login_button.setText("重新登录")
        self._set_status("请先登录", danger=True)

    def _handle_login_expired(self, message: str) -> None:
        self.logged_in = False
        self.pending_login_recovery = True
        self._apply_login_state(False)
        self._set_alert_mode(True)
        self._log(message)
        self.tray.showMessage(
            APP_NAME,
            "千牛登录已过期，请点击通知后重新扫码登录。",
            QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )

    def _set_status(self, text: str, danger: bool = False) -> None:
        self.status_pill.setText(text)
        color = "#b42318" if danger else "#0f172a"
        bg = "#fee4e2" if danger else "#eef4ff"
        border = "#fda29b" if danger else "#d7e5ff"
        self.status_pill.setStyleSheet(
            f"color:{color}; background:{bg}; border:1px solid {border}; border-radius:12px; padding:6px 12px; font-weight:700;"
        )

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
        if self.pending_login_recovery and not self.login_poll_timer.isActive():
            self.open_login_dialog()

    def _exit_from_tray(self) -> None:
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

    def _save_state(self) -> None:
        self._write_json(self.state_path, self.state)

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return dict(default)
        merged = dict(default)
        if isinstance(loaded, dict):
            merged.update(loaded)
        return merged

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def run() -> int:
    app = QApplication([])
    icon_path = Path(__file__).resolve().parent / "resources" / "yuansheng_logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    instance_name = "YuanshengDataAssistantDesktop"
    instance_manager = SingleInstanceManager(instance_name, app)
    if not instance_manager.acquire():
        return 0

    window = YuanshengMainWindow(Path(__file__).resolve().parent)
    instance_manager.set_activation_callback(window.handle_external_activation)
    app.instance_manager = instance_manager  # type: ignore[attr-defined]
    window.show()
    return app.exec()
