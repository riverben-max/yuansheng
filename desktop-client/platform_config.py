from __future__ import annotations

from urllib.parse import urlparse

QN_LOGIN_URL = "https://loginmyseller.taobao.com/"
JD_LOGIN_URL = "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F"
JD_SERVICE_URL = "https://kf.jd.com/"
JD_DATA_URL = "https://kf.jd.com/#/43"
PDD_LOGIN_URL = "https://mms.pinduoduo.com/login/?redirectUrl=https%3A%2F%2Fmms.pinduoduo.com%2Fmms-chat%2Foverview%2Fmerchant"
PDD_HOME_URL = "https://mms.pinduoduo.com/home/"
PDD_CHAT_OVERVIEW_URL = "https://mms.pinduoduo.com/mms-chat/overview/merchant"
DOUYIN_LOGIN_URL = "https://fxg.jinritemai.com/login/common"
DOUYIN_SERVICE_URL = "https://im.jinritemai.com/pc_seller_v2/main/data/customerService/index"


def normalize_platform(raw: object) -> str:
    platform = str(raw or "").strip().lower()
    return platform if platform in {"qn", "jd", "pdd", "douyin"} else "qn"


def login_start_url_for_platform(platform: object) -> str:
    normalized = normalize_platform(platform)
    if normalized == "jd":
        return JD_LOGIN_URL
    if normalized == "pdd":
        return PDD_LOGIN_URL
    if normalized == "douyin":
        return DOUYIN_LOGIN_URL
    return QN_LOGIN_URL


def is_jd_login_page(page_url: str) -> bool:
    return _host(page_url) == "passport.jd.com"


def is_jd_login_success_page(page_url: str) -> bool:
    return _host(page_url) == "kf.jd.com"


def is_jd_relevant_page(page_url: str) -> bool:
    return is_jd_login_page(page_url) or is_jd_login_success_page(page_url)


def is_pdd_login_page(page_url: str) -> bool:
    return _host(page_url) == "mms.pinduoduo.com" and _path(page_url).startswith("/login/")


def is_pdd_login_success_page(page_url: str) -> bool:
    return _host(page_url) == "mms.pinduoduo.com" and _normalized_path(page_url) in {
        "/home",
        "/mms-chat/overview/merchant",
    }


def is_pdd_relevant_page(page_url: str) -> bool:
    return is_pdd_login_page(page_url) or is_pdd_login_success_page(page_url)


def _host(page_url: str) -> str:
    parsed = urlparse(str(page_url or "").strip())
    return parsed.netloc.lower()


def _path(page_url: str) -> str:
    parsed = urlparse(str(page_url or "").strip())
    return parsed.path or "/"


def _normalized_path(page_url: str) -> str:
    path = _path(page_url).rstrip("/")
    return path or "/"



def is_douyin_login_page(page_url: str) -> bool:
    return _host(page_url) == "fxg.jinritemai.com" and "/login" in _path(page_url)


def is_douyin_login_success_page(page_url: str) -> bool:
    return _host(page_url) in {"fxg.jinritemai.com", "im.jinritemai.com"} and "/login" not in _path(page_url)


def is_douyin_relevant_page(page_url: str) -> bool:
    return is_douyin_login_page(page_url) or is_douyin_login_success_page(page_url)
