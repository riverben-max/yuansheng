from __future__ import annotations

from urllib.parse import urlparse

QN_LOGIN_URL = "https://loginmyseller.taobao.com/"
JD_LOGIN_URL = "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F"
JD_SERVICE_URL = "https://kf.jd.com/"
JD_DATA_URL = "https://kf.jd.com/#/43"
PDD_LOGIN_URL = "https://mms.pinduoduo.com/"


def normalize_platform(raw: object) -> str:
    platform = str(raw or "").strip().lower()
    return platform if platform in {"qn", "jd", "pdd"} else "qn"


def login_start_url_for_platform(platform: object) -> str:
    normalized = normalize_platform(platform)
    if normalized == "jd":
        return JD_LOGIN_URL
    if normalized == "pdd":
        return PDD_LOGIN_URL
    return QN_LOGIN_URL


def is_jd_login_page(page_url: str) -> bool:
    return _host(page_url) == "passport.jd.com"


def is_jd_login_success_page(page_url: str) -> bool:
    return _host(page_url) == "kf.jd.com"


def is_jd_relevant_page(page_url: str) -> bool:
    return is_jd_login_page(page_url) or is_jd_login_success_page(page_url)


def _host(page_url: str) -> str:
    parsed = urlparse(str(page_url or "").strip())
    return parsed.netloc.lower()
