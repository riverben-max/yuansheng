from __future__ import annotations

import unittest

from external_capture import _read_identity_from_cookies
from spider_core import extract_account_row, merge_capture_payloads, normalize_account_for_match
from table_capture import TABLE_METRIC_ROUNDS, table_result_to_payload


class TableCaptureTests(unittest.TestCase):
    def test_table_result_to_payload_matches_current_employee(self) -> None:
        result = {
            "ok": True,
            "headers": ["序号", "客服", "咨询人数", "接待人数", "有效接待人数", "询单人数", "询单转化率", "首次响应时长（秒）"],
            "rows": [
                ["1", "小王", "9", "8", "7", "2", "22.22%", "18秒"],
                ["2", "林志玲", "20", "18", "17", "5", "27.5%", "12秒"],
            ],
            "currentNick": "远盛电商:林志玲",
            "pageTitle": "绩效考核 2026-04-21",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-21",
        }

        payload = table_result_to_payload(result, TABLE_METRIC_ROUNDS[0])

        self.assertEqual(payload["loginAccount"], "远盛电商:林志玲")
        self.assertEqual(payload["recordDate"], "2026-04-21")
        self.assertEqual(payload["subAccount"], "林志玲")
        self.assertEqual(payload["consultationCount"], 20)
        self.assertEqual(payload["receiveCount"], 18)
        self.assertEqual(payload["validReceiveCount"], 17)
        self.assertEqual(payload["inquiryCount"], 5)
        self.assertEqual(payload["conversionRate"], 27.5)
        self.assertEqual(payload["firstReplyTime"], 12.0)

    def test_merge_two_round_payloads_keeps_single_employee_summary(self) -> None:
        first_round = {
            "ok": True,
            "headers": ["序号", "客服", "咨询人数", "接待人数", "有效接待人数", "询单人数", "询单转化率", "首次响应时长（秒）"],
            "rows": [
                ["全店", "汇总", "100", "80", "70", "50", "25%", "18秒"],
                ["1", "林志玲", "20", "18", "17", "5", "27.5%", "12秒"],
            ],
            "currentNick": "远盛电商:林志玲",
            "pageTitle": "绩效考核 2026-04-21",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-21",
        }
        second_round = {
            "ok": True,
            "headers": ["序号", "客服", "平均响应时长（秒）", "旺旺回复率", "客户满意率"],
            "rows": [
                ["全店", "平均", "20秒", "80%", "90%"],
                ["1", "林志玲", "9.5秒", "96.2%", "98.8%"],
            ],
            "currentNick": "远盛电商:林志玲",
            "pageTitle": "绩效考核 2026-04-21",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-21",
        }

        merged = merge_capture_payloads(
            [
                table_result_to_payload(first_round, TABLE_METRIC_ROUNDS[0]),
                table_result_to_payload(second_round, TABLE_METRIC_ROUNDS[1]),
            ]
        )

        self.assertEqual(merged["subAccount"], "林志玲")
        self.assertEqual(merged["consultationCount"], 20)
        self.assertEqual(merged["avgReplyTime"], 9.5)
        self.assertEqual(merged["wwReplyRate"], 96.2)
        self.assertEqual(merged["satisfaction"], 98.8)

    def test_table_result_to_payload_raises_when_current_employee_missing(self) -> None:
        result = {
            "ok": True,
            "headers": ["排名", "旺旺账号", "咨询人数"],
            "rows": [
                ["全店", "汇总", "100"],
                ["全店", "平均", "10"],
                ["1", "林志玲", "9"],
            ],
            "currentNick": "远盛电商:不存在的账号",
            "pageTitle": "绩效考核 2026-04-21",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-21",
        }

        with self.assertRaisesRegex(ValueError, "当前登录员工不在表格中"):
            table_result_to_payload(result, TABLE_METRIC_ROUNDS[0])

    def test_table_result_to_payload_matches_prefixed_headers(self) -> None:
        result = {
            "ok": True,
            "headers": ["排名", "旺旺账号", "咨询人数", "延 询单人数", "延 询单转化率", "首次响应时长（秒）"],
            "rows": [["1", "林志玲", "0", "3", "12.5%", "0.00"]],
            "currentNick": "远盛电商:林志玲",
            "pageTitle": "绩效考核 2026-04-21",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-21",
        }

        payload = table_result_to_payload(result, TABLE_METRIC_ROUNDS[0])
        self.assertEqual(payload["inquiryCount"], 3)
        self.assertEqual(payload["conversionRate"], 12.5)

    def test_table_result_to_payload_matches_delayed_inquiry_aliases(self) -> None:
        round_config = {
            "name": "第一阶段",
            "fields": {
                "inquiryCount": ["询单人数", "延询单人数"],
                "conversionRate": ["询单转化率", "延询单转化率"],
            },
        }
        result = {
            "ok": True,
            "headers": ["排名", "旺旺账号", "延询单人数", "延询单转化率"],
            "rows": [["1", "林志玲", "6", "33.3%"]],
            "currentNick": "远盛电商:林志玲",
            "pageTitle": "绩效考核 2026-04-22",
            "pageUrl": "https://myseller.taobao.com/home.htm/op-sycm-svc/overview",
            "bodyText": "绩效考核 2026-04-22",
        }

        payload = table_result_to_payload(result, round_config)
        self.assertEqual(payload["inquiryCount"], 6)
        self.assertEqual(payload["conversionRate"], 33.3)

    def test_account_matching_uses_suffix_after_shop_prefix(self) -> None:
        payload = {
            "data": {
                "data": {
                    "data": [
                        {"accountNickWang": {"value": "小猪"}},
                        {"accountNickWang": {"value": "林志玲"}},
                    ]
                }
            }
        }

        self.assertEqual(normalize_account_for_match("远盛电商:林志玲"), "林志玲")
        row = extract_account_row(payload, "远盛电商:林志玲")
        self.assertIsNotNone(row)
        self.assertEqual(row["accountNickWang"]["value"], "林志玲")

    def test_read_identity_from_encoded_sn_cookie(self) -> None:
        class FakePage:
            def cookies(self, all_domains=False):  # noqa: ANN001
                return [
                    {
                        "name": "sn",
                        "value": "%E8%BF%9C%E7%9B%9B%E7%94%B5%E5%95%86%3A%E6%9E%97%E5%BF%97%E7%8E%B2",
                        "domain": ".taobao.com",
                    }
                ]

        self.assertEqual(_read_identity_from_cookies(FakePage()), "远盛电商:林志玲")


if __name__ == "__main__":
    unittest.main()
