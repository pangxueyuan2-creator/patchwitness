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

_SAFE_TOOL_TOKEN = re.compile(r"[A-Za-z0-9_./:+-]+\Z")


def _resolve_trusted_command(command: str, root: Path) -> str:
    """Absolute-resolve a check command's leading tool outside an untrusted root.

    Checks run with shell=True, so bare tool names are resolved by the
    platform shell: cmd.exe on Windows searches the working directory first,
    and POSIX shells follow PATH. In clean-room mode the working directory
    contains untrusted repository content, so a malicious repository can
    plant an executable (e.g. a tracked .venv or a root-level python.exe)
    that runs with the verifier's privileges. The leading token is therefore
    resolved outside the worktree; complex shell commands authored in the
    trusted contract pass through unchanged, and a tool that resolves only
    inside the worktree refuses to run.
    """

    first, separator, remainder = command.partition(" ")
    if not first or _SAFE_TOOL_TOKEN.fullmatch(first) is None:
        return command
    resolved: str | None
    if first in {"python", "python3"}:
        resolved = sys.executable
    else:
        resolved = shutil.which(first)
        if resolved is None:
            return command  # the shell will produce its own explicit failure
    try:
        resolved_path = Path(resolved).resolve()
        repository_root = root.resolve()
    except OSError:
        return command
    if resolved_path == repository_root or repository_root in resolved_path.parents:
        raise ValueError(
            f"refusing to run check whose executable resolves inside the untrusted worktree: "
            f"{first}"
        )
    return f'"{resolved}"{separator}{remainder}'


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
        command = _resolve_trusted_command(spec.command, root)
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


def _prefer_project_virtualenv(root: Path, env: dict[str, str]) -> None:
    virtualenv = root / ".venv"
    executables = virtualenv / ("Scripts" if os.name == "nt" else "bin")
    if not executables.is_dir():
        return
    current_path = env.get("PATH", "")
    env["PATH"] = str(executables) + (os.pathsep + current_path if current_path else "")
    env["VIRTUAL_ENV"] = str(virtualenv)
