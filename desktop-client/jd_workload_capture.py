from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Mapping

import httpx

from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from secure_storage import unprotect_text
from spider_core import convert_metric_value, normalize_date_string, parse_json_text


JD_WORKLOAD_QUERY_URL = "https://kf.jd.com/waiterPerson/workload/queryList"
JD_WORKLOAD_REFERER = "https://xi.jd.com/customerassistant/filterCustomer.html?menu=waiterPerson&content=workload"
JD_WORKLOAD_ORIGIN = "https://xi.jd.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
JD_WORKLOAD_COOKIE_NAMES = {
    "3AB9D23F7A4B3C9B",
    "3AB9D23F7A4B3CSS",
    "DeviceSeq",
    "JSESSIONID",
    "TrackID",
    "__jda",
    "__jdb",
    "__jdc",
    "__jdu",
    "__jdv",
    "_pst",
    "_t",
    "_tp",
    "ceshi3.com",
    "csn",
    "cud",
    "cvt",
    "flash",
    "guid",
    "jr_ceshi",
    "light_key",
    "logining",
    "mp",
    "pin",
    "pinId",
    "sdtoken",
    "thor",
    "unick",
}


class JdWorkloadCaptureError(DirectApiCaptureError):
    pass


class JdWorkloadLoginRequiredError(DirectApiLoginRequiredError):
    pass


class JdWorkloadIdentityRequiredError(JdWorkloadCaptureError):
    pass


def capture_jd_workload(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    client: Any = None,
    today: date | None = None,
) -> Dict[str, Any]:
    cookie = _load_account_cookie(state)
    normalized_cookie = normalize_jd_cookie_header(cookie)
    service_pin = resolve_jd_service_pin(state)
    request_params = build_jd_workload_request_params(service_pin, today=today)
    log(f"京东工作量接口采集：servicePin={service_pin}，日期={request_params['startTime']}。")
    if normalized_cookie != cookie:
        log(
            "京东工作量 Cookie 已压缩："
            f"长度 {len(cookie)} -> {len(normalized_cookie)}，"
            f"数量 {_cookie_count(cookie)} -> {_cookie_count(normalized_cookie)}。"
        )
    response_data = fetch_jd_workload_data(normalized_cookie, request_params, client=client)
    payload = parse_jd_workload_payload(response_data, request_params=request_params, state=state)
    log(f"京东工作量采集成功：{payload.get('subAccount')} / {payload.get('recordDate')}。")
    return payload


def resolve_jd_service_pin(state: Mapping[str, Any]) -> str:
    for key in ("lastKnownLoginAccount", "loginHint"):
        value = str(state.get(key) or "").strip()
        if value:
            return value
    raise JdWorkloadIdentityRequiredError("京东客服账号识别名为空，请先登录或补充登录识别名。")


def build_jd_workload_request_params(service_pin: str, today: date | None = None) -> Dict[str, Any]:
    current_date = today or datetime.now().date()
    record_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "page": 1,
        "pageSize": 15,
        "startTime": record_date,
        "endTime": record_date,
        "transferType": 1,
        "type": 1,
        "servicePin": str(service_pin or "").strip(),
    }


def fetch_jd_workload_data(cookie: str, request_params: Mapping[str, Any], client: Any = None) -> Any:
    request_client = client or httpx
    headers = {
        "Cookie": cookie,
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
        "Origin": JD_WORKLOAD_ORIGIN,
        "Referer": JD_WORKLOAD_REFERER,
    }
    try:
        response = request_client.get(
            JD_WORKLOAD_QUERY_URL,
            params=dict(request_params),
            headers=headers,
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise JdWorkloadCaptureError(f"京东工作量接口请求失败：{exc}") from exc

    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code in {401, 403}:
        raise JdWorkloadLoginRequiredError("京东 Cookie 已过期或无权限，需要重新登录。")
    if status_code >= 400:
        raise JdWorkloadCaptureError(f"京东工作量接口 HTTP 错误：{status_code}。{_response_text_summary(response)}")

    try:
        return response.json()
    except Exception:
        parsed = parse_json_text(str(getattr(response, "text", "") or "").strip())
        if parsed is not None:
            return parsed
    raise JdWorkloadCaptureError("京东工作量接口响应不是可解析的 JSON。")


def normalize_jd_cookie_header(cookie: str) -> str:
    by_name: Dict[str, str] = {}
    order: list[str] = []
    for part in str(cookie or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if not sep or not name or name not in JD_WORKLOAD_COOKIE_NAMES:
            continue
        if name not in by_name:
            order.append(name)
        by_name[name] = value
    if "pin" not in by_name or "thor" not in by_name:
        raise JdWorkloadLoginRequiredError("京东账号 Cookie 缺少 pin 或 thor，需要重新登录。")
    return "; ".join(f"{name}={by_name[name]}" for name in order)


def parse_jd_workload_payload(
    raw_data: Any,
    request_params: Mapping[str, Any],
    state: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(raw_data, Mapping):
        raise JdWorkloadCaptureError(f"京东工作量接口响应根节点不是对象：{type(raw_data).__name__}")

    code = str(raw_data.get("code") or "").strip()
    if code != "success":
        message = str(raw_data.get("message") or raw_data.get("msg") or code or "未知错误")
        raise JdWorkloadCaptureError(f"京东工作量接口返回失败：{message}")

    rows = raw_data.get("workKpiList")
    if not isinstance(rows, list) or not rows:
        raise JdWorkloadCaptureError("京东工作量接口响应里没有 workKpiList 数据行。")
    row = rows[0]
    if not isinstance(row, Mapping):
        raise JdWorkloadCaptureError("京东工作量接口 workKpiList 第一行不是对象。")

    service_pin = str(request_params.get("servicePin") or state.get("lastKnownLoginAccount") or state.get("loginHint") or "").strip()
    login_account = _first_text(state.get("shopName"), state.get("lastKnownLoginAccount"), service_pin)
    record_date = normalize_date_string(row.get("dayStr")) or str(request_params.get("startTime") or "")
    sub_account = _first_text(row.get("waiter"), row.get("servicePin"), service_pin)
    payload = {
        "loginAccount": login_account,
        "recordDate": record_date,
        "subAccount": sub_account,
        "consultationCount": _metric("consultationCount", row.get("consultNum")),
        "receiveCount": _metric("receiveCount", _first_raw(row.get("servicedNum"), row.get("receiveNum"))),
        "validReceiveCount": None,
        "inquiryCount": None,
        "conversionRate": None,
        "firstReplyTime": _metric("firstReplyTime", row.get("responseAvgSpeed")),
        "avgReplyTime": _metric("avgReplyTime", row.get("responseAvgDurationWithLeave")),
        "wwReplyRate": _metric("wwReplyRate", row.get("responseRate")),
        "satisfaction": _metric("satisfaction", row.get("satisfiedRate")),
        "rawMetrics": {
            "source": "jd_workload",
            "requestUrl": JD_WORKLOAD_QUERY_URL,
            "requestParams": dict(request_params),
            "rowData": dict(row),
            "totalDetail": raw_data.get("totalDetail"),
            "AvgDetail": raw_data.get("AvgDetail"),
        },
    }
    return payload


def _load_account_cookie(state: Mapping[str, Any]) -> str:
    protected_cookie = str(state.get("cookieProtected") or "").strip()
    if not protected_cookie:
        raise JdWorkloadLoginRequiredError("京东账号未保存 Cookie，需要重新登录。")
    try:
        cookie = str(unprotect_text(protected_cookie) or "").strip()
    except Exception as exc:
        raise JdWorkloadLoginRequiredError(f"京东账号 Cookie 解密失败，需要重新登录：{exc}") from exc
    if not cookie:
        raise JdWorkloadLoginRequiredError("京东账号 Cookie 为空，需要重新登录。")
    return cookie


def _response_text_summary(response: Any) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    return f"响应摘要：{compact[:300]}"


def _cookie_count(cookie: str) -> int:
    count = 0
    for part in str(cookie or "").split(";"):
        if part.strip().partition("=")[1]:
            count += 1
    return count


def _metric(output_key: str, value: Any) -> Any:
    return convert_metric_value(output_key, value)


def _first_raw(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", "-", {}):
            return value
    return None


def _first_text(*values: Any) -> str:
    value = _first_raw(*values)
    return str(value or "").strip()
