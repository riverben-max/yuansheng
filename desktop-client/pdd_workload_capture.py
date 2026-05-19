from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, Mapping

import httpx

from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from platform_config import PDD_CHAT_OVERVIEW_URL
from secure_storage import unprotect_text
from spider_core import convert_metric_value, parse_json_text


PDD_REPORT_PATH = "/chats/csReportDetail"
PDD_REPORT_URL = f"https://mms.pinduoduo.com{PDD_REPORT_PATH}"
PDD_WORKLOAD_REFERER = PDD_CHAT_OVERVIEW_URL
PDD_WORKLOAD_ORIGIN = "https://mms.pinduoduo.com"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SHANGHAI_TZ = timezone(timedelta(hours=8))


class PddWorkloadCaptureError(DirectApiCaptureError):
    pass


class PddWorkloadLoginRequiredError(DirectApiLoginRequiredError):
    pass


def capture_pdd_workload(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    today: date | None = None,
    client: Any = None,
) -> Dict[str, Any]:
    cookie = _load_account_cookie(state)
    normalized_cookie = normalize_pdd_cookie_header(cookie)
    request_params = build_pdd_report_request_params(today=today)
    log(f"拼多多客服绩效接口采集：日期={request_params['recordDate']}。")
    if normalized_cookie != cookie:
        log(
            "拼多多客服绩效 Cookie 已规范化："
            f"长度 {len(cookie)} -> {len(normalized_cookie)}，"
            f"数量 {_cookie_count(cookie)} -> {_cookie_count(normalized_cookie)}。"
        )
    raw_data = fetch_pdd_report_data(normalized_cookie, request_params, client=client)
    payload = parse_pdd_workload_payload(raw_data, request_params=request_params, state=state)
    log(f"拼多多客服绩效采集成功：{payload.get('subAccount')} / {payload.get('recordDate')}。")
    return payload


def build_pdd_report_request_params(today: date | None = None) -> Dict[str, Any]:
    current_date = today or datetime.now(SHANGHAI_TZ).date()
    record_date = current_date - timedelta(days=1)
    record_start = datetime(record_date.year, record_date.month, record_date.day, tzinfo=SHANGHAI_TZ)
    record_timestamp = int(record_start.timestamp())
    return {
        "starttime": record_timestamp,
        "endtime": record_timestamp,
        "recordDate": record_date.strftime("%Y-%m-%d"),
    }


def fetch_pdd_report_data(cookie: str, request_params: Mapping[str, Any], client: Any = None) -> Any:
    request_client = client or httpx
    params = {
        "starttime": request_params.get("starttime"),
        "endtime": request_params.get("endtime"),
    }
    headers = {
        "Cookie": cookie,
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
        "Origin": PDD_WORKLOAD_ORIGIN,
        "Referer": PDD_WORKLOAD_REFERER,
    }
    try:
        response = request_client.get(
            PDD_REPORT_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise PddWorkloadCaptureError(f"拼多多客服绩效接口请求失败：{exc}") from exc

    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code in {401, 403}:
        raise PddWorkloadLoginRequiredError("拼多多 Cookie 已过期或无权限，需要重新登录。")
    if status_code >= 400:
        raise PddWorkloadCaptureError(f"拼多多客服绩效接口 HTTP 错误：{status_code}。{_response_text_summary(response)}")

    try:
        return response.json()
    except Exception:
        parsed = parse_json_text(str(getattr(response, "text", "") or "").strip())
        if parsed is not None:
            return parsed
    raise PddWorkloadCaptureError("拼多多客服绩效接口响应不是可解析的 JSON。")


def parse_pdd_workload_payload(raw_data: Any, request_params: Mapping[str, Any], state: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_data, Mapping):
        raise PddWorkloadCaptureError(f"拼多多客服绩效接口响应根节点不是对象：{type(raw_data).__name__}")
    if raw_data.get("success") is not True:
        message = str(raw_data.get("errorMsg") or raw_data.get("msg") or raw_data.get("message") or "未知错误")
        raise PddWorkloadCaptureError(f"拼多多客服绩效接口返回失败：{message}")
    result = raw_data.get("result")
    rows = result.get("data") if isinstance(result, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise PddWorkloadCaptureError("拼多多客服绩效接口响应里没有客服绩效数据。")
    row = _find_pdd_target_row(rows, state)
    if not isinstance(row, Mapping):
        raise PddWorkloadCaptureError("拼多多客服绩效接口匹配行不是对象。")

    record_date = str(request_params.get("recordDate") or "").strip()
    sub_account = _first_text(row.get("cs_name"), row.get("uid"))
    login_account = _first_text(state.get("shopName"), state.get("lastKnownLoginAccount"), "拼多多")
    raw_metrics = dict(row)
    raw_metrics.update(
        {
            "source": "pdd_cs_report_detail",
            "accountIdentity": sub_account,
            "requestUrl": PDD_REPORT_URL,
            "requestParams": {
                "starttime": request_params.get("starttime"),
                "endtime": request_params.get("endtime"),
            },
            "salesAmountYuan": _fen_to_yuan(row.get("cs_sales_amount")),
        }
    )
    return {
        "loginAccount": login_account,
        "recordDate": record_date,
        "subAccount": sub_account,
        "consultationCount": _metric("consultationCount", row.get("consult_user_cnt")),
        "receiveCount": _metric("receiveCount", row.get("receive_user_cnt")),
        "validReceiveCount": None,
        "inquiryCount": _metric("inquiryCount", row.get("inquiry_user")),
        "conversionRate": _rate(row.get("inquiry_group_rate")),
        "firstReplyTime": None,
        "avgReplyTime": _metric("avgReplyTime", row.get("avg_reply_time")),
        "wwReplyRate": _rate(row.get("reply_rate_3_min")),
        "satisfaction": None,
        "rawMetrics": raw_metrics,
    }


def _find_pdd_target_row(rows: list, state: Mapping[str, Any]) -> Mapping[str, Any]:
    if len(rows) == 1:
        return rows[0]
    target = str(state.get("lastKnownLoginAccount") or state.get("subAccount") or "").strip()
    if target:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            row_identity = _first_text(row.get("cs_name"), row.get("uid"))
            if row_identity and target in (row_identity, str(row.get("uid") or "")):
                return row
    return rows[0]


def normalize_pdd_cookie_header(cookie: str) -> str:
    parts: list[tuple[str, str]] = []
    names: set[str] = set()
    for part in str(cookie or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if not sep or not name:
            continue
        clean_name = name.strip()
        parts.append((clean_name, value.strip()))
        names.add(clean_name)
    missing: list[str] = []
    for required in ("PASS_ID", "JSESSIONID"):
        if required not in names:
            missing.append(required)
    if not any(name.startswith("mms_") for name in names):
        missing.append("mms_*")
    if not any(name.startswith("windows_app_shop_token_") for name in names):
        missing.append("windows_app_shop_token_*")
    if missing:
        raise PddWorkloadLoginRequiredError(f"拼多多账号 Cookie 缺少 {'、'.join(missing)}，需要重新登录。")
    return "; ".join(f"{name}={value}" for name, value in parts)


def _load_account_cookie(state: Mapping[str, Any]) -> str:
    protected_cookie = str(state.get("cookieProtected") or "").strip()
    if not protected_cookie:
        raise PddWorkloadLoginRequiredError("拼多多账号未保存 Cookie，需要重新登录。")
    try:
        cookie = str(unprotect_text(protected_cookie) or "").strip()
    except Exception as exc:
        raise PddWorkloadLoginRequiredError(f"拼多多账号 Cookie 解密失败，需要重新登录：{exc}") from exc
    if not cookie:
        raise PddWorkloadLoginRequiredError("拼多多账号 Cookie 为空，需要重新登录。")
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


def _rate(value: Any) -> Any:
    """将拼多多API返回的小数比率转换为统一百分比数值（0-100）。

    拼多多客服绩效接口返回的比率字段（inquiry_group_rate、reply_rate_3_min）
    为小数格式（如 0.95 表示 95%），统一乘以 100 转换为百分比数值。
    """
    metric = convert_metric_value("wwReplyRate", value)
    if metric is None:
        return None
    result = round(metric * 100, 2)
    if result > 100:
        return round(metric, 2)
    return result


def _fen_to_yuan(value: Any) -> Any:
    metric = convert_metric_value("salesAmount", value)
    if metric is None:
        return None
    return round(metric / 100, 2)


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
