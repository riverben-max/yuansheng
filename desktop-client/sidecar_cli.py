from __future__ import annotations

from datetime import datetime, timedelta
import argparse
from contextlib import contextmanager
import json
import ssl
import urllib.request
import os
from pathlib import Path
import sys
import threading
from typing import Any, Callable, Dict, Mapping, MutableMapping
from urllib.parse import unquote
import uuid

from direct_api_capture import (
    DirectApiCaptureError,
    DirectApiLoginRequiredError,
    capture_with_direct_api,
    format_cookie_diagnostics,
    migrate_direct_api_cookie_config,
    summarize_cookie,
    update_direct_api_cookie,
)
from error_sanitizer import sanitize_sensitive_text
from external_capture import LoginRequiredError, capture_with_external_chrome, inspect_existing_shadow_browser_state
from douyin_workload_capture import capture_douyin_workload
from jd_workload_capture import capture_jd_workload
from login_accounts import add_login_account, build_account_state, capture_enabled_accounts, ensure_login_accounts
from pdd_workload_capture import capture_pdd_workload
from platform_adapters import default_capture_adapters
from qn_cookie_refresh import QnCookieRefreshError, refresh_qn_cookie
from platform_config import (
    JD_LOGIN_URL,
    PDD_LOGIN_URL,
    QN_LOGIN_URL,
    is_douyin_login_success_page,
    is_jd_login_success_page,
    is_pdd_login_success_page,
    login_start_url_for_platform,
    normalize_platform,
)
from secure_storage import protect_text
from shadow_browser import (
    ChromeNotFoundError,
    DrissionTempBrowserDetected,
    PortOccupiedError,
    ShadowBrowserError,
    default_shadow_profile_dir,
    is_shadow_browser_running,
    kill_drission_temp_browsers,
    launch_shadow_browser_for_login,
    shadow_browser_closed_reason,
    shutdown_shadow_browser,
)
from spider_core import EMPLOYEE_TARGET_URL, format_employee_summary, payload_signature
from startup_manager import ensure_autostart, is_autostart_enabled
from upload_client import UploadClientError, upload_employee_payload, ensure_default_auth_config

APP_NAME = "远盛数据助手"
SIDECAR_VERSION = "1.1.9"
DEFAULT_SERVER_URL = "http://120.27.22.50"
DEFAULT_UPDATE_CHECK_URL = "http://120.27.22.50/desktop/update.json"
DIRECT_API_TEMPLATE_NAME = "direct_api_capture.template.json"
CONFIG_ERROR_MARKERS = ("配置文件", "合法 JSON", "未启用", "缺少", "根节点", "config")
LOGIN_PENDING_STATUSES = {"等待登录", "等待扫码", "等待登录检测", "正在清理临时浏览器"}
_PROCESS_LOCK = threading.RLock()
_LOCK_STATE = threading.local()


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "YuanshengDataAssistant" / "data"


def default_state(data_dir: Path) -> Dict[str, Any]:
    shadow_dir = str(default_shadow_profile_dir())
    return {
        "dataVersion": 1,
        "captureEngine": "external",
        "directApiPreferred": False,
        "directApiConfigPath": str(data_dir / "direct_api_capture.json"),
        "chromePath": "",
        "chromePort": 0,
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
        "updateCheckUrl": DEFAULT_UPDATE_CHECK_URL,
        "uploadTimeoutSeconds": 10,
        "uploadHistory": {},
    }


def default_direct_api_template() -> Dict[str, Any]:
    return {
        "enabled": True,
        "referer": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "loginAccount": "",
        "subAccount": "",
        "requests": [
            {
                "name": "qn-workload-primary",
                "method": "GET",
                "apiUrl": "https://h5api.m.taobao.com/h5/mtop.alibaba.sycm.domain.onequery/1.0/",
                "params": {
                    "jsv": "2.6.1",
                    "appKey": "12574478",
                    "t": "1777182250798",
                    "sign": "placeholder",
                    "api": "mtop.alibaba.sycm.domain.onequery",
                    "v": "1.0",
                    "ttid": "11320@taobao_WEB_9.9.99",
                    "type": "originaljsonp",
                    "dataType": "originaljsonp",
                    "callback": "mtopjsonp20",
                    "data": "{\"domainCode\":\"tao.shop.qos.subaccount\",\"dateType\":\"day\",\"dateRange\":\"2026-04-25|2026-04-25\",\"showType\":\"list\",\"device\":\"0\",\"page\":1,\"pageSize\":10,\"indexCodes\":\"consultUserCnt,consultFinalPayRate,avgReplyInterval,customerAllSateRate,customerServiceGmv,servSaleRate\",\"order\":\"desc\",\"orderBy\":\"consultUserCnt\",\"extMap\":\"{\\\"greyTag\\\":\\\"Y\\\"}\"}",
                },
                "body": {},
                "autoMtopSign": True,
                "autoDateRange": True,
            },
            {
                "name": "qn-workload-reply",
                "method": "GET",
                "apiUrl": "https://h5api.m.taobao.com/h5/mtop.alibaba.sycm.domain.onequery/1.0/",
                "params": {
                    "jsv": "2.6.1",
                    "appKey": "12574478",
                    "t": "1777182387321",
                    "sign": "placeholder",
                    "api": "mtop.alibaba.sycm.domain.onequery",
                    "v": "1.0",
                    "ttid": "11320@taobao_WEB_9.9.99",
                    "type": "originaljsonp",
                    "dataType": "originaljsonp",
                    "callback": "mtopjsonp47",
                    "data": "{\"domainCode\":\"tao.shop.qos.subaccount\",\"dateType\":\"day\",\"dateRange\":\"2026-04-25|2026-04-25\",\"showType\":\"list\",\"device\":\"0\",\"page\":1,\"pageSize\":10,\"indexCodes\":\"wwwConsultUv,validReplyUv,wwwRecUserCnt,customerAllSateRate,wwUserReplayRate,firstReplyInterval\",\"order\":\"desc\",\"orderBy\":\"consultUserCnt\",\"extMap\":\"{\\\"greyTag\\\":\\\"Y\\\"}\"}",
                },
                "body": {},
                "autoMtopSign": True,
                "autoDateRange": True,
            },
        ],
        "autoMtopSign": True,
        "autoDateRange": True,
        "dateOffsetDays": -1,
    }


def _template_search_paths() -> list[Path]:
    paths = []
    if hasattr(sys, "_MEIPASS"):
        paths.append(Path(getattr(sys, "_MEIPASS")) / "data" / DIRECT_API_TEMPLATE_NAME)
    paths.append(Path(__file__).resolve().parent / "data" / DIRECT_API_TEMPLATE_NAME)
    return paths


def load_direct_api_template() -> Dict[str, Any]:
    for path in _template_search_paths():
        try:
            if path.exists():
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    return loaded
        except (json.JSONDecodeError, OSError):
            continue
    return default_direct_api_template()


def ensure_direct_api_config(config_path: Path) -> bool:
    if config_path.exists():
        return True
    template = load_direct_api_template()
    template.pop("cookie", None)
    template.pop("cookieProtected", None)
    requests = template.get("requests")
    if isinstance(requests, list):
        for item in requests:
            if isinstance(item, dict):
                item.pop("cookie", None)
                item.pop("cookieProtected", None)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return True


def event(kind: str, **payload: Any) -> Dict[str, Any]:
    data = {"type": kind}
    data.update(payload)
    return data


def write_json_line(payload: Mapping[str, Any]) -> None:
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()


class SidecarApp:
    def __init__(
        self,
        data_dir: Path | None = None,
        emit: Callable[[Mapping[str, Any]], None] = write_json_line,
        capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
        direct_capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
        jd_capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
        pdd_capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
        douyin_capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
        upload_func: Callable[[MutableMapping[str, Any], Mapping[str, Any], str, str], tuple[str, Mapping[str, Any] | None]] | None = None,
    ):
        self.data_dir = data_dir or app_data_dir()
        self.state_path = self.data_dir / "app_state.json"
        self.emit = emit
        self.capture_func = capture_func or capture_with_external_chrome
        self.direct_capture_func = direct_capture_func or capture_with_direct_api
        self.jd_capture_func = jd_capture_func or capture_jd_workload
        self.pdd_capture_func = pdd_capture_func or capture_pdd_workload
        self.douyin_capture_func = douyin_capture_func or capture_douyin_workload
        self.upload_func = upload_func or upload_payload_with_state
        ensure_default_auth_config()

    def _qn_capture_with_refresh(self, state: Mapping[str, Any], log: Callable[[str], None]) -> Mapping[str, Any]:
        """千牛采集：如果 _m_h5_tk 未过期直接采集，否则先刷新再采集。"""
        if str(state.get("cookieProtected") or "").strip():
            # 检查现有 _m_h5_tk 是否还在有效期内
            if not self._qn_token_expired(state):
                log("千牛 _m_h5_tk 未过期，跳过刷新直接采集。")
                return self.direct_capture_func(state, log)
            try:
                new_cookie = refresh_qn_cookie(state, log)
                from secure_storage import protect_text as _pt
                state = dict(state)
                state["cookieProtected"] = _pt(new_cookie)
            except QnCookieRefreshError as exc:
                log(f"千牛 Cookie 刷新失败，尝试直接采集：{exc}")
        return self.direct_capture_func(state, log)

    def _qn_token_expired(self, state: Mapping[str, Any]) -> bool:
        """检查千牛 _m_h5_tk 是否已过期（有效期约 2 小时，从生成时间戳算起）。"""
        import time as _time
        try:
            from secure_storage import unprotect_text
            cookie = unprotect_text(str(state.get("cookieProtected") or ""))
            for part in str(cookie or "").split(";"):
                name, sep, val = part.strip().partition("=")
                if name.strip() == "_m_h5_tk" and sep:
                    parts = val.strip().split("_")
                    if len(parts) >= 2:
                        # 末尾是生成时间戳（毫秒），有效期约 7200 秒（2小时）
                        gen_ts = int(parts[-1]) / 1000
                        return _time.time() > gen_ts + 7200
        except Exception:
            pass
        return True

    def load_state(self) -> Dict[str, Any]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state = default_state(self.data_dir)
        if self.state_path.exists():
            try:
                loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    state.update(loaded)
            except json.JSONDecodeError:
                self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                 message="配置文件损坏，尝试从备份恢复。"))
                backup = self.state_path.with_suffix(".json.bak")
                if backup.exists():
                    try:
                        loaded = json.loads(backup.read_text(encoding="utf-8"))
                        if isinstance(loaded, dict):
                            state.update(loaded)
                        self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                         message="已从备份恢复配置。"))
                    except (json.JSONDecodeError, OSError):
                        self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                         message="备份文件也无法读取，使用默认配置。"))
                else:
                    self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                     message="无可用备份，使用默认配置。"))
            except OSError:
                self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                 message=f"无法读取配置文件（{self.state_path}），使用默认配置。"))
        state["directApiConfigPath"] = str(self.data_dir / "direct_api_capture.json")
        if not str(state.get("updateCheckUrl") or "").strip():
            state["updateCheckUrl"] = DEFAULT_UPDATE_CHECK_URL
        try:
            state["directApiConfigReady"] = ensure_direct_api_config(Path(str(state["directApiConfigPath"])))
        except OSError as exc:
            state["directApiConfigReady"] = False
            self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                            message=f"初始化接口直采配置失败：{sanitize_sensitive_text(exc)}"))
        ensure_login_accounts(state, self.data_dir)
        return state

    def save_state(self, state: Mapping[str, Any]) -> None:
        try:
            with self.state_file_lock():
                self.data_dir.mkdir(parents=True, exist_ok=True)
                state_json = json.dumps(dict(state), ensure_ascii=False, indent=2)
                state_size_mb = len(state_json.encode("utf-8")) / (1024 * 1024)
                if state_size_mb > 5:
                    self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                     message=f"配置文件较大（{state_size_mb:.1f}MB），建议清理历史数据。"))
                tmp_path = self.state_path.with_name(
                    f"{self.state_path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
                )
                tmp_path.write_text(state_json, encoding="utf-8", newline="\n")
                tmp_path.replace(self.state_path)
                backup = self.state_path.with_suffix(".json.bak")
                try:
                    backup.write_text(state_json, encoding="utf-8", newline="\n")
                except Exception:
                    pass
        except Exception as exc:
            self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                             message=f"保存配置文件失败，请检查磁盘空间和权限：{sanitize_sensitive_text(exc)}"))

    def response(self, data: Any = None) -> Dict[str, Any]:
        return {"ok": True, "data": data}

    @contextmanager
    def exclusive_operation_lock(self):
        with self.state_file_lock():
            yield

    @contextmanager
    def state_file_lock(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.data_dir / "sidecar.lock"
        depth = int(getattr(_LOCK_STATE, "state_lock_depth", 0) or 0)
        if depth > 0:
            yield
            return
        with _PROCESS_LOCK:
            with lock_path.open("a+b") as lock_file:
                _lock_file(lock_file)
                _LOCK_STATE.state_lock_depth = depth + 1
                try:
                    yield
                finally:
                    _LOCK_STATE.state_lock_depth = depth
                    _unlock_file(lock_file)

    def get_state(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        result = self.public_state(state)
        result["sidecarVersion"] = SIDECAR_VERSION
        return self.response(result)

    def save_settings(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            for key in ("serverUrl", "scheduleTime"):
                if key in payload:
                    state[key] = str(payload.get(key) or "").strip()
            for key in ("scheduleEnabled", "autoStartEnabled", "shadowChromeAutoLaunch", "exitRequiresConfirm"):
                if key in payload:
                    state[key] = bool(payload.get(key))
            if "autoStartEnabled" in payload:
                try:
                    ensure_autostart(bool(state.get("autoStartEnabled", False)))
                except OSError:
                    self.log("更新开机自启注册表失败，可能需要管理员权限。")
            self.save_state(state)
            return self.response(self.public_state(state))

    def account_create(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            account = add_login_account(
                state,
                self.data_dir,
                display_name=str(payload.get("displayName") or "新登录账户"),
                login_hint=str(payload.get("loginHint") or ""),
                platform=str(payload.get("platform") or "qn"),
                shop_name=str(payload.get("shopName") or ""),
                shop_id=_safe_shop_id(payload.get("shopId")),
            )
            if "enabled" in payload:
                account["enabled"] = bool(payload.get("enabled"))
            self.save_state(state)
            return self.response(account)

    def account_update(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("id") or "")
            account = self.find_account(state, account_id)
            if account is None:
                raise ValueError("登录账户不存在。")
            for key in ("displayName", "loginHint", "profileDir", "shopName"):
                if key in payload:
                    account[key] = str(payload.get(key) or "").strip()
            if "shopId" in payload:
                account["shopId"] = _safe_shop_id(payload.get("shopId"))
            if "platform" in payload:
                next_platform = normalize_platform(payload.get("platform"))
                if next_platform != normalize_platform(account.get("platform")):
                    _clear_platform_credentials(account)
                account["platform"] = next_platform
            if "chromePort" in payload:
                account["chromePort"] = int(payload.get("chromePort") or 9222)
            if "enabled" in payload:
                account["enabled"] = bool(payload.get("enabled"))
            self.save_state(state)
            return self.response(account)

    def account_delete(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("id") or "")
            accounts = ensure_login_accounts(state, self.data_dir)
            target = next((item for item in accounts if str(item.get("id") or "") == account_id), None)
            if target is None:
                raise ValueError("登录账户不存在。")
            profile_dir = str(target.get("profileDir") or "")
            next_accounts = [item for item in accounts if str(item.get("id") or "") != account_id]
            state["loginAccounts"] = next_accounts
            self.save_state(state)

        if bool(payload.get("removeProfile")) and profile_dir:
            target_path = Path(profile_dir).resolve()
            allowed_root = (self.data_dir / "profiles").resolve()
            try:
                target_path.relative_to(allowed_root)
            except ValueError:
                self.log(f"跳过删除影子目录：{target_path} 不在本程序 profiles 目录下。")
                return self.response({"id": account_id})
            try:
                import shutil
                if target_path.exists():
                    shutil.rmtree(target_path)
                    self.log(f"已删除影子目录：{target_path}")
            except Exception as exc:
                self.log(f"删除影子目录失败，可稍后手动清理：{exc}")

        return self.response({"id": account_id})

    def import_cookie(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("accountId") or payload.get("id") or "")
            raw_text = str(payload.get("cookieText") or "").strip()
            if not account_id:
                raise ValueError("请选择一个登录账号。")
            if not raw_text:
                raise ValueError("请粘贴 Cookie 或 cURL 命令内容。")
            account = self.find_account(state, account_id)
            if account is None:
                raise ValueError("登录账户不存在。")
            cookie_header, csrf_token = _parse_cookie_import(raw_text)
            if not cookie_header:
                raise ValueError("未能从输入内容中解析出 Cookie，请检查格式。")
            now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            account["cookieProtected"] = protect_text(cookie_header)
            account["cookieUpdatedAt"] = now_text
            account["loginStatus"] = "已登录"
            account["lastError"] = ""
            account["lastFailureReason"] = ""
            if csrf_token:
                account["douyinCsrfTokenProtected"] = protect_text(csrf_token)
                account.pop("douyinCsrfToken", None)
            else:
                account.pop("douyinCsrfToken", None)
                account.pop("douyinCsrfTokenProtected", None)
            # 自动识别登录身份
            platform = normalize_platform(account.get("platform"))
            identity, shop_name = "", ""
            if platform == "douyin":
                identity, shop_name = _resolve_douyin_user_info(cookie_header, csrf_token, self.log)
            elif platform == "pdd":
                identity, _ = _resolve_pdd_user_info(cookie_header, self.log)
            elif platform == "jd":
                from jd_workload_capture import resolve_jd_pin_from_cookie
                identity = resolve_jd_pin_from_cookie(cookie_header)
            else:
                # qn: 从 Cookie 的 sn/_nk_/tracknick 提取客服名
                identity = _resolve_qn_identity_from_cookie(cookie_header)
            if identity:
                account["lastKnownLoginAccount"] = identity
                if not str(account.get("loginHint") or "").strip():
                    account["loginHint"] = identity
            if shop_name and not str(account.get("shopName") or "").strip():
                account["shopName"] = shop_name
            self.save_state(state)
            self.log(f"已导入 Cookie（长度 {len(cookie_header)}），csrf-token {'已保存' if csrf_token else '未提供'}，识别身份：{identity or '未识别'}。")
            return self.response({"ok": True, "state": self.public_state(state)})

    def start_login(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.exclusive_operation_lock():
            state = self.load_state()
            account_id = str(payload.get("accountId") or payload.get("id") or "")
            if not account_id:
                raise ValueError("请选择一个登录账号。")
            account = self.find_account(state, account_id) if account_id else None
            if account is None:
                raise ValueError("登录账户不存在。")
            login_state = build_account_state(state, account)
            if _has_pending_login_session(login_state, account):
                browser_state = _browser_state_from_account(login_state, account, reused=True)
                return self.response({"browser": browser_state, "state": self.public_state(state), "reused": True})

            self.shutdown_known_shadow_browsers(state)
            launch_state = dict(login_state)
            launch_state["chromePort"] = 0
            launch_state.pop("activeChromePort", None)
            launch_state["shadowChromeStartupUrl"] = login_start_url_for_platform(account.get("platform"))
            kill_drission_temp_browsers(int(login_state.get("activeChromePort") or login_state.get("chromePort") or 0), self.log)
            session = launch_shadow_browser_for_login(launch_state, self.log)
            browser_state = {
                "chromePath": session.chrome_path,
                "shadowChromeProfileDir": session.profile_dir,
                "chromePort": int(launch_state.get("chromePort") or 0),
                "activeChromePort": session.port,
                "shadowChromePid": session.pid or 0,
                "launched": session.launched,
                "restarted": session.restarted,
                "reused": False,
            }
            state["chromePath"] = session.chrome_path
            state["shadowChromePid"] = session.pid or 0
            account["loginStatus"] = "等待登录"
            account["shadowChromePid"] = session.pid or 0
            account["activeChromePort"] = session.port
            account["loginStartedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_state(state)
            return self.response({"browser": browser_state, "state": self.public_state(state)})

    def poll_login(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.exclusive_operation_lock():
            return self._poll_login_locked(payload)

    def _poll_login_locked(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        state = self.load_state()
        account_id = str(payload.get("accountId") or payload.get("id") or "")
        if not account_id:
            raise ValueError("请选择一个登录账号。")
        account = self.find_account(state, account_id)
        if account is None:
            raise ValueError("登录账户不存在。")

        account_state = build_account_state(state, account)
        closed_reason = shadow_browser_closed_reason(account_state)
        if closed_reason:
            return self._mark_login_window_closed(state, account, closed_reason)
        try:
            browser_state = inspect_existing_shadow_browser_state(account_state, self.log)
        except DrissionTempBrowserDetected as exc:
            kill_drission_temp_browsers(int(account_state.get("activeChromePort") or account_state.get("chromePort") or 0), self.log)
            account["loginStatus"] = "等待扫码"
            account["lastError"] = ""
            self.save_state(state)
            return self.response(
                {
                    "loggedIn": False,
                    "status": "正在清理临时浏览器",
                    "message": str(exc),
                    "state": self.public_state(state),
                }
            )
        except ShadowBrowserError as exc:
            if is_shadow_browser_running(account_state):
                account["loginStatus"] = "等待登录检测"
                account["lastError"] = ""
                self.save_state(state)
                return self.response(
                    {
                        "loggedIn": False,
                        "status": "等待登录检测",
                        "message": str(exc),
                        "state": self.public_state(state),
                    }
                )
            return self._mark_login_window_closed(state, account, str(exc))
        except Exception as exc:
            account["loginStatus"] = "登录检测失败"
            account["lastError"] = str(exc)
            self.save_state(state)
            return self.response(
                {
                    "loggedIn": False,
                    "status": "登录检测失败",
                    "message": str(exc),
                    "state": self.public_state(state),
                }
            )

        cookie_header = str(browser_state.get("cookieHeader") or "").strip()
        cookie_summary = summarize_cookie(cookie_header)
        account["shadowChromePid"] = int(browser_state.get("shadowChromePid") or account.get("shadowChromePid") or 0)
        active_port = int(browser_state.get("activeChromePort") or browser_state.get("chromePort") or account.get("activeChromePort") or 0)
        if active_port > 0:
            account["activeChromePort"] = active_port
        account["cookieSummary"] = format_cookie_diagnostics(cookie_header) if cookie_header else ""
        normalized_platform = normalize_platform(account.get("platform"))
        if normalized_platform == "jd":
            self.log(_format_jd_login_diagnostics(browser_state, cookie_header))
        elif normalized_platform == "pdd":
            self.log(_format_pdd_login_diagnostics(browser_state, cookie_header))

        if not _browser_state_is_login_ready(browser_state, cookie_summary, account.get("platform"), cookie_header):
            account["loginStatus"] = "等待扫码"
            account["lastError"] = ""
            self.save_state(state)
            return self.response(
                {
                    "loggedIn": False,
                    "status": "等待扫码",
                    "cookieSummary": account["cookieSummary"],
                    "state": self.public_state(state),
                }
            )

        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        account["cookieProtected"] = protect_text(cookie_header)
        account["cookieUpdatedAt"] = now_text
        account["cookieSummary"] = format_cookie_diagnostics(cookie_header)
        login_identity = _resolve_login_identity(browser_state, cookie_header)
        account["lastKnownLoginAccount"] = login_identity
        if login_identity and not str(account.get("loginHint") or "").strip():
            account["loginHint"] = login_identity
        account["loginStatus"] = "已登录"
        account["lastFailureReason"] = ""
        account["lastError"] = ""

        try:
            shutdown_shadow_browser(account_state, self.log)
            account["shadowChromePid"] = 0
            account.pop("activeChromePort", None)
            state["shadowChromePid"] = 0
        except ShadowBrowserError as exc:
            self.log(f"登录成功，但关闭登录窗口失败：{exc}")

        self.save_state(state)
        return self.response(
            {
                "loggedIn": True,
                "status": "已登录",
                "loginAccount": account["lastKnownLoginAccount"],
                "state": self.public_state(state),
            }
        )

    def _mark_login_window_closed(
        self,
        state: MutableMapping[str, Any],
        account: MutableMapping[str, Any],
        message: str,
    ) -> Dict[str, Any]:
        account["loginStatus"] = "登录窗口已关闭"
        account["lastError"] = message
        account["shadowChromePid"] = 0
        account.pop("activeChromePort", None)
        state["shadowChromePid"] = 0
        self.save_state(state)
        return self.response(
            {
                "loggedIn": False,
                "status": "登录窗口已关闭",
                "message": message,
                "state": self.public_state(state),
            }
        )

    def shutdown_known_shadow_browsers(self, state: Mapping[str, Any]) -> None:
        seen: set[tuple[str, int]] = set()
        for config in self._known_shadow_configs(state):
            key = (
                str(config.get("shadowChromeProfileDir") or config.get("chromeUserDataDir") or ""),
                int(config.get("activeChromePort") or config.get("chromePort") or 0),
            )
            if key in seen:
                continue
            seen.add(key)
            try:
                shutdown_shadow_browser(config, self.log)
            except ShadowBrowserError as exc:
                self.log(f"清理旧影子浏览器失败，继续打开登录窗口：{exc}")

    def _known_shadow_configs(self, state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        configs: list[Mapping[str, Any]] = [state]
        for account in ensure_login_accounts(dict(state), self.data_dir):
            configs.append(build_account_state(state, account))
        return configs

    def check_login(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            try:
                browser_state = inspect_existing_shadow_browser_state(state, self.log)
            except ShadowBrowserError as exc:
                return self.response({"loggedIn": False, "message": str(exc), "state": self.public_state(state)})
            except Exception as exc:
                return self.response({"loggedIn": False, "message": str(exc), "state": self.public_state(state)})
            account = str(browser_state.get("loginAccount") or browser_state.get("nick") or "").strip()
            if account:
                state["lastKnownLoginAccount"] = account
                self.save_state(state)
            return self.response({"loggedIn": bool(account), "loginAccount": account, "browser": browser_state, "state": self.public_state(state)})

    def capture_all(self, payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        request_payload = payload or {}
        reason = str(request_payload.get("reason") or "手动采集")
        platform_filter = str(request_payload.get("platform") or "").strip()
        normalized_platform = normalize_platform(platform_filter) if platform_filter else ""
        self.emit(event("status", status="采集中", danger=False))
        try:
            with self.state_file_lock():
                state = self.load_state()
                accounts = ensure_login_accounts(state, self.data_dir)
                if normalized_platform:
                    accounts = [account for account in accounts if normalize_platform(account.get("platform")) == normalized_platform]
                    if not accounts:
                        state["lastRunAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.save_state(state)
                        self.emit(event("status", status="待命", danger=False))
                        return self.response(
                            {
                                "batch": True,
                                "results": [],
                                "skipped": True,
                                "message": f"没有匹配平台 {normalized_platform} 的登录账号，已跳过采集。",
                                "state": self.public_state(state),
                            }
                        )
            if accounts:
                results = capture_enabled_accounts(
                    state,
                    accounts,
                    reason=reason,
                    capture_func=self.direct_capture_func,
                    upload_func=self.upload_func,
                    log=self.log,
                    capture_adapters=default_capture_adapters(self._qn_capture_with_refresh, self.jd_capture_func, self.pdd_capture_func, self.douyin_capture_func),
                )
                state["lastRunAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._trim_upload_history(state)
                with self.state_file_lock():
                    self.save_state(state)
                self.emit(event("status", status="待命", danger=False))
                return self.response({"batch": True, "results": results, "state": self.public_state(state)})
            payload_data = self.capture_payload(state)
            result = self.apply_capture_result(state, payload_data, reason)
            with self.state_file_lock():
                self.save_state(state)
            self.emit(event("status", status="待命", danger=False))
            return self.response(result)
        except (LoginRequiredError, DirectApiLoginRequiredError) as exc:
            self.emit(event("status", status="请先登录", danger=True))
            self._mark_run_completed_silently()
            raise RuntimeError(sanitize_sensitive_text(exc)) from exc
        except Exception as exc:
            self.emit(event("status", status="采集失败", danger=True))
            self._mark_run_completed_silently()
            raise RuntimeError(sanitize_sensitive_text(exc)) from exc

    def _mark_run_completed_silently(self) -> None:
        """采集失败时也写一次 lastRunAt，避免前端定时器每分钟重试。

        异常情况下尽力更新 state，本身的 IO 错误不应再覆盖外层异常，所以这里
        吞掉自己的异常。
        """
        try:
            with self.state_file_lock():
                state = self.load_state()
                state["lastRunAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_state(state)
        except Exception:
            pass

    def capture_account(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("accountId") or payload.get("id") or "")
            accounts = ensure_login_accounts(state, self.data_dir)
            selected = [item for item in accounts if str(item.get("id") or "") == account_id]
            if not selected:
                raise ValueError("登录账户不存在。")
        self.emit(event("status", status="采集中", danger=False))
        results = capture_enabled_accounts(
            state,
            selected,
            reason=str(payload.get("reason") or "手动采集"),
            capture_func=self.direct_capture_func,
            upload_func=self.upload_func,
            log=self.log,
            capture_adapters=default_capture_adapters(self._qn_capture_with_refresh, self.jd_capture_func, self.pdd_capture_func, self.douyin_capture_func),
        )
        with self.state_file_lock():
            self.save_state(state)
        self.emit(event("status", status="待命", danger=False))
        return self.response({"batch": True, "results": results, "state": self.public_state(state)})

    def capture_account_direct(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """直接用已保存的 Cookie 采集（跳过浏览器刷新，适合每天手动导入 cURL 后使用）。"""
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("accountId") or payload.get("id") or "")
            accounts = ensure_login_accounts(state, self.data_dir)
            selected = [item for item in accounts if str(item.get("id") or "") == account_id]
            if not selected:
                raise ValueError("登录账户不存在。")
        self.emit(event("status", status="采集中", danger=False))
        results = capture_enabled_accounts(
            state,
            selected,
            reason=str(payload.get("reason") or "手动直接采集"),
            capture_func=self.direct_capture_func,
            upload_func=self.upload_func,
            log=self.log,
            capture_adapters=default_capture_adapters(self.direct_capture_func, self.jd_capture_func, self.pdd_capture_func, self.douyin_capture_func),
        )
        with self.state_file_lock():
            self.save_state(state)
        self.emit(event("status", status="待命", danger=False))
        return self.response({"batch": True, "results": results, "state": self.public_state(state)})

    def check_update(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        update_url = str(state.get("updateCheckUrl") or DEFAULT_UPDATE_CHECK_URL).strip()
        if not update_url:
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION})
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(update_url, headers={"User-Agent": f"YuanshengDataAssistant/{SIDECAR_VERSION}"})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                data = _read_update_manifest_response(resp)
            latest = str(data.get("version") or "").strip()
            if latest and _version_is_newer(latest, SIDECAR_VERSION):
                return self.response({
                    "updateAvailable": True,
                    "currentVersion": SIDECAR_VERSION,
                    "latestVersion": latest,
                    "downloadUrl": str(data.get("downloadUrl") or ""),
                    "sha256": str(data.get("sha256") or ""),
                    "notes": str(data.get("notes") or ""),
                    "force": bool(data.get("force", False)),
                })
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION})
        except Exception as exc:
            self.log(f"检查更新失败：{exc}")
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION, "reason": str(exc)})

    def shutdown(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        shutdown_shadow_browser(state, self.log)
        return self.response({"closed": True})

    def setup_browser_debug(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        from browser_debug_setup import (
            BROWSER_DEBUG_PORT,
            ShortcutModifyError,
            add_debug_port_to_shortcut,
            create_debug_shortcut,
            detect_browser_debug_status,
            find_browser_shortcuts,
        )

        account_id = str(payload.get("accountId") or payload.get("id") or "")
        port = int(payload.get("port") or BROWSER_DEBUG_PORT)
        browser_exe = str(payload.get("browserExePath") or "").strip() or None

        # 1) 扫描 + 修改快捷方式（无锁，IO 密集）
        all_shortcuts = find_browser_shortcuts(browser_exe)
        # 优先处理 360 浏览器快捷方式；如果完全没有 360 快捷方式，再考虑 Chrome 等其他浏览器
        sc_360 = [sc for sc in all_shortcuts if sc.get("is_360")]
        sc_other = [sc for sc in all_shortcuts if not sc.get("is_360")]
        target_shortcuts = sc_360 if sc_360 else sc_other

        results = []
        created_new = False
        if target_shortcuts:
            for sc in target_shortcuts:
                try:
                    result = add_debug_port_to_shortcut(sc["path"], port)
                    results.append(result)
                except ShortcutModifyError as exc:
                    results.append({"modified": False, "path": sc["path"], "error": str(exc)})

        # 如果没找到任何 360 快捷方式（哪怕找到了 Chrome 的也不算），自动创建一个 360 桌面快捷方式
        # 这是给客户机器上 360 没装快捷方式（从应用启动器/任务栏固定区启动）的兜底
        if not sc_360:
            try:
                created = create_debug_shortcut(browser_exe, port)
                results.append({
                    "modified": True,
                    "created": True,
                    "path": created["path"],
                    "arguments": created["arguments"],
                })
                created_new = True
            except ShortcutModifyError as exc:
                # 如果至少修改了 Chrome 等其他快捷方式，不报错；都没改才报错
                if not target_shortcuts:
                    raise ValueError(f"未找到浏览器快捷方式，且自动创建失败：{exc}")
                self.log(f"自动创建 360 快捷方式失败（已修改其他快捷方式）：{exc}")

        modified_count = sum(1 for r in results if r.get("modified"))
        failed_count = sum(1 for r in results if r.get("error"))
        total_count = len(results)
        # ready_count = 已经处于"带调试端口"状态的快捷方式总数（包括本次刚改的 + 之前已经有的）
        ready_count = sum(
            1 for r in results
            if r.get("modified") or f"--remote-debugging-port={port}" in str(r.get("arguments", ""))
        )
        browser_status = detect_browser_debug_status(port)
        needs_restart = browser_status["status"] == "running_no_debug"

        # 2) 仅在保存账号字段时持锁
        public_state = None
        if account_id:
            with self.state_file_lock():
                state = self.load_state()
                account = self.find_account(state, account_id)
                if account is not None:
                    account["browserDebugPort"] = port
                    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    account["browserDebugSetupAt"] = now_text
                    if browser_exe:
                        account["browserExePath"] = browser_exe
                    self.save_state(state)
                public_state = self.public_state(state)
        else:
            with self.state_file_lock():
                public_state = self.public_state(self.load_state())

        action = "创建了新" if created_new else "修改了"
        self.log(
            f"浏览器调试设置完成：{action} {modified_count} 个快捷方式（共发现 {total_count} 个，失败 {failed_count} 个），"
            f"端口 {port}，需要重启={needs_restart}。"
        )
        if created_new:
            self.log("已为你在桌面创建「抖店采集专用浏览器」快捷方式，请用它启动浏览器，登录抖店后再点「浏览器」按钮。")
        # 把详细诊断信息打到运行日志，让客户看到当前状态以及下一步该做什么
        from browser_debug_setup import collect_browser_diagnostics
        self.log("当前浏览器状态详情：")
        for line in collect_browser_diagnostics(port):
            self.log(line)

        return self.response({
            "shortcuts": results,
            "createdNew": created_new,
            "modifiedCount": modified_count,
            "failedCount": failed_count,
            "totalCount": total_count,
            "readyCount": ready_count,
            "needsRestart": needs_restart,
            "browserStatus": browser_status["status"],
            "port": port,
            "state": public_state,
        })

    def relaunch_browser_for_debug(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """关闭客户当前的所有 360 浏览器进程，用调试端口模式重新启动并打开对应平台的登录页。

        客户用现有的 360（同一个 exe、同一个 profile、同一个登录态），只是启动方式由软件接管，
        不依赖客户的快捷方式（解决"客户机器没有 360 桌面快捷方式"或"客户从非标方式启动"的场景）。

        Payload:
            startupUrl: 启动后跳转的登录页 URL（默认抖店）。
            platformLabel: 平台显示文案（"千牛"/"京东"/"拼多多"/"抖店"），仅用于日志和提示。
        """
        import subprocess
        import time as _time
        from browser_debug_setup import (
            BROWSER_DEBUG_PORT,
            _get_running_360_exe,
            _resolve_browser_exe,
            _port_is_open,
        )

        port = int(payload.get("port") or BROWSER_DEBUG_PORT)
        startup_url = str(payload.get("startupUrl") or "https://fxg.jinritemai.com").strip() or "https://fxg.jinritemai.com"
        platform_label = str(payload.get("platformLabel") or "").strip() or "对应平台"

        # 1. 拿到 360 exe 路径：先看运行中的进程，再走标准探测
        exe = _get_running_360_exe() or _resolve_browser_exe()
        if not exe:
            raise ValueError("找不到 360 极速浏览器，请先在桌面打开一次 360，再点「浏览器」按钮。")

        # 2. 关闭所有 360 进程
        self.log("正在关闭浏览器以接管登录…")
        for image_name in ("360ChromeX.exe", "360Chrome.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", image_name, "/T"],
                    capture_output=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                )
            except Exception as exc:
                self.log(f"关闭 {image_name} 时遇到异常（忽略继续）：{exc}")
        # 等待端口释放 + 进程退出
        for _ in range(20):  # 最多等 4 秒
            if not _port_is_open(port):
                break
            _time.sleep(0.2)

        # 3. 用调试端口启动新进程
        try:
            subprocess.Popen(
                [exe, f"--remote-debugging-port={port}", startup_url],
                creationflags=(
                    getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as exc:
            raise ValueError(f"启动浏览器失败：{exc}")

        # 4. 等待端口就绪（最多 10 秒）
        port_ready = False
        for _ in range(50):
            if _port_is_open(port):
                port_ready = True
                break
            _time.sleep(0.2)

        self.log(f"浏览器已用调试模式重新启动（端口 {port}）。请在弹出的浏览器里登录{platform_label}后台后，再点一次「浏览器」按钮。")
        return self.response({
            "launched": True,
            "exePath": exe,
            "port": port,
            "portReady": port_ready,
            "startupUrl": startup_url,
        })

    def grab_browser_cookie(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        from browser_debug_setup import (
            BROWSER_DEBUG_PORT,
            PLATFORM_COOKIE_DOMAINS,
            BrowserDebugError,
            BrowserNotReadyError,
            detect_browser_debug_status,
            grab_cookies_via_cdp,
        )

        # 1) 读取账号信息（短锁）
        with self.state_file_lock():
            state = self.load_state()
            account_id = str(payload.get("accountId") or payload.get("id") or "")
            if not account_id:
                raise ValueError("请选择一个登录账号。")
            account = self.find_account(state, account_id)
            if account is None:
                raise ValueError("登录账户不存在。")
            platform = normalize_platform(account.get("platform") or payload.get("platform") or "")
            port = int(payload.get("port") or account.get("browserDebugPort") or BROWSER_DEBUG_PORT)

        target_domains = PLATFORM_COOKIE_DOMAINS.get(platform, [])

        # 2) 浏览器状态检测（无锁）
        browser_status = detect_browser_debug_status(port)
        if browser_status["status"] != "running_with_debug":
            status = browser_status["status"]
            if status == "not_running":
                msg = "浏览器未运行，请先打开 360 极速浏览器。"
            elif status == "running_no_debug":
                msg = "浏览器正在运行但未开启调试端口。请关闭浏览器后用修改过的快捷方式重新打开。"
            elif status == "port_occupied_other":
                msg = f"端口 {port} 被其他程序占用，无法连接浏览器。"
            else:
                msg = f"浏览器调试端口未就绪（状态：{status}）。"
            # 把详细诊断信息打到运行日志，方便客户截图反馈
            from browser_debug_setup import collect_browser_diagnostics
            self.log(f"导入登录信息未成功（{status}）。详细诊断：")
            for line in collect_browser_diagnostics(port):
                self.log(line)
            return self.response({
                "cookieSaved": False,
                "message": msg,
                "browserStatus": status,
                "needsSetup": status in ("not_running", "running_no_debug"),
            })

        # 3) CDP 读取 Cookie（无锁，可能耗时数秒）
        try:
            cookie_header = grab_cookies_via_cdp(port, target_domains)
        except BrowserNotReadyError as exc:
            return self.response({
                "cookieSaved": False,
                "message": str(exc),
                "browserStatus": "connection_failed",
                "needsSetup": False,
            })
        except BrowserDebugError as exc:
            return self.response({
                "cookieSaved": False,
                "message": f"读取 Cookie 失败：{exc}",
                "browserStatus": "read_failed",
                "needsSetup": False,
            })

        # 千牛特殊处理：cookie 必须含 _m_h5_tk + 用户标识（sn/unb/_tb_token_/tracknick 任一）
        # 才能用于采集。如果不完整，先自动跳 myseller 工作台等 5 秒重抓；仍不完整则返回失败，
        # 引导客户在浏览器里完成登录后再点「浏览器」按钮。
        if platform == "qn":
            def _qn_cookie_complete(c: str) -> bool:
                if not c:
                    return False
                if "_m_h5_tk=" not in c:
                    return False
                # 用户标识至少有一个（_tb_token_ 是 CSRF token 不算用户身份，淘宝接口需要 unb/sn 等）
                return any(("; " + m) in (";" + c) for m in ("sn=", "unb=", "tracknick=", "_nk_="))

            def _log_qn_cookie_fields(c: str, tag: str) -> None:
                keys = [p.split("=")[0].strip() for p in (c or "").split(";") if "=" in p]
                key_set = set(keys)
                key_markers = {
                    "_m_h5_tk": "_m_h5_tk" in key_set,
                    "sn": "sn" in key_set,
                    "unb": "unb" in key_set,
                    "_tb_token_": "_tb_token_" in key_set,
                    "tracknick": "tracknick" in key_set,
                    "_nk_": "_nk_" in key_set,
                    "lgc": "lgc" in key_set,
                    "cookie2": "cookie2" in key_set,
                }
                marker_text = ", ".join(f"{k}={'有' if v else '无'}" for k, v in key_markers.items())
                self.log(f"[千牛 cookie 诊断 {tag}] 长度 {len(c or '')}，字段数 {len(keys)}，关键字段：{marker_text}")

            _log_qn_cookie_fields(cookie_header, "首次抓取")

            if not _qn_cookie_complete(cookie_header):
                try:
                    from browser_debug_setup import open_url_in_existing_browser
                    self.log("千牛 cookie 不完整，自动跳转 myseller 工作台等待登录态颁发…")
                    open_url_in_existing_browser(port, "https://myseller.taobao.com/home.htm/QnworkbenchHome/")
                    import time as _time
                    _time.sleep(5)
                    cookie_header = grab_cookies_via_cdp(port, target_domains)
                    _log_qn_cookie_fields(cookie_header, "重抓后")
                except Exception as exc:
                    self.log(f"千牛 cookie 自动补齐失败：{exc}")

            if not _qn_cookie_complete(cookie_header):
                # 仍不完整 → 引导客户继续登录
                try:
                    from browser_debug_setup import open_url_in_existing_browser
                    open_url_in_existing_browser(port, "https://myseller.taobao.com/home.htm/QnworkbenchHome/")
                except Exception:
                    pass
                return self.response({
                    "cookieSaved": False,
                    "message": "千牛登录信息不完整。已为你打开工作台首页，请在浏览器里完成登录后，再点「浏览器」按钮。",
                    "browserStatus": "running_with_debug",
                    "needsSetup": False,
                    "loginPageOpened": True,
                    "platformLabel": "千牛",
                })

        if not cookie_header:
            # 浏览器在调试模式但没读到目标平台 cookie：自动新开标签页跳到登录页，引导客户登录
            from browser_debug_setup import PLATFORM_LOGIN_URLS, open_url_in_existing_browser
            login_url = PLATFORM_LOGIN_URLS.get(platform, "")
            platform_label = {"qn": "千牛", "jd": "京东", "pdd": "拼多多", "douyin": "抖店"}.get(platform, platform or "对应平台")
            login_page_opened = False
            if login_url:
                try:
                    open_url_in_existing_browser(port, login_url)
                    login_page_opened = True
                    self.log(f"已在浏览器里为客户打开 {platform_label} 登录页：{login_url}")
                except Exception as exc:
                    self.log(f"自动打开 {platform_label} 登录页失败（不影响后续手动登录）：{exc}")
            if login_page_opened:
                msg = f"已为你打开{platform_label}登录页。请在浏览器中完成登录后，再点一次「浏览器」按钮。"
            else:
                msg = f"未读取到{platform_label}登录信息，请先在浏览器里登录{platform_label}后台再点「浏览器」按钮。"
            return self.response({
                "cookieSaved": False,
                "message": msg,
                "browserStatus": "running_with_debug",
                "needsSetup": False,
                "loginPageOpened": login_page_opened,
                "platformLabel": platform_label,
            })

        # 4) 身份识别（无锁，可能调用平台 API）
        identity, shop_name = "", ""
        if platform == "douyin":
            identity, shop_name = _resolve_douyin_user_info(cookie_header, "", self.log)
        elif platform == "pdd":
            identity, _ = _resolve_pdd_user_info(cookie_header, self.log)
        elif platform == "jd":
            try:
                from jd_workload_capture import resolve_jd_pin_from_cookie
                identity = resolve_jd_pin_from_cookie(cookie_header)
            except Exception as exc:
                self.log(f"京东身份识别失败（不影响保存）：{exc}")
        else:
            try:
                identity = _resolve_qn_identity_from_cookie(cookie_header)
            except Exception as exc:
                self.log(f"千牛身份识别失败（不影响保存）：{exc}")

        # 5) 保存 state（短锁）
        with self.state_file_lock():
            state = self.load_state()
            account = self.find_account(state, account_id)
            if account is None:
                raise ValueError("登录账户不存在（保存阶段）。")

            now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            account["cookieProtected"] = protect_text(cookie_header)
            account["cookieUpdatedAt"] = now_text
            account["loginStatus"] = "已登录"
            account["lastError"] = ""
            account["lastFailureReason"] = ""

            if identity:
                account["lastKnownLoginAccount"] = identity
                if not str(account.get("loginHint") or "").strip():
                    account["loginHint"] = identity
            if shop_name and not str(account.get("shopName") or "").strip():
                account["shopName"] = shop_name

            self.save_state(state)
            public_state = self.public_state(state)

        self.log(f"从浏览器导入 Cookie 成功（长度 {len(cookie_header)}），识别身份：{identity or '未识别'}，店铺：{shop_name or '未识别'}。")
        return self.response({
            "cookieSaved": True,
            "identity": identity,
            "shopName": shop_name,
            "cookieLength": len(cookie_header),
            "state": public_state,
        })

    def capture_payload(self, state: MutableMapping[str, Any]) -> Mapping[str, Any]:
        if bool(state.get("directApiPreferred", True)):
            try:
                self.refresh_cookie_from_existing_shadow_for_capture(state)
                return self.direct_capture_func(state, self.log)
            except DirectApiCaptureError as exc:
                message = str(exc)
                if any(marker in message for marker in CONFIG_ERROR_MARKERS):
                    self.log(f"接口直采配置错误，请检查 F12 配置文件：{exc}")
                else:
                    self.log(f"接口直采未完成：{exc}，回退到影子浏览器表格采集。")
        return self.capture_func(state, self.log)

    def apply_capture_result(self, state: MutableMapping[str, Any], payload: Mapping[str, Any], reason: str) -> Dict[str, Any]:
        signature = payload_signature(payload)
        upload_message, upload_record = self.upload_func(state, payload, signature, reason)
        summary = format_employee_summary(payload)
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state["lastRunAt"] = now_text
        state["lastCaptureAt"] = now_text
        state["lastCaptureDate"] = str(payload.get("recordDate") or "")
        state["lastPayloadSignature"] = signature
        state["lastPayloadSummary"] = summary
        if upload_record is not None:
            history = state.get("uploadHistory")
            if not isinstance(history, dict):
                history = {}
            history[signature] = dict(upload_record)
            state["uploadHistory"] = history
            self._trim_upload_history(state)
            state["lastUploadAt"] = now_text
            state["lastUploadDate"] = str(payload.get("recordDate") or "")
        self.log(f"采集成功：{summary}")
        if upload_message:
            self.log(upload_message)
        return {
            "batch": False,
            "payload": payload,
            "signature": signature,
            "summary": summary,
            "uploadMessage": upload_message,
            "uploadRecord": upload_record,
            "state": self.public_state(state),
        }

    def refresh_cookie_from_existing_shadow_for_capture(self, state: Mapping[str, Any]) -> None:
        config_path_text = str(state.get("directApiConfigPath") or "").strip()
        if not config_path_text:
            return
        try:
            browser_state = inspect_existing_shadow_browser_state(state, lambda _message: None)
        except Exception:
            return
        cookie_header = str(browser_state.get("cookieHeader") or "").strip()
        if not cookie_header:
            return
        summary = summarize_cookie(cookie_header)
        if not (summary["hasMtopToken"] and (summary["hasSn"] or summary["hasUnb"] or summary["hasTbToken"])):
            return
        update_direct_api_cookie(Path(config_path_text), cookie_header)
        self.log(f"采集前已从已打开的影子浏览器刷新 Cookie：{format_cookie_diagnostics(cookie_header)}")

    def find_account(self, state: MutableMapping[str, Any], account_id: str) -> MutableMapping[str, Any] | None:
        for account in ensure_login_accounts(state, self.data_dir):
            if str(account.get("id") or "") == account_id:
                return account
        return None

    def public_state(self, state: MutableMapping[str, Any]) -> Dict[str, Any]:
        accounts = ensure_login_accounts(state, self.data_dir)
        public = dict(state)
        public.pop("douyinCsrfToken", None)
        public.pop("douyinCsrfTokenProtected", None)
        public["loginAccounts"] = [_public_account(account) for account in accounts]
        public["autoStartEnabled"] = bool(state.get("autoStartEnabled", False)) or is_autostart_enabled()
        return public

    def log(self, message: str) -> None:
        self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"), message=sanitize_sensitive_text(message)))

    @staticmethod
    def _trim_upload_history(state: MutableMapping[str, Any]) -> None:
        history = state.get("uploadHistory")
        if not isinstance(history, dict):
            return
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        stale_keys = []
        for key, entry in history.items():
            if isinstance(entry, dict):
                record_date = str(entry.get("recordDate") or "")
                if record_date and record_date < cutoff:
                    stale_keys.append(key)
        for key in stale_keys:
            del history[key]
        if len(history) > 500:
            for key in list(history.keys())[:len(history) - 500]:
                del history[key]


def upload_payload_with_state(
    state: MutableMapping[str, Any],
    payload: Mapping[str, Any],
    signature: str,
    capture_reason: str,
) -> tuple[str, Mapping[str, Any] | None]:
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
        result = upload_employee_payload(server_url, dict(payload), timeout_seconds=timeout_seconds)
    except UploadClientError as exc:
        return f"服务端上传失败：{sanitize_sensitive_text(exc)}", None
    upload_record = {
        "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "serverUrl": server_url.rstrip("/"),
        "recordDate": payload.get("recordDate"),
        "subAccount": payload.get("subAccount"),
    }
    return f"服务端上传成功：{result['message']}。", upload_record


def _version_parts(version: str) -> tuple[int, ...]:
    parts = []
    for segment in str(version or "").split("."):
        digits = ""
        for char in segment:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _version_is_newer(latest: str, current: str) -> bool:
    return _version_parts(latest) > _version_parts(current)


def _read_update_manifest_response(resp: Any) -> Dict[str, Any]:
    content_type = _response_content_type(resp)
    raw = resp.read()
    text = raw.decode("utf-8-sig")
    if content_type and "json" not in content_type:
        hint = "，可能被前端页面兜底" if text.lstrip().startswith("<") else ""
        raise ValueError(f"更新清单不是 JSON（Content-Type={content_type}{hint}）。")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"更新清单不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("更新清单根节点必须是 JSON 对象。")
    if not str(data.get("version") or "").strip():
        raise ValueError("更新清单缺少 version 字段。")
    return data


def _response_content_type(resp: Any) -> str:
    headers = getattr(resp, "headers", None)
    if headers is not None:
        if hasattr(headers, "get_content_type"):
            return str(headers.get_content_type() or "").strip().lower()
        try:
            return str(headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        except AttributeError:
            pass
    if hasattr(resp, "getheader"):
        return str(resp.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
    return ""


COMMANDS = {
    "get_state": SidecarApp.get_state,
    "save_settings": SidecarApp.save_settings,
    "start_login": SidecarApp.start_login,
    "poll_login": SidecarApp.poll_login,
    "check_login": SidecarApp.check_login,
    "capture_all": SidecarApp.capture_all,
    "capture_account": SidecarApp.capture_account,
    "capture_account_direct": SidecarApp.capture_account_direct,
    "account_create": SidecarApp.account_create,
    "account_update": SidecarApp.account_update,
    "account_delete": SidecarApp.account_delete,
    "import_cookie": SidecarApp.import_cookie,
    "setup_browser_debug": SidecarApp.setup_browser_debug,
    "relaunch_browser_for_debug": SidecarApp.relaunch_browser_for_debug,
    "grab_browser_cookie": SidecarApp.grab_browser_cookie,
    "check_update": SidecarApp.check_update,
    "shutdown": SidecarApp.shutdown,
}


def _cookie_summary_is_login_ready(summary: Mapping[str, Any]) -> bool:
    has_user_marker = bool(summary.get("hasSn") or summary.get("hasUnb"))
    return bool(summary.get("hasMtopToken") and has_user_marker and summary.get("mtopExpired") is not True)


def _browser_state_is_login_ready(
    browser_state: Mapping[str, Any],
    cookie_summary: Mapping[str, Any],
    platform: Any = "qn",
    cookie_header: str = "",
) -> bool:
    if normalize_platform(platform) == "jd":
        page_url = str(browser_state.get("pageUrl") or browser_state.get("url") or "").strip()
        cookie_name_set = set(_cookie_names(cookie_header))
        return bool(is_jd_login_success_page(page_url) and {"pin", "thor"}.issubset(cookie_name_set))
    if normalize_platform(platform) == "pdd":
        page_url = str(browser_state.get("pageUrl") or browser_state.get("url") or "").strip()
        flags = _pdd_cookie_flags(_cookie_names(cookie_header))
        return bool(is_pdd_login_success_page(page_url) and all(flags.values()))
    if normalize_platform(platform) == "douyin":
        page_url = str(browser_state.get("pageUrl") or browser_state.get("url") or "").strip()
        return bool(is_douyin_login_success_page(page_url) and cookie_header)
    return bool(browser_state.get("loggedIn") is True and _cookie_summary_is_login_ready(cookie_summary))


def _has_pending_login_session(config: Mapping[str, Any], account: Mapping[str, Any]) -> bool:
    status = str(account.get("loginStatus") or "").strip()
    if status not in LOGIN_PENDING_STATUSES or int(account.get("shadowChromePid") or 0) <= 0:
        return False
    return is_shadow_browser_running(config)


def _browser_state_from_account(config: Mapping[str, Any], account: Mapping[str, Any], reused: bool) -> Dict[str, Any]:
    active_port = int(account.get("activeChromePort") or config.get("activeChromePort") or 0)
    return {
        "chromePath": str(config.get("chromePath") or ""),
        "shadowChromeProfileDir": str(config.get("shadowChromeProfileDir") or config.get("chromeUserDataDir") or ""),
        "chromePort": int(config.get("chromePort") or 0),
        "activeChromePort": active_port,
        "shadowChromePid": int(account.get("shadowChromePid") or 0),
        "launched": False,
        "restarted": False,
        "reused": reused,
    }


def _lock_file(lock_file: Any) -> None:
    lock_file.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _unlock_file(lock_file: Any) -> None:
    lock_file.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _public_account(account: Mapping[str, Any]) -> Dict[str, Any]:
    public = dict(account)
    public["cookieStatus"] = _account_cookie_status(account)
    public.pop("cookieProtected", None)
    public.pop("douyinCsrfToken", None)
    public.pop("douyinCsrfTokenProtected", None)
    return public


def _clear_platform_credentials(account: MutableMapping[str, Any]) -> None:
    for key in (
        "cookieProtected",
        "cookieSummary",
        "cookieUpdatedAt",
        "douyinCsrfToken",
        "douyinCsrfTokenProtected",
        "activeChromePort",
        "shadowChromePid",
        "lastKnownLoginAccount",
    ):
        account.pop(key, None)
    account["chromePort"] = 0
    account["loginStatus"] = "待登录"
    account["lastError"] = ""
    account["lastResult"] = ""
    account["lastFailureReason"] = ""


def _safe_shop_id(value: Any) -> int:
    try:
        parsed = int(str(value or "").strip())
    except (TypeError, ValueError):
        return 0
    if parsed < 0 or parsed > 9007199254740991:
        return 0
    return parsed


def _account_cookie_status(account: Mapping[str, Any]) -> str:
    status = str(account.get("loginStatus") or "").strip()
    failure_reason = str(account.get("lastFailureReason") or "").strip()
    if failure_reason == "需要重新登录" or status == "需要重新登录":
        return "需重新登录"
    if status in {"已失效", "Cookie 已失效"} or "过期" in status or "失效" in status:
        return "已失效"
    if str(account.get("cookieProtected") or "").strip():
        return "已保存"
    return "未登录"


def _format_jd_login_diagnostics(browser_state: Mapping[str, Any], cookie_header: str) -> str:
    page_url = str(browser_state.get("pageUrl") or browser_state.get("url") or "").strip() or "--"
    cookie_names = _cookie_names(cookie_header)
    name_set = set(cookie_names)
    return (
        f"京东登录诊断：url={page_url}，"
        f"cookieCount={len(cookie_names)}，"
        f"cookieNames={','.join(cookie_names) or '--'}，"
        f"hasPin={_yes_no('pin' in name_set)}，"
        f"hasPtPin={_yes_no('pt_pin' in name_set)}，"
        f"hasThor={_yes_no('thor' in name_set)}"
    )


def _format_pdd_login_diagnostics(browser_state: Mapping[str, Any], cookie_header: str) -> str:
    page_url = str(browser_state.get("pageUrl") or browser_state.get("url") or "").strip() or "--"
    cookie_names = _cookie_names(cookie_header)
    flags = _pdd_cookie_flags(cookie_names)
    return (
        f"拼多多登录诊断：url={page_url}，"
        f"cookieCount={len(cookie_names)}，"
        f"cookieNames={','.join(cookie_names) or '--'}，"
        f"hasPassId={_yes_no(flags['hasPassId'])}，"
        f"hasJsessionId={_yes_no(flags['hasJsessionId'])}，"
        f"hasMmsCookie={_yes_no(flags['hasMmsCookie'])}，"
        f"hasWindowsShopToken={_yes_no(flags['hasWindowsShopToken'])}"
    )


def _pdd_cookie_flags(cookie_names: list[str]) -> Dict[str, bool]:
    name_set = set(cookie_names)
    return {
        "hasPassId": "PASS_ID" in name_set,
        "hasJsessionId": "JSESSIONID" in name_set,
        "hasMmsCookie": any(name.startswith("mms_") for name in name_set),
        "hasWindowsShopToken": any(name.startswith("windows_app_shop_token_") for name in name_set),
    }


def _cookie_names(cookie_header: str) -> list[str]:
    names: set[str] = set()
    for part in str(cookie_header or "").split(";"):
        name, sep, _value = part.strip().partition("=")
        if sep and name:
            names.add(name)
    return sorted(names)


def _yes_no(value: bool) -> str:
    return "是" if value else "否"


def _resolve_login_identity(browser_state: Mapping[str, Any], cookie_header: str) -> str:
    for key in ("currentNick", "loginAccount", "nick", "displayNick"):
        text = str(browser_state.get(key) or "").strip()
        if text:
            return text

    cookie_values: Dict[str, str] = {}
    for part in str(cookie_header or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            cookie_values[name] = value
    for name in ("sn", "_nk_", "tracknick", "lgc", "pin", "pt_pin"):
        value = str(cookie_values.get(name) or "").strip()
        if value:
            return unquote(value)
    return ""


def _resolve_douyin_user_info(cookie_header: str, csrf_token: str, log: Callable) -> tuple[str, str]:
    """调用抖店 currentuser 接口，返回 (客服名, 店铺名)。"""
    try:
        from douyin_workload_capture import fetch_douyin_current_user
        user_data = fetch_douyin_current_user(cookie_header, csrf_token=csrf_token)
        screen_name = str((user_data.get("CustomerServiceInfo") or {}).get("screen_name") or "").strip()
        shop_name = str(user_data.get("ShopName") or "").strip()
        return screen_name or shop_name, shop_name
    except Exception as exc:
        log(f"自动识别抖店身份失败（不影响 Cookie 保存）：{exc}")
        return "", ""


def _resolve_pdd_user_info(cookie_header: str, log: Callable) -> tuple[str, str]:
    """调用拼多多 csReportDetail 接口，返回 (客服名, 空)。"""
    try:
        from pdd_workload_capture import fetch_pdd_current_user
        user_data = fetch_pdd_current_user(cookie_header)
        cs_name = str(user_data.get("cs_name") or "").strip()
        return cs_name, ""
    except Exception as exc:
        log(f"自动识别拼多多身份失败（不影响 Cookie 保存）：{exc}")
        return "", ""


def _resolve_qn_identity_from_cookie(cookie_header: str) -> str:
    """从千牛 Cookie 中提取客服名（sn/_nk_/tracknick/lgc）。

    跳过 ``tb`` + 纯数字这种淘宝内部分配的子账号 ID（对客户没意义），
    避免把 ``tb992171539020`` 这种当成"识别名"显示。
    """
    import re as _re
    cookie_values: dict[str, str] = {}
    for part in str(cookie_header or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            cookie_values[name.strip()] = value.strip()
    # 优先用真实中文昵称
    for key in ("sn", "_nk_", "tracknick"):
        value = str(cookie_values.get(key) or "").strip()
        if value:
            return unquote(value)
    # lgc 兜底，但跳过 "tb<数字>" 这种内部 ID 模式
    lgc = unquote(str(cookie_values.get("lgc") or "").strip())
    if lgc and not _re.fullmatch(r"tb\d+", lgc):
        return lgc
    return ""


def _parse_cookie_import(raw_text: str) -> tuple[str, str]:
    """从 cURL 命令或纯 Cookie 字符串中提取 Cookie header 和 csrf-token。"""
    import re
    cookie_header = ""
    csrf_token = ""
    # cURL -H 'cookie: ...' 格式
    cookie_match = re.search(r"-H\s+['\"]cookie:\s*([^'\"]+)['\"]", raw_text, re.IGNORECASE)
    if cookie_match:
        cookie_header = cookie_match.group(1).strip()
    # cURL -b '...' 格式（PDD 使用此格式）
    if not cookie_header:
        b_match = re.search(r"\s-b\s+['\"]([^'\"]+)['\"]", raw_text)
        if b_match:
            cookie_header = b_match.group(1).strip()
    # x-secsdk-csrf-token（抖店）
    csrf_match = re.search(r"-H\s+['\"]x-secsdk-csrf-token:\s*([^'\"]+)['\"]", raw_text, re.IGNORECASE)
    if csrf_match:
        csrf_token = csrf_match.group(1).strip()
    # 如果不是 cURL 格式，当作纯 Cookie 字符串
    if not cookie_header:
        if "=" in raw_text and (";" in raw_text or raw_text.count("=") == 1):
            cookie_header = raw_text.strip()
    return cookie_header, csrf_token


def parse_payload(text: str | None) -> Dict[str, Any]:
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("payload 必须是 JSON 对象。")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="远盛数据助手 sidecar JSON CLI")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("payload", nargs="?", default="")
    parser.add_argument("--data-dir", default="")
    args = parser.parse_args(argv)

    app = SidecarApp(data_dir=Path(args.data_dir) if args.data_dir else None)
    try:
        payload = parse_payload(args.payload)
        result = COMMANDS[args.command](app, payload)
        write_json_line(result)
        return 0
    except Exception as exc:
        write_json_line({"ok": False, "message": sanitize_sensitive_text(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


