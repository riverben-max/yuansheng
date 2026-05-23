from __future__ import annotations

import re
from typing import Any


SENSITIVE_KEY_RE = re.compile(
    r"(?i)(cookie|set-cookie|authorization|csrf|token|secret|x-sign|sign|thor|pin|pt_pin|"
    r"pass_id|jsessionid|windows_app_shop_token_[A-Za-z0-9_-]*|_m_h5_tk|_tb_token_)"
)


def sanitize_sensitive_text(value: Any, limit: int = 300) -> str:
    text = str(value or "")
    if not text:
        return ""

    text = re.sub(
        r"(?i)((?<![A-Za-z0-9_])[\"']?(?:cookie|set-cookie|authorization|csrf|token|secret|x-sign|sign|thor|pin|pt_pin|pass_id|jsessionid|windows_app_shop_token_[A-Za-z0-9_-]*|_m_h5_tk|_tb_token_)[\"']?\s*[:=]\s*)([\"']?)[^;,\s\"'}]+(\2)",
        lambda match: f"{match.group(1)}{match.group(2)}<redacted>{match.group(3)}",
        text,
    )
    text = re.sub(
        r"(?i)(?<![A-Za-z0-9_])(thor|pin|pt_pin|PASS_ID|JSESSIONID|_m_h5_tk|_tb_token_|windows_app_shop_token_[A-Za-z0-9_-]*)=([^;\s,]+)",
        lambda match: f"{match.group(1)}=<redacted>",
        text,
    )
    if len(text) > limit:
        return text[: max(0, limit - 3)] + "..."
    return text
