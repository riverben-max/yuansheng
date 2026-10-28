from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from direct_api_capture import (
    DirectApiCaptureError,
    DirectApiLoginRequiredError,
    capture_with_direct_api,
    fetch_direct_api_data,
    load_direct_api_config,
    migrate_direct_api_cookie_config,
    parse_direct_api_payload,
    summarize_cookie,
    update_direct_api_cookie,
)


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):  # noqa: ANN201
        return json.loads(self.text)


class FakeClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    def request(self, method: str, url: str, **kwargs):  # noqa: ANN001, ANN201
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        return self.response


def base_config(**overrides):  # noqa: ANN201
    payload = {
        "enabled": True,
        "method": "GET",
        "apiUrl": "https://example.taobao.com/api",
        "cookie": "cookie-a=1; cookie-b=2",
        "referer": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
        "params": {"startDate": "2026-04-01", "endDate": "2026-04-25"},
        "body": {},
        "loginAccount": "远盛电商",
        "subAccount": "林志玲",
    }
    payload.update(overrides)
    return payload


def onequery_payload(row: dict) -> dict:
    return {"data": {"data": {"data": [row]}}}


class DirectApiCaptureTests(unittest.TestCase):
    def test_get_request_passes_params_and_cookie_header(self) -> None:
        client = FakeClient(FakeResponse(200, '{"ok": true}'))
        config = base_config()

        fetch_direct_api_data(config, client=client)

        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["kwargs"]["params"], config["params"])
        self.assertEqual(call["kwargs"]["headers"]["Cookie"], "cookie-a=1; cookie-b=2")

    def test_post_request_uses_json_body(self) -> None:
        client = FakeClient(FakeResponse(200, '{"ok": true}'))
        config = base_config(method="POST", params={}, body={"page": 1, "pageSize": 20})

        fetch_direct_api_data(config, client=client)

        call = client.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["kwargs"]["json"], {"page": 1, "pageSize": 20})

    def test_jsonp_response_is_parsed(self) -> None:
        client = FakeClient(FakeResponse(200, 'mtopjsonp1({"data":{"data":{"data":[]}}});'))

        parsed = fetch_direct_api_data(base_config(), client=client)

        self.assertEqual(parsed, {"data": {"data": {"data": []}}})

    def test_onequery_row_is_matched_and_converted_to_upload_payload(self) -> None:
        raw = onequery_payload(
            {
                "accountNickWang": {"value": "林志玲"},
                "statDate": {"value": "2026-04-25"},
                "consultUserCnt": {"value": "20"},
                "wwwRecUserCnt": {"value": "18"},
                "validReplyUv": {"value": "-"},
                "wwwConsultUv": {"value": "5"},
                "consultFinalPayRate": {"value": "27.5%"},
                "firstReplyInterval": {"value": "12秒"},
                "avgReplyInterval": {"value": "9.5秒"},
                "wwUserReplayRate": {"value": "96.2%"},
                "customerAllSateRate": {"value": "98.8%"},
            }
        )

        payload = parse_direct_api_payload(raw, base_config(), {})

        self.assertEqual(payload["loginAccount"], "远盛电商")
        self.assertEqual(payload["recordDate"], "2026-04-25")
        self.assertEqual(payload["subAccount"], "林志玲")
        self.assertEqual(payload["consultationCount"], 20)
        self.assertEqual(payload["receiveCount"], 18)
        self.assertIsNone(payload["validReceiveCount"])
        self.assertEqual(payload["inquiryCount"], 5)
        self.assertEqual(payload["conversionRate"], 27.5)
        self.assertEqual(payload["firstReplyTime"], 12.0)
        self.assertEqual(payload["avgReplyTime"], 9.5)
        self.assertEqual(payload["wwReplyRate"], 96.2)
        self.assertEqual(payload["satisfaction"], 98.8)

    def test_unauthorized_response_reports_cookie_expired(self) -> None:
        client = FakeClient(FakeResponse(401, '{"message":"unauthorized"}'))

        with self.assertRaisesRegex(DirectApiCaptureError, "Cookie 已过期"):
            fetch_direct_api_data(base_config(), client=client)

    def test_mtop_token_expired_response_reports_cookie_expired(self) -> None:
        client = FakeClient(FakeResponse(200, 'mtopjsonp1({"ret":["FAIL_SYS_TOKEN_EXOIRED::令牌过期"],"data":{}});'))

        with self.assertRaisesRegex(DirectApiCaptureError, "Cookie 已过期"):
            fetch_direct_api_data(base_config(), client=client)

    def test_mtop_error_response_is_logged_before_raising(self) -> None:
        client = FakeClient(FakeResponse(200, 'mtopjsonp1({"ret":["FAIL_SYS_TOKEN_EXOIRED::令牌过期"],"data":{}});'))
        logs = []

        with self.assertRaisesRegex(DirectApiCaptureError, "Cookie 已过期"):
            fetch_direct_api_data(base_config(), client=client, log=logs.append)

        self.assertTrue(any("ret=FAIL_SYS_TOKEN_EXOIRED::令牌过期" in item for item in logs))

    def test_capture_with_direct_api_uses_account_protected_cookie_without_writing_config(self) -> None:
        config = base_config()
        config.pop("cookie")
        config.pop("cookieProtected", None)
        client = FakeClient(
            FakeResponse(
                200,
                json.dumps(
                    onequery_payload(
                        {
                            "accountNickWang": {"value": "林志玲"},
                            "statDate": {"value": "2026-05-08"},
                            "consultUserCnt": {"value": "7"},
                        }
                    ),
                    ensure_ascii=False,
                ),
            )
        )
        account_cookie = "_m_h5_tk=token_1999999999999; sn=%E6%9E%97%E5%BF%97%E7%8E%B2; _tb_token_=tb"

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(config, ensure_ascii=False)),
            patch.object(Path, "write_text") as write_text,
            patch("direct_api_capture.unprotect_text", return_value=account_cookie) as unprotect_text,
        ):
            payload = capture_with_direct_api(
                {
                    "directApiConfigPath": "direct_api_capture.json",
                    "accountCookieRequired": True,
                    "cookieProtected": "dpapi:v1:encrypted-account-cookie",
                    "lastKnownLoginAccount": "林志玲",
                },
                log=lambda _message: None,
                client=client,
            )

        self.assertEqual(payload["subAccount"], "林志玲")
        self.assertEqual(client.calls[0]["kwargs"]["headers"]["Cookie"], account_cookie)
        unprotect_text.assert_called_once_with("dpapi:v1:encrypted-account-cookie")
        write_text.assert_not_called()

    def test_capture_with_direct_api_requires_saved_account_cookie(self) -> None:
        with self.assertRaisesRegex(DirectApiLoginRequiredError, "需要重新登录"):
            capture_with_direct_api(
                {
                    "directApiConfigPath": "direct_api_capture.json",
                    "accountCookieRequired": True,
                },
                log=lambda _message: None,
            )

    def test_capture_with_direct_api_rejects_account_cookie_without_login_markers(self) -> None:
        with patch("direct_api_capture.unprotect_text", return_value="_m_h5_tk=token_1999999999999"):
            with self.assertRaisesRegex(DirectApiLoginRequiredError, "需要重新登录"):
                capture_with_direct_api(
                    {
                        "directApiConfigPath": "direct_api_capture.json",
                        "accountCookieRequired": True,
                        "cookieProtected": "dpapi:v1:encrypted-account-cookie",
                    },
                    log=lambda _message: None,
                )

    def test_missing_config_does_not_send_request(self) -> None:
        client = FakeClient(FakeResponse(200, "{}"))
        missing_path = Path("missing_direct_api_capture.json")

        with self.assertRaisesRegex(DirectApiCaptureError, "未找到接口直采配置文件"):
            capture_with_direct_api({}, lambda _message: None, config_path=missing_path, client=client)

        self.assertEqual(client.calls, [])

    def test_config_loader_requires_params_or_body(self) -> None:
        raw_config = json.dumps(base_config(params={}, body={}), ensure_ascii=False)

        with patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", return_value=raw_config):
            with self.assertRaisesRegex(DirectApiCaptureError, "至少要填写一个"):
                load_direct_api_config(Path("direct_api_capture.json"))

    def test_config_loader_decrypts_protected_cookie(self) -> None:
        raw = base_config()
        raw.pop("cookie")
        raw["cookieProtected"] = "dpapi:v1:encrypted"

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(raw, ensure_ascii=False)),
            patch("direct_api_capture.unprotect_text", return_value="secret=hidden; _m_h5_tk=token_1"),
        ):
            loaded = load_direct_api_config(Path("direct_api_capture.json"))

        self.assertEqual(loaded["cookie"], "secret=hidden; _m_h5_tk=token_1")
        self.assertEqual(loaded["cookieProtected"], "dpapi:v1:encrypted")

    def test_multiple_requests_are_merged(self) -> None:
        class MultiClient:
            def __init__(self):
                self.calls = []
                self.responses = [
                    FakeResponse(
                        200,
                        json.dumps(
                            onequery_payload(
                                {
                                    "accountNickWang": {"value": "林志玲"},
                                    "statDate": {"value": "2026-04-25 00:00:00"},
                                    "consultUserCnt": {"value": 20},
                                    "consultFinalPayRate": {"value": "27.5%"},
                                    "avgReplyInterval": {"value": "9.5秒"},
                                }
                            ),
                            ensure_ascii=False,
                        ),
                    ),
                    FakeResponse(
                        200,
                        json.dumps(
                            onequery_payload(
                                {
                                    "accountNickWang": {"value": "林志玲"},
                                    "statDate": {"value": "2026-04-25 00:00:00"},
                                    "wwwRecUserCnt": {"value": 18},
                                    "validReplyUv": {"value": 17},
                                    "wwwConsultUv": {"value": 5},
                                    "firstReplyInterval": {"value": "12秒"},
                                    "wwUserReplayRate": {"value": "96.2%"},
                                }
                            ),
                            ensure_ascii=False,
                        ),
                    ),
                ]

            def request(self, method: str, url: str, **kwargs):  # noqa: ANN001, ANN201
                self.calls.append({"method": method, "url": url, "kwargs": kwargs})
                return self.responses.pop(0)

        config = base_config()
        config["requests"] = [
            {"apiUrl": "https://example.taobao.com/one", "params": {"data": "one"}},
            {"apiUrl": "https://example.taobao.com/two", "params": {"data": "two"}},
        ]
        client = MultiClient()

        with patch("direct_api_capture.load_direct_api_config", return_value=config):
            payload = capture_with_direct_api({}, lambda _message: None, client=client)

        self.assertEqual(len(client.calls), 2)
        self.assertEqual(payload["consultationCount"], 20)
        self.assertEqual(payload["conversionRate"], 27.5)
        self.assertEqual(payload["avgReplyTime"], 9.5)
        self.assertEqual(payload["receiveCount"], 18)
        self.assertEqual(payload["validReceiveCount"], 17)
        self.assertEqual(payload["inquiryCount"], 5)
        self.assertEqual(payload["firstReplyTime"], 12.0)
        self.assertEqual(payload["wwReplyRate"], 96.2)

    def test_capture_logs_cookie_and_response_summary_without_raw_cookie(self) -> None:
        row = {
            "accountNickWang": {"value": "林志玲"},
            "statDate": {"value": "2026-04-25"},
            "consultUserCnt": {"value": 20},
        }
        response = FakeResponse(
            200,
            json.dumps({"ret": ["SUCCESS::调用成功"], "data": {"data": {"data": [row]}}}, ensure_ascii=False),
        )
        client = FakeClient(response)
        config = base_config(cookie="secret-cookie=hidden; _m_h5_tk=abc_1777188499080; sn=x; unb=1; _tb_token_=token")
        logs = []

        with patch("direct_api_capture.load_direct_api_config", return_value=config):
            capture_with_direct_api({}, logs.append, client=client)

        joined = "\n".join(logs)
        self.assertIn("接口直采第 1 组 Cookie 状态", joined)
        self.assertIn("ret=SUCCESS::调用成功", joined)
        self.assertIn("data.data.data行数=1", joined)
        self.assertNotIn("secret-cookie=hidden", joined)

    def test_mtop_sign_and_date_range_are_generated_without_clicking_query(self) -> None:
        client = FakeClient(FakeResponse(200, '{"ok": true}'))
        data = {
            "domainCode": "tao.shop.qos.subaccount",
            "dateRange": "2026-04-25|2026-04-25",
            "extMap": "{\"greyTag\":\"Y\"}",
        }
        config = base_config(
            cookie="_m_h5_tk=abc123_1777188499080; other=1",
            recordDate="2026-04-26",
            params={
                "appKey": "12574478",
                "t": "old",
                "sign": "old",
                "data": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            },
        )

        with patch("direct_api_capture.time.time", return_value=1777182002.463):
            fetch_direct_api_data(config, client=client)

        sent_params = client.calls[0]["kwargs"]["params"]
        sent_data = json.loads(sent_params["data"])
        self.assertEqual(sent_params["t"], "1777182002463")
        self.assertEqual(sent_params["sign"], "3ea7ae2f9d4c07e8d5e0421fa4b1dbda")
        self.assertEqual(sent_data["dateRange"], "2026-04-26|2026-04-26")
        self.assertEqual(json.loads(sent_data["extMap"])["dateRange"], "2026-04-26|2026-04-26")

    def test_update_direct_api_cookie_updates_root_cookie(self) -> None:
        config_path = Path("direct_api_capture.json")
        config = base_config(cookie="old=1")
        config["extraField"] = "kept"

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(config, ensure_ascii=False)),
            patch.object(Path, "write_text") as write_text,
            patch.object(Path, "mkdir"),
            patch("direct_api_capture.protect_text", return_value="dpapi:v1:new-cookie"),
        ):
            updated = update_direct_api_cookie(config_path, "new=2; _m_h5_tk=token_1")

        written = json.loads(write_text.call_args.args[0])
        self.assertNotIn("cookie", updated)
        self.assertNotIn("cookie", written)
        self.assertEqual(updated["cookieProtected"], "dpapi:v1:new-cookie")
        self.assertEqual(written["cookieProtected"], "dpapi:v1:new-cookie")
        self.assertEqual(written["extraField"], "kept")
        self.assertEqual(write_text.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(write_text.call_args.kwargs["newline"], "\n")

    def test_update_direct_api_cookie_syncs_request_level_cookie(self) -> None:
        config_path = Path("direct_api_capture.json")
        config = base_config(cookie="old-root=1")
        config["requests"] = [
            {"apiUrl": "https://example.taobao.com/one", "params": {"data": "one"}, "cookie": "old-one=1"},
            {"apiUrl": "https://example.taobao.com/two", "params": {"data": "two"}},
        ]

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(config, ensure_ascii=False)),
            patch.object(Path, "write_text") as write_text,
            patch.object(Path, "mkdir"),
            patch("direct_api_capture.protect_text", return_value="dpapi:v1:new-cookie"),
        ):
            update_direct_api_cookie(config_path, "new-cookie=1; _m_h5_tk=token_1")

        written = json.loads(write_text.call_args.args[0])
        self.assertNotIn("cookie", written)
        self.assertEqual(written["cookieProtected"], "dpapi:v1:new-cookie")
        self.assertNotIn("cookie", written["requests"][0])
        self.assertNotIn("cookie", written["requests"][1])

    def test_migrate_direct_api_cookie_config_removes_plaintext_cookie(self) -> None:
        config_path = Path("direct_api_capture.json")
        config = base_config(cookie="old-root=1")
        config["requests"] = [
            {"apiUrl": "https://example.taobao.com/one", "params": {"data": "one"}, "cookie": "old-one=1"},
            {"apiUrl": "https://example.taobao.com/two", "params": {"data": "two"}},
        ]

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(config, ensure_ascii=False)),
            patch.object(Path, "write_text") as write_text,
            patch.object(Path, "mkdir"),
            patch("direct_api_capture.protect_text", return_value="dpapi:v1:migrated-cookie"),
        ):
            migrated = migrate_direct_api_cookie_config(config_path)

        written = json.loads(write_text.call_args.args[0])
        self.assertTrue(migrated)
        self.assertNotIn("cookie", written)
        self.assertNotIn("cookie", written["requests"][0])
        self.assertEqual(written["cookieProtected"], "dpapi:v1:migrated-cookie")
        self.assertEqual(written["loginAccount"], "远盛电商")
        self.assertEqual(written["subAccount"], "林志玲")

    def test_migrate_direct_api_cookie_config_keeps_file_on_encrypt_failure(self) -> None:
        config_path = Path("direct_api_capture.json")
        config = base_config(cookie="old-root=1")

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value=json.dumps(config, ensure_ascii=False)),
            patch.object(Path, "write_text") as write_text,
            patch("direct_api_capture.protect_text", side_effect=DirectApiCaptureError("encrypt failed")),
        ):
            with self.assertRaisesRegex(DirectApiCaptureError, "encrypt failed"):
                migrate_direct_api_cookie_config(config_path)

        write_text.assert_not_called()

    def test_summarize_cookie_reports_token_markers_without_value(self) -> None:
        summary = summarize_cookie("secret=hidden; _m_h5_tk=abc_1777188499080; sn=x; unb=1; _tb_token_=token")

        self.assertGreater(summary["length"], 0)
        self.assertTrue(summary["hasMtopToken"])
        self.assertEqual(summary["mtopExpiresAt"], "2026-04-26 15:28:19")
        self.assertTrue(summary["hasSn"])
        self.assertTrue(summary["hasUnb"])
        self.assertTrue(summary["hasTbToken"])


if __name__ == "__main__":
    unittest.main()
