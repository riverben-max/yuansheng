from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import time
from typing import Any, Callable, Dict, Mapping

from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from platform_config import PDD_CHAT_OVERVIEW_URL, is_pdd_login_page
from shadow_browser import ensure_shadow_browser
from spider_core import convert_metric_value


PDD_REPORT_PATH = "/chats/csReportDetail"
PDD_CAPTURE_RESULT_KEY = "__YS_PDD_CAPTURE_RESULT"
SHANGHAI_TZ = timezone(timedelta(hours=8))


class PddWorkloadCaptureError(DirectApiCaptureError):
    pass


class PddWorkloadLoginRequiredError(DirectApiLoginRequiredError):
    pass


def capture_pdd_workload(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    today: date | None = None,
    browser_factory: Callable[[Mapping[str, Any], Callable[[str], None]], Any] | None = None,
) -> Dict[str, Any]:
    request_params = build_pdd_report_request_params(today=today)
    session_factory = browser_factory or ensure_shadow_browser
    session = session_factory(state, log)
    page = session.page
    log(f"拼多多客服绩效采集：打开客服概览页，日期={request_params['recordDate']}。")
    page.get(PDD_CHAT_OVERVIEW_URL)
    time.sleep(1)
    if is_pdd_login_page(str(getattr(page, "url", "") or "")):
        raise PddWorkloadLoginRequiredError("拼多多页面跳转到登录页，需要重新登录。")

    raw_data = fetch_pdd_report_data_via_page(page, request_params)
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


def fetch_pdd_report_data_via_page(page: Any, request_params: Mapping[str, Any], timeout: float = 15.0) -> Any:
    endpoint = f"{PDD_REPORT_PATH}?starttime={int(request_params['starttime'])}&endtime={int(request_params['endtime'])}"
    page.run_js(_build_fetch_script(endpoint))
    deadline = time.time() + timeout
    last_raw = ""
    while time.time() < deadline:
        raw = page.run_js(f"JSON.stringify(window.{PDD_CAPTURE_RESULT_KEY} || null)")
        last_raw = str(raw or "")
        result = _parse_page_json(raw)
        if not isinstance(result, Mapping) or not result.get("done"):
            time.sleep(0.25)
            continue
        if result.get("ok") is True:
            return result.get("data")
        status = int(result.get("status") or 0)
        message = str(result.get("error") or result.get("text") or f"HTTP {status}" if status else "未知错误")
        if status in {401, 403} or "login" in message.lower() or "登录" in message:
            raise PddWorkloadLoginRequiredError(f"拼多多客服绩效接口需要重新登录：{message}")
        raise PddWorkloadCaptureError(f"拼多多客服绩效接口请求失败：{message}")
    raise PddWorkloadCaptureError(f"拼多多客服绩效接口等待超时：{last_raw[:300]}")


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
    row = rows[0]
    if not isinstance(row, Mapping):
        raise PddWorkloadCaptureError("拼多多客服绩效接口第一行不是对象。")

    record_date = str(request_params.get("recordDate") or "").strip()
    sub_account = _first_text(row.get("cs_name"), row.get("uid"))
    login_account = _first_text(state.get("shopName"), state.get("lastKnownLoginAccount"), "拼多多")
    raw_metrics = dict(row)
    raw_metrics.update(
        {
            "source": "pdd_cs_report_detail",
            "accountIdentity": sub_account,
            "requestUrl": f"https://mms.pinduoduo.com{PDD_REPORT_PATH}",
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


def _build_fetch_script(endpoint: str) -> str:
    endpoint_json = json.dumps(endpoint, ensure_ascii=False)
    return f"""
(() => {{
  window.{PDD_CAPTURE_RESULT_KEY} = {{ done: false }};
  fetch({endpoint_json}, {{ credentials: 'include' }})
    .then(async (response) => {{
      const text = await response.text();
      let data = null;
      try {{
        data = JSON.parse(text);
      }} catch (error) {{}}
      window.{PDD_CAPTURE_RESULT_KEY} = {{
        done: true,
        ok: response.ok,
        status: response.status,
        url: response.url,
        data,
        text: data ? '' : text.slice(0, 1000)
      }};
    }})
    .catch((error) => {{
      window.{PDD_CAPTURE_RESULT_KEY} = {{
        done: true,
        ok: false,
        error: String(error)
      }};
    }});
  return true;
}})()
"""


def _parse_page_json(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    text = str(raw or "").strip()
    if not text or text == "null":
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _metric(output_key: str, value: Any) -> Any:
    return convert_metric_value(output_key, value)


def _rate(value: Any) -> Any:
    metric = convert_metric_value("wwReplyRate", value)
    if metric is None:
        return None
    return round(metric * 100, 2) if abs(metric) <= 1 else metric


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
