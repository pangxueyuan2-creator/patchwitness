"""Concurrent, bounded execution of repository-owned verification checks."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from patchwitness.models import CheckResult, CheckSpec
from patchwitness.redaction import excerpt, redact

_SHELL_INTERPRETERS = frozenset(
    {
        "cmd",
        "cmd.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "bash",
        "sh",
        "zsh",
        "fish",
        "dash",
        "csh",
        "tcsh",
        "wscript",
        "wscript.exe",
        "cscript",
        "cscript.exe",
        "mshta",
        "mshta.exe",
    }
)
_SHELL_TOKENS = frozenset({";", "&&", "||", "|", "`", ">", "<", "$(", "${"})
_INLINE_PAYLOAD_FLAGS = frozenset(
    {"-c", "/c", "-command", "-enc", "-encodedcommand", "--eval", "-e"}
)
_POLICY_EXECUTABLES = frozenset(
    {
        "python",
        "python.exe",
        "python3",
        "python3.exe",
        "py",
        "py.exe",
        "pytest",
        "pytest.exe",
        "ruff",
        "ruff.exe",
        "mypy",
        "mypy.exe",
        "npm",
        "npm.cmd",
        "npx",
        "npx.cmd",
        "node",
        "node.exe",
        "pnpm",
        "pnpm.cmd",
        "yarn",
        "yarn.cmd",
        "bun",
        "bun.exe",
        "go",
        "go.exe",
        "cargo",
        "cargo.exe",
        "make",
        "make.exe",
        "uv",
        "uv.exe",
        "hatch",
        "hatch.exe",
        "tox",
        "tox.exe",
        "nox",
        "nox.exe",
    }
)
_INLINE_INTERPRETERS = frozenset(
    {
        "python",
        "python.exe",
        "python3",
        "python3.exe",
        "py",
        "py.exe",
        "node",
        "node.exe",
        "perl",
        "perl.exe",
        "ruby",
        "ruby.exe",
        "php",
        "php.exe",
    }
)


def run_checks(
    root: Path,
    checks: Iterable[CheckSpec],
    *,
    parallel: bool = True,
    max_workers: int = 4,
) -> tuple[CheckResult, ...]:
    specs = tuple(checks)
    if not specs:
        return ()
    if not parallel or len(specs) == 1:
        return tuple(_run_one(root, spec) for spec in specs)
    workers = max(1, min(max_workers, len(specs)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="patchwitness-check") as pool:
        futures = {spec.id: pool.submit(_run_one, root, spec) for spec in specs}
        return tuple(futures[spec.id].result() for spec in specs)


def split_check_command(command: str) -> list[str]:
    """Split a check command into argv without invoking a shell.

    Quotes group tokens. Backslashes stay literal except for ``\\\\`` and
    ``\\"`` inside double quotes. POSIX ``shlex`` would swallow unquoted
    Windows path separators; Windows ``shlex`` leaves stray quotes on
    ``"C:\\...\\python.exe"``.
    """

    stripped = command.strip()
    if not stripped:
        raise ValueError("empty check command")
    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if quote == '"':
            if char == "\\" and index + 1 < len(stripped) and stripped[index + 1] in '"\\':
                current.append(stripped[index + 1])
                index += 2
                continue
            if char == '"':
                quote = None
                index += 1
                continue
            current.append(char)
            index += 1
            continue
        if quote == "'":
            if char == "'":
                quote = None
                index += 1
                continue
            current.append(char)
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char.isspace():
            if current:
                tokens.append("".join(current))
                current = []
            index += 1
            continue
        current.append(char)
        index += 1
    if quote is not None:
        raise ValueError("unbalanced quotes in check command")
    if current:
        tokens.append("".join(current))
    if not tokens:
        raise ValueError("empty check command")
    return tokens


def validate_policy_check(argv: list[str]) -> None:
    """Refuse compiled-policy command shapes that are not a test/build runner.

    This is not a general sandbox. It only rejects the command forms reproduced
    in tests: shell interpreters, inline interpreter payloads, and shell tokens.
    """

    if not argv:
        raise ValueError("empty check command")
    executable = Path(argv[0].strip("\"'")).name.lower()
    if executable in _SHELL_INTERPRETERS:
        raise ValueError(f"shell interpreter is not accepted from compiled policy: {executable}")
    if executable not in _POLICY_EXECUTABLES:
        raise ValueError(f"executable is not accepted from compiled policy: {executable}")
    for token in argv:
        if (
            token in _SHELL_TOKENS
            or token.startswith("$(")
            or token.startswith("${")
            or any(meta in token for meta in ("&&", "||", ";", "|", "`"))
        ):
            raise ValueError("shell metacharacters are not accepted from compiled policy")
    if executable in _INLINE_INTERPRETERS and any(
        token.lower() in _INLINE_PAYLOAD_FLAGS for token in argv[1:]
    ):
        raise ValueError("inline interpreter payloads are not accepted from compiled policy")


def resolve_check_executable(argv: list[str], env: dict[str, str]) -> list[str]:
    """Resolve argv[0] through PATH so Windows does not pick the store alias.

    ``CreateProcess('python')`` on this host launches the global interpreter
    even when PATH starts with a virtualenv. ``shutil.which`` honors PATH.
    """

    if not argv:
        return argv
    name = argv[0]
    search_path = env.get("PATH", os.defpath)
    found = shutil.which(name, path=search_path)
    if found:
        return [found, *argv[1:]]
    return argv


def _refused(spec: CheckSpec, message: str) -> CheckResult:
    sanitized = redact(message)
    return CheckResult(
        id=spec.id,
        command=spec.command,
        required=spec.required,
        exit_code=126,
        duration_ms=0,
        timed_out=False,
        output_sha256=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
        output_excerpt=excerpt(sanitized),
    )


def _run_one(root: Path, spec: CheckSpec) -> CheckResult:
    started = time.perf_counter()
    try:
        argv = split_check_command(spec.command)
        if not spec.trusted:
            validate_policy_check(argv)
    except ValueError as exc:
        return _refused(spec, f"check command refused: {exc}")
    timed_out = False
    exit_code: int | None
    output: str
    env = os.environ.copy()
    _prefer_project_virtualenv(root, env)
    argv = resolve_check_executable(argv, env)
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
            argv,
            cwd=root,
            shell=False,
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
    except FileNotFoundError as exc:
        duration_ms = max(0, round((time.perf_counter() - started) * 1_000))
        sanitized = redact(f"check executable was not found: {exc}")
        return CheckResult(
            id=spec.id,
            command=spec.command,
            required=spec.required,
            exit_code=127,
            duration_ms=duration_ms,
            timed_out=False,
            output_sha256=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
            output_excerpt=excerpt(sanitized),
        )
    except OSError as exc:
        duration_ms = max(0, round((time.perf_counter() - started) * 1_000))
        sanitized = redact(f"check executable could not be started: {exc}")
        return CheckResult(
            id=spec.id,
            command=spec.command,
            required=spec.required,
            exit_code=127,
            duration_ms=duration_ms,
            timed_out=False,
            output_sha256=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
            output_excerpt=excerpt(sanitized),
        )
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
    if executables.is_dir():
        current_path = env.get("PATH", "")
        env["PATH"] = str(executables) + (os.pathsep + current_path if current_path else "")
        env["VIRTUAL_ENV"] = str(virtualenv)
        return
    if sys.prefix != sys.base_prefix:
        current = Path(sys.executable).parent
        if current.is_dir():
            current_path = env.get("PATH", "")
            env["PATH"] = str(current) + (os.pathsep + current_path if current_path else "")
