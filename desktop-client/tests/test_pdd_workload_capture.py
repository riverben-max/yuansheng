from __future__ import annotations

from datetime import date
import json
import unittest

from platform_config import PDD_CHAT_OVERVIEW_URL
from pdd_workload_capture import (
    PddWorkloadCaptureError,
    PddWorkloadLoginRequiredError,
    build_pdd_report_request_params,
    capture_pdd_workload,
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


class FakePage:
    def __init__(self, response: object, url: str = PDD_CHAT_OVERVIEW_URL) -> None:
        self.response = response
        self.url = url
        self.title = "拼多多商家后台"
        self.opened_urls: list[str] = []
        self.scripts: list[str] = []
        self._result_json = ""

    def get(self, url: str) -> None:
        self.opened_urls.append(url)
        if "/login/" not in self.url:
            self.url = url

    def run_js(self, script: str) -> str:
        self.scripts.append(script)
        if "__YS_PDD_CAPTURE_RESULT" in script and "fetch(" in script:
            self._result_json = json.dumps({"done": True, "ok": True, "data": self.response}, ensure_ascii=False)
            return ""
        if "JSON.stringify(window.__YS_PDD_CAPTURE_RESULT" in script:
            return self._result_json
        return ""


class FakeSession:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.pid = 123
        self.chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.profile_dir = r"C:\profile"
        self.port = 45678


class PddWorkloadCaptureTests(unittest.TestCase):
    def test_builds_yesterday_unix_seconds_for_report_query(self) -> None:
        params = build_pdd_report_request_params(today=date(2026, 5, 18))

        self.assertEqual(params, {"starttime": 1778947200, "endtime": 1778947200, "recordDate": "2026-05-17"})

    def test_capture_uses_page_fetch_and_maps_har_fields(self) -> None:
        page = FakePage({"success": True, "result": {"data": [SAMPLE_ROW]}})

        payload = capture_pdd_workload(
            {"shopName": "拼多多远盛店"},
            log=lambda _message: None,
            today=date(2026, 5, 18),
            browser_factory=lambda _state, _log: FakeSession(page),
        )

        self.assertEqual(page.opened_urls, [PDD_CHAT_OVERVIEW_URL])
        injected = "\n".join(page.scripts)
        self.assertIn("/chats/csReportDetail?starttime=1778947200&endtime=1778947200", injected)
        self.assertIn("credentials: 'include'", injected)
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

    def test_api_failure_raises_capture_error(self) -> None:
        with self.assertRaisesRegex(PddWorkloadCaptureError, "接口返回失败"):
            parse_pdd_workload_payload({"success": False, "errorMsg": "forbidden"}, {}, {})

    def test_empty_rows_raise_capture_error(self) -> None:
        with self.assertRaisesRegex(PddWorkloadCaptureError, "没有客服绩效数据"):
            parse_pdd_workload_payload({"success": True, "result": {"data": []}}, {}, {})

    def test_login_page_after_navigation_raises_login_required(self) -> None:
        page = FakePage({"success": True, "result": {"data": [SAMPLE_ROW]}}, url="https://mms.pinduoduo.com/login/")

        with self.assertRaisesRegex(PddWorkloadLoginRequiredError, "需要重新登录"):
            capture_pdd_workload(
                {},
                log=lambda _message: None,
                today=date(2026, 5, 18),
                browser_factory=lambda _state, _log: FakeSession(page),
            )


if __name__ == "__main__":
    unittest.main()
