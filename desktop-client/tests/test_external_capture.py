from __future__ import annotations

import unittest

import external_capture
from spider_core import EMPLOYEE_TARGET_URL, PageSnapshot, snapshot_requires_login


class FakePage:
    def __init__(self, url: str, title: str = "新标签页") -> None:
        self.url = url
        self.title = title
        self.opened_urls = []

    def get(self, url: str) -> None:
        self.opened_urls.append(url)
        self.url = url
        self.title = "千牛工作台"


class ExternalCapturePageSelectionTests(unittest.TestCase):
    def test_login_check_navigates_blank_or_google_tab_to_target_page(self) -> None:
        page = FakePage("chrome://newtab/")
        logs = []

        external_capture._ensure_login_relevant_page(page, logs.append)

        self.assertEqual(page.opened_urls, [EMPLOYEE_TARGET_URL])
        self.assertTrue(any("当前接管页面" in item for item in logs))

    def test_login_check_keeps_existing_taobao_login_page(self) -> None:
        page = FakePage("https://loginmyseller.taobao.com/", "千牛登录")
        logs = []

        external_capture._ensure_login_relevant_page(page, logs.append)

        self.assertEqual(page.opened_urls, [])
        self.assertTrue(any("loginmyseller.taobao.com" in item for item in logs))

    def test_jd_login_check_keeps_existing_service_page(self) -> None:
        page = FakePage("https://kf.jd.com/#/43", "京东客服")
        logs = []

        external_capture._ensure_login_relevant_page(page, logs.append, platform="jd")

        self.assertEqual(page.opened_urls, [])
        self.assertTrue(any("kf.jd.com" in item for item in logs))

    def test_loginmyseller_page_always_requires_login(self) -> None:
        snapshot = PageSnapshot(
            title="千牛工作台 - 商家一站式经营阵地",
            url="https://loginmyseller.taobao.com/",
            text="",
        )

        self.assertTrue(snapshot_requires_login(snapshot))

    def test_myseller_overview_without_login_markers_is_logged_in_candidate(self) -> None:
        snapshot = PageSnapshot(
            title="千牛工作台 - 商家一站式经营阵地",
            url=EMPLOYEE_TARGET_URL,
            text="经营数据概览",
        )

        self.assertFalse(snapshot_requires_login(snapshot))


if __name__ == "__main__":
    unittest.main()
