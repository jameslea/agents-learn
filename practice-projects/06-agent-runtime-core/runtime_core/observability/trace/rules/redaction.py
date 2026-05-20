from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from runtime_core.observability.trace.event import TraceEvent


SENSITIVE_KEYWORDS = ("api_key", "apikey", "token", "password", "secret", "credential")
REDACTED = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: REDACTED if _is_sensitive_key(str(key)) else _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, str):
        return _redact_string(value)
    return value

def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(keyword in lower for keyword in SENSITIVE_KEYWORDS)

def _redact_string(value: str) -> str:
    redacted = value
    for keyword in SENSITIVE_KEYWORDS:
        redacted = _redact_inline_secret(redacted, keyword)
    return redacted

def _redact_inline_secret(value: str, keyword: str) -> str:
    lower = value.lower()
    marker = f"{keyword}="
    start = lower.find(marker)
    if start == -1:
        return value
    end = value.find(" ", start)
    if end == -1:
        end = len(value)
    return value[: start + len(marker)] + REDACTED + value[end:]

def has_sensitive_plaintext(events: Iterable[TraceEvent], secrets: Iterable[str]) -> bool:
    """测试辅助：检查 trace 事件中是否仍有指定敏感明文。"""
    text = json.dumps([event.model_dump(mode="json") for event in events], ensure_ascii=False)
    return any(secret and secret in text for secret in secrets)
