"""Real child processes exercise capture limits, cleanup and evidence behavior."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from patchwitness import check_process
from patchwitness.checks import run_checks
from patchwitness.evidence import capture_evidence, verify_evidence
from patchwitness.models import CheckSpec, Contract, GateStatus


def command(root: Path, source: str) -> str:
    script = root / "check.py"
    script.write_text(source, encoding="utf-8")
    return f'"{sys.executable}" "{script}"'


def run(root: Path, source: str, *, limit: int = 4096, timeout: float = 5.0):
    return check_process.run_check_process(
        command(root, source), root=root, env=os.environ.copy(),
        timeout=timeout, stream_limit=limit,
    )


@pytest.mark.parametrize("size", [0, 4096])
def test_empty_and_exact_limit_on_both_streams(tmp_path: Path, size: int) -> None:
    result = run(tmp_path, f"import os\nos.write(1, b'a' * {size})\nos.write(2, b'b' * {size})")
    assert result.failure is None
    assert result.returncode == 0
    assert result.stdout == b"a" * size
    assert result.stderr == b"b" * size


@pytest.mark.parametrize("fd", [1, 2])
def test_limit_plus_one_cannot_pass_even_when_child_exits_zero(tmp_path: Path, fd: int) -> None:
    result = run(tmp_path, f"import os\nos.write({fd}, b'a' * 4097)")
    assert result.failure == "output_limit"
    assert result.returncode is None
    assert result.stdout == result.stderr == b""


@pytest.mark.parametrize("streams", [(1,), (2,), (1, 2)])
def test_output_flood_stops_without_retaining_partial_output(
    tmp_path: Path, streams: tuple[int, ...],
) -> None:
    started = time.monotonic()
    result = run(
        tmp_path,
        f"import os\nwhile True:\n for fd in {streams!r}:\n  os.write(fd, b'x' * 8192)\n",
    )
    assert result.failure == "output_limit"
    assert result.stdout == result.stderr == b""
    assert time.monotonic() - started < 15


def test_drains_stderr_before_stdout_without_deadlock(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        "import sys\n"
        "sys.stderr.buffer.write(b'b' * 131072)\nsys.stderr.buffer.flush()\n"
        "sys.stdout.buffer.write(b'a' * 131072)\nsys.stdout.buffer.flush()\n",
        limit=131072,
    )
    assert result.failure is None and result.returncode == 0
    assert result.stdout == b"a" * 131072
    assert result.stderr == b"b" * 131072


def test_limits_count_bytes_not_unicode_characters(tmp_path: Path) -> None:
    result = run(tmp_path, "import os\nos.write(1, bytes([0xe7, 0x95, 0x8c]) * 10)", limit=29)
    assert result.failure == "output_limit"


def test_success_preserves_stdout_then_stderr_redacted_hash(tmp_path: Path) -> None:
    check = CheckSpec(
        "streams",
        command(tmp_path, "import os\nos.write(2, b'err')\nos.write(1, b'out\\xff')"),
        timeout_seconds=5,
    )
    result = run_checks(tmp_path, [check])[0]
    expected = "out\ufffderr"
    assert result.passed
    assert result.output_excerpt == expected
    assert result.output_sha256 == hashlib.sha256(expected.encode()).hexdigest()


def test_nonzero_child_exit_is_preserved(tmp_path: Path) -> None:
    result = run(tmp_path, "print('failed')\nraise SystemExit(7)")
    assert result.failure is None
    assert result.returncode == 7
    assert result.stdout.strip() == b"failed"


def test_checks_are_noninteractive(tmp_path: Path) -> None:
    result = run(tmp_path, "import sys\nassert sys.stdin.buffer.read() == b''\nprint('done')")
    assert result.failure is None and result.returncode == 0


def test_timeout_discards_partial_child_diagnostics(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        "import os, time\nos.write(1, b'synthetic-private-diagnostic')\ntime.sleep(5)",
        timeout=0.3,
    )
    assert result.failure == "timeout"
    assert result.timed_out
    assert result.returncode is None
    assert result.stdout == result.stderr == b""


def test_exited_shell_with_inherited_pipes_cannot_return_success(tmp_path: Path) -> None:
    started = time.monotonic()
    result = run(
        tmp_path,
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(2)'])\n",
        timeout=0.4,
    )
    assert result.failure == "timeout"
    assert result.timed_out
    assert time.monotonic() - started < 15


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup contract")
def test_timeout_kills_noncooperative_descendant(tmp_path: Path) -> None:
    marker = tmp_path / "survived"
    child = tmp_path / "child.py"
    child.write_text(
        "import signal, time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(1)\n"
        f"Path({str(marker)!r}).write_text('survived')\n",
        encoding="utf-8",
    )
    result = run(
        tmp_path,
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, {str(child)!r}])\ntime.sleep(5)\n",
        timeout=0.4,
    )
    assert result.failure == "timeout"
    time.sleep(1.1)
    assert not marker.exists()


def test_invalid_limits_do_not_start_a_process(tmp_path: Path, monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("process must not start")

    monkeypatch.setattr(check_process.subprocess, "Popen", forbidden)
    for timeout, limit in ((0, 1), (-1, 1), (float("nan"), 1), (float("inf"), 1),
                           (True, 1), (1, True), (1, 0), (1, 1_048_577)):
        result = check_process.run_check_process(
            "unused", root=tmp_path, env={}, timeout=timeout, stream_limit=limit,
        )
        assert result.failure == "invalid_limits"


def test_spawn_errors_never_echo_exception_text(tmp_path: Path) -> None:
    result = check_process.run_check_process(
        "unused", root=tmp_path / "synthetic-private-missing-path", env={}, timeout=5,
    )
    assert result.failure == "execution_failed"
    assert result.stdout == result.stderr == b""
    assert "synthetic-private" not in repr(result)


def test_pipe_read_error_fails_closed_and_reaps_shell(tmp_path: Path, monkeypatch) -> None:
    processes = []
    original = check_process.subprocess.Popen

    def start(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    def broken_read(*args):
        raise OSError("synthetic-private-read-error")

    monkeypatch.setattr(check_process.subprocess, "Popen", start)
    monkeypatch.setattr(check_process, "_read_available", broken_read)
    result = run(tmp_path, "import time\ntime.sleep(5)")
    assert result.failure == "execution_failed"
    assert "synthetic-private" not in repr(result)
    assert len(processes) == 1 and processes[0].poll() is not None


def test_required_output_overflow_produces_a_failed_verifiable_passport(tmp_path: Path) -> None:
    check = CheckSpec(
        "noisy",
        command(tmp_path, "import sys\nsys.stdout.buffer.write(b'x' * 1048577)\n"),
        timeout_seconds=5,
    )
    for args in (
        ("init", "-b", "main"), ("config", "user.name", "Synthetic Test"),
        ("config", "user.email", "test@example.invalid"),
        ("add", "."), ("commit", "-m", "fixture"),
    ):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    pack = capture_evidence(tmp_path, Contract(checks=(check,)))
    assert pack.status == GateStatus.FAIL
    assert pack.summary["checks_passed"] == 0
    assert pack.checks[0]["exit_code"] == 125
    assert any(finding["rule_id"] == "PW021" for finding in pack.findings)
    assert verify_evidence(pack).payload_sha256 == pack.payload_sha256
    assert "xxxxxx" not in json.dumps(pack.to_dict())


def test_output_hash_preserves_legacy_universal_newlines(tmp_path: Path) -> None:
    check = CheckSpec(
        "newlines", command(tmp_path, "import os\nos.write(1, b'a\\r\\nb\\r')"),
        timeout_seconds=5,
    )
    result = run_checks(tmp_path, [check])[0]
    assert result.passed
    assert result.output_sha256 == hashlib.sha256(b"a\nb\n").hexdigest()


def test_completed_process_still_requires_both_pipe_eofs(tmp_path: Path) -> None:
    # Keep real write handles open after an observed process exit. This isolates
    # the inherited-pipe state without depending on child startup/scheduling time.
    fds = []
    try:
        for _ in range(2):
            read_fd, write_fd = os.pipe()
            fds.extend([read_fd, write_fd])
            if os.name != "nt":
                os.set_blocking(read_fd, False)
        with subprocess.Popen(
            [sys.executable, "-c", "pass"], cwd=tmp_path,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ) as process:
            assert process.wait(timeout=5) == 0
            with pytest.raises(check_process._BoundaryError, match="timeout"):
                check_process._capture(process, [fds[0], fds[2]], time.monotonic() + 0.1, 4096)
    finally:
        for fd in fds:
            os.close(fd)
