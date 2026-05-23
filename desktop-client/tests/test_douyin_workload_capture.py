from __future__ import annotations

import unittest

from douyin_workload_capture import DouyinWorkloadCaptureError, parse_douyin_workload_payload


FIRST_ROW = {
    "staffName": "抖店客服一号",
    "staffUserInfo": {"staffNickName": "客服一号昵称", "staffAccountName": "dy-one"},
    "inquiryCnt": 3,
    "servUserCnt": 2,
    "servConvCnt": 1,
    "threeMinRespRate": "90.00%",
}

SECOND_ROW = {
    "staffName": "抖店客服二号",
    "staffUserInfo": {"staffNickName": "客服二号昵称", "staffAccountName": "dy-two"},
    "inquiryCnt": 8,
    "servUserCnt": 7,
    "servConvCnt": 6,
    "threeMinRespRate": "60.00%",
}


class DouyinWorkloadCaptureTests(unittest.TestCase):
    def test_multi_row_matches_login_hint(self) -> None:
        payload = parse_douyin_workload_payload(
            {"code": 0, "data": {"staffDataModel": [FIRST_ROW, SECOND_ROW]}},
            request_params={"recordDate": "2026-05-17"},
            state={"shopName": "抖店远盛店", "loginHint": "dy-two"},
        )

        self.assertEqual(payload["subAccount"], "抖店客服二号")
        self.assertEqual(payload["consultationCount"], 8)
        self.assertEqual(payload["wwReplyRate"], 60.0)

    def test_multi_row_requires_identity_match(self) -> None:
        with self.assertRaisesRegex(DouyinWorkloadCaptureError, "多个客服.*登录识别名"):
            parse_douyin_workload_payload(
                {"code": 0, "data": {"staffDataModel": [FIRST_ROW, SECOND_ROW]}},
                request_params={"recordDate": "2026-05-17"},
                state={"shopName": "抖店远盛店", "loginHint": "不存在"},
            )

    def test_multi_row_does_not_match_shop_name(self) -> None:
        with self.assertRaisesRegex(DouyinWorkloadCaptureError, "多个客服.*登录识别名"):
            parse_douyin_workload_payload(
                {"code": 0, "data": {"staffDataModel": [FIRST_ROW, SECOND_ROW]}},
                request_params={"recordDate": "2026-05-17"},
                state={"shopName": "dy-two"},
            )


if __name__ == "__main__":
    unittest.main()
