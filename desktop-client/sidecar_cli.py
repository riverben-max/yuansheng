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

from direct_api_capture import (
    DirectApiCaptureError,
    DirectApiLoginRequiredError,
    capture_with_direct_api,
    format_cookie_diagnostics,
    migrate_direct_api_cookie_config,
    summarize_cookie,
    update_direct_api_cookie,
)
from external_capture import LoginRequiredError, capture_with_external_chrome, inspect_existing_shadow_browser_state
from douyin_workload_capture import capture_douyin_workload
from jd_workload_capture import capture_jd_workload
from login_accounts import add_login_account, build_account_state, capture_enabled_accounts, ensure_login_accounts
from pdd_workload_capture import capture_pdd_workload
from platform_adapters import default_capture_adapters
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
from upload_client import UploadClientError, upload_employee_payload

APP_NAME = "远盛数据助手"
SIDECAR_VERSION = "1.0.0"
DEFAULT_SERVER_URL = "http://120.27.22.50"
CONFIG_ERROR_MARKERS = ("配置文件", "合法 JSON", "未启用", "缺少", "根节点", "config")
LOGIN_PENDING_STATUSES = {"等待登录", "等待扫码", "等待登录检测", "正在清理临时浏览器"}
_PROCESS_LOCK = threading.RLock()


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
        "uploadTimeoutSeconds": 10,
        "uploadHistory": {},
    }


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
        ensure_login_accounts(state, self.data_dir)
        return state

    def save_state(self, state: Mapping[str, Any]) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            state_json = json.dumps(dict(state), ensure_ascii=False, indent=2)
            state_size_mb = len(state_json.encode("utf-8")) / (1024 * 1024)
            if state_size_mb > 5:
                self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                                 message=f"配置文件较大（{state_size_mb:.1f}MB），建议清理历史数据。"))
            tmp_path = self.state_path.with_suffix(".json.tmp")
            tmp_path.write_text(state_json, encoding="utf-8", newline="\n")
            tmp_path.replace(self.state_path)
            backup = self.state_path.with_suffix(".json.bak")
            try:
                backup.write_text(state_json, encoding="utf-8", newline="\n")
            except Exception:
                pass
        except Exception as exc:
            self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"),
                             message=f"保存配置文件失败，请检查磁盘空间和权限：{exc}"))

    def response(self, data: Any = None) -> Dict[str, Any]:
        return {"ok": True, "data": data}

    @contextmanager
    def exclusive_operation_lock(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.data_dir / "sidecar.lock"
        with _PROCESS_LOCK:
            with lock_path.open("a+b") as lock_file:
                _lock_file(lock_file)
                try:
                    yield
                finally:
                    _unlock_file(lock_file)

    def get_state(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        result = self.public_state(state)
        result["sidecarVersion"] = SIDECAR_VERSION
        return self.response(result)

    def save_settings(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
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
        state = self.load_state()
        account = add_login_account(
            state,
            self.data_dir,
            display_name=str(payload.get("displayName") or "新登录账户"),
            login_hint=str(payload.get("loginHint") or ""),
            platform=str(payload.get("platform") or "qn"),
            shop_name=str(payload.get("shopName") or ""),
            shop_id=int(payload.get("shopId") or 0),
        )
        if "enabled" in payload:
            account["enabled"] = bool(payload.get("enabled"))
        self.save_state(state)
        return self.response(account)

    def account_update(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        state = self.load_state()
        account_id = str(payload.get("id") or "")
        account = self.find_account(state, account_id)
        if account is None:
            raise ValueError("登录账户不存在。")
        for key in ("displayName", "loginHint", "profileDir", "shopName"):
            if key in payload:
                account[key] = str(payload.get(key) or "").strip()
        if "shopId" in payload:
            account["shopId"] = int(payload.get("shopId") or 0)
        if "platform" in payload:
            account["platform"] = normalize_platform(payload.get("platform"))
        if "chromePort" in payload:
            account["chromePort"] = int(payload.get("chromePort") or 9222)
        if "enabled" in payload:
            account["enabled"] = bool(payload.get("enabled"))
        self.save_state(state)
        return self.response(account)

    def account_delete(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
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
            account["douyinCsrfToken"] = csrf_token
        # 自动识别登录身份
        platform = normalize_platform(account.get("platform"))
        identity, shop_name = "", ""
        if platform == "douyin":
            identity, shop_name = _resolve_douyin_user_info(cookie_header, csrf_token, self.log)
        elif platform == "pdd":
            identity, _ = _resolve_pdd_user_info(cookie_header, self.log)
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
        state = self.load_state()
        reason = str((payload or {}).get("reason") or "手动采集")
        self.emit(event("status", status="采集中", danger=False))
        try:
            accounts = ensure_login_accounts(state, self.data_dir)
            if accounts:
                results = capture_enabled_accounts(
                    state,
                    accounts,
                    reason=reason,
                    capture_func=self.direct_capture_func,
                    upload_func=self.upload_func,
                    log=self.log,
                    capture_adapters=default_capture_adapters(self.direct_capture_func, self.jd_capture_func, self.pdd_capture_func, self.douyin_capture_func),
                )
                state["lastRunAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._trim_upload_history(state)
                self.save_state(state)
                self.emit(event("status", status="待命", danger=False))
                return self.response({"batch": True, "results": results, "state": self.public_state(state)})
            payload_data = self.capture_payload(state)
            result = self.apply_capture_result(state, payload_data, reason)
            self.save_state(state)
            self.emit(event("status", status="待命", danger=False))
            return self.response(result)
        except (LoginRequiredError, DirectApiLoginRequiredError) as exc:
            self.emit(event("status", status="请先登录", danger=True))
            raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            self.emit(event("status", status="采集失败", danger=True))
            raise RuntimeError(str(exc)) from exc

    def capture_account(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
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
            capture_adapters=default_capture_adapters(self.direct_capture_func, self.jd_capture_func, self.pdd_capture_func, self.douyin_capture_func),
        )
        self.save_state(state)
        self.emit(event("status", status="待命", danger=False))
        return self.response({"batch": True, "results": results, "state": self.public_state(state)})

    def check_update(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        update_url = str(state.get("updateCheckUrl") or "").strip()
        if not update_url:
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION})
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(update_url, headers={"User-Agent": f"YuanshengDataAssistant/{SIDECAR_VERSION}"})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest = str(data.get("version") or "").strip()
            if latest and latest != SIDECAR_VERSION:
                return self.response({
                    "updateAvailable": True,
                    "currentVersion": SIDECAR_VERSION,
                    "latestVersion": latest,
                    "downloadUrl": str(data.get("downloadUrl") or ""),
                })
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION})
        except Exception as exc:
            self.log(f"检查更新失败：{exc}")
            return self.response({"updateAvailable": False, "currentVersion": SIDECAR_VERSION, "reason": str(exc)})

    def shutdown(self, _payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        state = self.load_state()
        shutdown_shadow_browser(state, self.log)
        return self.response({"closed": True})

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
        public["loginAccounts"] = [_public_account(account) for account in accounts]
        public["autoStartEnabled"] = bool(state.get("autoStartEnabled", False)) or is_autostart_enabled()
        return public

    def log(self, message: str) -> None:
        self.emit(event("log", time=datetime.now().strftime("%H:%M:%S"), message=message))

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
        return f"服务端上传失败：{exc}", None
    upload_record = {
        "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "serverUrl": server_url.rstrip("/"),
        "recordDate": payload.get("recordDate"),
        "subAccount": payload.get("subAccount"),
    }
    return f"服务端上传成功：{result['message']}。", upload_record


COMMANDS = {
    "get_state": SidecarApp.get_state,
    "save_settings": SidecarApp.save_settings,
    "start_login": SidecarApp.start_login,
    "poll_login": SidecarApp.poll_login,
    "check_login": SidecarApp.check_login,
    "capture_all": SidecarApp.capture_all,
    "capture_account": SidecarApp.capture_account,
    "account_create": SidecarApp.account_create,
    "account_update": SidecarApp.account_update,
    "account_delete": SidecarApp.account_delete,
    "import_cookie": SidecarApp.import_cookie,
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
    return public


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
        write_json_line({"ok": False, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
