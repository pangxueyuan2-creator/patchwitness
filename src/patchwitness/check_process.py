"""Bounded capture for trusted check commands, not a hostile-code sandbox.

No background reader threads or unbounded communicate() buffers are used. The
parent retains at most MAX_STREAM_BYTES per pipe plus one bounded read chunk.
"""

from __future__ import annotations

import math
import os
import signal
import subprocess
import sys
import time
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from pathlib import Path

MAX_STREAM_BYTES = 1_048_576
_READ_BYTES = 8_192
_CLEANUP_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class ProcessOutput:
    returncode: int | None = None
    stdout: bytes = b""
    stderr: bytes = b""
    failure: str | None = None
    timed_out: bool = False


class _BoundaryError(Exception):
    pass


def _read_available(fd: int, count: int) -> bytes | None:
    if sys.platform == "win32":
        # Peek supports anonymous pipes on Windows, including Python 3.11.
        # Only this loop reads these handles; never issue a read with no data.
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        peek = kernel.PeekNamedPipe
        peek.argtypes = [
            wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
            wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD,
        ]
        peek.restype = wintypes.BOOL
        available = wintypes.DWORD()
        if not peek(msvcrt.get_osfhandle(fd), None, 0, None, ctypes.byref(available), None):
            if ctypes.get_last_error() in {109, 232}:  # broken pipe / no more writers
                return b""
            raise OSError("check pipe read failed")
        if not available.value:
            return None
        return os.read(fd, min(count, available.value))
    try:
        return os.read(fd, count)
    except BlockingIOError:
        return None


def _capture(
    process: subprocess.Popen[bytes], fds: list[int], deadline: float, limit: int,
) -> ProcessOutput:
    buffers = [bytearray(), bytearray()]
    active = {0, 1}
    while True:
        if time.monotonic() >= deadline:
            raise _BoundaryError("timeout")
        progressed = False
        for index in sorted(active):
            remaining = limit - len(buffers[index])
            chunk = _read_available(fds[index], min(_READ_BYTES, remaining + 1))
            if chunk is None:
                continue
            progressed = True
            if not chunk:
                active.remove(index)
            elif len(chunk) > remaining:
                # Never hash a truncated prefix as though it were complete output.
                raise _BoundaryError("output_limit")
            else:
                buffers[index].extend(chunk)
        code = process.poll()
        if code is not None and not active:
            return ProcessOutput(code, bytes(buffers[0]), bytes(buffers[1]))
        if not progressed:
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))


def _kill_group(pid: int) -> bool:
    if sys.platform == "win32":
        # The POSIX-only helper must not resolve unavailable Windows APIs.
        return False
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        # No group remains. In particular, a reaped final member is not a failure.
        return True
    except OSError:
        return False
    return True


def _stop(process: subprocess.Popen[bytes]) -> bool:
    group_ok = True
    if sys.platform != "win32":
        # Reap an already exited shell before signalling its group. Darwin can
        # reject signals to a group whose only remaining member is a zombie.
        process.poll()
        group_ok = _kill_group(process.pid)
    elif process.poll() is None:
        # Best effort only: Windows cannot enumerate children of an exited shell
        # this way. Closing our read handles still bounds capture and return time.
        system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
        taskkill = system_root / "System32" / "taskkill.exe"
        if taskkill.is_absolute():
            with suppress(OSError, subprocess.TimeoutExpired):
                subprocess.run(
                    [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=_CLEANUP_SECONDS, check=False,
                )
    direct_ok = True
    try:
        if process.poll() is None:
            process.kill()
    except OSError:
        direct_ok = False
    # A failed group signal must never prevent the direct child from being reaped.
    try:
        process.wait(timeout=_CLEANUP_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if sys.platform != "win32" and not group_ok:
        # One bounded retry after reaping handles an exit racing the first poll.
        # A surviving group that still refuses the signal remains cleanup_failed.
        group_ok = _kill_group(process.pid)
    return direct_ok and group_ok


def run_check_process(
    command: str, *, root: Path, env: dict[str, str], timeout: float,
    stream_limit: int = MAX_STREAM_BYTES,
) -> ProcessOutput:
    """Capture both pipes fairly; the deadline also covers inherited open pipes.

    Limits bound parent-side retained output, not child RSS or OS process creation.
    On a boundary failure all partial child output is discarded. POSIX cleanup
    covers descendants remaining in the new process group. Detached processes and
    Windows descendants after shell exit require an external sandbox/job boundary.
    """
    if (
        isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0
        or type(stream_limit) is not int or not 1 <= stream_limit <= MAX_STREAM_BYTES
    ):
        return ProcessOutput(failure="invalid_limits")
    process: subprocess.Popen[bytes] | None = None
    failure = "execution_failed"
    timed_out = False
    complete = False
    with ExitStack() as readers, ExitStack() as writers:
        try:
            fds = []
            outputs = []
            for _ in range(2):
                read_fd, write_fd = os.pipe()
                readers.callback(os.close, read_fd)
                writers.callback(os.close, write_fd)
                if sys.platform != "win32":
                    os.set_blocking(read_fd, False)
                fds.append(read_fd)
                outputs.append(write_fd)
            deadline = time.monotonic() + timeout
            process = subprocess.Popen(
                command, cwd=root, env=env, shell=True, stdin=subprocess.DEVNULL,
                stdout=outputs[0], stderr=outputs[1], start_new_session=os.name == "posix",
            )
            writers.close()
            result = _capture(process, fds, deadline, stream_limit)
            complete = True
            return result
        except _BoundaryError as exc:
            failure = str(exc)
            timed_out = failure == "timeout"
        except (OSError, ValueError):
            # No command, environment, captured text or arbitrary exception data.
            failure = "execution_failed"
        finally:
            if process is not None and not complete:
                try:
                    if not _stop(process):
                        failure = "cleanup_failed"
                except OSError:
                    failure = "cleanup_failed"
    return ProcessOutput(failure=failure, timed_out=timed_out)
