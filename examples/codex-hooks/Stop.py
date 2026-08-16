#!/usr/bin/env python3
"""Codex Stop hook that captures a structural PatchWitness Change Passport.

The hook uses only Codex's documented lifecycle fields. It never copies the
prompt, transcript path, model output, or any extra hook payload into evidence.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _log(message: str) -> None:
    print(f"[PatchWitness] {message}", file=sys.stderr, flush=True)


def _safe_token(value: object, *, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return token[:64] or default


def _git_root(cwd: object) -> Path | None:
    if not isinstance(cwd, str) or not cwd.strip():
        return None
    try:
        resolved_cwd = Path(cwd).expanduser().resolve(strict=True)
    except OSError:
        return None
    if not resolved_cwd.is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=resolved_cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        root = Path(result.stdout.strip()).resolve(strict=True)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not root.is_dir() or not resolved_cwd.is_relative_to(root):
        return None
    return root


def _patchwitness_command(root: Path) -> list[str] | None:
    configured = os.environ.get("PATCHWITNESS_EXECUTABLE", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            resolved_candidate = candidate.resolve()
            return None if resolved_candidate.is_relative_to(root) else [str(resolved_candidate)]
        resolved = shutil.which(configured)
        if not resolved:
            return None
        resolved_candidate = Path(resolved).resolve()
        return None if resolved_candidate.is_relative_to(root) else [str(resolved_candidate)]

    executable = shutil.which("patchwitness")
    if executable:
        resolved_candidate = Path(executable).resolve()
        return None if resolved_candidate.is_relative_to(root) else [str(resolved_candidate)]
    return None


def _read_status(evidence_path: Path) -> tuple[str, int, int]:
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        summary = evidence.get("summary", {})
        status = str(summary.get("status", "unknown")).upper()
        files = int(summary.get("files_changed", 0))
        raw_findings = evidence.get("findings", [])
        findings = len(raw_findings) if isinstance(raw_findings, list) else 0
        return status, files, findings
    except (OSError, ValueError, TypeError):
        return "UNKNOWN", 0, 0


def _capture(root: Path, event: dict[str, Any], command: list[str]) -> None:
    session_id = _safe_token(event.get("session_id"), default="codex-session")
    turn_id = _safe_token(event.get("turn_id"), default="stopped")
    relative_output = Path(".patchwitness") / "evidence" / f"codex-stop-{session_id}-{turn_id}.json"
    evidence_dir = (root / relative_output.parent).resolve()
    if not evidence_dir.is_relative_to(root):
        _log("refused an evidence directory that resolves outside the Git workspace")
        return

    scan_command = [
        *command,
        "gate",
        "--base",
        "HEAD",
        "--policy-ref",
        "HEAD",
        "--no-checks",
        "--output",
        str(relative_output),
    ]
    try:
        result = subprocess.run(
            scan_command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        _log("gate timed out after 120 seconds; no Codex data was recorded")
        return
    except OSError as exc:
        _log(f"could not start PatchWitness ({exc.__class__.__name__})")
        return

    evidence_path = root / relative_output
    if result.returncode not in {0, 1} or not evidence_path.is_file():
        _log(f"gate failed with exit code {result.returncode}; run 'patchwitness doctor'")
        return

    status, files, findings = _read_status(evidence_path)
    _log(
        f"{status}: {files} file(s), {findings} finding(s); "
        f"evidence: {relative_output.as_posix()}"
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        _log("ignored invalid hook JSON")
        return 0
    if not isinstance(event, dict) or event.get("hook_event_name") != "Stop":
        return 0

    root = _git_root(event.get("cwd"))
    if root is None:
        _log("no Git workspace was present in the Codex Stop payload")
        return 0
    command = _patchwitness_command(root)
    if command is None:
        _log(
            "PatchWitness was not found outside the Git workspace; "
            "see docs/integrations/codex.md"
        )
        return 0

    _capture(root, event, command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
