"""Conservative redaction for command output stored in evidence packs."""

from __future__ import annotations

import re

_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def redact(text: str) -> str:
    value = text
    value = _PATTERNS[0].sub(r"\1\2[REDACTED]", value)
    for pattern in _PATTERNS[1:]:
        value = pattern.sub("[REDACTED]", value)
    return value


def excerpt(text: str, *, limit: int = 4_000) -> str:
    sanitized = redact(text).replace("\r\n", "\n")
    if len(sanitized) <= limit:
        return sanitized
    head = limit * 3 // 4
    tail = limit - head
    return f"{sanitized[:head]}\n... [output truncated] ...\n{sanitized[-tail:]}"

