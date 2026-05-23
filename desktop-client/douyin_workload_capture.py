from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, Mapping

import httpx

from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from error_sanitizer import sanitize_sensitive_text
from secure_storage import unprotect_text
from spider_core import convert_metric_value, parse_json_text


DOUYIN_STAFF_DATA_URL = "https://pigeon.jinritemai.com/backstage/queryStaffData"
DOUYIN_CURRENT_USER_URL = "https://pigeon.jinritemai.com/backstage/currentuser"
DOUYIN_REFERER = "https://im.jinritemai.com/pc_seller_v2/main/data/customerService/index"
DOUYIN_ORIGIN = "https://pigeon.jinritemai.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SHANGHAI_TZ = timezone(timedelta(hours=8))


class DouyinWorkloadCaptureError(DirectApiCaptureError):
    pass


class DouyinWorkloadLoginRequiredError(DirectApiLoginRequiredError):
    pass


def capture_douyin_workload(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    today: date | None = None,
    client: Any = None,
) -> Dict[str, Any]:
    cookie = _load_account_cookie(state)
    csrf_token = str(state.get("douyinCsrfToken") or "").strip()
    normalized_cookie = normalize_douyin_cookie_header(cookie)
    request_params = build_douyin_request_params(today=today)
    log(f"抖店客服绩效接口采集：日期={request_params['recordDate']}。")
    raw_data = fetch_douyin_workload_data(normalized_cookie, request_params, csrf_token=csrf_token, client=client)
    payload = parse_douyin_workload_payload(raw_data, request_params=request_params, state=state)
    log(f"抖店客服绩效采集成功：{payload.get('subAccount')} / {payload.get('recordDate')}。")
    return payload


def build_douyin_request_params(today: date | None = None) -> Dict[str, Any]:
    current_date = today or datetime.now(SHANGHAI_TZ).date()
    record_date = current_date - timedelta(days=1)
    date_str = record_date.strftime("%Y%m%d")
    return {
        "startTime": date_str,
        "endTime": date_str,
        "recordDate": record_date.strftime("%Y-%m-%d"),
    }


def fetch_douyin_workload_data(cookie: str, request_params: Mapping[str, Any], csrf_token: str = "", client: Any = None) -> Any:
    request_client = client or httpx
    params = {
        "_pms": "1",
        "page": "1",
        "size": "50",
        "queryType": "1",
        "startTime": request_params["startTime"],
        "endTime": request_params["endTime"],
    }
    headers = _build_headers(cookie, csrf_token=csrf_token)
    try:
        response = request_client.get(DOUYIN_STAFF_DATA_URL, params=params, headers=headers, timeout=15)
    except httpx.HTTPError as exc:
        raise DouyinWorkloadCaptureError(f"抖店客服绩效接口请求失败：{exc}") from exc

    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code in {401, 403}:
        raise DouyinWorkloadLoginRequiredError("抖店 Cookie 已过期或无权限，需要重新登录。")
    if status_code >= 400:
        raise DouyinWorkloadCaptureError(f"抖店客服绩效接口 HTTP 错误：{status_code}。{_response_text_summary(response)}")

    try:
        return response.json()
    except Exception:
        parsed = parse_json_text(str(getattr(response, "text", "") or "").strip())
        if parsed is not None:
            return parsed
    raise DouyinWorkloadCaptureError("抖店客服绩效接口响应不是可解析的 JSON。")


def fetch_douyin_current_user(cookie: str, csrf_token: str = "", client: Any = None) -> Dict[str, Any]:
    request_client = client or httpx
    params = {"biz_type": "4", "_pms": "1"}
    headers = _build_headers(cookie, csrf_token=csrf_token)
    try:
        response = request_client.get(DOUYIN_CURRENT_USER_URL, params=params, headers=headers, timeout=10)
    except httpx.HTTPError as exc:
        raise DouyinWorkloadCaptureError(f"抖店 currentuser 接口请求失败：{exc}") from exc
    try:
        data = response.json()
    except Exception:
        data = parse_json_text(str(getattr(response, "text", "") or "").strip())
    if not isinstance(data, Mapping) or data.get("code") != 0:
        raise DouyinWorkloadLoginRequiredError("抖店 Cookie 无效，currentuser 返回失败，需要重新登录。")
    return dict(data.get("data") or {})


def parse_douyin_workload_payload(raw_data: Any, *, request_params: Mapping[str, Any], state: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_data, Mapping):
        raise DouyinWorkloadCaptureError(f"抖店客服绩效接口响应根节点不是对象：{type(raw_data).__name__}")
    if raw_data.get("code") != 0:
        message = str(raw_data.get("msg") or raw_data.get("message") or "未知错误")
        raise DouyinWorkloadCaptureError(f"抖店客服绩效接口返回失败：{message}")

    data = raw_data.get("data")
    rows = data.get("staffDataModel") if isinstance(data, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise DouyinWorkloadCaptureError("抖店客服绩效接口响应里没有客服绩效数据。")

    row = _find_douyin_target_row(rows, state)
    record_date = str(request_params.get("recordDate") or "").strip()
    staff_info = row.get("staffUserInfo") or {}
    sub_account = _first_text(row.get("staffName"), staff_info.get("staffNickName"))
    login_account = _first_text(state.get("loginHint"), state.get("lastKnownLoginAccount"), sub_account, "抖店")

    raw_metrics = dict(row)
    raw_metrics["source"] = "douyin_query_staff_data"
    raw_metrics["shopName"] = str(state.get("shopName") or "").strip()
    raw_metrics["requestUrl"] = DOUYIN_STAFF_DATA_URL

    return {
        "loginAccount": login_account,
        "recordDate": record_date,
        "subAccount": sub_account,
        "consultationCount": _metric(row.get("inquiryCnt")),
        "receiveCount": _metric(row.get("servUserCnt")),
        "validReceiveCount": _metric(row.get("servConvCnt")),
        "inquiryCount": _metric(row.get("inquiryCnt")),
        "conversionRate": _parse_rate(row.get("inquiryOrderRate")),
        "firstReplyTime": _parse_duration(row.get("firstRespDuration")),
        "avgReplyTime": _parse_duration(row.get("avgRespDuration")),
        "salesAmount": _parse_amount(row.get("inquiryPayAmount")),
        "wwReplyRate": _parse_rate(row.get("threeMinRespRate")),
        "satisfaction": _parse_rate(row.get("satisfyRate")),
        "rawMetrics": raw_metrics,
    }


def _find_douyin_target_row(rows: list, state: Mapping[str, Any]) -> Mapping[str, Any]:
    if len(rows) == 1:
        return rows[0]
    targets = []
    for key in ("loginHint", "lastKnownLoginAccount", "subAccount"):
        target = str(state.get(key) or "").strip()
        if target and target not in targets:
            targets.append(target)
    for target in targets:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            staff_info = row.get("staffUserInfo") or {}
            identities = [
                str(v or "").strip()
                for v in (row.get("staffName"), staff_info.get("staffNickName"), staff_info.get("staffAccountName"))
                if str(v or "").strip()
            ]
            if target in identities:
                return row
    raise DouyinWorkloadCaptureError("抖店接口返回多个客服，但当前账号未匹配到目标客服，请补充登录识别名。")


def normalize_douyin_cookie_header(cookie: str) -> str:
    parts: list[tuple[str, str]] = []
    for part in str(cookie or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if not sep or not name:
            continue
        parts.append((name.strip(), value.strip()))
    if not parts:
        raise DouyinWorkloadLoginRequiredError("抖店账号 Cookie 为空，需要重新登录。")
    return "; ".join(f"{name}={value}" for name, value in parts)


def _load_account_cookie(state: Mapping[str, Any]) -> str:
    protected_cookie = str(state.get("cookieProtected") or "").strip()
    if not protected_cookie:
        raise DouyinWorkloadLoginRequiredError("抖店账号未保存 Cookie，需要重新登录。")
    try:
        cookie = str(unprotect_text(protected_cookie) or "").strip()
    except Exception as exc:
        raise DouyinWorkloadLoginRequiredError(f"抖店账号 Cookie 解密失败，需要重新登录：{exc}") from exc
    if not cookie:
        raise DouyinWorkloadLoginRequiredError("抖店账号 Cookie 为空，需要重新登录。")
    return cookie


def _build_headers(cookie: str, csrf_token: str = "") -> Dict[str, str]:
    headers = {
        "Cookie": cookie,
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": DOUYIN_REFERER,
        "Origin": DOUYIN_ORIGIN,
    }
    if csrf_token:
        headers["x-secsdk-csrf-token"] = csrf_token
    return headers


def _response_text_summary(response: Any) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if not text:
        return ""
    return f"响应摘要：{sanitize_sensitive_text(' '.join(text.split()))}"


def _metric(value: Any) -> Any:
    if value is None or value == "-":
        return None
    return convert_metric_value("receiveCount", value)


def _parse_rate(value: Any) -> Any:
    if value is None or value == "-":
        return None
    if isinstance(value, Mapping):
        value = value.get("fieldValue", value)
    if value == "-":
        return None
    text = str(value).strip().rstrip("%")
    try:
        return round(float(text), 2)
    except (ValueError, TypeError):
        return None


def _parse_duration(value: Any) -> Any:
    """解析抖店时长字段，支持纯数字（秒）和中文格式（如"10分0秒"、"0秒"、"1小时2分3秒"）。"""
    if value is None or value == "-":
        return None
    if isinstance(value, Mapping):
        value = value.get("fieldValue", value)
    if value is None or value == "-":
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    # 尝试中文格式解析
    import re
    hours = re.search(r"(\d+)\s*小时", text)
    minutes = re.search(r"(\d+)\s*分", text)
    seconds = re.search(r"(\d+)\s*秒", text)
    if hours or minutes or seconds:
        total = 0
        if hours:
            total += int(hours.group(1)) * 3600
        if minutes:
            total += int(minutes.group(1)) * 60
        if seconds:
            total += int(seconds.group(1))
        return total
    # 纯数字
    try:
        return round(float(text), 2)
    except (ValueError, TypeError):
        return None


def _parse_amount(value: Any) -> Any:
    if value is None or value == "-":
        return None
    text = str(value).strip().replace(",", "")
    try:
        return round(float(text), 2)
    except (ValueError, TypeError):
        return None


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
