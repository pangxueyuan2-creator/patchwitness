"""Concurrent, bounded execution of repository-owned verification checks."""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from patchwitness.models import CheckResult, CheckSpec
from patchwitness.redaction import excerpt, redact


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


def _run_one(root: Path, spec: CheckSpec) -> CheckResult:
    started = time.perf_counter()
    timed_out = False
    exit_code: int | None
    output: str
    env = os.environ.copy()
    env["PATCHWITNESS_CHECK_ID"] = spec.id
    env["NO_COLOR"] = "1"
    try:
        result = subprocess.run(
            spec.command,
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
