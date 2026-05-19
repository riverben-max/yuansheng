from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch

import httpx

import pdd_workload_capture
from pdd_workload_capture import (
    PDD_REPORT_URL,
    PddWorkloadCaptureError,
    PddWorkloadLoginRequiredError,
    build_pdd_report_request_params,
    capture_pdd_workload,
    normalize_pdd_cookie_header,
    parse_pdd_workload_payload,
)


SAMPLE_ROW = {
    "cs_name": "屿你服饰星星",
    "uid": 172906144,
    "mms_uid": 172906144,
    "recv_user": 0,
    "inquiry_user": 2,
    "final_group_user": 1,
    "inquiry_loss_user": 0,
    "inquiry_group_rate": 0.5,
    "cs_sales_amount": 12345,
    "nrfnd_ordr_amt_3d": 1000,
    "send_user": 0,
    "unreply_user": 0,
    "delay30_reply": 0,
    "5min_reply_rate": 100,
    "reply_30s_rate": 0.75,
    "avg_reply_time": 12,
    "unsatisfied_serve_score_cnt": 3,
    "serve_score_cnt": 0,
    "unsatisfied_serve_score_rate": 0,
    "serve_refund_cnt": 4,
    "serve_order_cnt": 0,
    "complain_user_cnt": 5,
    "reply_rate_3_min": 0.8,
    "delay_reply": 6,
    "consult_user_cnt": 7,
    "receive_user_cnt": 8,
    "need_manu_reply_consult_user_cnt": 9,
    "in_24hour_reply_rate_3_min": 0,
    "in_24hour_reply_30s_rate": 0,
    "mcht_server_score": "3.7",
}

SECOND_ROW = {
    **SAMPLE_ROW,
    "cs_name": "远盛客服小满",
    "uid": 99887766,
    "mms_uid": 99887766,
    "consult_user_cnt": 11,
    "receive_user_cnt": 10,
    "inquiry_user": 4,
    "inquiry_group_rate": 0.25,
    "reply_rate_3_min": 0.6,
    "cs_sales_amount": 8800,
}


class FakeResponse:
    def __init__(self, status_code: int, payload: object):
        self.status_code = status_code
        self._payload = payload
        self.text = "{}"

    def json(self) -> object:
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


VALID_COOKIE = (
    "PASS_ID=pass-token; JSESSIONID=session-token; "
    "mms_user=merchant; windows_app_shop_token_123=shop-token"
)


class PddWorkloadCaptureTests(unittest.TestCase):
    def test_builds_yesterday_unix_seconds_for_report_query(self) -> None:
        params = build_pdd_report_request_params(today=date(2026, 5, 18))

        self.assertEqual(params, {"starttime": 1778947200, "endtime": 1778947200, "recordDate": "2026-05-17"})

    def test_capture_fetches_report_endpoint_with_cookie_and_params(self) -> None:
        client = FakeClient(FakeResponse(200, {"success": True, "result": {"data": [SAMPLE_ROW]}}))

        with (
            patch("pdd_workload_capture.unprotect_text", return_value=VALID_COOKIE),
            patch("pdd_workload_capture.ensure_shadow_browser", side_effect=AssertionError("should not launch browser"), create=True),
        ):
            payload = capture_pdd_workload(
                {"cookieProtected": "dpapi:v1:cookie", "shopName": "拼多多远盛店"},
                log=lambda _message: None,
                today=date(2026, 5, 18),
                client=client,
            )

        self.assertEqual(client.calls[0][0], PDD_REPORT_URL)
        self.assertEqual(client.calls[0][1]["params"], {"starttime": 1778947200, "endtime": 1778947200})
        self.assertEqual(client.calls[0][1]["headers"]["Cookie"], VALID_COOKIE)
        self.assertEqual(client.calls[0][1]["headers"]["Origin"], "https://mms.pinduoduo.com")
        self.assertEqual(
            client.calls[0][1]["headers"]["Referer"],
            "https://mms.pinduoduo.com/mms-chat/overview/merchant",
        )
        self.assertEqual(payload["loginAccount"], "拼多多远盛店")
        self.assertEqual(payload["recordDate"], "2026-05-17")
        self.assertEqual(payload["subAccount"], "屿你服饰星星")
        self.assertEqual(payload["consultationCount"], 7)
        self.assertEqual(payload["receiveCount"], 8)
        self.assertEqual(payload["inquiryCount"], 2)
        self.assertEqual(payload["conversionRate"], 50)
        self.assertEqual(payload["avgReplyTime"], 12)
        self.assertEqual(payload["wwReplyRate"], 80)
        self.assertEqual(payload["rawMetrics"]["mcht_server_score"], "3.7")
        self.assertEqual(payload["rawMetrics"]["reply_30s_rate"], 0.75)
        self.assertEqual(payload["rawMetrics"]["salesAmountYuan"], 123.45)
        self.assertEqual(payload["rawMetrics"]["accountIdentity"], "屿你服饰星星")
        self.assertEqual(payload["rawMetrics"]["source"], "pdd_cs_report_detail")

    def test_capture_requires_saved_cookie(self) -> None:
        with self.assertRaises(PddWorkloadLoginRequiredError):
            capture_pdd_workload({}, lambda _message: None)

    def test_capture_wraps_cookie_decrypt_failure_as_relogin(self) -> None:
        with patch("pdd_workload_capture.unprotect_text", side_effect=Exception("bad dpapi")):
            with self.assertRaises(PddWorkloadLoginRequiredError):
                capture_pdd_workload({"cookieProtected": "dpapi:v1:cookie"}, lambda _message: None)

    def test_normalize_cookie_rejects_missing_login_markers(self) -> None:
        required_parts = [
            "PASS_ID=pass-token",
            "JSESSIONID=session-token",
            "mms_user=merchant",
            "windows_app_shop_token_123=shop-token",
        ]
        for part in required_parts:
            cookie = "; ".join(item for item in required_parts if item != part)
            with self.subTest(missing=part):
                with self.assertRaises(PddWorkloadLoginRequiredError):
                    normalize_pdd_cookie_header(cookie)

    def test_capture_treats_401_and_403_as_relogin(self) -> None:
        for status_code in (401, 403):
            client = FakeClient(FakeResponse(status_code, {"success": False}))
            with patch("pdd_workload_capture.unprotect_text", return_value=VALID_COOKIE):
                with self.subTest(status_code=status_code):
                    with self.assertRaises(PddWorkloadLoginRequiredError):
                        capture_pdd_workload(
                            {"cookieProtected": "dpapi:v1:cookie"},
                            lambda _message: None,
                            today=date(2026, 5, 18),
                            client=client,
                        )

    def test_api_failure_raises_capture_error(self) -> None:
        with self.assertRaisesRegex(PddWorkloadCaptureError, "接口返回失败"):
            parse_pdd_workload_payload({"success": False, "errorMsg": "forbidden"}, {}, {})

    def test_empty_rows_raise_capture_error(self) -> None:
        with self.assertRaisesRegex(PddWorkloadCaptureError, "没有客服绩效数据"):
            parse_pdd_workload_payload({"success": True, "result": {"data": []}}, {}, {})

    def test_multi_row_matches_last_known_login_account(self) -> None:
        payload = parse_pdd_workload_payload(
            {"success": True, "result": {"data": [SAMPLE_ROW, SECOND_ROW]}},
            {"recordDate": "2026-05-17"},
            {"shopName": "拼多多远盛店", "lastKnownLoginAccount": "远盛客服小满"},
        )

        self.assertEqual(payload["subAccount"], "远盛客服小满")
        self.assertEqual(payload["consultationCount"], 11)
        self.assertEqual(payload["wwReplyRate"], 60)

    def test_multi_row_matches_login_hint_uid(self) -> None:
        payload = parse_pdd_workload_payload(
            {"success": True, "result": {"data": [SAMPLE_ROW, SECOND_ROW]}},
            {"recordDate": "2026-05-17"},
            {"shopName": "拼多多远盛店", "loginHint": "99887766"},
        )

        self.assertEqual(payload["subAccount"], "远盛客服小满")
        self.assertEqual(payload["rawMetrics"]["accountIdentity"], "远盛客服小满")

    def test_multi_row_prefers_last_known_login_account_when_hints_conflict(self) -> None:
        payload = parse_pdd_workload_payload(
            {"success": True, "result": {"data": [SAMPLE_ROW, SECOND_ROW]}},
            {"recordDate": "2026-05-17"},
            {
                "shopName": "拼多多远盛店",
                "lastKnownLoginAccount": "远盛客服小满",
                "loginHint": "172906144",
            },
        )

        self.assertEqual(payload["subAccount"], "远盛客服小满")

    def test_multi_row_requires_identity_match(self) -> None:
        with self.assertRaisesRegex(PddWorkloadCaptureError, "多个客服.*登录识别名"):
            parse_pdd_workload_payload(
                {"success": True, "result": {"data": [SAMPLE_ROW, SECOND_ROW]}},
                {"recordDate": "2026-05-17"},
                {"shopName": "拼多多远盛店", "loginHint": "不存在"},
            )

    def test_rate_values_are_normalized_to_percent(self) -> None:
        cases = [
            (0, 0),
            (0.5, 50),
            (1, 100),
            (50, 50),
            (95, 95),
            (100, 100),
        ]
        for raw_value, expected in cases:
            row = {**SAMPLE_ROW, "inquiry_group_rate": raw_value, "reply_rate_3_min": raw_value}
            payload = parse_pdd_workload_payload(
                {"success": True, "result": {"data": [row]}},
                {"recordDate": "2026-05-17"},
                {"shopName": "拼多多远盛店"},
            )
            with self.subTest(raw_value=raw_value):
                self.assertEqual(payload["conversionRate"], expected)
                self.assertEqual(payload["wwReplyRate"], expected)

    def test_http_400_error_includes_response_body_summary(self) -> None:
        client = FakeClient(FakeResponse(400, {"success": False, "errorMsg": "referer invalid"}))
        client.response.text = '{"success":false,"errorMsg":"referer invalid"}'

        with patch("pdd_workload_capture.unprotect_text", return_value=VALID_COOKIE):
            with self.assertRaisesRegex(PddWorkloadCaptureError, "referer invalid"):
                capture_pdd_workload(
                    {"cookieProtected": "dpapi:v1:cookie"},
                    lambda _message: None,
                    client=client,
                )

    def test_capture_wraps_http_transport_errors(self) -> None:
        class BrokenClient:
            def get(self, *_args, **_kwargs):
                raise httpx.ConnectError("network down")

        with patch("pdd_workload_capture.unprotect_text", return_value=VALID_COOKIE):
            with self.assertRaises(PddWorkloadCaptureError):
                capture_pdd_workload(
                    {"cookieProtected": "dpapi:v1:cookie"},
                    lambda _message: None,
                    client=BrokenClient(),
                )


if __name__ == "__main__":
    unittest.main()
