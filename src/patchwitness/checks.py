"""Concurrent, bounded execution of repository-owned verification checks."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from patchwitness.models import CheckResult, CheckSpec
from patchwitness.redaction import excerpt, redact

_LEADING_TOOL = re.compile(r'^\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))(.*)\Z', re.S)


def run_checks(
    root: Path,
    checks: Iterable[CheckSpec],
    *,
    parallel: bool = True,
    max_workers: int = 4,
    untrusted: bool = False,
) -> tuple[CheckResult, ...]:
    specs = tuple(checks)
    if not specs:
        return ()
    if not parallel or len(specs) == 1:
        return tuple(_run_one(root, spec, untrusted=untrusted) for spec in specs)
    workers = max(1, min(max_workers, len(specs)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="patchwitness-check") as pool:
        futures = {
            spec.id: pool.submit(_run_one, root, spec, untrusted=untrusted) for spec in specs
        }
        return tuple(futures[spec.id].result() for spec in specs)


def _run_one(root: Path, spec: CheckSpec, *, untrusted: bool = False) -> CheckResult:
    started = time.perf_counter()
    timed_out = False
    exit_code: int | None
    output: str
    env = os.environ.copy()
    if untrusted:
        try:
            command = _resolve_trusted_command(spec.command, root)
        except ValueError as exc:
            return _blocked_result(spec, started, str(exc))
    else:
        command = spec.command
        _prefer_project_virtualenv(root, env)
    env["PATCHWITNESS_CHECK_ID"] = spec.id
    env["PATCHWITNESS_REPOSITORY_ROOT"] = str(root)
    env["NO_COLOR"] = "1"
    source_root = root / "src"
    if source_root.is_dir():
        existing_python_path = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(source_root)
            if not existing_python_path
            else str(source_root) + os.pathsep + existing_python_path
        )
    try:
        result = subprocess.run(
            command,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=spec.timeout_seconds,
            env=env,
            check=False,
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else exc.stdout
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        output = (stdout or "") + (stderr or "")
    duration_ms = max(0, round((time.perf_counter() - started) * 1_000))
    sanitized = redact(output)
    return CheckResult(
        id=spec.id,
        command=spec.command,
        required=spec.required,
        exit_code=exit_code,
        duration_ms=duration_ms,
        timed_out=timed_out,
        output_sha256=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
        output_excerpt=excerpt(sanitized),
    )


def _blocked_result(spec: CheckSpec, started: float, reason: str) -> CheckResult:
    output = redact(f"PatchWitness refused to execute clean-room check: {reason}")
    return CheckResult(
        id=spec.id,
        command=spec.command,
        required=spec.required,
        exit_code=126,
        duration_ms=max(0, round((time.perf_counter() - started) * 1_000)),
        timed_out=False,
        output_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest(),
        output_excerpt=excerpt(output),
    )


def _resolve_trusted_command(command: str, root: Path) -> str:
    """Resolve a clean-room command's executable outside the untrusted worktree.

    Clean-room checks use a trusted contract but execute inside untrusted repository
    content. The shell must therefore never discover an executable from the worktree,
    and compound shell syntax is rejected rather than partially sanitized.
    """

    if _contains_shell_control(command):
        raise ValueError("compound shell syntax is not allowed in clean-room checks")
    match = _LEADING_TOOL.fullmatch(command)
    if match is None:
        raise ValueError("check command has no safely resolvable executable")
    first = next(value for value in match.groups()[:3] if value is not None)
    remainder = match.group(4)
    if first in {"python", "python3"}:
        resolved = sys.executable
    else:
        candidate = Path(first)
        if candidate.is_absolute():
            resolved = str(candidate)
        else:
            resolved = shutil.which(first)
        if resolved is None:
            raise ValueError(f"check executable is not available on PATH: {first}")
    try:
        resolved_path = Path(resolved).resolve()
        repository_root = root.resolve()
    except OSError as exc:
        raise ValueError(f"check executable could not be resolved safely: {first}") from exc
    if resolved_path == repository_root or repository_root in resolved_path.parents:
        raise ValueError(
            "check executable resolves inside the untrusted worktree: " f"{first}"
        )
    escaped = str(resolved_path).replace('"', '\\"')
    return f'"{escaped}"{remainder}'


def _contains_shell_control(command: str) -> bool:
    """Return True for shell composition/substitution outside single quotes."""

    single = False
    double = False
    escaped = False
    index = 0
    while index < len(command):
        char = command[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\" and not single:
            escaped = True
            index += 1
            continue
        if char == "'" and not double:
            single = not single
            index += 1
            continue
        if char == '"' and not single:
            double = not double
            index += 1
            continue
        if not single:
            if char in "\r\n`" or (not double and char in "&|<>;"):
                return True
            if char == "$" and index + 1 < len(command) and command[index + 1] == "(":
                return True
        index += 1
    return single or double


def _prefer_project_virtualenv(root: Path, env: dict[str, str]) -> None:
    virtualenv = root / ".venv"
    executables = virtualenv / ("Scripts" if os.name == "nt" else "bin")
    if not executables.is_dir():
        return
    current_path = env.get("PATH", "")
    env["PATH"] = str(executables) + (os.pathsep + current_path if current_path else "")
    env["VIRTUAL_ENV"] = str(virtualenv)
