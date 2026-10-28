from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence
from urllib.parse import unquote

import httpx

from secure_storage import SecureStorageError, protect_text, unprotect_text
from spider_core import (
    EMPLOYEE_TARGET_URL,
    convert_metric_value,
    extract_field_value,
    merge_capture_payloads,
    normalize_account_for_match,
    normalize_date_string,
    parse_json_text,
)

def _default_config_path() -> Path:
    import os
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "YuanshengDataAssistant" / "data" / "direct_api_capture.json"


DIRECT_API_CONFIG_PATH = _default_config_path()
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

FIELD_ALIASES = {
    "consultationCount": ["consultUserCnt", "consultationCount", "咨询人数"],
    "receiveCount": ["wwwRecUserCnt", "receiveCount", "接待人数"],
    "validReceiveCount": ["validReplyUv", "validReceiveCount", "有效接待人数"],
    "inquiryCount": ["wwwConsultUv", "inquiryCount", "询单人数", "延询单人数"],
    "conversionRate": ["consultFinalPayRate", "conversionRate", "询单转化率", "延询单转化率"],
    "firstReplyTime": ["firstReplyInterval", "firstReplyTime", "首次响应时长（秒）", "首次响应时长"],
    "avgReplyTime": ["avgReplyInterval", "avgReplyTime", "平均响应时长（秒）", "平均响应时长"],
    "wwReplyRate": ["wwUserReplayRate", "wwReplyRate", "旺旺回复率"],
    "satisfaction": ["customerAllSateRate", "satisfaction", "客户满意率"],
}

ACCOUNT_FIELD_ALIASES = (
    "accountNickWang",
    "accountNick",
    "subAccount",
    "sub_account",
    "nick",
    "nickName",
    "userName",
    "user_name",
    "客服",
    "客服账号",
    "旺旺账号",
    "子账号",
    "账号",
)


class DirectApiCaptureError(RuntimeError):
    pass


class DirectApiLoginRequiredError(DirectApiCaptureError):
    pass


PROTECTED_COOKIE_KEY = "cookieProtected"


def capture_with_direct_api(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    config_path: Path | None = None,
    client: Any = None,
) -> Dict[str, Any]:
    resolved_config_path = config_path or _resolve_config_path_from_state(state)
    if bool(state.get("accountCookieRequired")):
        account_cookie = _load_account_cookie(state)
        config = load_direct_api_config_with_cookie(resolved_config_path, account_cookie)
    else:
        config = load_direct_api_config(resolved_config_path)
    return capture_with_direct_api_config(config, state, log, client=client)


def capture_with_direct_api_config(
    config: Mapping[str, Any],
    state: Mapping[str, Any],
    log: Callable[[str], None],
    client: Any = None,
) -> Dict[str, Any]:
    request_configs = _collect_request_configs(config)
    payloads = []
    for index, request_config in enumerate(request_configs, start=1):
        log(f"接口直采第 {index} 组 Cookie 状态：{format_cookie_diagnostics(str(request_config.get('cookie') or ''))}")
        response_data = fetch_direct_api_data(request_config, client=client, log=log)
        payloads.append(parse_direct_api_payload(response_data, request_config, state))
        log(f"接口直采第 {index} 组数据解析完成。")
    payload = merge_capture_payloads(payloads)
    log(f"接口直采成功：{payload.get('subAccount')} / {payload.get('recordDate')}。")
    return payload


def _resolve_config_path_from_state(state: Mapping[str, Any]) -> Path:
    configured_path = str(state.get("directApiConfigPath") or "").strip()
    if configured_path:
        return Path(configured_path)
    return DIRECT_API_CONFIG_PATH


def load_direct_api_config(config_path: Path = DIRECT_API_CONFIG_PATH) -> Dict[str, Any]:
    loaded = _read_direct_api_config(config_path)

    if not loaded.get("enabled"):
        raise DirectApiCaptureError("接口直采未启用：direct_api_capture.json enabled=false。")

    _materialize_protected_cookies(loaded)
    return normalize_direct_api_config(loaded)


def load_direct_api_config_with_cookie(config_path: Path, cookie: str) -> Dict[str, Any]:
    loaded = _read_direct_api_config(config_path)
    if not loaded.get("enabled"):
        raise DirectApiCaptureError("接口直采未启用：direct_api_capture.json enabled=false。")
    _inject_cookie_override(loaded, cookie)
    return normalize_direct_api_config(loaded)


def normalize_direct_api_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    loaded = deepcopy(dict(config))

    requests = loaded.get("requests")
    if isinstance(requests, list) and requests:
        inherited = {key: value for key, value in loaded.items() if key != "requests"}
        loaded["requests"] = [_normalize_request_config(item, inherited) for item in requests if isinstance(item, dict)]
        if not loaded["requests"]:
            raise DirectApiCaptureError("接口直采配置 requests 至少要包含一个请求对象。")
        return loaded

    loaded.update(_normalize_request_config(loaded, {}))
    return loaded


def _read_direct_api_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise DirectApiCaptureError(f"未找到接口直采配置文件：{config_path}")

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DirectApiCaptureError(f"接口直采配置不是合法 JSON：{exc}") from exc
    except OSError as exc:
        raise DirectApiCaptureError(f"无法读取接口直采配置文件：{exc}") from exc

    if not isinstance(loaded, dict):
        raise DirectApiCaptureError("接口直采配置根节点必须是 JSON 对象。")
    return loaded


def update_direct_api_cookie(config_path: Path, cookie: str) -> Dict[str, Any]:
    clean_cookie = str(cookie or "").strip()
    if not clean_cookie:
        raise DirectApiCaptureError("未读取到影子浏览器 Cookie，无法刷新接口直采配置。")
    if not config_path.exists():
        raise DirectApiCaptureError(f"未找到接口直采配置文件：{config_path}")

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DirectApiCaptureError(f"接口直采配置不是合法 JSON：{exc}") from exc
    except OSError as exc:
        raise DirectApiCaptureError(f"无法读取接口直采配置文件：{exc}") from exc

    if not isinstance(loaded, dict):
        raise DirectApiCaptureError("接口直采配置根节点必须是 JSON 对象。")

    loaded[PROTECTED_COOKIE_KEY] = _protect_cookie(clean_cookie)
    loaded.pop("cookie", None)
    requests = loaded.get("requests")
    if isinstance(requests, list):
        for item in requests:
            if isinstance(item, dict):
                item.pop("cookie", None)
                item.pop(PROTECTED_COOKIE_KEY, None)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(loaded, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    except OSError as exc:
        raise DirectApiCaptureError(f"无法写入接口直采配置文件：{exc}") from exc
    return loaded


def migrate_direct_api_cookie_config(config_path: Path = DIRECT_API_CONFIG_PATH) -> bool:
    if not config_path.exists():
        return False

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DirectApiCaptureError(f"接口直采配置不是合法 JSON：{exc}") from exc
    except OSError as exc:
        raise DirectApiCaptureError(f"无法读取接口直采配置文件：{exc}") from exc

    if not isinstance(loaded, dict):
        raise DirectApiCaptureError("接口直采配置根节点必须是 JSON 对象。")

    plaintext_cookie = str(loaded.get("cookie") or "").strip()
    requests = loaded.get("requests")
    if not plaintext_cookie and isinstance(requests, list):
        for item in requests:
            if isinstance(item, dict):
                plaintext_cookie = str(item.get("cookie") or "").strip()
                if plaintext_cookie:
                    break

    if not plaintext_cookie:
        return False

    loaded[PROTECTED_COOKIE_KEY] = _protect_cookie(plaintext_cookie)
    loaded.pop("cookie", None)
    if isinstance(requests, list):
        for item in requests:
            if isinstance(item, dict):
                item.pop("cookie", None)
                item.pop(PROTECTED_COOKIE_KEY, None)

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(loaded, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    except OSError as exc:
        raise DirectApiCaptureError(f"无法写入接口直采配置文件：{exc}") from exc
    return True


def _protect_cookie(cookie: str) -> str:
    try:
        return protect_text(cookie)
    except SecureStorageError as exc:
        raise DirectApiCaptureError(f"Cookie 安全加密失败：{exc}") from exc


def _unprotect_cookie(protected_cookie: str) -> str:
    try:
        return unprotect_text(protected_cookie)
    except SecureStorageError as exc:
        raise DirectApiCaptureError(f"Cookie 安全解密失败：{exc}") from exc


def _materialize_protected_cookies(config: Dict[str, Any]) -> None:
    protected_cookie = str(config.get(PROTECTED_COOKIE_KEY) or "").strip()
    if protected_cookie:
        config["cookie"] = _unprotect_cookie(protected_cookie)

    requests = config.get("requests")
    if isinstance(requests, list):
        for item in requests:
            if not isinstance(item, dict):
                continue
            protected_item_cookie = str(item.get(PROTECTED_COOKIE_KEY) or "").strip()
            if protected_item_cookie:
                item["cookie"] = _unprotect_cookie(protected_item_cookie)


def _load_account_cookie(state: Mapping[str, Any]) -> str:
    protected_cookie = str(state.get(PROTECTED_COOKIE_KEY) or "").strip()
    if not protected_cookie:
        raise DirectApiLoginRequiredError("账号未保存 Cookie，需要重新登录。")
    cookie = _unprotect_cookie_for_login(protected_cookie)
    summary = summarize_cookie(cookie)
    has_user_marker = bool(
        summary.get("hasSn")
        or summary.get("hasUnb")
        or summary.get("hasTbToken")
        or summary.get("hasTracknick")
    )
    if not summary.get("hasMtopToken") or not has_user_marker or summary.get("mtopExpired") is True:
        raise DirectApiLoginRequiredError("账号 Cookie 已失效，需要重新登录。")
    return cookie


def _unprotect_cookie_for_login(protected_cookie: str) -> str:
    try:
        return unprotect_text(protected_cookie)
    except SecureStorageError as exc:
        raise DirectApiLoginRequiredError(f"账号 Cookie 解密失败，需要重新登录：{exc}") from exc


def _inject_cookie_override(config: Dict[str, Any], cookie: str) -> None:
    clean_cookie = str(cookie or "").strip()
    if not clean_cookie:
        raise DirectApiLoginRequiredError("账号 Cookie 为空，需要重新登录。")
    config["cookie"] = clean_cookie
    config.pop(PROTECTED_COOKIE_KEY, None)
    requests = config.get("requests")
    if isinstance(requests, list):
        for item in requests:
            if not isinstance(item, dict):
                continue
            item["cookie"] = clean_cookie
            item.pop(PROTECTED_COOKIE_KEY, None)


def summarize_cookie(cookie: str) -> Dict[str, Any]:
    cookie_text = str(cookie or "")
    names = set()
    mtop_token_value = ""
    for part in cookie_text.split(";"):
        name, sep, value = part.strip().partition("=")
        if not sep or not name:
            continue
        names.add(name)
        if name == "_m_h5_tk":
            mtop_token_value = unquote(value)

    expires_at = ""
    expired = None
    if "_" in mtop_token_value:
        expires_text = mtop_token_value.rsplit("_", 1)[1]
        try:
            expires_dt = datetime.fromtimestamp(int(expires_text) / 1000)
            expires_at = expires_dt.strftime("%Y-%m-%d %H:%M:%S")
            expired = expires_dt < datetime.now()
        except Exception:
            expires_at = "解析失败"

    return {
        "length": len(cookie_text),
        "hasMtopToken": bool(mtop_token_value),
        "mtopExpiresAt": expires_at,
        "mtopExpired": expired,
        "hasSn": "sn" in names,
        "hasUnb": "unb" in names,
        "hasTbToken": "_tb_token_" in names,
        "hasTracknick": "tracknick" in names,
    }


def format_cookie_diagnostics(cookie: str) -> str:
    summary = summarize_cookie(cookie)
    expired = summary.get("mtopExpired")
    if expired is None:
        expired_text = "未知"
    else:
        expired_text = "是" if expired else "否"
    return (
        f"长度={summary['length']}，"
        f"_m_h5_tk={'有' if summary['hasMtopToken'] else '无'}，"
        f"过期时间={summary['mtopExpiresAt'] or '--'}，"
        f"已过期={expired_text}，"
        f"sn={'有' if summary['hasSn'] else '无'}，"
        f"unb={'有' if summary['hasUnb'] else '无'}，"
        f"_tb_token_={'有' if summary['hasTbToken'] else '无'}，"
        f"tracknick={'有' if summary['hasTracknick'] else '无'}"
    )


def summarize_response_shape(raw_data: Any) -> str:
    if not isinstance(raw_data, Mapping):
        return f"类型={type(raw_data).__name__}"

    ret_text = _extract_ret_text(raw_data) or "--"
    root_keys = ",".join(str(key) for key in raw_data.keys()) or "--"
    rows = _get_nested(raw_data, ("data", "data", "data"))
    row_count = str(len(rows)) if isinstance(rows, list) else "未找到"
    return f"ret={ret_text}，根节点={root_keys}，data.data.data行数={row_count}"


def fetch_direct_api_data(config: Mapping[str, Any], client: Any = None, log: Callable[[str], None] | None = None) -> Any:
    method = str(config.get("method") or "GET").upper()
    raw_params = config.get("params") if isinstance(config.get("params"), dict) else {}
    params = _prepare_request_params(config, raw_params)
    body = config.get("body") if isinstance(config.get("body"), dict) else {}
    request_client = client or httpx

    headers = _build_headers(config)
    request_kwargs: Dict[str, Any] = {
        "headers": headers,
        "timeout": float(config.get("timeoutSeconds") or 10),
    }
    if method == "GET":
        request_kwargs["params"] = params
    else:
        if params and body:
            request_kwargs["params"] = params
            request_kwargs["json"] = body
        elif body:
            request_kwargs["json"] = body
        else:
            request_kwargs["json"] = params

    try:
        response = request_client.request(method, str(config.get("apiUrl")), **request_kwargs)
    except httpx.HTTPError as exc:
        raise DirectApiCaptureError(f"接口直采请求失败：{exc}") from exc

    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code in {401, 403}:
        raise DirectApiLoginRequiredError("接口直采 Cookie 已过期或无权限，请重新登录千牛。")
    if status_code >= 400:
        raise DirectApiCaptureError(f"接口直采 HTTP 错误：{status_code}。")

    text = str(getattr(response, "text", "") or "").strip()
    parsed = parse_json_text(text)
    if parsed is not None:
        _log_response_diagnostics(parsed, log)
        _raise_for_mtop_error(parsed)
        return parsed

    try:
        parsed_json = response.json()
    except Exception as exc:
        raise DirectApiCaptureError("接口直采响应不是可解析的 JSON/JSONP。") from exc
    _log_response_diagnostics(parsed_json, log)
    _raise_for_mtop_error(parsed_json)
    return parsed_json


def parse_direct_api_payload(raw_data: Any, config: Mapping[str, Any], state: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    _raise_for_mtop_error(raw_data)
    rows = _extract_rows(raw_data)
    if not rows:
        root_keys = ", ".join(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data).__name__
        raise DirectApiCaptureError(f"接口直采响应里没有找到客服数据行，根节点：{root_keys}")

    target_row = _find_target_row(rows, config, state or {})
    sub_account = _extract_row_account(target_row)
    if not sub_account:
        raise DirectApiCaptureError("接口直采响应中未识别到客服子账号字段。")

    login_account = _resolve_login_account(config, state or {}, sub_account)
    record_date = _resolve_record_date(target_row, config)
    payload = {
        "loginAccount": login_account,
        "recordDate": record_date,
        "subAccount": sub_account,
        "consultationCount": None,
        "receiveCount": None,
        "validReceiveCount": None,
        "inquiryCount": None,
        "conversionRate": None,
        "firstReplyTime": None,
        "avgReplyTime": None,
        "wwReplyRate": None,
        "satisfaction": None,
        "rawMetrics": {
            "source": "direct_api",
            "requestUrl": str(config.get("apiUrl") or ""),
            "method": str(config.get("method") or "GET").upper(),
            "rowData": target_row,
        },
    }

    for output_key, aliases in FIELD_ALIASES.items():
        raw_value = _first_row_value(target_row, aliases)
        if raw_value is not None:
            payload[output_key] = convert_metric_value(output_key, raw_value)

    return payload


def _raise_for_mtop_error(raw_data: Any) -> None:
    ret_text = _extract_ret_text(raw_data)
    if not ret_text:
        return
    if ret_text.startswith("SUCCESS::"):
        return
    if "TOKEN" in ret_text.upper() or "SESSION" in ret_text.upper() or "LOGIN" in ret_text.upper():
        raise DirectApiLoginRequiredError("接口直采 Cookie 已过期，请重新登录千牛。")
    raise DirectApiCaptureError(f"接口直采被淘宝拒绝：{ret_text}")


def _extract_ret_text(raw_data: Any) -> str:
    if not isinstance(raw_data, Mapping):
        return ""
    ret = raw_data.get("ret")
    if not isinstance(ret, list) or not ret:
        return ""
    return "；".join(str(item) for item in ret if item)


def _log_response_diagnostics(raw_data: Any, log: Callable[[str], None] | None) -> None:
    if log is None:
        return
    log(f"接口响应摘要：{summarize_response_shape(raw_data)}")


def _collect_request_configs(config: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    requests = config.get("requests")
    if isinstance(requests, list) and requests:
        return [item for item in requests if isinstance(item, Mapping)]
    return [config]


def _normalize_request_config(config: Mapping[str, Any], inherited: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(inherited)
    merged.update(config)
    method = str(merged.get("method") or "").strip().upper()
    api_url = str(merged.get("apiUrl") or "").strip()
    cookie = str(merged.get("cookie") or "").strip()
    params = merged.get("params") if isinstance(merged.get("params"), dict) else {}
    body = merged.get("body") if isinstance(merged.get("body"), dict) else {}

    if method not in {"GET", "POST"}:
        raise DirectApiCaptureError("接口直采配置 method 只能是 GET 或 POST。")
    if not api_url:
        raise DirectApiCaptureError("接口直采配置缺少 apiUrl。")
    if not cookie:
        raise DirectApiCaptureError("接口直采配置缺少 cookie。")
    if not params and not body:
        raise DirectApiCaptureError("接口直采配置 params 和 body 至少要填写一个。")

    merged["method"] = method
    merged["apiUrl"] = api_url
    merged["cookie"] = cookie
    merged["params"] = params
    merged["body"] = body
    return merged


def _build_headers(config: Mapping[str, Any]) -> Dict[str, str]:
    custom_headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}
    headers = {str(key): str(value) for key, value in custom_headers.items() if value is not None}
    headers["Cookie"] = str(config.get("cookie") or "")
    headers.setdefault("User-Agent", str(config.get("userAgent") or DEFAULT_USER_AGENT))
    headers.setdefault("Content-Type", str(config.get("contentType") or "application/json"))
    headers.setdefault("Referer", str(config.get("referer") or EMPLOYEE_TARGET_URL))
    return headers


def _prepare_request_params(config: Mapping[str, Any], params: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = dict(params)
    data_value = prepared.get("data")
    if not data_value:
        return prepared

    data_json = _parse_data_param(data_value)
    if data_json is not None and config.get("autoDateRange", True):
        record_date = _resolve_config_record_date(config)
        data_json["dateRange"] = f"{record_date}|{record_date}"
        ext_map = data_json.get("extMap")
        if isinstance(ext_map, str) and ext_map.strip().startswith("{"):
            try:
                ext_map_json = json.loads(ext_map)
            except Exception:
                ext_map_json = None
            if isinstance(ext_map_json, dict):
                ext_map_json["dateRange"] = f"{record_date}|{record_date}"
                data_json["extMap"] = json.dumps(ext_map_json, ensure_ascii=False, separators=(",", ":"))
        prepared["data"] = json.dumps(data_json, ensure_ascii=False, separators=(",", ":"))

    if config.get("autoMtopSign", True):
        app_key = str(prepared.get("appKey") or config.get("appKey") or "").strip()
        data_text = str(prepared.get("data") or "")
        if app_key and data_text:
            timestamp = str(int(time.time() * 1000))
            token = _extract_mtop_token(str(config.get("cookie") or ""))
            if not token:
                raise DirectApiCaptureError("接口直采 Cookie 中缺少 _m_h5_tk，无法自动生成 mtop sign。")
            prepared["t"] = timestamp
            prepared["sign"] = hashlib.md5(f"{token}&{timestamp}&{app_key}&{data_text}".encode("utf-8")).hexdigest()

    return prepared


def _parse_data_param(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        return None
    text = unquote(value.strip())
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _resolve_config_record_date(config: Mapping[str, Any]) -> str:
    configured = normalize_date_string(config.get("recordDate"))
    if configured:
        return configured
    offset_days = int(config.get("dateOffsetDays") if config.get("dateOffsetDays") is not None else -1)
    return (datetime.now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def _extract_mtop_token(cookie: str) -> str:
    for part in cookie.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name == "_m_h5_tk":
            return unquote(value).split("_", 1)[0]
    return ""


def _extract_rows(raw_data: Any) -> Sequence[Mapping[str, Any]]:
    if not isinstance(raw_data, dict):
        return []

    candidate_paths = (
        ("data", "data", "data"),
        ("data", "data", "list"),
        ("data", "data", "rows"),
        ("data", "resultList"),
        ("data", "list"),
        ("data", "rows"),
        ("resultList",),
        ("list",),
        ("rows",),
    )
    for path in candidate_paths:
        value = _get_nested(raw_data, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _get_nested(root: Mapping[str, Any], path: Iterable[str]) -> Any:
    value: Any = root
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _find_target_row(
    rows: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    state: Mapping[str, Any],
) -> Mapping[str, Any]:
    target_account = _resolve_target_account(config, state)
    if target_account:
        normalized_target = normalize_account_for_match(target_account)
        for row in rows:
            account = _extract_row_account(row)
            if account and normalize_account_for_match(account) == normalized_target:
                return row
        raise DirectApiCaptureError(f"接口直采响应中未找到当前客服行：{target_account}")

    if len(rows) == 1:
        return rows[0]

    raise DirectApiCaptureError("接口直采配置缺少 subAccount，且响应包含多行客服数据，无法确定当前员工。")


def _resolve_target_account(config: Mapping[str, Any], state: Mapping[str, Any]) -> str:
    for source in (
        config.get("subAccount"),
        state.get("subAccount"),
        state.get("currentAccount"),
        state.get("lastKnownLoginAccount"),
        config.get("loginAccount"),
    ):
        value = str(source or "").strip()
        if value:
            return value
    return ""


def _extract_row_account(row: Mapping[str, Any]) -> str:
    for alias in ACCOUNT_FIELD_ALIASES:
        value = extract_field_value(row, alias)
        if value not in (None, "", "-", {}):
            return str(value).strip()
    return ""


def _resolve_login_account(config: Mapping[str, Any], state: Mapping[str, Any], sub_account: str) -> str:
    for source in (
        config.get("loginAccount"),
        state.get("loginAccount"),
        state.get("lastKnownLoginAccount"),
        state.get("currentAccount"),
    ):
        value = str(source or "").strip()
        if value:
            return value
    return sub_account


def _resolve_record_date(row: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    for source in (
        extract_field_value(row, "statDate"),
        extract_field_value(row, "recordDate"),
        config.get("recordDate"),
        _first_mapping_value(config.get("body"), ("recordDate", "statDate", "endDate", "startDate")),
        _first_mapping_value(config.get("params"), ("recordDate", "statDate", "endDate", "startDate")),
    ):
        normalized = normalize_date_string(source)
        if normalized:
            return normalized
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def _first_mapping_value(source: Any, keys: Sequence[str]) -> Optional[Any]:
    if not isinstance(source, Mapping):
        return None
    for key in keys:
        value = source.get(key)
        if value:
            return value
    return None


def _first_row_value(row: Mapping[str, Any], aliases: Sequence[str]) -> Any:
    for alias in aliases:
        value = extract_field_value(row, alias)
        if value not in (None, "", "-", {}):
            return value
    return None
