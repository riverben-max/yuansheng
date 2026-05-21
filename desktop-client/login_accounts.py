from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping

from shadow_browser import DEFAULT_REMOTE_PORT, default_shadow_profile_dir
from spider_core import format_employee_summary, payload_signature, positive_int
from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from platform_adapters import CaptureAdapter, select_capture_adapter
from platform_config import normalize_platform


LoginAccount = Dict[str, Any]
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
    _ensure_unique_profile_dirs(accounts, data_dir)
    state["loginAccounts"] = accounts
    return accounts


def add_login_account(
    state: MutableMapping[str, Any],
    data_dir: Path,
    display_name: str,
    login_hint: str = "",
    platform: str = "qn",
    shop_name: str = "",
    shop_id: int = 0,
) -> LoginAccount:
    accounts = ensure_login_accounts(state, data_dir)

    clean_name = str(display_name or "").strip() or f"账号{len(accounts) + 1}"
    clean_hint = str(login_hint or "").strip()
    slug = _profile_slug(clean_hint or clean_name)
    profile_dir = _unique_profile_dir(data_dir, slug, _used_profile_paths(accounts))
    account = {
        "id": _next_account_id(accounts),
        "displayName": clean_name,
        "loginHint": clean_hint,
        "platform": normalize_platform(platform),
        "shopName": str(shop_name or "").strip(),
        "shopId": int(shop_id) if shop_id else 0,
        "enabled": True,
        "profileDir": str(profile_dir),
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
    capture_adapters: Mapping[str, CaptureAdapter] | None = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    adapters = capture_adapters or {"qn": capture_func}
    enabled_accounts = [account for account in accounts if bool(account.get("enabled", True))]
    for index, account in enumerate(enabled_accounts, start=1):
        display_name = str(account.get("displayName") or account.get("loginHint") or account.get("id") or "").strip()
        log(f"开始采集登录账户 {index}/{len(enabled_accounts)}：{display_name or '--'}。")
        platform = normalize_platform(account.get("platform"))
        try:
            account_state = build_account_state(state, account)
            selected_capture_func = select_capture_adapter(platform, adapters)
            payload = dict(selected_capture_func(account_state, log))
            payload["platform"] = platform
            payload["shopId"] = int(account.get("shopId") or 0)
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
                    "errorType": _error_type(exc, status),
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
        upload_succeeded = upload_record is not None
        failure_reason = "" if upload_succeeded else _upload_failure_reason(upload_message)
        login_status = "采集成功+已上传" if upload_succeeded else "采集成功+上传失败"
        capture_summary = _build_capture_summary(
            display_name=display_name,
            payload=payload,
            captured_at=now_text,
            uploaded=upload_succeeded,
            upload_message=upload_message,
        )
        account["loginStatus"] = login_status
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
                "loginStatus": login_status,
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
    account_state["platform"] = normalize_platform(account.get("platform"))
    account_state["shopName"] = str(account.get("shopName") or "").strip()
    account_state["shopId"] = int(account.get("shopId") or 0)
    account_state["shadowChromeProfileDir"] = profile_dir
    account_state["chromeUserDataDir"] = profile_dir
    account_state["chromePort"] = _account_port(account)
    shadow_pid = positive_int(account.get("shadowChromePid"))
    if shadow_pid:
        account_state["shadowChromePid"] = shadow_pid
    protected_cookie = str(account.get("cookieProtected") or "").strip()
    if protected_cookie:
        account_state["cookieProtected"] = protected_cookie
    active_port = positive_int(account.get("activeChromePort"))
    if active_port:
        account_state["activeChromePort"] = active_port
    raw_login_hint = str(account.get("loginHint") or "").strip()
    if raw_login_hint:
        account_state["loginHint"] = raw_login_hint
    login_hint = str(account.get("lastKnownLoginAccount") or account.get("loginHint") or "").strip()
    if login_hint:
        account_state["lastKnownLoginAccount"] = login_hint
    douyin_csrf = str(account.get("douyinCsrfToken") or "").strip()
    if douyin_csrf:
        account_state["douyinCsrfToken"] = douyin_csrf
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
            "platform": normalize_platform(account.get("platform")),
            "shopName": str(account.get("shopName") or "").strip(),
            "shopId": int(account.get("shopId") or 0),
            "enabled": bool(account.get("enabled", True)),
            "profileDir": profile_dir,
            "chromePort": _account_port(account),
            "loginStatus": str(account.get("loginStatus") or "待验证"),
            "lastCaptureAt": str(account.get("lastCaptureAt") or ""),
            "lastResult": str(account.get("lastResult") or ""),
            "lastError": str(account.get("lastError") or ""),
        }
    )
    active_port = positive_int(account.get("activeChromePort"))
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


def _ensure_unique_profile_dirs(accounts: List[LoginAccount], data_dir: Path) -> None:
    used: set[str] = set()
    for account in accounts:
        profile_dir = str(account.get("profileDir") or "").strip()
        normalized = _normalize_profile_path(profile_dir)
        if normalized and normalized not in used:
            used.add(normalized)
            continue

        base_slug = _profile_slug(Path(profile_dir).name if profile_dir else "")
        if not base_slug:
            base_slug = _profile_slug(
                str(account.get("displayName") or account.get("loginHint") or account.get("id") or "account")
            )
        replacement = _unique_profile_dir(data_dir, base_slug, used)
        account["profileDir"] = str(replacement)
        _clear_login_state_for_profile_change(account)
        used.add(_normalize_profile_path(str(replacement)))


def _clear_login_state_for_profile_change(account: MutableMapping[str, Any]) -> None:
    message = "账号浏览器目录与其他账号重复，已分配独立目录，请重新登录。"
    account["chromePort"] = 0
    account["shadowChromePid"] = 0
    account["loginStatus"] = "需要重新登录"
    account["lastError"] = message
    account["lastResult"] = message
    account["lastFailureReason"] = "需要重新登录"
    for key in ("cookieProtected", "cookieSummary", "cookieUpdatedAt", "activeChromePort"):
        account.pop(key, None)


def _used_profile_paths(accounts: Iterable[Mapping[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for account in accounts:
        normalized = _normalize_profile_path(str(account.get("profileDir") or ""))
        if normalized:
            paths.add(normalized)
    return paths


def _unique_profile_dir(data_dir: Path, base_slug: str, used_paths: set[str]) -> Path:
    clean_slug = base_slug or "account"
    index = 1
    while True:
        suffix = "" if index == 1 else f"-{index}"
        candidate = data_dir / "profiles" / f"{clean_slug}{suffix}"
        if _normalize_profile_path(str(candidate)) not in used_paths:
            return candidate
        index += 1


def _normalize_profile_path(raw: str) -> str:
    text = str(raw or "").strip().strip('"')
    return str(Path(text)).replace("/", "\\").lower() if text else ""


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


def _looks_like_login_error(exc: Exception) -> bool:
    if exc.__class__.__name__ == "JdWorkloadIdentityRequiredError":
        return False
    if isinstance(exc, DirectApiLoginRequiredError):
        return True
    text = str(exc)
    return "登录" in text


def _failure_reason(exc: Exception) -> str:
    if exc.__class__.__name__ == "JdWorkloadIdentityRequiredError":
        return "需要配置客服身份"
    if _looks_like_login_error(exc):
        return "需要重新登录"
    if isinstance(exc, DirectApiCaptureError):
        return "接口失败"
    return "采集失败"


def _error_type(exc: Exception, status: str) -> str:
    if exc.__class__.__name__ == "JdWorkloadIdentityRequiredError":
        return "identity_required"
    if status == "需要重新登录":
        return "login_required"
    return "generic"


def _upload_failure_reason(upload_message: str) -> str:
    message = str(upload_message or "")
    if "未找到员工账号映射" in message:
        return "平台未配置客服账号"
    return "上传失败"


def _capture_identity_for_account(account: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    raw_metrics = payload.get("rawMetrics")
    account_identity = raw_metrics.get("accountIdentity") if isinstance(raw_metrics, Mapping) else ""
    for value in (
        account_identity,
        payload.get("loginAccount"),
        payload.get("subAccount"),
        account.get("lastKnownLoginAccount"),
        account.get("loginHint"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return ""


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
