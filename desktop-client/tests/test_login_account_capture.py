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
from jd_workload_capture import JdWorkloadIdentityRequiredError


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
        self.assertEqual(accounts[0]["platform"], "qn")
        self.assertEqual(accounts[0]["shopName"], "")
        self.assertIs(state["loginAccounts"], accounts)

    def test_existing_login_account_without_platform_defaults_to_qn(self) -> None:
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
                    }
                ]
            }

            accounts = ensure_login_accounts(state, data_dir)

        self.assertEqual(accounts[0]["platform"], "qn")
        self.assertEqual(accounts[0]["shopName"], "")

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
        self.assertEqual(account["platform"], "qn")
        self.assertEqual(account["shopName"], "")
        self.assertIn(account, state["loginAccounts"])

    def test_add_login_account_allocates_unique_profile_when_name_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {}

            first = add_login_account(state, data_dir, display_name="新登录账户", platform="jd")
            second = add_login_account(state, data_dir, display_name="新登录账户", platform="pdd")

        self.assertNotEqual(first["profileDir"], second["profileDir"])
        self.assertTrue(second["profileDir"].replace("\\", "/").endswith("-2"))

    def test_ensure_login_accounts_reassigns_duplicate_profile_and_requires_relogin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            shared_profile = str(data_dir / "profiles" / "account-b8b8fefd")
            state = {
                "loginAccounts": [
                    {
                        "id": "account-3",
                        "platform": "jd",
                        "displayName": "京东账号",
                        "profileDir": shared_profile,
                        "cookieProtected": "dpapi:v1:jd-cookie",
                        "loginStatus": "采集成功",
                    },
                    {
                        "id": "account-4",
                        "platform": "pdd",
                        "displayName": "拼多多账号",
                        "profileDir": shared_profile,
                        "cookieProtected": "dpapi:v1:pdd-cookie",
                        "cookieUpdatedAt": "2026-05-19 12:52:39",
                        "activeChromePort": 33963,
                        "shadowChromePid": 23524,
                        "loginStatus": "已登录",
                    },
                ]
            }

            accounts = ensure_login_accounts(state, data_dir)

        self.assertEqual(accounts[0]["profileDir"], shared_profile)
        self.assertNotEqual(accounts[1]["profileDir"], shared_profile)
        self.assertTrue(accounts[1]["profileDir"].replace("\\", "/").endswith("/profiles/account-b8b8fefd-2"))
        self.assertEqual(accounts[1]["loginStatus"], "需要重新登录")
        self.assertEqual(accounts[1]["lastFailureReason"], "需要重新登录")
        self.assertNotIn("cookieProtected", accounts[1])
        self.assertNotIn("activeChromePort", accounts[1])
        self.assertEqual(accounts[1]["shadowChromePid"], 0)

    def test_add_login_account_accepts_jd_platform_and_shop_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {}

            account = add_login_account(
                state,
                data_dir,
                display_name="京东账号",
                login_hint="jd-user",
                platform="jd",
                shop_name="医谷特膳膳养道专卖店",
            )

        self.assertEqual(account["platform"], "jd")
        self.assertEqual(account["shopName"], "医谷特膳膳养道专卖店")

    def test_add_login_account_accepts_pdd_platform_and_shop_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {}

            account = add_login_account(
                state,
                data_dir,
                display_name="拼多多账号",
                login_hint="pdd-user",
                platform="pdd",
                shop_name="拼多多远盛店",
            )

        self.assertEqual(account["platform"], "pdd")
        self.assertEqual(account["shopName"], "拼多多远盛店")

    def test_invalid_platform_normalizes_to_qn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            state = {
                "loginAccounts": [
                    {
                        "id": "bad-platform",
                        "displayName": "旧账号",
                        "platform": "unknown",
                        "shopName": "远盛电商",
                    }
                ]
            }

            accounts = ensure_login_accounts(state, data_dir)
            account = add_login_account(state, data_dir, display_name="新账号", platform="bad")

        self.assertEqual(accounts[0]["platform"], "qn")
        self.assertEqual(accounts[0]["shopName"], "远盛电商")
        self.assertEqual(account["platform"], "qn")


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

    def test_missing_employee_mapping_upload_failure_is_classified_for_platform_account(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "jd-no-employee",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]

        def fake_capture(_config, _log):
            return {
                "loginAccount": "京东菠萝店",
                "recordDate": "2026-05-12",
                "subAccount": "未分配",
                "consultationCount": 58,
            }

        upload_message = "服务端上传失败：未找到员工账号映射：subAccount=未分配，请先在系统用户中创建对应客服账号"
        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: (upload_message, None),
            log=lambda _message: None,
            capture_adapters={"jd": fake_capture},
        )

        self.assertTrue(results[0]["ok"])
        self.assertFalse(accounts[0]["lastCaptureSummary"]["uploaded"])
        self.assertEqual(accounts[0]["lastCaptureSummary"]["uploadMessage"], upload_message)
        self.assertEqual(accounts[0]["lastFailureReason"], "平台未配置客服账号")
        self.assertEqual(results[0]["lastFailureReason"], "平台未配置客服账号")

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
        self.assertEqual(accounts[1]["loginStatus"], "采集成功+已上传")
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

    def test_jd_account_uses_jd_capture_adapter_and_uploads(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "jd-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:jd-cookie",
                "lastKnownLoginAccount": "if自营菠萝",
                "lastCaptureSummary": {"ok": True, "subAccount": "旧数据"},
            }
        ]
        uploaded_sub_accounts = []

        def fail_capture(_config, _log):
            raise AssertionError("jd account should not call qn capture")

        def fake_jd_capture(config, _log):
            self.assertEqual(config["platform"], "jd")
            self.assertEqual(config["lastKnownLoginAccount"], "if自营菠萝")
            return {
                "loginAccount": "京东店铺名",
                "recordDate": "2026-05-12",
                "subAccount": "if自营菠萝",
                "consultationCount": 58,
                "rawMetrics": {
                    "source": "jd_workload",
                    "accountIdentity": "if自营菠萝",
                    "requestParams": {"servicePin": "if自营菠萝"},
                },
            }

        def fake_upload(_state, payload, _signature, _reason):
            uploaded_sub_accounts.append(payload["subAccount"])
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fail_capture,
            upload_func=fake_upload,
            log=lambda _message: None,
            capture_adapters={"qn": fail_capture, "jd": fake_jd_capture},
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["ok"])
        self.assertEqual(uploaded_sub_accounts, ["if自营菠萝"])
        self.assertEqual(accounts[0]["loginStatus"], "采集成功+已上传")
        self.assertEqual(accounts[0]["lastFailureReason"], "")
        self.assertEqual(accounts[0]["lastKnownLoginAccount"], "if自营菠萝")
        self.assertEqual(accounts[0]["lastCaptureSummary"]["subAccount"], "if自营菠萝")

    def test_jd_capture_keeps_existing_service_pin_when_payload_has_shop_name(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "jd-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:jd-cookie",
                "lastKnownLoginAccount": "if自营菠萝",
                "shopName": "1",
            }
        ]

        def fake_jd_capture(_config, _log):
            return {
                "loginAccount": "1",
                "recordDate": "2026-05-12",
                "subAccount": "未分配",
                "consultationCount": 58,
                "rawMetrics": {
                    "source": "jd_workload",
                    "accountIdentity": "if自营菠萝",
                    "requestParams": {"servicePin": "if自营菠萝"},
                },
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}),
            log=lambda _message: None,
            capture_adapters={"jd": fake_jd_capture},
        )

        self.assertTrue(results[0]["ok"])
        self.assertEqual(accounts[0]["lastKnownLoginAccount"], "if自营菠萝")

    def test_mixed_qn_and_jd_batch_captures_both_platforms(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "qn-account",
                "platform": "qn",
                "displayName": "千牛账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            },
            {
                "id": "jd-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            },
        ]
        captured_platforms = []
        uploaded_sub_accounts = []

        def fake_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-09", "subAccount": "千牛账号"}

        def fake_jd_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "京东店铺", "recordDate": "2026-05-12", "subAccount": "京东账号"}

        def fake_upload(_state, payload, _signature, _reason):
            uploaded_sub_accounts.append(payload["subAccount"])
            return "服务端上传成功：上传成功。", {"uploadedAt": "2026-05-09 09:00:00"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=fake_upload,
            log=lambda _message: None,
            capture_adapters={"qn": fake_capture, "jd": fake_jd_capture},
        )

        self.assertEqual(captured_platforms, ["qn", "jd"])
        self.assertEqual(uploaded_sub_accounts, ["千牛账号", "京东账号"])
        self.assertTrue(results[0]["ok"])
        self.assertTrue(results[1]["ok"])

    def test_jd_missing_service_pin_is_capture_failure_not_relogin(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "jd-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:jd-cookie",
            }
        ]

        def fake_jd_capture(_config, _log):
            raise JdWorkloadIdentityRequiredError("京东客服账号识别名为空，请先登录或补充登录识别名。")

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
            capture_adapters={"jd": fake_jd_capture},
        )

        self.assertFalse(results[0]["ok"])
        self.assertEqual(results[0]["errorType"], "identity_required")
        self.assertEqual(accounts[0]["loginStatus"], "采集失败")
        self.assertEqual(accounts[0]["lastFailureReason"], "需要配置客服身份")

    def test_jd_account_without_registered_adapter_fails_instead_of_using_qn_capture(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "jd-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:jd-cookie",
            }
        ]
        captured_platforms = []

        def fake_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-09", "subAccount": "误采集"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
            capture_adapters={"qn": fake_capture},
        )

        self.assertEqual(captured_platforms, [])
        self.assertFalse(results[0]["ok"])
        self.assertEqual(accounts[0]["loginStatus"], "采集失败")
        self.assertIn("未注册", results[0]["message"])

    def test_pdd_account_without_registered_adapter_fails_instead_of_using_qn_capture(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "pdd-account",
                "platform": "pdd",
                "displayName": "拼多多账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:pdd-cookie",
            }
        ]
        captured_platforms = []

        def fake_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-09", "subAccount": "误采集"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("", None),
            log=lambda _message: None,
            capture_adapters={"qn": fake_capture},
        )

        self.assertEqual(captured_platforms, [])
        self.assertFalse(results[0]["ok"])
        self.assertEqual(accounts[0]["loginStatus"], "采集失败")
        self.assertIn("平台 pdd 未注册采集适配器", results[0]["message"])

    def test_pdd_account_uses_registered_adapter(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "pdd-account",
                "platform": "pdd",
                "displayName": "拼多多账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:pdd-cookie",
                "shopName": "拼多多远盛店",
            }
        ]
        captured_platforms = []

        def bad_qn_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-17", "subAccount": "误采集"}

        def fake_pdd_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {
                "loginAccount": config["shopName"],
                "recordDate": "2026-05-17",
                "subAccount": "屿你服饰星星",
                "consultationCount": 7,
                "rawMetrics": {"accountIdentity": "屿你服饰星星"},
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=bad_qn_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-18 09:00:00"}),
            log=lambda _message: None,
            capture_adapters={"qn": bad_qn_capture, "pdd": fake_pdd_capture},
        )

        self.assertEqual(captured_platforms, ["pdd"])
        self.assertTrue(results[0]["ok"])
        self.assertEqual(accounts[0]["loginStatus"], "采集成功+已上传")
        self.assertEqual(accounts[0]["lastKnownLoginAccount"], "屿你服饰星星")

    def test_missing_platform_still_uses_qn_capture(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "legacy-account",
                "displayName": "旧账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]
        captured_platforms = []

        def fake_capture(config, _log):
            captured_platforms.append(config["platform"])
            return {"loginAccount": "远盛电商", "recordDate": "2026-05-09", "subAccount": "旧账号"}

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=fake_capture,
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-09 09:00:00"}),
            log=lambda _message: None,
        )

        self.assertEqual(captured_platforms, ["qn"])
        self.assertTrue(results[0]["ok"])

    def test_account_identity_uses_raw_metrics_identity_before_payload_names(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "custom-account",
                "platform": "jd",
                "displayName": "京东账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
                "loginHint": "hint-user",
            }
        ]

        def fake_capture(_config, _log):
            return {
                "loginAccount": "店铺名",
                "recordDate": "2026-05-12",
                "subAccount": "页面客服名",
                "rawMetrics": {"accountIdentity": "adapter-identity"},
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}),
            log=lambda _message: None,
            capture_adapters={"jd": fake_capture},
        )

        self.assertTrue(results[0]["ok"])
        self.assertEqual(accounts[0]["lastKnownLoginAccount"], "adapter-identity")

    def test_account_identity_keeps_explicit_login_hint_before_last_known_identity(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "custom-account",
                "platform": "pdd",
                "displayName": "拼多多账号",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
                "loginHint": "manual-cs",
                "lastKnownLoginAccount": "detected-old",
            }
        ]

        def fake_capture(_config, _log):
            return {
                "loginAccount": "店铺名",
                "recordDate": "2026-05-12",
                "subAccount": "",
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}),
            log=lambda _message: None,
            capture_adapters={"pdd": fake_capture},
        )

        self.assertTrue(results[0]["ok"])
        self.assertEqual(accounts[0]["lastKnownLoginAccount"], "店铺名")

    def test_non_numeric_shop_id_is_treated_as_zero(self) -> None:
        state = {"serverUrl": "http://example.com", "uploadHistory": {}}
        accounts = [
            {
                "id": "bad-shop-id",
                "platform": "jd",
                "displayName": "京东账号",
                "shopId": "not-a-number",
                "enabled": True,
                "cookieProtected": "dpapi:v1:cookie",
            }
        ]
        seen = {}

        def fake_capture(config, _log):
            seen["shopId"] = config.get("shopId")
            return {
                "loginAccount": "京东店铺",
                "recordDate": "2026-05-12",
                "subAccount": "客服A",
            }

        results = capture_enabled_accounts(
            state,
            accounts,
            reason="手动采集",
            capture_func=lambda _config, _log: {},
            upload_func=lambda _state, _payload, _signature, _reason: ("服务端上传成功：上传成功。", {"uploadedAt": "2026-05-12 09:00:00"}),
            log=lambda _message: None,
            capture_adapters={"jd": fake_capture},
        )

        self.assertTrue(results[0]["ok"])
        self.assertEqual(seen["shopId"], 0)
        self.assertEqual(results[0]["payload"]["shopId"], 0)


if __name__ == "__main__":
    unittest.main()
