"""Minimal, dependency-free Git adapter."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from patchwitness.models import FileChange


class GitError(RuntimeError):
    """Raised when repository facts cannot be collected."""


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
        root, "diff", "--name-status", "--find-renames", "--no-ext-diff", base_revision, "--"
    )
    statuses: dict[str, str] = {}
    for line in status_result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0]
        path = parts[-1].replace("\\", "/")
        statuses[path] = code

    numstat_result = _run(root, "diff", "--numstat", "--no-ext-diff", base_revision, "--")
    stats: dict[str, tuple[int, int, bool]] = {}
    for line in numstat_result.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added_text, deleted_text, path = parts
        path = _normalize_rename_path(path)
        binary = added_text == "-" or deleted_text == "-"
        stats[path] = (
            0 if binary else int(added_text),
            0 if binary else int(deleted_text),
            binary,
        )

    untracked_result = _run(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in untracked_result.stdout.split("\0"):
        if not raw_path:
            continue
        path = raw_path.replace("\\", "/")
        if path.startswith(".patchwitness/evidence/"):
            continue
        statuses[path] = "A"
        full_path = root / path
        binary = _is_binary(full_path)
        lines = 0 if binary else _count_lines(full_path)
        stats[path] = (lines, 0, binary)

    changes: list[FileChange] = []
    for path in sorted(statuses):
        additions, deletions, binary = stats.get(path, (0, 0, False))
        status = statuses[path]
        before = None if status.startswith("A") else _git_blob_sha256(root, base_revision, path)
        after = None if status.startswith("D") else _file_sha256(root / path)
        changes.append(
            FileChange(
                path=path,
                status=status,
                additions=additions,
                deletions=deletions,
                binary=binary,
                before_sha256=before,
                after_sha256=after,
            )
        )
    return tuple(changes)


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


def _file_sha256(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256")
    except OSError:
        return None
    return digest.hexdigest()


def _git_blob_sha256(root: Path, revision: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def _is_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:8_192]
    except OSError:
        return False
    return b"\0" in sample


def _count_lines(path: Path) -> int:
    try:
        raw = path.read_bytes()
    except OSError:
        return 0
    if not raw:
        return 0
    return raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
