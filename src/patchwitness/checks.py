"""Concurrent, bounded execution of repository-owned verification checks."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from patchwitness.check_process import run_check_process
from patchwitness.models import CheckResult, CheckSpec
from patchwitness.redaction import excerpt, redact

_LEADING_TOOL = re.compile(r'^\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))(.*)\Z', re.S)
_SHELL_WRAPPERS = {
    "bash",
    "cmd",
    "cmd.exe",
    "dash",
    "fish",
    "ksh",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "sh",
    "zsh",
}


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
    with ExitStack() as cleanup:
        if untrusted:
            hooks = cleanup.enter_context(TemporaryDirectory(prefix="patchwitness-hooks-"))
            # Git propagates -c options through this quoted parameter list. Append
            # after inherited options (including GIT_CONFIG_COUNT) without editing
            # shared repository config or the parent process's environment.
            value = "core.hooksPath=" + Path(hooks).as_posix()
            quoted = "'" + value.replace("'", "'\\''") + "'"
            inherited = env.get("GIT_CONFIG_PARAMETERS", "")
            env["GIT_CONFIG_PARAMETERS"] = (inherited + " " if inherited else "") + quoted
        result = run_check_process(command, root=root, env=env, timeout=spec.timeout_seconds)
    timed_out = result.timed_out
    if result.failure is None:
        exit_code = result.returncode
        # Preserve v1's stdout-then-stderr ordering and UTF-8 replacement behavior.
        output = "".join(
            stream.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
            for stream in (result.stdout, result.stderr)
        )
    else:
        exit_code = None if timed_out else 125
        messages = {
            "timeout": "PatchWitness check exceeded its execution deadline.",
            "output_limit": "PatchWitness check exceeded the 1048576-byte per-stream output limit.",
            "invalid_limits": "PatchWitness check has invalid execution limits.",
            "execution_failed": "PatchWitness check execution or pipe capture failed.",
            "cleanup_failed": "PatchWitness could not confirm direct check process cleanup.",
        }
        output = messages[result.failure]
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
    if Path(first).name.casefold() in _SHELL_WRAPPERS:
        raise ValueError("shell interpreter wrappers are not allowed in clean-room checks")
    resolved: str | None = sys.executable if first in {"python", "python3"} else None
    if resolved is None:
        candidate = Path(first)
        resolved = str(candidate) if candidate.is_absolute() else shutil.which(first)
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
    """Return True for shell composition/substitution in a check command."""

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
        if char == "\\" and not single and os.name != "nt":
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
            if os.name == "nt" and not double and char == "^":
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
