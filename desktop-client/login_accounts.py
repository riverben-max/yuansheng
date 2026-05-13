from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping

from shadow_browser import DEFAULT_REMOTE_PORT, default_shadow_profile_dir
from spider_core import format_employee_summary, payload_signature
from direct_api_capture import DirectApiCaptureError
from jd_workload_capture import capture_jd_workload


LoginAccount = Dict[str, Any]
VALID_PLATFORMS = {"qn", "jd"}
DISPLAY_METRIC_KEYS = (
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


def ensure_login_accounts(state: MutableMapping[str, Any], data_dir: Path) -> List[LoginAccount]:
    raw_accounts = state.get("loginAccounts")
    if isinstance(raw_accounts, list) and raw_accounts:
        accounts = [_normalize_account(item, data_dir, index) for index, item in enumerate(raw_accounts)]
    else:
        accounts = [_legacy_account_from_state(state, data_dir)]
    state["loginAccounts"] = accounts
    return accounts


def add_login_account(
    state: MutableMapping[str, Any],
    data_dir: Path,
    display_name: str,
    login_hint: str = "",
    platform: str = "qn",
    shop_name: str = "",
) -> LoginAccount:
    accounts = ensure_login_accounts(state, data_dir)

    clean_name = str(display_name or "").strip() or f"账号{len(accounts) + 1}"
    clean_hint = str(login_hint or "").strip()
    slug = _profile_slug(clean_hint or clean_name)
    account = {
        "id": _next_account_id(accounts),
        "displayName": clean_name,
        "loginHint": clean_hint,
        "platform": _normalize_platform(platform),
        "shopName": str(shop_name or "").strip(),
        "enabled": True,
        "profileDir": str(data_dir / "profiles" / slug),
        "chromePort": 0,
        "loginStatus": "待登录",
        "lastCaptureAt": "",
        "lastResult": "",
        "lastError": "",
    }
    accounts.append(account)
    return account


def capture_enabled_accounts(
    state: MutableMapping[str, Any],
    accounts: Iterable[MutableMapping[str, Any]],
    reason: str,
    capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]],
    upload_func: Callable[[MutableMapping[str, Any], Mapping[str, Any], str, str], tuple[str, Mapping[str, Any] | None]],
    log: Callable[[str], None],
    jd_capture_func: Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    enabled_accounts = [account for account in accounts if bool(account.get("enabled", True))]
    for index, account in enumerate(enabled_accounts, start=1):
        display_name = str(account.get("displayName") or account.get("loginHint") or account.get("id") or "").strip()
        log(f"开始采集登录账户 {index}/{len(enabled_accounts)}：{display_name or '--'}。")
        platform = _normalize_platform(account.get("platform"))
        try:
            account_state = build_account_state(state, account)
            selected_capture_func = (jd_capture_func or capture_jd_workload) if platform == "jd" else capture_func
            payload = dict(selected_capture_func(account_state, log))
            signature = payload_signature(payload)
            upload_message, upload_record = upload_func(state, payload, signature, reason)
        except Exception as exc:
            status = "需要重新登录" if _looks_like_login_error(exc) else "采集失败"
            failure_reason = _failure_reason(exc)
            now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = str(exc)
            account["loginStatus"] = status
            account["lastCaptureAt"] = now_text
            account["lastError"] = message
            account["lastResult"] = message
            account["lastFailureReason"] = failure_reason
            account["lastFailureAt"] = now_text
            account.pop("lastCaptureSummary", None)
            results.append(
                {
                    "accountId": account.get("id"),
                    "displayName": display_name,
                    "ok": False,
                    "errorType": "login_required" if status == "需要重新登录" else "generic",
                    "message": message,
                    "loginStatus": status,
                    "lastCaptureAt": now_text,
                    "lastResult": message,
                    "lastError": message,
                    "lastFailureReason": failure_reason,
                    "lastFailureAt": account["lastFailureAt"],
                }
            )
            log(f"登录账户 {display_name or '--'} 采集失败：{message}")
            continue

        summary = format_employee_summary(payload)
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        upload_succeeded = _upload_succeeded(upload_message, upload_record)
        failure_reason = "" if upload_succeeded else _upload_failure_reason(upload_message)
        capture_summary = _build_capture_summary(
            display_name=display_name,
            payload=payload,
            captured_at=now_text,
            uploaded=upload_succeeded,
            upload_message=upload_message,
        )
        account["loginStatus"] = "采集成功"
        account["lastCaptureAt"] = now_text
        account["lastResult"] = summary
        account["lastError"] = ""
        account["lastFailureReason"] = failure_reason
        account["lastCaptureSummary"] = capture_summary
        account["lastKnownLoginAccount"] = _capture_identity_for_account(account, payload)
        if upload_record is not None:
            account["lastUploadAt"] = now_text

        results.append(
            {
                "accountId": account.get("id"),
                "displayName": display_name,
                "ok": True,
                "payload": payload,
                "signature": signature,
                "summary": summary,
                "uploadMessage": upload_message,
                "uploadRecord": upload_record,
                "lastCaptureSummary": capture_summary,
                "loginStatus": "采集成功",
                "lastCaptureAt": now_text,
                "lastResult": summary,
                "lastError": "",
                "lastFailureReason": failure_reason,
                "lastKnownLoginAccount": account["lastKnownLoginAccount"],
                "lastUploadAt": now_text if upload_record is not None else str(account.get("lastUploadAt") or ""),
            }
        )
        log(f"登录账户 {display_name or '--'} 采集成功：{summary}")
        if upload_message:
            log(upload_message)
    return results


def build_account_state(state: Mapping[str, Any], account: Mapping[str, Any]) -> Dict[str, Any]:
    account_state = deepcopy(dict(state))
    profile_dir = str(account.get("profileDir") or "").strip() or str(default_shadow_profile_dir())
    account_state["captureEngine"] = "direct_api"
    account_state["directApiPreferred"] = True
    account_state["accountCookieRequired"] = True
    account_state["platform"] = _normalize_platform(account.get("platform"))
    account_state["shopName"] = str(account.get("shopName") or "").strip()
    account_state["shadowChromeProfileDir"] = profile_dir
    account_state["chromeUserDataDir"] = profile_dir
    account_state["chromePort"] = _account_port(account)
    shadow_pid = _positive_int(account.get("shadowChromePid"))
    if shadow_pid:
        account_state["shadowChromePid"] = shadow_pid
    protected_cookie = str(account.get("cookieProtected") or "").strip()
    if protected_cookie:
        account_state["cookieProtected"] = protected_cookie
    active_port = _positive_int(account.get("activeChromePort"))
    if active_port:
        account_state["activeChromePort"] = active_port
    raw_login_hint = str(account.get("loginHint") or "").strip()
    if raw_login_hint:
        account_state["loginHint"] = raw_login_hint
    login_hint = str(account.get("lastKnownLoginAccount") or account.get("loginHint") or "").strip()
    if login_hint:
        account_state["lastKnownLoginAccount"] = login_hint
    return account_state


def _normalize_account(raw: Any, data_dir: Path, index: int) -> LoginAccount:
    account = dict(raw) if isinstance(raw, Mapping) else {}
    display_name = str(account.get("displayName") or account.get("loginHint") or f"账号{index + 1}").strip()
    login_hint = str(account.get("loginHint") or "").strip()
    profile_dir = str(account.get("profileDir") or "").strip()
    if not profile_dir:
        profile_dir = str(data_dir / "profiles" / _profile_slug(login_hint or display_name))
    account.update(
        {
            "id": str(account.get("id") or f"account-{index + 1}"),
            "displayName": display_name,
            "loginHint": login_hint,
            "platform": _normalize_platform(account.get("platform")),
            "shopName": str(account.get("shopName") or "").strip(),
            "enabled": bool(account.get("enabled", True)),
            "profileDir": profile_dir,
            "chromePort": _account_port(account),
            "loginStatus": str(account.get("loginStatus") or "待验证"),
            "lastCaptureAt": str(account.get("lastCaptureAt") or ""),
            "lastResult": str(account.get("lastResult") or ""),
            "lastError": str(account.get("lastError") or ""),
        }
    )
    active_port = _positive_int(account.get("activeChromePort"))
    if active_port:
        account["activeChromePort"] = active_port
    else:
        account.pop("activeChromePort", None)
    return account


def _legacy_account_from_state(state: Mapping[str, Any], data_dir: Path) -> LoginAccount:
    display_name = str(state.get("lastKnownLoginAccount") or "默认账号").strip()
    profile_dir = str(state.get("shadowChromeProfileDir") or state.get("chromeUserDataDir") or "").strip()
    if not profile_dir:
        profile_dir = str(data_dir / "profiles" / "default")
    return {
        "id": "default",
        "displayName": display_name,
        "loginHint": display_name if display_name != "默认账号" else "",
        "platform": "qn",
        "shopName": "",
        "enabled": True,
        "profileDir": profile_dir,
        "chromePort": 0,
        "loginStatus": "待验证",
        "lastCaptureAt": str(state.get("lastCaptureAt") or ""),
        "lastResult": str(state.get("lastPayloadSummary") or ""),
        "lastError": "",
    }


def _normalize_platform(raw: Any) -> str:
    platform = str(raw or "").strip().lower()
    return platform if platform in VALID_PLATFORMS else "qn"


def _profile_slug(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-").lower()
    if normalized:
        return normalized
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()[:8]
    return f"account-{digest}"


def _next_account_id(accounts: Iterable[Mapping[str, Any]]) -> str:
    existing = {str(item.get("id") or "") for item in accounts}
    index = len(existing) + 1
    candidate = f"account-{index}"
    while candidate in existing:
        index += 1
        candidate = f"account-{index}"
    return candidate


def _account_port(account: Mapping[str, Any]) -> int:
    try:
        raw = account.get("chromePort")
        if raw is None or str(raw).strip() == "":
            return 0
        return int(raw)
    except Exception:
        return 0


def _positive_int(raw: Any) -> int:
    try:
        value = int(raw)
    except Exception:
        return 0
    return value if value > 0 else 0


def _looks_like_login_error(exc: Exception) -> bool:
    if exc.__class__.__name__ == "JdWorkloadIdentityRequiredError":
        return False
    text = str(exc)
    return "登录" in text or exc.__class__.__name__ in {"LoginRequiredError", "DirectApiLoginRequiredError"}


def _failure_reason(exc: Exception) -> str:
    if exc.__class__.__name__ == "JdWorkloadIdentityRequiredError":
        return "采集失败"
    if _looks_like_login_error(exc):
        return "需要重新登录"
    if isinstance(exc, DirectApiCaptureError):
        return "接口失败"
    return "采集失败"


def _upload_succeeded(upload_message: str, upload_record: Mapping[str, Any] | None) -> bool:
    if upload_record is not None:
        return True
    message = str(upload_message or "")
    return "上传成功" in message or "已上传过" in message or "跳过重复上传" in message


def _upload_failure_reason(upload_message: str) -> str:
    message = str(upload_message or "")
    if "未找到员工账号映射" in message:
        return "平台未配置客服账号"
    return "上传失败"


def _capture_identity_for_account(account: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    platform = _normalize_platform(account.get("platform"))
    if platform == "jd":
        raw_metrics = payload.get("rawMetrics")
        request_params = raw_metrics.get("requestParams") if isinstance(raw_metrics, Mapping) else None
        service_pin = str(request_params.get("servicePin") or "").strip() if isinstance(request_params, Mapping) else ""
        for value in (
            service_pin,
            account.get("lastKnownLoginAccount"),
            account.get("loginHint"),
            payload.get("subAccount"),
        ):
            text = str(value or "").strip()
            if text:
                return text
        return ""
    return str(payload.get("loginAccount") or payload.get("subAccount") or "").strip()


def _build_capture_summary(
    display_name: str,
    payload: Mapping[str, Any],
    captured_at: str,
    uploaded: bool,
    upload_message: str,
) -> Dict[str, Any]:
    metrics = {key: payload.get(key) for key in DISPLAY_METRIC_KEYS if key in payload}
    return {
        "ok": True,
        "displayName": display_name,
        "loginAccount": payload.get("loginAccount") or "",
        "subAccount": payload.get("subAccount") or "",
        "recordDate": payload.get("recordDate") or "",
        "capturedAt": captured_at,
        "uploaded": uploaded,
        "uploadMessage": upload_message or "",
        "metrics": metrics,
    }
