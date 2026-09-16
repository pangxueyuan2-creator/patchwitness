"""Byte-bounded regular-file input with best-effort replacement detection."""

from __future__ import annotations

import os
import stat
from pathlib import Path


class FileInputError(ValueError):
    """A file cannot be read within the requested input boundary."""


def _file_state(value: os.stat_result) -> tuple[int, int, int, int, int]:
    # Windows path/descriptor ctime can report different creation/change times.
    change_time = value.st_ctime_ns if os.name != "nt" else 0
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, change_time


def read_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    """Read at most the byte budget plus one probe; reject observed identity changes."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise FileInputError(f"{label} must be a regular non-symlink file")
    if before.st_size > max_bytes:
        raise FileInputError(f"{label} exceeds the byte limit (byte budget)")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _file_state(before) != _file_state(opened):
            raise FileInputError(f"{label} changed before reading")
        chunks: list[bytes] = []
        size = 0
        while size <= max_bytes:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > max_bytes:
            raise FileInputError(f"{label} exceeds the byte limit (byte budget)")
        if (
            _file_state(opened) != _file_state(os.fstat(descriptor))
            or _file_state(opened) != _file_state(path.lstat())
            or size != opened.st_size
        ):
            raise FileInputError(f"{label} changed while reading")
        return b"".join(chunks)
    finally:
        os.close(descriptor)
