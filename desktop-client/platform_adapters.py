from __future__ import annotations

from typing import Any, Callable, Mapping

from platform_config import normalize_platform


CaptureAdapter = Callable[[Mapping[str, Any], Callable[[str], None]], Mapping[str, Any]]


class PlatformAdapterNotRegisteredError(RuntimeError):
    pass


def default_capture_adapters(
    qn_capture_func: CaptureAdapter,
    jd_capture_func: CaptureAdapter,
    pdd_capture_func: CaptureAdapter,
) -> dict[str, CaptureAdapter]:
    return {
        "qn": qn_capture_func,
        "jd": jd_capture_func,
        "pdd": pdd_capture_func,
    }


def select_capture_adapter(platform: object, adapters: Mapping[str, CaptureAdapter]) -> CaptureAdapter:
    normalized = normalize_platform(platform)
    adapter = adapters.get(normalized)
    if adapter is None:
        raise PlatformAdapterNotRegisteredError(f"平台 {normalized} 未注册采集适配器。")
    return adapter
