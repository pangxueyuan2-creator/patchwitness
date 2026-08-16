#!/usr/bin/env python3
"""Cline TaskComplete hook that captures a structural Change Passport.

The hook intentionally uses only Python's standard library. It never copies the
Cline prompt, model output, user ID, or hook payload into PatchWitness evidence.
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


def _finish() -> int:
    # Cline reserves hook stdout for one JSON control object.
    print("{}", flush=True)
    return 0


def _safe_token(value: object, *, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip(".-")
    return token[:64] or default


def _workspace_roots(event: dict[str, Any]) -> tuple[Path, ...]:
    raw_roots = event.get("workspaceRoots")
    if not isinstance(raw_roots, list):
        return ()
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw_root in raw_roots:
        if not isinstance(raw_root, str) or not raw_root.strip():
            continue
        try:
            root = Path(raw_root).expanduser().resolve(strict=True)
        except OSError:
            continue
        if root in seen or not root.is_dir() or not (root / ".git").exists():
            continue
        seen.add(root)
        roots.append(root)
    return tuple(roots)


def _is_within(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _patchwitness_command(roots: tuple[Path, ...]) -> list[str] | None:
    configured = os.environ.get("PATCHWITNESS_EXECUTABLE", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            resolved_candidate = candidate.resolve()
            return None if _is_within(resolved_candidate, roots) else [str(resolved_candidate)]
        resolved = shutil.which(configured)
        if not resolved:
            return None
        resolved_candidate = Path(resolved).resolve()
        return None if _is_within(resolved_candidate, roots) else [str(resolved_candidate)]

    executable = shutil.which("patchwitness")
    if executable:
        resolved_candidate = Path(executable).resolve()
        return None if _is_within(resolved_candidate, roots) else [str(resolved_candidate)]
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
    task_id = _safe_token(event.get("taskId"), default="cline-task")
    timestamp = _safe_token(event.get("timestamp"), default="completed")
    relative_output = Path(".patchwitness") / "evidence" / f"cline-{task_id}-{timestamp}.json"
    evidence_dir = (root / relative_output.parent).resolve()
    if not evidence_dir.is_relative_to(root):
        _log("refused an evidence directory that resolves outside the Git workspace")
        return
    scan_command = [*command, "scan", "--no-checks", "--output", str(relative_output)]

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
        _log("scan timed out after 120 seconds; no Cline data was recorded")
        return
    except OSError as exc:
        _log(f"could not start PatchWitness ({exc.__class__.__name__})")
        return

    evidence_path = root / relative_output
    if result.returncode not in {0, 1} or not evidence_path.is_file():
        _log(f"scan failed with exit code {result.returncode}; run 'patchwitness doctor'")
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
        return _finish()
    if not isinstance(event, dict) or event.get("hookName") != "agent_end":
        return _finish()

    roots = _workspace_roots(event)
    if not roots:
        _log("no Git workspace was present in the Cline TaskComplete payload")
        return _finish()
    command = _patchwitness_command(roots)
    if command is None:
        _log(
            "PatchWitness was not found outside the Git workspace; "
            "see docs/integrations/cline.md"
        )
        return _finish()

    for root in roots:
        _capture(root, event, command)
    return _finish()


if __name__ == "__main__":
    raise SystemExit(main())