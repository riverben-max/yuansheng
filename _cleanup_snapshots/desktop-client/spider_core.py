from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import parse_qs, unquote, urlparse

EMPLOYEE_TARGET_URL = "https://myseller.taobao.com/home.htm/op-sycm-svc/overview"
EMPLOYEE_TARGET_PATHS = {
    "/home.htm/op-sycm-svc/overview",
}
LOGIN_MARKERS = (
    "请输入登录密码",
    "账号名/邮箱/手机号",
    "忘记密码",
    "扫码登录",
    "登录千牛",
    "立即登录",
    "验证码",
)
FIELD_LABELS = {
    "loginAccount": "登录账号",
    "recordDate": "数据日期",
    "subAccount": "子账号",
    "consultationCount": "咨询人数",
    "receiveCount": "接待人数",
    "validReceiveCount": "有效接待人数",
    "inquiryCount": "询单人数",
    "conversionRate": "询单转化率",
    "firstReplyTime": "首次响应时长",
    "avgReplyTime": "平均响应时长",
    "wwReplyRate": "旺旺回复率",
    "satisfaction": "客户满意率",
}
REQUEST_KEY_TO_OUTPUT = {
    "consultUserCnt": "consultationCount",
    "wwwRecUserCnt": "receiveCount",
    "validReplyUv": "validReceiveCount",
    "wwwConsultUv": "inquiryCount",
    "consultFinalPayRate": "conversionRate",
    "firstReplyInterval": "firstReplyTime",
    "avgReplyInterval": "avgReplyTime",
    "wwUserReplayRate": "wwReplyRate",
    "customerAllSateRate": "satisfaction",
}
METRIC_ROUNDS = [
    {
        "name": "第一轮",
        "labels": ["咨询人数", "接待人数", "有效接待人数", "询单人数", "询单转化率"],
        "requestKeys": ["consultUserCnt", "wwwRecUserCnt", "validReplyUv", "wwwConsultUv", "consultFinalPayRate"],
    },
    {
        "name": "第二轮",
        "labels": ["首次响应时长（秒）", "平均响应时长（秒）", "旺旺回复率", "客户满意率"],
        "requestKeys": ["firstReplyInterval", "avgReplyInterval", "wwUserReplayRate", "customerAllSateRate"],
    },
]


@dataclass
class PageSnapshot:
    title: str
    url: str
    text: str


def snapshot_requires_login(snapshot: PageSnapshot) -> bool:
    parsed = urlparse(snapshot.url or "")
    host = parsed.netloc.lower()
    if host in {"loginmyseller.taobao.com", "login.taobao.com"}:
        return True
    if host != "myseller.taobao.com":
        return True
    text = f"{snapshot.title}\n{snapshot.text}"
    return any(marker in text for marker in LOGIN_MARKERS)


def clean_lines(raw_text: str) -> List[str]:
    return [line.strip() for line in raw_text.splitlines() if line and line.strip()]


def extract_capture_payload(snapshot: PageSnapshot, expected_request_keys: Iterable[str]) -> Dict[str, Any]:
    lines = clean_lines(snapshot.text)
    if len(lines) < 10:
        raise ValueError("页面内容尚未稳定加载，稍后会自动重试。")

    current_nick = extract_current_nick_marker(snapshot.text)
    current_account = infer_current_account(lines, current_nick)
    login_account = normalize_login_account(current_nick, current_account)

    round_payload = extract_round_payload(snapshot, current_account, expected_request_keys)
    if round_payload is None:
        raise ValueError(f"未截获当前轮可用接口响应，账号 {current_account} 本轮没有拿到目标指标。")

    payload = {
        "loginAccount": login_account,
        "recordDate": round_payload.get("recordDate") or infer_record_date(snapshot),
        "subAccount": current_account,
        "consultationCount": None,
        "receiveCount": None,
        "validReceiveCount": None,
        "inquiryCount": None,
        "conversionRate": None,
        "firstReplyTime": None,
        "avgReplyTime": None,
        "wwReplyRate": None,
        "satisfaction": None,
        "rawMetrics": round_payload.get("rawMetrics", {}),
    }
    payload.update(round_payload.get("metrics", {}))
    return payload


def extract_round_payload(
    snapshot: PageSnapshot,
    current_account: str,
    expected_request_keys: Iterable[str],
) -> Optional[Dict[str, Any]]:
    expected_keys = list(expected_request_keys)
    logs = extract_network_logs(snapshot.text)
    best_candidate: Optional[Dict[str, Any]] = None
    best_overlap = -1

    for item in logs:
        meta = parse_request_meta(item.get("url") or "")
        if not meta.get("isTarget"):
            continue
        overlap = len(set(meta.get("indexCodes", [])) & set(expected_keys))
        if overlap <= 0:
            continue

        payload = parse_json_text(item.get("body"))
        if payload is None:
            continue

        row = extract_account_row(payload, current_account)
        if row is None:
            continue

        metrics: Dict[str, Any] = {}
        for request_key in expected_keys:
            output_key = REQUEST_KEY_TO_OUTPUT[request_key]
            metrics[output_key] = convert_metric_value(output_key, extract_field_value(row, request_key))

        candidate = {
            "recordDate": normalize_date_string(extract_field_value(row, "statDate")) or infer_record_date(snapshot),
            "metrics": metrics,
            "rawMetrics": {
                "source": "network",
                "url": item.get("url"),
                "requestKeys": meta.get("indexCodes", []),
                "rowData": row,
            },
        }
        if overlap > best_overlap:
            best_overlap = overlap
            best_candidate = candidate

    return best_candidate


def extract_account_row(payload: Any, current_account: str) -> Optional[Mapping[str, Any]]:
    rows = []
    if isinstance(payload, dict):
        rows = (
            payload.get("data", {})
            .get("data", {})
            .get("data", [])
        )
    if not isinstance(rows, list):
        return None

    for row in rows:
        if not isinstance(row, dict):
            continue
        account = extract_field_value(row, "accountNickWang")
        if isinstance(account, str) and normalize_account_for_match(account) == normalize_account_for_match(current_account):
            return row
    return None


def extract_field_value(row: Mapping[str, Any], key: str) -> Any:
    value = row.get(key)
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def convert_metric_value(output_key: str, value: Any) -> Any:
    if value in (None, "", "-", {}):
        return None
    if output_key in {"consultationCount", "receiveCount", "validReceiveCount", "inquiryCount"}:
        parsed = extract_number(value)
        return int(parsed) if parsed is not None else None
    parsed = extract_number(value)
    return round(parsed, 2) if parsed is not None else None


def extract_current_nick_marker(text: str) -> str:
    match = re.search(r"__YS_CURRENT_NICK__\s*(.*?)\s*__YS_CURRENT_NICK_END__", text, re.S)
    return match.group(1).strip() if match else ""


def infer_current_account(lines: Iterable[str], current_nick: str) -> str:
    if current_nick:
        nick = re.split(r"[:：]", current_nick, maxsplit=1)[-1].strip()
        if nick:
            return nick

    for line in list(lines)[:80]:
        if "客服主管" in line or "客服专员" in line or "客服" in line:
            tokens = re.split(r"[\s|/]+", line)
            for token in tokens:
                token = token.strip()
                if is_reasonable_account_name(token):
                    return token

    raise ValueError("未识别到当前登录员工账号，请确认千牛页面右上角显示了当前客服账号。")


def normalize_login_account(current_nick: str, current_account: str) -> str:
    return current_nick.strip() or current_account


def normalize_account_for_match(account: Any) -> str:
    text = str(account or "").strip()
    if not text:
        return ""
    text = re.split(r"[:：]", text, maxsplit=1)[-1].strip()
    return re.sub(r"\s+", "", text)


def is_reasonable_account_name(candidate: str) -> bool:
    if not candidate:
        return False
    if len(candidate) < 2 or len(candidate) > 20:
        return False
    if re.search(r"(有限公司|专业客服外包|商家一站式经营阵地|千牛|绩效考核|客服总览)", candidate):
        return False
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z0-9_-]{2,}", candidate))


def infer_record_date(snapshot: PageSnapshot) -> str:
    current_nick = extract_current_nick_marker(snapshot.text)
    for source in [snapshot.text, snapshot.title, snapshot.url, current_nick]:
        if not source:
            continue
        matches = re.findall(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})", source)
        if matches:
            year, month, day = matches[0]
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def extract_network_logs(page_text: str) -> List[Dict[str, Any]]:
    match = re.search(r"__YS_NETWORK_LOGS_START__\s*(.*?)\s*__YS_NETWORK_LOGS_END__", page_text, re.S)
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def parse_request_meta(url: str) -> Dict[str, Any]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    raw_data = query.get("data", [""])[0]
    decoded_data = unquote(raw_data) if raw_data else ""
    data_json: Dict[str, Any] = {}
    if decoded_data:
        try:
            data_json = json.loads(decoded_data)
        except Exception:
            data_json = {}
    domain_code = data_json.get("domainCode")
    index_codes = [item.strip() for item in str(data_json.get("indexCodes") or "").split(",") if item.strip()]
    return {
        "isTarget": "mtop.alibaba.sycm.domain.onequery" in url and domain_code == "tao.shop.qos.subaccount",
        "domainCode": domain_code,
        "indexCodes": index_codes,
        "decodedData": data_json,
        "url": url,
    }


def parse_json_text(text: Any) -> Optional[Any]:
    if not isinstance(text, str) or not text.strip():
        return None
    body = text.strip()
    if body.startswith("{") or body.startswith("["):
        try:
            return json.loads(body)
        except Exception:
            return None
    jsonp_match = re.match(r"^[^(]+\((.*)\)\s*;?\s*$", body, re.S)
    if jsonp_match:
        try:
            return json.loads(jsonp_match.group(1))
        except Exception:
            return None
    return None


def normalize_date_string(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    match = re.search(r"(20\d{2})[-/年 ]?(\d{1,2})[-/月 ]?(\d{1,2})", text)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def extract_number(value: Any) -> Optional[float]:
    if value in (None, "", "-", {}):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    for suffix in ("时", "秒", "元"):
        text = text.replace(suffix, "")
    if text.endswith("%"):
        text = text[:-1]
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def merge_capture_payloads(payloads: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    payload_list = list(payloads)
    _validate_payload_identity(payload_list)
    merged = {
        "loginAccount": None,
        "recordDate": None,
        "subAccount": None,
        "consultationCount": None,
        "receiveCount": None,
        "validReceiveCount": None,
        "inquiryCount": None,
        "conversionRate": None,
        "firstReplyTime": None,
        "avgReplyTime": None,
        "wwReplyRate": None,
        "satisfaction": None,
        "rawMetrics": {"rounds": []},
    }
    for payload in payload_list:
        for key in ("loginAccount", "recordDate", "subAccount"):
            if merged[key] is None and payload.get(key):
                merged[key] = payload.get(key)
        for key in (
            "consultationCount",
            "receiveCount",
            "validReceiveCount",
            "inquiryCount",
            "conversionRate",
            "firstReplyTime",
            "avgReplyTime",
            "wwReplyRate",
            "satisfaction",
        ):
            if payload.get(key) is not None:
                merged[key] = payload.get(key)
        raw = payload.get("rawMetrics")
        if raw:
            merged["rawMetrics"]["rounds"].append(raw)
    return merged


def _validate_payload_identity(payloads: Iterable[Mapping[str, Any]]) -> None:
    expected: Dict[str, Any] = {}
    for payload in payloads:
        for key in ("loginAccount", "recordDate", "subAccount"):
            value = payload.get(key)
            if value in (None, ""):
                continue
            if key not in expected:
                expected[key] = value
                continue
            if str(expected[key]) != str(value):
                raise ValueError(f"多轮采集数据 {key} 不一致：{expected[key]} != {value}")


def payload_signature(payload: Mapping[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def format_employee_summary(payload: Mapping[str, Any]) -> str:
    ordered_keys = (
        "consultationCount",
        "receiveCount",
        "validReceiveCount",
        "inquiryCount",
        "conversionRate",
        "firstReplyTime",
        "avgReplyTime",
        "wwReplyRate",
        "satisfaction",
    )
    metric_parts = []
    for key in ordered_keys:
        value = payload.get(key)
        if value is None:
            continue
        suffix = "%" if key in {"conversionRate", "wwReplyRate", "satisfaction"} else ""
        metric_parts.append(f"{FIELD_LABELS[key]}={value}{suffix}")
    joined = "，".join(metric_parts) if metric_parts else "当前未拿到员工绩效指标"
    return f"登录账号={payload.get('loginAccount')}，数据日期={payload.get('recordDate')}，子账号={payload.get('subAccount')}，{joined}"


def summarize_network_logs(snapshot: PageSnapshot, expected_request_keys: Optional[Iterable[str]] = None) -> str:
    logs = extract_network_logs(snapshot.text)
    relevant: List[str] = []
    expected = set(expected_request_keys or [])
    for item in logs:
        meta = parse_request_meta(item.get("url") or "")
        if not meta.get("isTarget"):
            continue
        keys = meta.get("indexCodes", [])
        if expected and not (set(keys) & expected):
            continue
        relevant.append(f"{item.get('url')} [indexCodes={','.join(keys)}]")
    if not relevant:
        return "当前轮尚未截获目标员工绩效接口响应。"
    visible = relevant[:4]
    suffix = "" if len(relevant) <= 4 else f" 等共 {len(relevant)} 条"
    return f"当前轮已截获 {len(relevant)} 条目标响应：{' | '.join(visible)}{suffix}"
