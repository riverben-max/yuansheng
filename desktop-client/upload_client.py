from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Mapping

import httpx

APP_KEY = "QINGBIRD_RPA_01"
SECRET_KEY = "8c7v6b5n4m3,2.1/"
EMPLOYEE_UPLOAD_PATH = "/spider/upload/employee-performance"
PLATFORM_TYPE_MAP = {"qn": 1, "jd": 2, "pdd": 3}


def _load_auth_overrides() -> tuple[str, str]:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Roaming")
    auth_path = Path(base) / "YuanshengDataAssistant" / "data" / "auth_config.json"
    try:
        if auth_path.exists():
            config = json.loads(auth_path.read_text(encoding="utf-8"))
            if isinstance(config, dict):
                return str(config.get("appKey") or APP_KEY), str(config.get("secretKey") or SECRET_KEY)
    except Exception:
        pass
    return APP_KEY, SECRET_KEY


class UploadClientError(RuntimeError):
    pass


def build_employee_upload_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    platform_str = str(payload.get("platform") or "qn").strip().lower()
    platform_type = PLATFORM_TYPE_MAP.get(platform_str, 1)
    shop_id = payload.get("shopId")
    return {
        "shopId": int(shop_id) if shop_id is not None else None,
        "loginAccount": payload.get("loginAccount"),
        "recordDate": payload.get("recordDate"),
        "subAccount": payload.get("subAccount"),
        "platformType": platform_type,
        "consultationCount": payload.get("consultationCount"),
        "receiveCount": payload.get("receiveCount"),
        "validReceiveCount": payload.get("validReceiveCount"),
        "inquiryCount": payload.get("inquiryCount"),
        "conversionRate": payload.get("conversionRate"),
        "firstReplyTime": payload.get("firstReplyTime"),
        "avgReplyTime": payload.get("avgReplyTime"),
        "wwReplyRate": payload.get("wwReplyRate"),
        "satisfaction": payload.get("satisfaction"),
        "rawMetrics": payload.get("rawMetrics"),
    }


def upload_employee_payload(server_url: str, payload: Mapping[str, Any], timeout_seconds: float = 10.0) -> Dict[str, Any]:
    base_url = str(server_url or "").strip().rstrip("/")
    if not base_url:
        raise UploadClientError("未配置服务端地址。")

    app_key, secret_key = _load_auth_overrides()
    timestamp = str(int(time.time()))
    sign = hashlib.md5(f"{app_key}{timestamp}{secret_key}".encode("utf-8")).hexdigest()
    url = f"{base_url}{EMPLOYEE_UPLOAD_PATH}"
    headers = {
        "X-App-Key": app_key,
        "X-Timestamp": timestamp,
        "X-Sign": sign,
        "Content-Type": "application/json; charset=utf-8",
    }
    request_payload = build_employee_upload_payload(payload)

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
