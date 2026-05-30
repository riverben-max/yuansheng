from __future__ import annotations

import os
from pathlib import Path
import json
from contextlib import contextmanager
from types import SimpleNamespace
import tempfile
import threading
import time
import unittest

import sidecar_cli
from sidecar_cli import SidecarApp


PDD_VISITOR_COOKIE = (
    "_a42=visitor-a42; _bee=visitor-bee; _f77=visitor-f77; _nano_fp=visitor-nano; "
    "api_uid=visitor-api; msfe-pc-cookie-captcha-token=visitor-captcha; "
    "rckk=visitor-rckk; ru1k=visitor-ru1k; ru2k=visitor-ru2k; webp=1"
)
PDD_SUCCESS_COOKIE = (
    f"{PDD_VISITOR_COOKIE}; JSESSIONID=secret-session; PASS_ID=secret-pass; "
    "mms_b84d1838=secret-mms; windows_app_shop_token_23=secret-shop-token; "
    "x-visit-time=secret-visit-time"
)


class SidecarStateTests(unittest.TestCase):
    def test_write_json_line_writes_utf8_bytes(self) -> None:
        class FakeStdout:
            def __init__(self) -> None:
                self.buffer = self
                self.data = b""

            def write(self, data: bytes) -> None:
                self.data += data

            def flush(self) -> None:
                pass

        fake = FakeStdout()
        original_stdout = sidecar_cli.sys.stdout
        sidecar_cli.sys.stdout = fake
        try:
            sidecar_cli.write_json_line({"message": "默认账号"})
        finally:
            sidecar_cli.sys.stdout = original_stdout

        decoded = fake.data.decode("utf-8")
        self.assertEqual(json.loads(decoded)["message"], "默认账号")
        self.assertIn("默认账号", decoded)

    def test_get_state_creates_default_account_without_bom_sensitive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)

            result = app.get_state({})

        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["serverUrl"], sidecar_cli.DEFAULT_SERVER_URL)
        self.assertEqual(len(data["loginAccounts"]), 1)
        self.assertEqual(data["loginAccounts"][0]["id"], "default")

    def test_get_state_initializes_direct_api_template_without_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)

            result = app.get_state({})
            config_path = data_dir / "direct_api_capture.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))

            self.assertTrue(result["ok"])
            self.assertTrue(config["enabled"])
            self.assertNotIn("cookie", config)
            self.assertNotIn("cookieProtected", config)
            self.assertIsInstance(config["requests"], list)
            self.assertGreaterEqual(len(config["requests"]), 1)
            self.assertTrue(result["data"]["directApiConfigReady"])

    def test_public_state_hides_protected_cookie_but_keeps_capture_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:secret"
            state["loginAccounts"][0]["douyinCsrfToken"] = "plain-csrf"
            state["loginAccounts"][0]["douyinCsrfTokenProtected"] = "dpapi:v1:csrf"
            state["loginAccounts"][0]["lastCaptureSummary"] = {
                "ok": True,
                "displayName": "林志玲",
                "recordDate": "2026-05-09",
            }

            result = app.public_state(state)

        public_account = result["loginAccounts"][0]
        self.assertNotIn("cookieProtected", public_account)
        self.assertNotIn("douyinCsrfToken", public_account)
        self.assertNotIn("douyinCsrfTokenProtected", public_account)
        self.assertEqual(public_account["lastCaptureSummary"]["displayName"], "林志玲")

    def test_save_settings_persists_schedule_and_runtime_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_ensure_autostart = sidecar_cli.ensure_autostart
            original_is_autostart_enabled = sidecar_cli.is_autostart_enabled
            calls = []
            sidecar_cli.ensure_autostart = lambda enabled: calls.append(enabled)
            sidecar_cli.is_autostart_enabled = lambda: False
            try:
                result = app.save_settings(
                    {
                        "serverUrl": "http://example.com",
                        "scheduleTime": "03:00",
                        "scheduleEnabled": False,
                        "autoStartEnabled": True,
                        "shadowChromeAutoLaunch": True,
                        "exitRequiresConfirm": False,
                    }
                )
                reloaded = app.load_state()
            finally:
                sidecar_cli.ensure_autostart = original_ensure_autostart
                sidecar_cli.is_autostart_enabled = original_is_autostart_enabled

        self.assertTrue(result["ok"])
        self.assertEqual(calls, [True])
        self.assertEqual(reloaded["serverUrl"], "http://example.com")
        self.assertEqual(reloaded["scheduleTime"], "03:00")
        self.assertFalse(reloaded["scheduleEnabled"])
        self.assertTrue(reloaded["shadowChromeAutoLaunch"])
        self.assertFalse(reloaded["exitRequiresConfirm"])

    def test_state_writing_commands_hold_file_lock_across_load_mutate_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_lock = app.state_file_lock
            depth = {"value": 0}
            observed = []

            @contextmanager
            def tracking_lock():
                with original_lock():
                    depth["value"] += 1
                    try:
                        yield
                    finally:
                        depth["value"] -= 1

            def observed_load_state():
                observed.append(("load", depth["value"]))
                return SidecarApp.load_state(app)

            def observed_save_state(state):
                observed.append(("save", depth["value"]))
                return SidecarApp.save_state(app, state)

            app.state_file_lock = tracking_lock
            app.load_state = observed_load_state
            app.save_state = observed_save_state

            app.save_settings({"scheduleTime": "10:30"})

        self.assertIn(("load", 1), observed)
        self.assertIn(("save", 1), observed)

    def test_capture_all_releases_state_lock_during_capture_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"] = [
                {
                    "id": "default",
                    "displayName": "默认账号",
                    "platform": "qn",
                    "enabled": True,
                    "cookieProtected": "dpapi:v1:cookie",
                }
            ]
            app.save_state(state)

            original_lock = app.state_file_lock
            depth = {"value": 0}
            capture_depths = []

            @contextmanager
            def tracking_lock():
                with original_lock():
                    depth["value"] += 1
                    try:
                        yield
                    finally:
                        depth["value"] -= 1

            def fake_capture(_config, _log):
                capture_depths.append(depth["value"])
                return {
                    "loginAccount": "shop",
                    "recordDate": "2026-05-12",
                    "subAccount": "客服A",
                }

            app.state_file_lock = tracking_lock
            app.direct_capture_func = fake_capture
            app.upload_func = lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"})

            result = app.capture_all({"reason": "手动采集"})

        self.assertTrue(result["ok"])
        self.assertEqual(capture_depths, [0])


class SidecarAccountTests(unittest.TestCase):
    def test_account_create_update_delete_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_is_autostart_enabled = sidecar_cli.is_autostart_enabled
            sidecar_cli.is_autostart_enabled = lambda: False

            try:
                created = app.account_create(
                    {
                        "displayName": "张三",
                        "loginHint": "zhangsan",
                        "platform": "jd",
                        "shopName": "医谷特膳膳养道专卖店",
                    }
                )
                account_id = created["data"]["id"]
                updated = app.account_update(
                    {
                        "id": account_id,
                        "displayName": "张三客服",
                        "enabled": False,
                        "chromePort": 9333,
                        "platform": "bad",
                        "shopName": "远盛电商",
                    }
                )
                deleted = app.account_delete({"id": account_id})
                state = app.load_state()
            finally:
                sidecar_cli.is_autostart_enabled = original_is_autostart_enabled

        self.assertTrue(created["ok"])
        self.assertEqual(created["data"]["platform"], "jd")
        self.assertEqual(created["data"]["shopName"], "医谷特膳膳养道专卖店")
        self.assertEqual(updated["data"]["displayName"], "张三客服")
        self.assertFalse(updated["data"]["enabled"])
        self.assertEqual(updated["data"]["chromePort"], 9333)
        self.assertEqual(updated["data"]["platform"], "qn")
        self.assertEqual(updated["data"]["shopName"], "远盛电商")
        self.assertEqual(deleted["data"]["id"], account_id)
        self.assertNotIn(account_id, [item["id"] for item in state["loginAccounts"]])

    def test_account_create_update_keeps_pdd_platform_in_public_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_is_autostart_enabled = sidecar_cli.is_autostart_enabled
            sidecar_cli.is_autostart_enabled = lambda: False

            try:
                created = app.account_create(
                    {
                        "displayName": "拼多多账号",
                        "loginHint": "pdd-user",
                        "platform": "pdd",
                        "shopName": "拼多多远盛店",
                        "shopId": 42,
                    }
                )
                account_id = created["data"]["id"]
                updated = app.account_update(
                    {
                        "id": account_id,
                        "platform": "pdd",
                        "shopName": "拼多多远盛旗舰店",
                        "shopId": 43,
                    }
                )
                public_state = app.get_state({})["data"]
            finally:
                sidecar_cli.is_autostart_enabled = original_is_autostart_enabled

        public_account = next(item for item in public_state["loginAccounts"] if item["id"] == account_id)
        self.assertEqual(created["data"]["platform"], "pdd")
        self.assertEqual(updated["data"]["platform"], "pdd")
        self.assertEqual(created["data"]["shopId"], 42)
        self.assertEqual(updated["data"]["shopId"], 43)
        self.assertEqual(public_account["platform"], "pdd")
        self.assertEqual(public_account["shopName"], "拼多多远盛旗舰店")
        self.assertEqual(public_account["shopId"], 43)

    def test_account_update_clears_platform_specific_credentials_when_platform_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            account = state["loginAccounts"][0]
            account.update(
                {
                    "platform": "douyin",
                    "cookieProtected": "dpapi:v1:cookie",
                    "douyinCsrfTokenProtected": "dpapi:v1:csrf",
                    "lastKnownLoginAccount": "douyin-user",
                    "cookieUpdatedAt": "2026-05-18 09:00:00",
                    "activeChromePort": 9333,
                }
            )
            app.save_state(state)

            result = app.account_update({"id": "default", "platform": "jd"})
            reloaded = app.load_state()

        self.assertTrue(result["ok"])
        account = reloaded["loginAccounts"][0]
        self.assertEqual(account["platform"], "jd")
        self.assertNotIn("cookieProtected", account)
        self.assertNotIn("douyinCsrfTokenProtected", account)
        self.assertEqual(account.get("lastKnownLoginAccount", ""), "")
        self.assertEqual(account["loginStatus"], "待登录")

    def test_import_cookie_without_new_douyin_csrf_clears_old_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            account = state["loginAccounts"][0]
            account["platform"] = "douyin"
            account["douyinCsrfTokenProtected"] = "dpapi:v1:old-csrf"
            app.save_state(state)

            original_protect = sidecar_cli.protect_text
            original_resolve = sidecar_cli._resolve_douyin_user_info
            sidecar_cli.protect_text = lambda value: f"dpapi:v1:{value}"
            sidecar_cli._resolve_douyin_user_info = lambda _cookie, _csrf, _log: ("dy-user", "抖店远盛店")
            try:
                result = app.import_cookie({"accountId": "default", "cookieText": "sessionid=abc; uid=1"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.protect_text = original_protect
                sidecar_cli._resolve_douyin_user_info = original_resolve

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertNotIn("douyinCsrfToken", account)
        self.assertNotIn("douyinCsrfTokenProtected", account)
        self.assertNotIn("douyinCsrfTokenProtected", result["data"]["state"]["loginAccounts"][0])

    def test_start_login_requires_selected_account(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.launch_shadow_browser_for_login = lambda _config, _log: (_ for _ in ()).throw(
                AssertionError("should not launch")
            )
            try:
                with self.assertRaises(ValueError) as context:
                    app.start_login({})
            finally:
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertEqual(str(context.exception), "请选择一个登录账号。")

    def test_start_login_closes_known_shadow_browsers_and_opens_selected_fixed_profile(self) -> None:
        shutdown_calls = []
        opened_configs = []

        def fake_shutdown(config, _log):
            shutdown_calls.append(
                (
                    str(config.get("shadowChromeProfileDir") or ""),
                    int(config.get("chromePort") or 0),
                )
            )
            return 1

        def fake_launch(config, _log):
            opened_configs.append(dict(config))
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=1234,
                launched=True,
                restarted=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["shadowChromeProfileDir"] = str(data_dir / "profiles" / "default")
            state["chromeUserDataDir"] = str(data_dir / "profiles" / "default")
            state["chromePort"] = 9222
            state["loginAccounts"] = [
                {
                    "id": "default",
                    "displayName": "默认账号",
                    "profileDir": str(data_dir / "profiles" / "default"),
                    "chromePort": 9222,
                    "enabled": True,
                },
                {
                    "id": "account-2",
                    "displayName": "测试账户",
                    "profileDir": str(data_dir / "profiles" / "account-2"),
                    "chromePort": 9223,
                    "enabled": True,
                },
            ]
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            try:
                result = app.start_login({"accountId": "account-2"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertTrue(result["ok"])
        self.assertEqual(
            shutdown_calls,
            [
                (str(data_dir / "profiles" / "default"), 9222),
                (str(data_dir / "profiles" / "account-2"), 9223),
            ],
        )
        self.assertEqual(len(opened_configs), 1)
        self.assertEqual(opened_configs[0]["shadowChromeProfileDir"], str(data_dir / "profiles" / "account-2"))
        self.assertEqual(opened_configs[0]["chromePort"], 0)
        account_2 = next(item for item in reloaded["loginAccounts"] if item["id"] == "account-2")
        self.assertEqual(account_2["activeChromePort"], 45678)
        self.assertEqual(result["data"]["browser"]["activeChromePort"], 45678)

    def test_start_login_forces_legacy_account_to_auto_port_and_records_runtime_port(self) -> None:
        opened_configs = []

        def fake_launch(config, _log):
            opened_configs.append(dict(config))
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=1234,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 0
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            try:
                result = app.start_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertTrue(result["ok"])
        self.assertEqual(opened_configs[0]["chromePort"], 0)
        self.assertEqual(result["data"]["browser"]["activeChromePort"], 45678)
        self.assertEqual(reloaded["loginAccounts"][0]["activeChromePort"], 45678)

    def test_start_login_uses_platform_login_start_url(self) -> None:
        opened_configs = []

        def fake_launch(config, _log):
            opened_configs.append(dict(config))
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=1234,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"] = [
                {
                    "id": "qn-account",
                    "platform": "qn",
                    "displayName": "千牛账号",
                    "profileDir": str(data_dir / "profiles" / "qn"),
                    "chromePort": 9222,
                    "enabled": True,
                },
                {
                    "id": "jd-account",
                    "platform": "jd",
                    "displayName": "京东账号",
                    "profileDir": str(data_dir / "profiles" / "jd"),
                    "chromePort": 9223,
                    "enabled": True,
                },
                {
                    "id": "pdd-account",
                    "platform": "pdd",
                    "displayName": "拼多多账号",
                    "profileDir": str(data_dir / "profiles" / "pdd"),
                    "chromePort": 9224,
                    "enabled": True,
                },
            ]
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 0
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            try:
                qn_result = app.start_login({"accountId": "qn-account"})
                reloaded = app.load_state()
                reloaded["loginAccounts"][0]["loginStatus"] = "登录窗口已关闭"
                reloaded["loginAccounts"][0]["shadowChromePid"] = 0
                app.save_state(reloaded)
                jd_result = app.start_login({"accountId": "jd-account"})
                reloaded = app.load_state()
                reloaded["loginAccounts"][1]["loginStatus"] = "登录窗口已关闭"
                reloaded["loginAccounts"][1]["shadowChromePid"] = 0
                app.save_state(reloaded)
                pdd_result = app.start_login({"accountId": "pdd-account"})
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertTrue(qn_result["ok"])
        self.assertTrue(jd_result["ok"])
        self.assertTrue(pdd_result["ok"])
        self.assertEqual(opened_configs[0]["shadowChromeStartupUrl"], sidecar_cli.QN_LOGIN_URL)
        self.assertEqual(opened_configs[1]["shadowChromeStartupUrl"], sidecar_cli.JD_LOGIN_URL)
        self.assertEqual(opened_configs[2]["shadowChromeStartupUrl"], sidecar_cli.PDD_LOGIN_URL)

    def test_concurrent_start_login_reuses_single_login_session(self) -> None:
        opened_configs = []
        call_lock = threading.Lock()

        def fake_shutdown(_config, _log):
            time.sleep(0.02)
            return 0

        def fake_launch(config, _log):
            time.sleep(0.05)
            with call_lock:
                opened_configs.append(dict(config))
                pid = 2000 + len(opened_configs)
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=pid,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            original_alive = sidecar_cli.is_shadow_browser_running
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            sidecar_cli.is_shadow_browser_running = lambda _config: bool(opened_configs)
            errors = []
            results = []

            def worker() -> None:
                try:
                    result = app.start_login({"accountId": "default"})
                    with call_lock:
                        results.append(result)
                except Exception as exc:
                    with call_lock:
                        errors.append(exc)

            try:
                threads = [threading.Thread(target=worker) for _ in range(10)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=3)
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch
                sidecar_cli.is_shadow_browser_running = original_alive

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 10)
        self.assertEqual(len(opened_configs), 1)

    def test_start_login_reopens_when_pending_browser_was_closed(self) -> None:
        opened_configs = []

        def fake_launch(config, _log):
            opened_configs.append(dict(config))
            pid = 3000 + len(opened_configs)
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=pid,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            original_alive = sidecar_cli.is_shadow_browser_running
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 0
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            sidecar_cli.is_shadow_browser_running = lambda _config: False
            try:
                first = app.start_login({"accountId": "default"})
                second = app.start_login({"accountId": "default"})
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch
                sidecar_cli.is_shadow_browser_running = original_alive

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(opened_configs), 2)
        self.assertFalse(second["data"]["browser"]["reused"])
        self.assertEqual(second["data"]["browser"]["shadowChromePid"], 3002)

    def test_closed_browser_then_repeated_start_login_opens_one_new_session(self) -> None:
        opened_configs = []
        results = []
        errors = []
        call_lock = threading.Lock()
        browser_alive = {"value": True}

        def fake_launch(config, _log):
            time.sleep(0.05)
            with call_lock:
                opened_configs.append(dict(config))
                browser_alive["value"] = True
                pid = 4000 + len(opened_configs)
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=pid,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            app.save_state(state)

            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            original_alive = sidecar_cli.is_shadow_browser_running
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 0
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            sidecar_cli.is_shadow_browser_running = lambda _config: browser_alive["value"]

            try:
                first = app.start_login({"accountId": "default"})
                browser_alive["value"] = False

                def worker() -> None:
                    try:
                        result = app.start_login({"accountId": "default"})
                        with call_lock:
                            results.append(result)
                    except Exception as exc:
                        with call_lock:
                            errors.append(exc)

                threads = [threading.Thread(target=worker) for _ in range(10)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=3)
            finally:
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch
                sidecar_cli.is_shadow_browser_running = original_alive

        self.assertTrue(first["ok"])
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 10)
        self.assertEqual(len(opened_configs), 2)
        self.assertEqual(sum(1 for item in results if item["data"]["browser"]["reused"] is False), 1)
        self.assertEqual(sum(1 for item in results if item["data"]["browser"]["reused"] is True), 9)

    def test_poll_login_closed_browser_allows_next_start_login(self) -> None:
        opened_configs = []

        def fake_inspect(_config, _log):
            raise sidecar_cli.ShadowBrowserError("影子浏览器未启动")

        def fake_launch(config, _log):
            opened_configs.append(dict(config))
            return SimpleNamespace(
                page=None,
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=str(config["shadowChromeProfileDir"]),
                port=45678,
                pid=5001,
                launched=True,
                restarted=False,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["shadowChromePid"] = 4999
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_alive = sidecar_cli.is_shadow_browser_running
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.is_shadow_browser_running = lambda _config: False
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 0
            sidecar_cli.launch_shadow_browser_for_login = fake_launch
            try:
                poll_result = app.poll_login({"accountId": "default"})
                after_poll = app.load_state()
                start_result = app.start_login({"accountId": "default"})
                after_start = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.is_shadow_browser_running = original_alive
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertEqual(poll_result["data"]["status"], "登录窗口已关闭")
        self.assertEqual(after_poll["loginAccounts"][0]["loginStatus"], "登录窗口已关闭")
        self.assertEqual(after_poll["loginAccounts"][0]["shadowChromePid"], 0)
        self.assertTrue(start_result["ok"])
        self.assertFalse(start_result["data"]["browser"]["reused"])
        self.assertEqual(after_start["loginAccounts"][0]["loginStatus"], "等待登录")
        self.assertEqual(after_start["loginAccounts"][0]["shadowChromePid"], 5001)
        self.assertEqual(len(opened_configs), 1)

    def test_start_login_waits_for_poll_login_lock(self) -> None:
        inspect_entered = threading.Event()
        release_inspect = threading.Event()
        errors = []
        results = []
        call_lock = threading.Lock()
        shutdown_calls = []
        launch_calls = []

        def fake_inspect(_config, _log):
            inspect_entered.set()
            self.assertTrue(release_inspect.wait(timeout=3))
            return {"cookieHeader": "", "shadowChromePid": os.getpid()}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 9222
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["shadowChromePid"] = os.getpid()
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_alive = sidecar_cli.is_shadow_browser_running
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.is_shadow_browser_running = lambda _config: True
            sidecar_cli.shutdown_shadow_browser = lambda config, _log: shutdown_calls.append(dict(config)) or 0
            sidecar_cli.launch_shadow_browser_for_login = lambda config, _log: launch_calls.append(dict(config))

            def run_poll() -> None:
                try:
                    result = app.poll_login({"accountId": "default"})
                    with call_lock:
                        results.append(("poll", result))
                except Exception as exc:
                    with call_lock:
                        errors.append(exc)

            def run_start() -> None:
                try:
                    result = app.start_login({"accountId": "default"})
                    with call_lock:
                        results.append(("start", result))
                except Exception as exc:
                    with call_lock:
                        errors.append(exc)

            try:
                poll_thread = threading.Thread(target=run_poll)
                poll_thread.start()
                self.assertTrue(inspect_entered.wait(timeout=3))
                start_thread = threading.Thread(target=run_start)
                start_thread.start()
                time.sleep(0.05)
                self.assertEqual(results, [])
                release_inspect.set()
                poll_thread.join(timeout=3)
                start_thread.join(timeout=3)
                final_state = app.load_state()
            finally:
                release_inspect.set()
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.is_shadow_browser_running = original_alive
                sidecar_cli.shutdown_shadow_browser = original_shutdown
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertEqual(errors, [])
        self.assertEqual([name for name, _result in results], ["poll", "start"])
        start_result = results[1][1]
        self.assertTrue(start_result["ok"])
        self.assertTrue(start_result["data"]["browser"]["reused"])
        self.assertEqual(shutdown_calls, [])
        self.assertEqual(launch_calls, [])
        self.assertEqual(final_state["loginAccounts"][0]["loginStatus"], "等待扫码")

    def test_poll_login_requires_selected_account(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)

            with self.assertRaises(ValueError) as context:
                app.poll_login({})

        self.assertEqual(str(context.exception), "请选择一个登录账号。")

    def test_poll_login_waits_when_cookie_is_not_valid_yet(self) -> None:
        shutdown_calls = []

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": "_m_h5_tk=token_1777188499080",
                "currentNick": "",
                "shadowChromePid": 2345,
            }

        def fake_shutdown(config, _log):
            shutdown_calls.append(config)
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 9222
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])
        self.assertEqual(shutdown_calls, [])

    def test_poll_login_does_not_close_or_save_cookie_on_login_page(self) -> None:
        shutdown_calls = []
        cookie = "_m_h5_tk=abc_1999999999999; sn=%E6%9E%97%E5%BF%97%E7%8E%B2; _tb_token_=token"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": False,
                "pageUrl": "https://loginmyseller.taobao.com/",
                "pageTitle": "千牛登录",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fake_shutdown(config, _log):
            shutdown_calls.append(config)
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], 2345)
        self.assertEqual(reloaded["loginAccounts"][0]["activeChromePort"], 45678)
        self.assertEqual(shutdown_calls, [])

    def test_poll_login_requires_strong_user_cookie_marker_before_closing(self) -> None:
        shutdown_calls = []
        cookie = "_m_h5_tk=abc_1999999999999; tracknick=%E6%9E%97%E5%BF%97%E7%8E%B2; _tb_token_=token"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": True,
                "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
                "pageTitle": "千牛工作台",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fake_shutdown(config, _log):
            shutdown_calls.append(config)
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])
        self.assertEqual(shutdown_calls, [])

    def test_poll_login_for_jd_waits_on_passport_page_without_saving_cookie(self) -> None:
        shutdown_calls = []
        cookie = "thor=jd-token; pin=jd-user"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": False,
                "pageUrl": "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F",
                "pageTitle": "京东登录",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "jd"
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.shutdown_shadow_browser = lambda config, _log: shutdown_calls.append(config) or 1
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], 2345)
        self.assertEqual(shutdown_calls, [])

    def test_poll_login_for_jd_logs_cookie_names_without_cookie_values(self) -> None:
        events = []
        cookie = "thor=secret-thor; pin=secret-pin; pt_pin=secret-pt-pin; __jda=secret-jda"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": False,
                "pageUrl": "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F",
                "pageTitle": "京东登录",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=events.append)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "jd"
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            try:
                app.poll_login({"accountId": "default"})
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect

        diagnostic_logs = [
            str(item.get("message") or "")
            for item in events
            if item.get("type") == "log" and "京东登录诊断" in str(item.get("message") or "")
        ]
        self.assertEqual(len(diagnostic_logs), 1)
        diagnostic = diagnostic_logs[0]
        self.assertIn("url=https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F", diagnostic)
        self.assertIn("cookieCount=4", diagnostic)
        self.assertIn("cookieNames=__jda,pin,pt_pin,thor", diagnostic)
        self.assertIn("hasPin=是", diagnostic)
        self.assertIn("hasPtPin=是", diagnostic)
        self.assertIn("hasThor=是", diagnostic)
        self.assertNotIn("secret", diagnostic)
        self.assertNotIn("secret-thor", diagnostic)

    def test_poll_login_for_pdd_login_page_logs_diagnostics_but_does_not_save_cookie(self) -> None:
        events = []
        shutdown_calls = []
        cookie = PDD_VISITOR_COOKIE

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": True,
                "pageUrl": "https://mms.pinduoduo.com/login/?redirectUrl=https%3A%2F%2Fmms.pinduoduo.com%2F",
                "pageTitle": "拼多多商家后台",
                "currentNick": "拼多多远盛店",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fail_protect(_value):
            raise AssertionError("3A 不应保存拼多多 Cookie 成功态")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=events.append)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "pdd"
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = fail_protect
            sidecar_cli.shutdown_shadow_browser = lambda config, _log: shutdown_calls.append(config) or 1
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertNotIn("cookieProtected", account)
        self.assertEqual(account["loginStatus"], "等待扫码")
        self.assertEqual(shutdown_calls, [])
        diagnostic_logs = [
            str(item.get("message") or "")
            for item in events
            if item.get("type") == "log" and "拼多多登录诊断" in str(item.get("message") or "")
        ]
        self.assertEqual(len(diagnostic_logs), 1)
        diagnostic = diagnostic_logs[0]
        self.assertIn("url=https://mms.pinduoduo.com/login/?redirectUrl=https%3A%2F%2Fmms.pinduoduo.com%2F", diagnostic)
        self.assertIn("cookieCount=10", diagnostic)
        self.assertIn("cookieNames=_a42,_bee,_f77,_nano_fp,api_uid,msfe-pc-cookie-captcha-token,rckk,ru1k,ru2k,webp", diagnostic)
        self.assertIn("hasPassId=否", diagnostic)
        self.assertIn("hasJsessionId=否", diagnostic)
        self.assertIn("hasMmsCookie=否", diagnostic)
        self.assertIn("hasWindowsShopToken=否", diagnostic)
        self.assertNotIn("secret", diagnostic)

    def test_poll_login_for_pdd_home_saves_cookie_and_hides_protected_cookie(self) -> None:
        shutdown_calls = []
        protected_cookie = "dpapi:v1:pdd-cookie"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": PDD_SUCCESS_COOKIE,
                "loggedIn": False,
                "pageUrl": "https://mms.pinduoduo.com/home/",
                "pageTitle": "首页",
                "currentNick": "拼多多远盛店",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fake_shutdown(config, _log):
            shutdown_calls.append(
                (
                    str(config.get("shadowChromeProfileDir") or ""),
                    int(config.get("activeChromePort") or config.get("chromePort") or 0),
                )
            )
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "pdd"
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "pdd")
            state["loginAccounts"][0]["chromePort"] = 0
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = lambda value: protected_cookie
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "已登录")
        self.assertEqual(account["cookieProtected"], protected_cookie)
        self.assertEqual(account["loginStatus"], "已登录")
        self.assertEqual(account["lastKnownLoginAccount"], "拼多多远盛店")
        self.assertTrue(account["cookieUpdatedAt"])
        self.assertEqual(shutdown_calls, [(str(data_dir / "profiles" / "pdd"), 45678)])
        self.assertNotIn("activeChromePort", account)
        public_account = result["data"]["state"]["loginAccounts"][0]
        self.assertNotIn("cookieProtected", public_account)
        self.assertEqual(public_account["cookieStatus"], "已保存")

    def test_poll_login_for_pdd_chat_overview_saves_cookie(self) -> None:
        protected_cookie = "dpapi:v1:pdd-cookie"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": PDD_SUCCESS_COOKIE,
                "loggedIn": False,
                "pageUrl": "https://mms.pinduoduo.com/mms-chat/overview/merchant",
                "pageTitle": "拼多多商家后台",
                "currentNick": "拼多多远盛店",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "pdd"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = lambda value: protected_cookie
            sidecar_cli.shutdown_shadow_browser = lambda _config, _log: 1
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["data"]["loggedIn"])
        self.assertEqual(reloaded["loginAccounts"][0]["cookieProtected"], protected_cookie)

    def test_poll_login_for_pdd_missing_required_cookie_keeps_waiting(self) -> None:
        required_parts = {
            "JSESSIONID": "JSESSIONID=secret-session",
            "PASS_ID": "PASS_ID=secret-pass",
            "mms": "mms_b84d1838=secret-mms",
            "shop_token": "windows_app_shop_token_23=secret-shop-token",
        }

        for missing_key in required_parts:
            with self.subTest(missing_key=missing_key):
                cookie = "; ".join(
                    [PDD_VISITOR_COOKIE]
                    + [value for key, value in required_parts.items() if key != missing_key]
                    + ["x-visit-time=secret-visit-time"]
                )

                def fake_inspect(_config, _log):
                    return {
                        "cookieHeader": cookie,
                        "loggedIn": True,
                        "pageUrl": "https://mms.pinduoduo.com/home/",
                        "pageTitle": "首页",
                        "currentNick": "拼多多远盛店",
                        "shadowChromePid": 2345,
                        "activeChromePort": 45678,
                    }

                def fail_protect(_value):
                    raise AssertionError("缺少拼多多关键 Cookie 时不应保存")

                with tempfile.TemporaryDirectory() as temp_dir:
                    app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
                    state = app.load_state()
                    state["loginAccounts"][0]["platform"] = "pdd"
                    state["loginAccounts"][0]["activeChromePort"] = 45678
                    app.save_state(state)

                    original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
                    original_protect = sidecar_cli.protect_text
                    original_shutdown = sidecar_cli.shutdown_shadow_browser
                    sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
                    sidecar_cli.protect_text = fail_protect
                    sidecar_cli.shutdown_shadow_browser = lambda _config, _log: (_ for _ in ()).throw(
                        AssertionError("缺少拼多多关键 Cookie 时不应关闭窗口")
                    )
                    try:
                        result = app.poll_login({"accountId": "default"})
                        reloaded = app.load_state()
                    finally:
                        sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                        sidecar_cli.protect_text = original_protect
                        sidecar_cli.shutdown_shadow_browser = original_shutdown

                self.assertFalse(result["data"]["loggedIn"])
                self.assertEqual(result["data"]["status"], "等待扫码")
                self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])

    def test_poll_login_for_jd_waits_on_service_page_without_pin_and_thor(self) -> None:
        shutdown_calls = []
        cookie = "__jda=visitor; __jdb=session; guid=visitor-guid"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": False,
                "pageUrl": "https://kf.jd.com/#/218",
                "pageTitle": "京东客服管家",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "jd"
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.shutdown_shadow_browser = lambda config, _log: shutdown_calls.append(config) or 1
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], 2345)
        self.assertEqual(shutdown_calls, [])

    def test_poll_login_for_jd_saves_cookie_on_service_page_and_hides_protected_cookie(self) -> None:
        shutdown_calls = []
        protected_cookie = "dpapi:v1:jd-cookie"
        cookie = "thor=jd-token; pin=jd-user"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": False,
                "pageUrl": "https://kf.jd.com/#/43",
                "pageTitle": "京东客服",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fake_shutdown(config, _log):
            shutdown_calls.append(
                (
                    str(config.get("shadowChromeProfileDir") or ""),
                    int(config.get("activeChromePort") or config.get("chromePort") or 0),
                )
            )
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "jd"
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "jd")
            state["loginAccounts"][0]["chromePort"] = 0
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = lambda value: protected_cookie if value == cookie else value
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["loggedIn"])
        self.assertEqual(account["cookieProtected"], protected_cookie)
        self.assertEqual(account["loginStatus"], "已登录")
        self.assertEqual(account["lastKnownLoginAccount"], "jd-user")
        self.assertEqual(shutdown_calls, [(str(data_dir / "profiles" / "jd"), 45678)])
        self.assertNotIn("activeChromePort", account)
        public_account = result["data"]["state"]["loginAccounts"][0]
        self.assertNotIn("cookieProtected", public_account)

    def test_poll_login_saves_protected_cookie_closes_browser_and_keeps_profile_dir(self) -> None:
        shutdown_calls = []
        protected_cookie = "dpapi:v1:encrypted-cookie"
        cookie = "_m_h5_tk=abc_1999999999999; sn=%E6%9E%97%E5%BF%97%E7%8E%B2; _tb_token_=token"

        def fake_inspect(_config, _log):
            self.assertEqual(_config["chromePort"], 0)
            self.assertEqual(_config["activeChromePort"], 45678)
            return {
                "cookieHeader": cookie,
                "loggedIn": True,
                "currentNick": "远盛电商:林志玲",
                "shadowChromePid": 2345,
                "activeChromePort": 45678,
            }

        def fake_protect(value):
            self.assertEqual(value, cookie)
            return protected_cookie

        def fake_shutdown(config, _log):
            shutdown_calls.append(
                (
                    str(config.get("shadowChromeProfileDir") or ""),
                    int(config.get("activeChromePort") or config.get("chromePort") or 0),
                )
            )
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["profileDir"] = str(data_dir / "profiles" / "default")
            state["loginAccounts"][0]["chromePort"] = 0
            state["loginAccounts"][0]["activeChromePort"] = 45678
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = fake_protect
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["loggedIn"])
        self.assertEqual(account["cookieProtected"], protected_cookie)
        self.assertEqual(account["loginStatus"], "已登录")
        self.assertEqual(account["lastKnownLoginAccount"], "远盛电商:林志玲")
        self.assertEqual(account["loginHint"], "远盛电商:林志玲")
        self.assertIn("_m_h5_tk=有", account["cookieSummary"])
        self.assertTrue(account["cookieUpdatedAt"])
        self.assertEqual(shutdown_calls, [(str(data_dir / "profiles" / "default"), 45678)])
        self.assertNotIn("activeChromePort", account)
        self.assertEqual(account["shadowChromePid"], 0)
        self.assertEqual(account["profileDir"], str(data_dir / "profiles" / "default"))
        public_account = result["data"]["state"]["loginAccounts"][0]
        self.assertNotIn("cookieProtected", public_account)
        self.assertIn("cookieSummary", public_account)

    def test_poll_login_marks_account_when_browser_is_closed(self) -> None:
        def fake_inspect(_config, _log):
            raise sidecar_cli.ShadowBrowserError("影子浏览器未启动")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 9222
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_alive = sidecar_cli.is_shadow_browser_running
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.is_shadow_browser_running = lambda _config: False
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.is_shadow_browser_running = original_alive

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "登录窗口已关闭")
        self.assertIn("影子浏览器未启动", result["data"]["message"])
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "登录窗口已关闭")

    def test_poll_login_skips_drission_when_recorded_pid_is_gone(self) -> None:
        def fail_if_inspected(_config, _log):
            raise AssertionError("不应接管已关闭的登录窗口")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待扫码"
            state["loginAccounts"][0]["shadowChromePid"] = 999999
            state["loginAccounts"][0]["activeChromePort"] = 35820
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            sidecar_cli.inspect_existing_shadow_browser_state = fail_if_inspected
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect

        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "登录窗口已关闭")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "登录窗口已关闭")
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], 0)
        self.assertNotIn("activeChromePort", reloaded["loginAccounts"][0])

    def test_poll_login_skips_drission_when_recorded_port_is_closed(self) -> None:
        def fail_if_inspected(_config, _log):
            raise AssertionError("不应接管端口已关闭的登录窗口")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待扫码"
            state["loginAccounts"][0]["shadowChromePid"] = os.getpid()
            state["loginAccounts"][0]["activeChromePort"] = 9
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            sidecar_cli.inspect_existing_shadow_browser_state = fail_if_inspected
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect

        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "登录窗口已关闭")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "登录窗口已关闭")
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], 0)
        self.assertNotIn("activeChromePort", reloaded["loginAccounts"][0])

    def test_poll_login_keeps_waiting_when_attach_fails_but_browser_is_alive(self) -> None:
        def fake_inspect(_config, _log):
            raise sidecar_cli.ShadowBrowserError("接管暂时失败")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["shadowChromePid"] = os.getpid()
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_alive = sidecar_cli.is_shadow_browser_running
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.is_shadow_browser_running = lambda _config: True
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.is_shadow_browser_running = original_alive

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "等待登录检测")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "等待登录检测")
        self.assertEqual(reloaded["loginAccounts"][0]["shadowChromePid"], os.getpid())

    def test_poll_login_keeps_saved_cookie_when_close_browser_fails(self) -> None:
        protected_cookie = "dpapi:v1:encrypted-cookie"
        cookie = "_m_h5_tk=abc_1999999999999; sn=%E6%9E%97%E5%BF%97%E7%8E%B2; _tb_token_=token"

        def fake_inspect(_config, _log):
            return {
                "cookieHeader": cookie,
                "loggedIn": True,
                "currentNick": "远盛电商:林志玲",
                "shadowChromePid": 2345,
            }

        def fake_shutdown(_config, _log):
            raise sidecar_cli.ShadowBrowserError("窗口关闭失败")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_protect = sidecar_cli.protect_text
            original_shutdown = sidecar_cli.shutdown_shadow_browser
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.protect_text = lambda value: protected_cookie
            sidecar_cli.shutdown_shadow_browser = fake_shutdown
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.protect_text = original_protect
                sidecar_cli.shutdown_shadow_browser = original_shutdown

        account = reloaded["loginAccounts"][0]
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["loggedIn"])
        self.assertEqual(account["loginStatus"], "已登录")
        self.assertEqual(account["cookieProtected"], protected_cookie)
        self.assertEqual(account["lastKnownLoginAccount"], "远盛电商:林志玲")

    def test_poll_login_cleans_drission_temp_browser_and_waits_for_retry(self) -> None:
        cleanup_ports = []

        def fake_inspect(_config, _log):
            raise sidecar_cli.DrissionTempBrowserDetected("检测到 DrissionPage 临时浏览器占用端口 9222。")

        def fake_cleanup(port, _log):
            cleanup_ports.append(port)
            return 1

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            state = app.load_state()
            state["loginAccounts"][0]["loginStatus"] = "等待登录"
            state["loginAccounts"][0]["activeChromePort"] = 9222
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_cleanup = sidecar_cli.kill_drission_temp_browsers
            sidecar_cli.inspect_existing_shadow_browser_state = fake_inspect
            sidecar_cli.kill_drission_temp_browsers = fake_cleanup
            try:
                result = app.poll_login({"accountId": "default"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.kill_drission_temp_browsers = original_cleanup

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["loggedIn"])
        self.assertEqual(result["data"]["status"], "正在清理临时浏览器")
        self.assertEqual(cleanup_ports, [9222])
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "等待扫码")
        self.assertNotIn("cookieProtected", reloaded["loginAccounts"][0])


class SidecarCaptureTests(unittest.TestCase):
    def test_capture_all_uses_saved_account_cookie_direct_capture(self) -> None:
        events = []
        captured_states = []

        def fake_direct_capture(state, log):
            captured_states.append(dict(state))
            log("开始账号 Cookie 接口采集。")
            return {
                "loginAccount": "远盛电商",
                "recordDate": "2026-05-09",
                "subAccount": "林志玲",
                "consultationCount": 3,
            }

        def bad_external_capture(_state, _log):
            raise AssertionError("账号采集不应回退影子 Chrome 表格采集")

        def fake_upload(_state, _payload, _signature, _reason):
            return "服务端上传失败：连接超时", None

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(
                data_dir=Path(temp_dir),
                emit=events.append,
                capture_func=bad_external_capture,
                direct_capture_func=fake_direct_capture,
                upload_func=fake_upload,
            )
            state = app.load_state()
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:encrypted-cookie"
            app.save_state(state)

            original_inspect = sidecar_cli.inspect_existing_shadow_browser_state
            original_launch = sidecar_cli.launch_shadow_browser_for_login
            sidecar_cli.inspect_existing_shadow_browser_state = lambda _config, _log: (_ for _ in ()).throw(
                AssertionError("账号 Cookie 采集不应检查或接管浏览器")
            )
            sidecar_cli.launch_shadow_browser_for_login = lambda _config, _log: (_ for _ in ()).throw(
                AssertionError("账号 Cookie 采集不应启动浏览器")
            )
            try:
                result = app.capture_all({"reason": "手动采集"})
                reloaded = app.load_state()
            finally:
                sidecar_cli.inspect_existing_shadow_browser_state = original_inspect
                sidecar_cli.launch_shadow_browser_for_login = original_launch

        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["batch"])
        self.assertTrue(result["data"]["results"][0]["ok"])
        self.assertIn("服务端上传失败", result["data"]["results"][0]["uploadMessage"])
        self.assertEqual(reloaded["loginAccounts"][0]["lastKnownLoginAccount"], "远盛电商:林志玲")
        self.assertEqual(captured_states[0]["cookieProtected"], "dpapi:v1:encrypted-cookie")
        self.assertTrue(captured_states[0]["accountCookieRequired"])
        self.assertEqual(events[0]["status"], "采集中")
        self.assertTrue(any(item.get("type") == "log" and "开始账号 Cookie 接口采集" in item.get("message", "") for item in events))
        self.assertEqual(events[-1]["status"], "待命")

    def test_capture_exception_returns_structured_account_result(self) -> None:
        def bad_direct_capture(_state, _log):
            raise RuntimeError("采集失败")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None, direct_capture_func=bad_direct_capture)
            state = app.load_state()
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:encrypted-cookie"
            app.save_state(state)
            result = app.capture_all({"reason": "手动采集"})

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["results"][0]["ok"])
        self.assertEqual(result["data"]["results"][0]["message"], "采集失败")

    def test_upload_failure_message_redacts_sensitive_text(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}

        def bad_upload(_server_url, _payload, timeout_seconds=10.0):
            raise sidecar_cli.UploadClientError("服务端拒绝：Cookie=secret; thor=abc; X-Sign=sign-value")

        original_upload = sidecar_cli.upload_employee_payload
        sidecar_cli.upload_employee_payload = bad_upload
        try:
            message, record = sidecar_cli.upload_payload_with_state(
                state,
                {"platform": "pdd", "loginAccount": "shop", "recordDate": "2026-05-12"},
                "signature",
                "手动采集",
            )
        finally:
            sidecar_cli.upload_employee_payload = original_upload

        self.assertIsNone(record)
        self.assertIn("<redacted>", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("sign-value", message)

    def test_capture_account_disabled_account_returns_skipped(self) -> None:
        def bad_direct_capture(_state, _log):
            raise AssertionError("禁用账号不应执行采集")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None, direct_capture_func=bad_direct_capture)
            state = app.load_state()
            state["loginAccounts"][0]["enabled"] = False
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:encrypted-cookie"
            app.save_state(state)

            result = app.capture_account({"accountId": "default"})

        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["batch"])
        self.assertEqual(result["data"]["results"][0]["status"], "skipped")
        self.assertIn("已禁用", result["data"]["results"][0]["message"])

    def test_capture_account_for_jd_uses_jd_adapter(self) -> None:
        def bad_direct_capture(_state, _log):
            raise AssertionError("京东账号不应调用千牛采集")

        def fake_jd_capture(_state, _log):
            return {
                "loginAccount": "京东账号",
                "recordDate": "2026-05-12",
                "subAccount": "if自营菠萝",
                "consultationCount": 58,
            }

        def fake_upload(_state, _payload, _signature, _reason):
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(
                data_dir=Path(temp_dir),
                emit=lambda _event: None,
                direct_capture_func=bad_direct_capture,
                jd_capture_func=fake_jd_capture,
                upload_func=fake_upload,
            )
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "jd"
            state["loginAccounts"][0]["displayName"] = "京东账号"
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:encrypted-cookie"
            app.save_state(state)

            result = app.capture_account({"accountId": "default"})
            reloaded = app.load_state()

        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["batch"])
        self.assertTrue(result["data"]["results"][0]["ok"])
        self.assertEqual(result["data"]["results"][0]["payload"]["subAccount"], "if自营菠萝")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "采集成功+已上传")

    def test_capture_account_for_pdd_uses_pdd_adapter(self) -> None:
        captured_platforms = []

        def bad_direct_capture(state, _log):
            captured_platforms.append(state["platform"])
            raise AssertionError("拼多多账号不应调用千牛采集")

        def fake_pdd_capture(state, _log):
            captured_platforms.append(state["platform"])
            return {
                "loginAccount": state["shopName"],
                "recordDate": "2026-05-17",
                "subAccount": "屿你服饰星星",
                "consultationCount": 7,
                "rawMetrics": {"accountIdentity": "屿你服饰星星"},
            }

        def fake_upload(_state, _payload, _signature, _reason):
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-18 09:00:00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(
                data_dir=Path(temp_dir),
                emit=lambda _event: None,
                direct_capture_func=bad_direct_capture,
                pdd_capture_func=fake_pdd_capture,
                upload_func=fake_upload,
            )
            state = app.load_state()
            state["loginAccounts"][0]["platform"] = "pdd"
            state["loginAccounts"][0]["displayName"] = "拼多多账号"
            state["loginAccounts"][0]["shopName"] = "拼多多远盛店"
            state["loginAccounts"][0]["cookieProtected"] = "dpapi:v1:encrypted-cookie"
            app.save_state(state)

            result = app.capture_account({"accountId": "default"})
            reloaded = app.load_state()

        self.assertTrue(result["ok"])
        self.assertEqual(captured_platforms, ["pdd"])
        self.assertTrue(result["data"]["results"][0]["ok"])
        self.assertEqual(result["data"]["results"][0]["payload"]["subAccount"], "屿你服饰星星")
        self.assertEqual(reloaded["loginAccounts"][0]["loginStatus"], "采集成功+已上传")
        self.assertEqual(reloaded["loginAccounts"][0]["lastKnownLoginAccount"], "屿你服饰星星")

    def test_capture_all_mixed_accounts_returns_qn_and_jd_results(self) -> None:
        captured_platforms = []

        def fake_direct_capture(state, _log):
            captured_platforms.append(state["platform"])
            return {
                "loginAccount": "远盛电商",
                "recordDate": "2026-05-09",
                "subAccount": "千牛账号",
                "consultationCount": 3,
            }

        def fake_jd_capture(state, _log):
            captured_platforms.append(state["platform"])
            return {
                "loginAccount": "京东账号",
                "recordDate": "2026-05-12",
                "subAccount": "if自营菠萝",
                "consultationCount": 58,
            }

        def fake_upload(_state, _payload, _signature, _reason):
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-09 09:00:00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(
                data_dir=data_dir,
                emit=lambda _event: None,
                direct_capture_func=fake_direct_capture,
                jd_capture_func=fake_jd_capture,
                upload_func=fake_upload,
            )
            state = app.load_state()
            state["loginAccounts"] = [
                {
                    "id": "qn-account",
                    "platform": "qn",
                    "displayName": "千牛账号",
                    "enabled": True,
                    "profileDir": str(data_dir / "profiles" / "qn"),
                    "cookieProtected": "dpapi:v1:qn-cookie",
                },
                {
                    "id": "jd-account",
                    "platform": "jd",
                    "displayName": "京东账号",
                    "enabled": True,
                    "profileDir": str(data_dir / "profiles" / "jd"),
                    "cookieProtected": "dpapi:v1:jd-cookie",
                },
            ]
            app.save_state(state)

            result = app.capture_all({"reason": "手动采集"})
            reloaded = app.load_state()

        self.assertTrue(result["ok"])
        self.assertEqual(captured_platforms, ["qn", "jd"])
        self.assertEqual(len(result["data"]["results"]), 2)
        self.assertTrue(result["data"]["results"][0]["ok"])
        self.assertTrue(result["data"]["results"][1]["ok"])
        self.assertTrue(reloaded["lastRunAt"])
        jd_account = next(item for item in reloaded["loginAccounts"] if item["id"] == "jd-account")
        self.assertEqual(jd_account["lastFailureReason"], "")

    def test_capture_all_with_platform_only_captures_that_platform(self) -> None:
        captured_platforms = []

        def fake_direct_capture(state, _log):
            captured_platforms.append(state["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-09", "subAccount": "千牛账号"}

        def fake_jd_capture(state, _log):
            captured_platforms.append(state["platform"])
            return {"loginAccount": "京东账号", "recordDate": "2026-05-12", "subAccount": "if自营菠萝"}

        def fake_upload(_state, _payload, _signature, _reason):
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-09 09:00:00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(
                data_dir=data_dir,
                emit=lambda _event: None,
                direct_capture_func=fake_direct_capture,
                jd_capture_func=fake_jd_capture,
                upload_func=fake_upload,
            )
            state = app.load_state()
            state["loginAccounts"] = [
                {
                    "id": "qn-account",
                    "platform": "qn",
                    "displayName": "千牛账号",
                    "enabled": True,
                    "profileDir": str(data_dir / "profiles" / "qn"),
                    "cookieProtected": "dpapi:v1:qn-cookie",
                },
                {
                    "id": "jd-account",
                    "platform": "jd",
                    "displayName": "京东账号",
                    "enabled": True,
                    "profileDir": str(data_dir / "profiles" / "jd"),
                    "cookieProtected": "dpapi:v1:jd-cookie",
                },
            ]
            app.save_state(state)

            result = app.capture_all({"reason": "手动采集", "platform": "jd"})

        self.assertTrue(result["ok"])
        self.assertEqual(captured_platforms, ["jd"])
        self.assertEqual(len(result["data"]["results"]), 1)

    def test_capture_all_with_platform_no_match_returns_empty_batch(self) -> None:
        captured_platforms = []

        def bad_direct_capture(state, _log):
            captured_platforms.append(state.get("platform"))
            raise AssertionError("指定平台无账号时不应回退旧单账号采集")

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            app = SidecarApp(data_dir=data_dir, emit=lambda _event: None, direct_capture_func=bad_direct_capture)
            state = app.load_state()
            state["loginAccounts"] = [
                {
                    "id": "jd-account",
                    "platform": "jd",
                    "displayName": "京东账号",
                    "enabled": True,
                    "profileDir": str(data_dir / "profiles" / "jd"),
                    "cookieProtected": "dpapi:v1:jd-cookie",
                }
            ]
            app.save_state(state)

            result = app.capture_all({"reason": "手动采集", "platform": "pdd"})

        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["batch"])
        self.assertEqual(result["data"]["results"], [])
        self.assertEqual(result["data"]["skipped"], True)
        self.assertEqual(captured_platforms, [])


class SidecarUpdateTests(unittest.TestCase):
    def test_check_update_uses_default_server_manifest_and_returns_metadata(self) -> None:
        opened_urls = []

        class FakeUrlResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps(
                    {
                        "version": "999.0.0",
                        "downloadUrl": "http://120.27.22.50/downloads/yuansheng-data-assistant-999.0.0-x64-setup.exe",
                        "sha256": "abc123",
                        "notes": "修复安装包",
                        "force": True,
                    },
                    ensure_ascii=False,
                ).encode("utf-8")

        def fake_urlopen(request, timeout, context):  # noqa: ANN001, ANN202
            opened_urls.append(request.full_url)
            self.assertEqual(timeout, 8)
            self.assertIsNotNone(context)
            return FakeUrlResponse()

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_urlopen = sidecar_cli.urllib.request.urlopen
            sidecar_cli.urllib.request.urlopen = fake_urlopen
            try:
                result = app.check_update({})
            finally:
                sidecar_cli.urllib.request.urlopen = original_urlopen

        self.assertTrue(result["ok"])
        self.assertEqual(opened_urls, [sidecar_cli.DEFAULT_UPDATE_CHECK_URL])
        self.assertTrue(result["data"]["updateAvailable"])
        self.assertEqual(result["data"]["latestVersion"], "999.0.0")
        self.assertEqual(result["data"]["sha256"], "abc123")
        self.assertEqual(result["data"]["notes"], "修复安装包")
        self.assertTrue(result["data"]["force"])

    def test_check_update_ignores_same_or_older_version(self) -> None:
        class FakeUrlResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps({"version": sidecar_cli.SIDECAR_VERSION}).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=lambda _event: None)
            original_urlopen = sidecar_cli.urllib.request.urlopen
            sidecar_cli.urllib.request.urlopen = lambda *_args, **_kwargs: FakeUrlResponse()
            try:
                result = app.check_update({})
            finally:
                sidecar_cli.urllib.request.urlopen = original_urlopen

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["updateAvailable"])

    def test_check_update_reports_html_manifest_response_clearly(self) -> None:
        events = []

        class FakeUrlResponse:
            headers = {"Content-Type": "text/html; charset=utf-8"}

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return b"<!doctype html><html><body>index</body></html>"

        with tempfile.TemporaryDirectory() as temp_dir:
            app = SidecarApp(data_dir=Path(temp_dir), emit=events.append)
            original_urlopen = sidecar_cli.urllib.request.urlopen
            sidecar_cli.urllib.request.urlopen = lambda *_args, **_kwargs: FakeUrlResponse()
            try:
                result = app.check_update({})
            finally:
                sidecar_cli.urllib.request.urlopen = original_urlopen

        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["updateAvailable"])
        self.assertIn("更新清单不是 JSON", result["data"]["reason"])
        self.assertIn("text/html", result["data"]["reason"])
        self.assertTrue(any("更新清单不是 JSON" in str(item.get("message") or "") for item in events))


if __name__ == "__main__":
    unittest.main()
