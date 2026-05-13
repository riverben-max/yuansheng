from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch

import httpx

from jd_workload_capture import (
    JD_WORKLOAD_QUERY_URL,
    JdWorkloadCaptureError,
    JdWorkloadLoginRequiredError,
    build_jd_workload_request_params,
    capture_jd_workload,
    normalize_jd_cookie_header,
    parse_jd_workload_payload,
)


SAMPLE_RESPONSE = {
    "code": "success",
    "totalPage": 1,
    "totalDetail": {"consultNum": 58, "servicedNum": 58},
    "AvgDetail": {"responseAvgSpeed": 12.4},
    "totalRecordNum": 1,
    "page": 1,
    "workKpiList": [
        {
            "dayStr": "2026-05-12",
            "waiter": "未分配",
            "servicePin": "if自营菠萝",
            "consultNum": 58,
            "servicedNum": 58,
            "receiveNum": 99,
            "responseAvgSpeed": 12.4,
            "responseAvgDurationWithLeave": 25.98,
            "sessionAvgDuration": 14.7,
            "responseRate": "100.0%",
            "satisfiedRate": "75.00%",
            "onlineTime": 16.2,
            "serviceTime": 16.2,
            "receiveNum30Rate": "92.8%",
            "solvedRate": "50.00%",
        }
    ],
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


class JdWorkloadCaptureTests(unittest.TestCase):
    def test_build_request_params_uses_yesterday_and_service_pin(self) -> None:
        params = build_jd_workload_request_params("if自营菠萝", today=date(2026, 5, 13))

        self.assertEqual(
            params,
            {
                "page": 1,
                "pageSize": 15,
                "startTime": "2026-05-12",
                "endTime": "2026-05-12",
                "transferType": 1,
                "type": 1,
                "servicePin": "if自营菠萝",
            },
        )

    def test_parse_payload_maps_har_workload_row_to_upload_fields(self) -> None:
        payload = parse_jd_workload_payload(
            SAMPLE_RESPONSE,
            request_params={"servicePin": "if自营菠萝", "startTime": "2026-05-12"},
            state={"shopName": "京东菠萝店", "lastKnownLoginAccount": "if自营菠萝"},
        )

        self.assertEqual(payload["loginAccount"], "京东菠萝店")
        self.assertEqual(payload["recordDate"], "2026-05-12")
        self.assertEqual(payload["subAccount"], "未分配")
        self.assertEqual(payload["consultationCount"], 58)
        self.assertEqual(payload["receiveCount"], 58)
        self.assertIsNone(payload["validReceiveCount"])
        self.assertIsNone(payload["inquiryCount"])
        self.assertIsNone(payload["conversionRate"])
        self.assertEqual(payload["firstReplyTime"], 12.4)
        self.assertEqual(payload["avgReplyTime"], 25.98)
        self.assertEqual(payload["wwReplyRate"], 100.0)
        self.assertEqual(payload["satisfaction"], 75.0)
        self.assertEqual(payload["rawMetrics"]["source"], "jd_workload")
        self.assertEqual(payload["rawMetrics"]["requestParams"]["servicePin"], "if自营菠萝")
        self.assertEqual(payload["rawMetrics"]["rowData"]["onlineTime"], 16.2)
        self.assertEqual(payload["rawMetrics"]["totalDetail"]["consultNum"], 58)
        self.assertEqual(payload["rawMetrics"]["AvgDetail"]["responseAvgSpeed"], 12.4)

    def test_receive_count_falls_back_to_receive_num(self) -> None:
        response = dict(SAMPLE_RESPONSE)
        row = dict(SAMPLE_RESPONSE["workKpiList"][0])
        row.pop("servicedNum")
        row["receiveNum"] = 45
        response["workKpiList"] = [row]

        payload = parse_jd_workload_payload(response, request_params={}, state={})

        self.assertEqual(payload["receiveCount"], 45)

    def test_avg_reply_time_uses_with_leave_not_session_duration(self) -> None:
        payload = parse_jd_workload_payload(SAMPLE_RESPONSE, request_params={}, state={})

        self.assertEqual(payload["avgReplyTime"], 25.98)
        self.assertNotEqual(payload["avgReplyTime"], 14.7)

    def test_capture_requires_saved_cookie(self) -> None:
        with self.assertRaises(JdWorkloadLoginRequiredError):
            capture_jd_workload({"lastKnownLoginAccount": "if自营菠萝"}, lambda _message: None)

    def test_capture_requires_service_pin(self) -> None:
        with patch("jd_workload_capture.unprotect_text", return_value="pin=if自营菠萝; thor=token"):
            with self.assertRaises(JdWorkloadCaptureError):
                capture_jd_workload({"cookieProtected": "dpapi:v1:cookie"}, lambda _message: None)

    def test_capture_wraps_cookie_decrypt_failure_as_relogin(self) -> None:
        with patch("jd_workload_capture.unprotect_text", side_effect=Exception("bad dpapi")):
            with self.assertRaises(JdWorkloadLoginRequiredError):
                capture_jd_workload(
                    {"cookieProtected": "dpapi:v1:cookie", "lastKnownLoginAccount": "if自营菠萝"},
                    lambda _message: None,
                )

    def test_capture_treats_401_and_403_as_relogin(self) -> None:
        for status_code in (401, 403):
            client = FakeClient(FakeResponse(status_code, {"code": "fail"}))
            with patch("jd_workload_capture.unprotect_text", return_value="pin=if自营菠萝; thor=token"):
                with self.assertRaises(JdWorkloadLoginRequiredError):
                    capture_jd_workload(
                        {"cookieProtected": "dpapi:v1:cookie", "lastKnownLoginAccount": "if自营菠萝"},
                        lambda _message: None,
                        client=client,
                        today=date(2026, 5, 13),
                    )

    def test_capture_rejects_non_success_code_and_empty_rows(self) -> None:
        with self.assertRaises(JdWorkloadCaptureError):
            parse_jd_workload_payload({"code": "fail", "message": "bad"}, request_params={}, state={})

        with self.assertRaises(JdWorkloadCaptureError):
            parse_jd_workload_payload({"code": "success", "workKpiList": []}, request_params={}, state={})

    def test_capture_fetches_workload_endpoint_with_cookie_and_params(self) -> None:
        client = FakeClient(FakeResponse(200, SAMPLE_RESPONSE))

        with patch("jd_workload_capture.unprotect_text", return_value="pin=if自营菠萝; thor=token"):
            payload = capture_jd_workload(
                {
                    "cookieProtected": "dpapi:v1:cookie",
                    "lastKnownLoginAccount": "if自营菠萝",
                    "shopName": "京东菠萝店",
                },
                lambda _message: None,
                client=client,
                today=date(2026, 5, 13),
            )

        self.assertEqual(payload["recordDate"], "2026-05-12")
        self.assertEqual(client.calls[0][0], JD_WORKLOAD_QUERY_URL)
        self.assertEqual(client.calls[0][1]["params"]["servicePin"], "if自营菠萝")
        self.assertEqual(client.calls[0][1]["headers"]["Cookie"], "pin=if自营菠萝; thor=token")
        self.assertEqual(client.calls[0][1]["headers"]["Origin"], "https://xi.jd.com")
        self.assertEqual(
            client.calls[0][1]["headers"]["Referer"],
            "https://xi.jd.com/customerassistant/filterCustomer.html?menu=waiterPerson&content=workload",
        )

    def test_capture_sends_deduplicated_jd_cookie_header(self) -> None:
        client = FakeClient(FakeResponse(200, SAMPLE_RESPONSE))
        noisy_cookie = (
            "QRCodeKey=login-page; pin=old-pin; thor=old-thor; flash=old; "
            "pin=if自营菠萝; thor=token; light_key=light; unick=name; "
            "pin=if自营菠萝; thor=token; __jda=track; __jdb=session; random_cookie=value"
        )

        with patch("jd_workload_capture.unprotect_text", return_value=noisy_cookie):
            capture_jd_workload(
                {"cookieProtected": "dpapi:v1:cookie", "lastKnownLoginAccount": "if自营菠萝"},
                lambda _message: None,
                client=client,
                today=date(2026, 5, 13),
            )

        sent_cookie = client.calls[0][1]["headers"]["Cookie"]
        self.assertEqual(sent_cookie.count("pin="), 1)
        self.assertEqual(sent_cookie.count("thor="), 1)
        self.assertIn("pin=if自营菠萝", sent_cookie)
        self.assertIn("thor=token", sent_cookie)
        self.assertNotIn("QRCodeKey=", sent_cookie)
        self.assertNotIn("random_cookie=", sent_cookie)

    def test_normalize_jd_cookie_header_rejects_missing_login_markers(self) -> None:
        with self.assertRaises(JdWorkloadLoginRequiredError):
            normalize_jd_cookie_header("__jda=track; __jdb=session")

    def test_http_400_error_includes_response_body_summary(self) -> None:
        client = FakeClient(FakeResponse(400, {"code": "bad", "message": "referer invalid"}))
        client.response.text = '{"code":"bad","message":"referer invalid"}'

        with patch("jd_workload_capture.unprotect_text", return_value="pin=if自营菠萝; thor=token"):
            with self.assertRaisesRegex(JdWorkloadCaptureError, "referer invalid"):
                capture_jd_workload(
                    {"cookieProtected": "dpapi:v1:cookie", "lastKnownLoginAccount": "if自营菠萝"},
                    lambda _message: None,
                    client=client,
                )

    def test_capture_wraps_http_transport_errors(self) -> None:
        class BrokenClient:
            def get(self, *_args, **_kwargs):
                raise httpx.ConnectError("network down")

        with patch("jd_workload_capture.unprotect_text", return_value="pin=if自营菠萝; thor=token"):
            with self.assertRaises(JdWorkloadCaptureError):
                capture_jd_workload(
                    {"cookieProtected": "dpapi:v1:cookie", "lastKnownLoginAccount": "if自营菠萝"},
                    lambda _message: None,
                    client=BrokenClient(),
                )


if __name__ == "__main__":
    unittest.main()
