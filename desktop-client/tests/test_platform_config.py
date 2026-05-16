from __future__ import annotations

import unittest

from platform_config import (
    JD_DATA_URL,
    JD_LOGIN_URL,
    JD_SERVICE_URL,
    PDD_LOGIN_URL,
    QN_LOGIN_URL,
    is_jd_login_page,
    is_jd_login_success_page,
    login_start_url_for_platform,
    normalize_platform,
)


class PlatformConfigTests(unittest.TestCase):
    def test_login_start_url_for_platform_routes_jd_and_keeps_qn_default(self) -> None:
        self.assertEqual(
            JD_LOGIN_URL,
            "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F",
        )
        self.assertEqual(JD_SERVICE_URL, "https://kf.jd.com/")
        self.assertEqual(JD_DATA_URL, "https://kf.jd.com/#/43")
        self.assertEqual(login_start_url_for_platform("jd"), JD_LOGIN_URL)
        self.assertEqual(login_start_url_for_platform("qn"), QN_LOGIN_URL)
        self.assertEqual(login_start_url_for_platform("unknown"), QN_LOGIN_URL)

    def test_pdd_platform_routes_to_merchant_login_entry(self) -> None:
        self.assertEqual(PDD_LOGIN_URL, "https://mms.pinduoduo.com/")
        self.assertEqual(normalize_platform("pdd"), "pdd")
        self.assertEqual(login_start_url_for_platform("pdd"), PDD_LOGIN_URL)
        self.assertEqual(normalize_platform("unknown"), "qn")

    def test_jd_login_page_detection(self) -> None:
        self.assertTrue(is_jd_login_page("https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F"))
        self.assertTrue(is_jd_login_page("http://passport.jd.com/uc/login"))
        self.assertFalse(is_jd_login_page("https://kf.jd.com/"))

    def test_jd_success_page_detection_accepts_http_and_https_service_home(self) -> None:
        self.assertTrue(is_jd_login_success_page("http://kf.jd.com/"))
        self.assertTrue(is_jd_login_success_page("https://kf.jd.com/"))
        self.assertTrue(is_jd_login_success_page("https://kf.jd.com/#/43"))
        self.assertFalse(is_jd_login_success_page("https://passport.jd.com/new/login.aspx"))


if __name__ == "__main__":
    unittest.main()
