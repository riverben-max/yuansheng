from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from login_accounts import (
    add_login_account,
    capture_enabled_accounts,
    ensure_login_accounts,
)
from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError


class LoginAccountConfigTests(unittest.TestCase):
    def test_legacy_shadow_config_migrates_to_one_enabled_account(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {
                "lastKnownLoginAccount": "张三",
                "shadowChromeProfileDir": str(data_dir / "legacy-profile"),
                "chromePort": 9222,
            }

            accounts = ensure_login_accounts(state, data_dir)

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["displayName"], "张三")
        self.assertTrue(accounts[0]["enabled"])
        self.assertEqual(accounts[0]["chromePort"], 0)
        self.assertTrue(accounts[0]["profileDir"].endswith("legacy-profile"))
        self.assertIs(state["loginAccounts"], accounts)

    def test_add_login_account_allocates_profile_and_uses_auto_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {
                "loginAccounts": [
                    {
                        "id": "account-1",
                        "displayName": "张三",
                        "loginHint": "zhangsan",
                        "enabled": True,
                        "profileDir": str(data_dir / "profiles" / "zhangsan"),
                        "chromePort": 9222,
                    }
                ]
            }

            account = add_login_account(state, data_dir, display_name="李四", login_hint="lisi")

        self.assertEqual(account["displayName"], "李四")
        self.assertEqual(account["loginHint"], "lisi")
        self.assertTrue(account["enabled"])
        self.assertEqual(account["chromePort"], 0)
        self.assertTrue(account["profileDir"].replace("\\", "/").endswith("/profiles/lisi"))
        self.assertIn(account, state["loginAccounts"])


class BatchCaptureTests(unittest.TestCase):
    def test_successful_batch_capture_saves_display_summary_without_raw_metrics(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "ok-account",
                "displayName": "林志玲",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]

        def fake_capture(_config, _log):
            return {
                "loginAccount": "远盛电商",
                "recordDate": "2026-05-09",
                "subAccount": "林志玲",
                "consultationCount": 12,
                "receiveCount": 10,
                "validReceiveCount": 9,
                "inquiryCount": 6,
                "conversionRate": 33.33,
                "firstReplyTime": 8,
                "avgReplyTime": 18,
                "wwReplyRate": 99.5,
                "satisfaction": 100,
                "rawMetrics": {"debug": "not-for-ui"},
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-09 09:00:00"}),
            log=lambda _message: None,
        )

        summary = accounts[0]["lastCaptureSummary"]
        self.assertTrue(results[0]["ok"])
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["displayName"], "林志玲")
        self.assertEqual(summary["loginAccount"], "远盛电商")
        self.assertEqual(summary["subAccount"], "林志玲")
        self.assertEqual(summary["recordDate"], "2026-05-09")
        self.assertTrue(summary["uploaded"])
        self.assertEqual(summary["metrics"]["consultationCount"], 12)
        self.assertEqual(summary["metrics"]["satisfaction"], 100)
        self.assertNotIn("rawMetrics", summary)
        self.assertNotIn("rawMetrics", summary["metrics"])
        self.assertEqual(accounts[0]["lastFailureReason"], "")

    def test_upload_failure_keeps_capture_success_with_failed_upload_summary(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "upload-failed",
                "displayName": "林志玲",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]

        def fake_capture(_config, _log):
            return {
                "loginAccount": "远盛电商",
                "recordDate": "2026-05-09",
                "subAccount": "林志玲",
                "consultationCount": 12,
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传失败：连接超时", None),
            log=lambda _message: None,
        )

        summary = accounts[0]["lastCaptureSummary"]
        self.assertTrue(results[0]["ok"])
        self.assertTrue(summary["ok"])
        self.assertFalse(summary["uploaded"])
        self.assertEqual(summary["uploadMessage"], "服务端上传失败：连接超时")
        self.assertEqual(accounts[0]["lastFailureReason"], "上传失败")
        self.assertEqual(results[0]["lastFailureReason"], "上传失败")

    def test_failed_capture_records_failure_reason_and_clears_stale_summary(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "need-login",
                "displayName": "林志玲",
                "enabled": True,
                "cookieProtected": "dpapi:v1:expired",
                "lastCaptureSummary": {"ok": True, "subAccount": "旧数据"},
            }
        ]

        def fake_capture(_config, _log):
            raise DirectApiLoginRequiredError("接口直采 Cookie 已过期，请重新登录千牛。")

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
        )

        self.assertFalse(results[0]["ok"])
        self.assertEqual(accounts[0]["lastFailureReason"], "需要重新登录")
        self.assertNotIn("lastCaptureSummary", accounts[0])
        self.assertEqual(results[0]["lastFailureReason"], "需要重新登录")

    def test_batch_capture_continues_after_login_required_account(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "need-login",
                "displayName": "张三",
                "enabled": True,
                "profileDir": r"D:\profiles\zhangsan",
                "chromePort": 9222,
            },
            {
                "id": "ok-account",
                "displayName": "李四",
                "enabled": True,
                "profileDir": r"D:\profiles\lisi",
                "chromePort": 9223,
            },
        ]
        captured_ports = []
        uploaded = []

        def fake_capture(config, _log):
            captured_ports.append(config["chromePort"])
            if config["chromePort"] == 9222:
                raise RuntimeError("需要重新登录")
            return {"loginAccount": "远盛电商:李四", "recordDate": "2026-05-08", "subAccount": "李四"}

        def fake_upload(_state, payload, _signature, _reason):
            uploaded.append(payload["subAccount"])
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-08 09:00:00"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=fake_upload,
            log=lambda _message: None,
        )

        self.assertEqual(captured_ports, [9222, 9223])
        self.assertEqual(uploaded, ["李四"])
        self.assertFalse(results[0]["ok"])
        self.assertTrue(results[1]["ok"])
        self.assertEqual(accounts[0]["loginStatus"], "需要重新登录")
        self.assertEqual(accounts[1]["loginStatus"], "采集成功")
        self.assertIn("lastResult", accounts[1])

    def test_batch_capture_marks_direct_login_required_as_relogin(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "need-login",
                "displayName": "张三",
                "enabled": True,
                "cookieProtected": "dpapi:v1:expired",
            }
        ]

        def fake_capture(_config, _log):
            raise DirectApiLoginRequiredError("接口直采 Cookie 已过期，请重新登录千牛。")

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
        )

        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["errorType"], "login_required")
        self.assertEqual(accounts[0]["loginStatus"], "需要重新登录")

    def test_batch_capture_marks_generic_direct_failure_as_capture_failed(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "bad-response",
                "displayName": "张三",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]

        def fake_capture(_config, _log):
            raise DirectApiCaptureError("接口直采响应里没有找到客服数据行")

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
        )

        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["errorType"], "generic")
        self.assertEqual(accounts[0]["loginStatus"], "采集失败")


if __name__ == "__main__":
    unittest.main()
