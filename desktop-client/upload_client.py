from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Mapping

import httpx

from secure_storage import unprotect_text

EMPLOYEE_UPLOAD_PATH = "/spider/upload"
PLATFORM_TYPE_MAP = {"qn": 1, "jd": 2, "pdd": 3}


def _auth_config_path() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "YuanshengDataAssistant" / "data" / "auth_config.json"


def _load_auth_config() -> Dict[str, Any]:
    auth_path = _auth_config_path()
    try:
        if auth_path.exists():
            config = json.loads(auth_path.read_text(encoding="utf-8"))
            if isinstance(config, dict):
                return config
    except Exception:
        pass
    return {}


def resolve_upload_auth() -> tuple[str, str]:
    env_app_key = str(os.environ.get("YUANSHENG_RPA_APP_KEY") or "").strip()
    env_secret_key = str(os.environ.get("YUANSHENG_RPA_SECRET_KEY") or "").strip()
    if env_app_key and env_secret_key:
        return env_app_key, env_secret_key

    config = _load_auth_config()
    app_key = str(config.get("appKey") or "").strip()
    protected_secret = str(config.get("secretKeyProtected") or "").strip()
    if app_key and protected_secret:
        try:
            secret_key = str(unprotect_text(protected_secret) or "").strip()
        except Exception as exc:
            raise UploadClientError(f"上传签名凭据解密失败：{exc}") from exc
        if secret_key:
            return app_key, secret_key

    raise UploadClientError("未配置上传签名凭据，请设置 YUANSHENG_RPA_APP_KEY/YUANSHENG_RPA_SECRET_KEY 或 auth_config.json。")


class UploadClientError(RuntimeError):
    pass


def build_employee_upload_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    platform_str = str(payload.get("platform") or "qn").strip().lower()
    platform_type = PLATFORM_TYPE_MAP.get(platform_str, 1)
    try:
        shop_id = int(payload.get("shopId") or 0)
    except Exception as exc:
        raise UploadClientError("系统店铺 ID 必须是正整数。") from exc
    if shop_id <= 0:
        raise UploadClientError("系统店铺 ID 未绑定，请在账号里填写后端店铺 ID。")
    reply_rate = payload.get("wwReplyRate")
    return {
        "shopId": shop_id,
        "platformType": platform_type,
        "loginAccount": payload.get("loginAccount"),
        "recordDate": payload.get("recordDate"),
        "subAccount": payload.get("subAccount"),
        "consultationCount": payload.get("consultationCount"),
        "receptionCount": payload.get("receiveCount"),
        "effectiveReceptionCount": payload.get("validReceiveCount"),
        "conversionRate": payload.get("conversionRate"),
        "firstResponseTime": payload.get("firstReplyTime"),
        "avgResponseTime": payload.get("avgReplyTime"),
        "salesAmount": payload.get("salesAmount"),
        "responseRate3m": reply_rate,
        "responseRate30s": payload.get("responseRate30s"),
        "replyRate": reply_rate,
        "satisfaction": payload.get("satisfaction"),
        "shopSatisfaction": payload.get("shopSatisfaction"),
        "rawMetrics": payload.get("rawMetrics"),
    }


def upload_employee_payload(server_url: str, payload: Mapping[str, Any], timeout_seconds: float = 10.0) -> Dict[str, Any]:
    base_url = str(server_url or "").strip().rstrip("/")
    if not base_url:
        raise UploadClientError("未配置服务端地址。")

    request_payload = build_employee_upload_payload(payload)
    app_key, secret_key = resolve_upload_auth()
    timestamp = str(int(time.time()))
    sign = hashlib.md5(f"{app_key}{timestamp}{secret_key}".encode("utf-8")).hexdigest()
    url = f"{base_url}{EMPLOYEE_UPLOAD_PATH}"
    headers = {
        "X-App-Key": app_key,
        "X-Timestamp": timestamp,
        "X-Sign": sign,
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        response = httpx.post(url, json=request_payload, headers=headers, timeout=timeout_seconds)
    except httpx.HTTPError as exc:
        raise UploadClientError(f"请求服务端失败：{exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        text = response.text.strip()
        raise UploadClientError(f"服务端返回了非 JSON 响应：HTTP {response.status_code} {text}") from exc

    if response.status_code >= 400:
        raise UploadClientError(body.get("msg") or f"HTTP {response.status_code}")

    if body.get("code") != 200:
        raise UploadClientError(body.get("msg") or "服务端返回失败")

    return {
        "url": url,
        "message": body.get("msg") or "上传成功",
        "data": body.get("data") or {},
    }
