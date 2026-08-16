"""High-confidence, value-free secret detection for changed text files."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from patchwitness.git import safe_regular_file
from patchwitness.models import FileChange, Finding, Severity

MAX_SCAN_BYTES = 2_000_000
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{36,255}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI-style secret key", re.compile(r"\bsk-[A-Za-z0-9_-]{32,255}\b")),
    (
        "generic assigned secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)\b"
            r"\s*[:=]\s*['\"]([A-Za-z0-9_./+=-]{24,})['\"]"
        ),
    ),
)


def scan_changed_files(root: Path, changes: Iterable[FileChange]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for change in changes:
        if change.binary or change.after_sha256 is None:
            continue
        path = safe_regular_file(root, change.path)
        if path is None:
            continue
        try:
            size = path.stat().st_size
            if size > MAX_SCAN_BYTES:
                findings.append(
                    Finding(
                        "PW031",
                        Severity.INFO,
                        f"secret scan skipped for {change.path}: {size} bytes exceeds "
                        f"the {MAX_SCAN_BYTES}-byte limit",
                        change.path,
                    )
                )
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for label, pattern in _SECRET_PATTERNS:
            match = pattern.search(text)
            if match is None:
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                Finding(
                    "PW030",
                    Severity.ERROR,
                    f"possible {label} detected; value omitted from evidence",
                    change.path,
                    line,
                )
            )
    return tuple(findings)
