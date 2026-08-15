"""Minimal, dependency-free Git adapter."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from patchwitness.models import FileChange


class GitError(RuntimeError):
    """Raised when repository facts cannot be collected."""


_UNTRACKED_NOISE_PARTS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".eggs",
        ".tasktopr",
        "node_modules",
        ".venv",
        "venv",
    }
)
_UNTRACKED_NOISE_SUFFIXES = (".pyc", ".pyo", ".pyd")


def is_untracked_noise(path: str) -> bool:
    """Return True for local caches and tool evidence that are not review surface.

    Untracked inclusion exists to catch sneaky new files. Bytecode, virtualenvs,
    and per-run evidence directories are not that surface.
    """

    normalized = path.replace("\\", "/")
    if normalized.startswith((".patchwitness/evidence/", ".patchwitness/cache/")):
        return True
    if normalized.endswith(_UNTRACKED_NOISE_SUFFIXES):
        return True
    return any(part in _UNTRACKED_NOISE_PARTS for part in normalized.split("/"))


def find_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    result = _run(cwd, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        raise GitError(f"not inside a Git repository: {cwd}")
    return Path(result.stdout.strip()).resolve()


def resolve_revision(root: Path, revision: str) -> str:
    result = _run(root, "rev-parse", "--verify", f"{revision}^{{commit}}", check=False)
    if result.returncode != 0:
        raise GitError(f"cannot resolve base revision {revision!r}: {result.stderr.strip()}")
    return result.stdout.strip()


def head_revision(root: Path) -> str | None:
    result = _run(root, "rev-parse", "--verify", "HEAD", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def branch_name(root: Path) -> str | None:
    result = _run(root, "branch", "--show-current", check=False)
    value = result.stdout.strip()
    return value or None


def remote_url(root: Path) -> str | None:
    result = _run(root, "remote", "get-url", "origin", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def load_file_at_revision(root: Path, revision: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{relative_path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"cannot load {relative_path!r} from {revision}: {detail}")
    return result.stdout


def collect_changes(root: Path, base_revision: str) -> tuple[FileChange, ...]:
    status_result = _run(
        root,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--no-ext-diff",
        base_revision,
        "--",
    )
    statuses: dict[str, tuple[str, str | None]] = {}
    for dest, status, previous in _parse_name_status_z(status_result.stdout):
        statuses[dest] = (status, previous)

    numstat_result = _run(
        root, "diff", "--numstat", "-z", "--find-renames", "--no-ext-diff", base_revision, "--"
    )
    stats = _parse_numstat_z(numstat_result.stdout)

    untracked_result = _run(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in untracked_result.stdout.split("\0"):
        if not raw_path:
            continue
        path = raw_path.replace("\\", "/")
        if is_untracked_noise(path):
            continue
        statuses[path] = ("A", None)
        full_path = root / path
        binary = _is_binary(full_path)
        lines = 0 if binary else _count_lines(full_path)
        stats[path] = (lines, 0, binary)

    before_keys: list[str] = []
    for dest, (status, previous) in statuses.items():
        if status.startswith("A"):
            continue
        before_keys.append(previous if previous else dest)
    before_hashes = _batch_git_blob_sha256(root, base_revision, list(dict.fromkeys(before_keys)))
    after_paths = [path for path, (status, _) in statuses.items() if not status.startswith("D")]
    after_hashes = _parallel_file_sha256(root, after_paths)
    changes: list[FileChange] = []
    for path in sorted(statuses):
        status, previous = statuses[path]
        additions, deletions, binary = stats.get(path, (0, 0, False))
        before_key = previous if previous else path
        before = None if status.startswith("A") else before_hashes.get(before_key)
        after = after_hashes.get(path)
        changes.append(
            FileChange(
                path=path,
                status=status,
                additions=additions,
                deletions=deletions,
                binary=binary,
                before_sha256=before,
                after_sha256=after,
                previous_path=previous,
            )
        )
    return tuple(changes)


def _parse_name_status_z(payload: str) -> list[tuple[str, str, str | None]]:
    """Parse `git diff --name-status -z`. Rename/copy is STATUS\\0old\\0new\\0."""

    tokens = [token for token in payload.split("\0") if token != ""]
    records: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        letter = status[:1] if status else ""
        if letter in {"R", "C"}:
            if index + 2 >= len(tokens):
                break
            previous = tokens[index + 1].replace("\\", "/")
            dest = tokens[index + 2].replace("\\", "/")
            records.append((dest, status, previous))
            index += 3
            continue
        if index + 1 >= len(tokens):
            break
        dest = tokens[index + 1].replace("\\", "/")
        records.append((dest, status, None))
        index += 2
    return records


def _parse_numstat_z(payload: str) -> dict[str, tuple[int, int, bool]]:
    """Parse `git diff --numstat -z`. Rename is added\\tdeleted\\0old\\0new\\0."""

    tokens = [token for token in payload.split("\0") if token != ""]
    stats: dict[str, tuple[int, int, bool]] = {}
    index = 0
    while index < len(tokens):
        parts = tokens[index].split("\t")
        if len(parts) == 3:
            added_text, deleted_text, path = parts
            dest = _normalize_rename_path(path)
            binary = added_text == "-" or deleted_text == "-"
            stats[dest] = (
                0 if binary else int(added_text),
                0 if binary else int(deleted_text),
                binary,
            )
            index += 1
            continue
        if len(parts) == 2 and index + 2 < len(tokens):
            added_text, deleted_text = parts
            dest = tokens[index + 2].replace("\\", "/")
            binary = added_text == "-" or deleted_text == "-"
            stats[dest] = (
                0 if binary else int(added_text),
                0 if binary else int(deleted_text),
                binary,
            )
            index += 3
            continue
        index += 1
    return stats


def is_dirty(root: Path) -> bool:
    return bool(_run(root, "status", "--porcelain").stdout.strip())


def _run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        command = "git " + " ".join(args)
        raise GitError(f"{command} failed: {result.stderr.strip()}")
    return result


def _normalize_rename_path(path: str) -> str:
    if " => " not in path:
        return path.replace("\\", "/")
    if "{" in path and "}" in path:
        prefix, rest = path.split("{", 1)
        middle, suffix = rest.split("}", 1)
        _old, new = middle.split(" => ", 1)
        return f"{prefix}{new}{suffix}".replace("\\", "/")
    return path.rsplit(" => ", 1)[-1].replace("\\", "/")


def safe_regular_file(root: Path, relative_path: str) -> Path | None:
    """Return a repository-contained regular file without following symlinks.

    Git paths are repository-relative, but untracked paths can still be symlinks.
    Hashing or scanning such a path must not read data outside the repository.
    """
    try:
        repository = root.resolve(strict=True)
        candidate = Path(os.path.abspath(root / relative_path))
        candidate.relative_to(repository)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repository)
        if resolved != candidate or not stat.S_ISREG(resolved.stat().st_mode):
            return None
    except (OSError, ValueError):
        return None
    return resolved


def _file_sha256(root: Path, relative_path: str) -> str | None:
    path = safe_regular_file(root, relative_path)
    if path is None:
        return None
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return None
            digest = hashlib.file_digest(handle, "sha256")
    except OSError:
        return None
    return digest.hexdigest()


def _batch_git_blob_sha256(root: Path, revision: str, paths: list[str]) -> dict[str, str | None]:
    if not paths:
        return {}
    process = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    output: dict[str, str | None] = {}
    try:
        for path in paths:
            process.stdin.write(f"{revision}:{path}\n".encode())
        process.stdin.flush()
        process.stdin.close()
        for path in paths:
            header = process.stdout.readline().decode("utf-8", errors="replace").strip()
            if header.endswith(" missing"):
                output[path] = None
                continue
            parts = header.rsplit(" ", 2)
            if len(parts) != 3 or parts[1] != "blob":
                output[path] = None
                continue
            size = int(parts[2])
            content = process.stdout.read(size)
            process.stdout.read(1)
            output[path] = hashlib.sha256(content).hexdigest()
    finally:
        process.wait(timeout=30)
    return output


def _parallel_file_sha256(root: Path, paths: list[str]) -> dict[str, str | None]:
    if not paths:
        return {}
    workers = min(8, max(1, len(paths)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="patchwitness-hash") as pool:
        values = pool.map(lambda path: _file_sha256(root, path), paths)
        return dict(zip(paths, values, strict=True))


def _is_binary(path: Path) -> bool:
    try:
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            return False
        sample = path.read_bytes()[:8_192]
    except OSError:
        return False
    return b"\0" in sample


def _count_lines(path: Path) -> int:
    try:
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            return 0
        raw = path.read_bytes()
    except OSError:
        return 0
    if not raw:
        return 0
    return raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
