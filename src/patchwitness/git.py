"""Minimal, dependency-free Git adapter."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
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
    cached_status_result = _run(
        root,
        "diff",
        "--cached",
        "--name-status",
        "-z",
        "--find-renames",
        "--no-ext-diff",
        base_revision,
        "--",
    )
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
    cached_statuses: dict[str, tuple[str, str | None]] = {}
    for dest, status, previous in _parse_name_status_z(cached_status_result.stdout):
        cached_statuses[dest] = (status, previous)
    worktree_statuses: dict[str, tuple[str, str | None]] = {}
    for dest, status, previous in _parse_name_status_z(status_result.stdout):
        worktree_statuses[dest] = (status, previous)
    # The index participates in what will be committed even when the working
    # tree looks clean. The working tree takes precedence for shared paths.
    statuses = {**cached_statuses, **worktree_statuses}

    cached_numstat_result = _run(
        root,
        "diff",
        "--cached",
        "--numstat",
        "-z",
        "--find-renames",
        "--no-ext-diff",
        base_revision,
        "--",
    )
    numstat_result = _run(
        root, "diff", "--numstat", "-z", "--find-renames", "--no-ext-diff", base_revision, "--"
    )
    stats = _parse_numstat_z(cached_numstat_result.stdout)
    stats.update(_parse_numstat_z(numstat_result.stdout))

    untracked_after_paths: list[str] = []
    untracked_result = _run(root, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in untracked_result.stdout.split("\0"):
        if not raw_path:
            continue
        path = raw_path.replace("\\", "/")
        if path.startswith(".patchwitness/evidence/"):
            continue
        if path in cached_statuses or path in worktree_statuses:
            # A staged deletion with an untracked replacement must stay a
            # deletion: the commit records the index state, not the
            # replacement file that would remain untracked.
            continue
        statuses[path] = ("A", None)
        untracked_after_paths.append(path)
        full_path = root / path
        binary = _is_binary(full_path)
        lines = 0 if binary else _count_lines(full_path)
        stats[path] = (lines, 0, binary)

    before_paths = [
        previous_path or path
        for path, (status, previous_path) in statuses.items()
        if not status.startswith("A")
    ]
    before_hashes = _batch_git_blob_sha256(root, base_revision, before_paths)
    worktree_after_paths = [
        path
        for path, (status, _previous_path) in worktree_statuses.items()
        if not status.startswith("D")
    ]
    after_hashes = _parallel_file_sha256(root, worktree_after_paths)
    # Untracked additions are part of the reported change set too. Hash them
    # so downstream content-sensitive checks (notably secret scanning) inspect
    # brand-new files instead of skipping them because after_sha256 is absent.
    after_hashes.update(_parallel_file_sha256(root, untracked_after_paths))
    # For every staged path the commit records the INDEX blob, even when the
    # working tree holds different bytes for the same path. Prefer ":path" so
    # the evidence hash matches what a commit would actually record.
    index_after_paths = [
        path for path in cached_statuses if not cached_statuses[path][0].startswith("D")
    ]
    after_hashes.update(_batch_git_blob_sha256(root, "", index_after_paths))
    # Files marked assume-unchanged or skip-worktree are invisible to both
    # diffs above. Their content can still differ from the base; surface such
    # edits instead of letting the gate pass over them silently.
    flagged_result = _run(root, "ls-files", "-v", "-z", check=False)
    for entry in flagged_result.stdout.split("\0"):
        if not entry or entry[0] == "H":
            # "H" is the normal cached state; lowercase tags mark
            # assume-unchanged, "S" marks skip-worktree, and the remaining
            # uppercase tags mark unmerged index states.
            continue
        path = entry[2:].replace("\\", "/")
        if not path or path in statuses:
            continue
        current_hash = _file_sha256(root, path)
        if current_hash is None:
            continue
        base_hash = _batch_git_blob_sha256(root, base_revision, [path]).get(path)
        if current_hash == base_hash:
            continue
        full_path = root / path
        binary = _is_binary(full_path)
        statuses[path] = ("M", None)
        stats[path] = (0 if binary else _count_lines(full_path), 0, binary)
        before_hashes[path] = base_hash
        after_hashes[path] = current_hash
    changes: list[FileChange] = []
    for path in sorted(statuses):
        additions, deletions, binary = stats.get(path, (0, 0, False))
        status, previous_path = statuses[path]
        before = before_hashes.get(previous_path or path)
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
                previous_path=previous_path,
            )
        )
    return tuple(changes)


def verification_conflicts(root: Path, base_revision: str) -> tuple[str, ...]:
    """Find index changes that checks would observe differently in the worktree.

    Evidence records index blobs for paths changed in the index relative to
    the base. Both live checks and clean-room materialization read worktree
    content, so divergent versions of those paths cannot share check evidence.
    Git's comparison preserves configured line-ending semantics. Masked index
    paths are rejected conservatively because Git may omit them.
    """
    staged = {
        path: status
        for path, status, _previous in _parse_name_status_z(
            _run(
                root, "diff", "--cached", "--name-status", "-z", "--no-renames",
                "--no-ext-diff", base_revision, "--",
            ).stdout
        )
    }
    if not staged:
        return ()
    unstaged = {
        path.replace("\\", "/")
        for path in _run(
            root, "diff", "--name-only", "-z", "--no-ext-diff", "--no-textconv",
            "--ignore-submodules=none", "--",
        ).stdout.split("\0")
    }
    conflicts = set(staged) & unstaged
    # A staged deletion leaves its replacement untracked, outside the index diff.
    for path, status in staged.items():
        if status.startswith("D") and os.path.lexists(root / path):
            conflicts.add(path)
    for entry in _run(root, "ls-files", "-v", "-z").stdout.split("\0"):
        if len(entry) >= 3 and (entry[0].islower() or entry[0] == "S"):
            path = entry[2:].replace("\\", "/")
            if path in staged:
                conflicts.add(path)
    return tuple(sorted(conflicts))


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
    """Parse literal NUL-delimited paths; never interpret display-only rename notation."""
    if not payload:
        return {}
    if not payload.endswith("\0"):
        raise GitError("unterminated NUL-delimited numstat output")
    tokens = payload[:-1].split("\0")
    stats: dict[str, tuple[int, int, bool]] = {}
    index = 0
    while index < len(tokens):
        # Only the first two tabs are separators. A filename may contain more.
        parts = tokens[index].split("\t", 2)
        if len(parts) != 3:
            raise GitError("malformed numstat record")
        added_text, deleted_text, path = parts
        index += 1
        if not path:
            # Rename/copy records are counts\t\0old\0new\0.
            if index + 1 >= len(tokens) or not tokens[index] or not tokens[index + 1]:
                raise GitError("incomplete numstat rename record")
            path = tokens[index + 1]
            index += 2
        binary = added_text == deleted_text == "-"
        if not binary and not (
            added_text.isascii() and added_text.isdecimal()
            and deleted_text.isascii() and deleted_text.isdecimal()
        ):
            raise GitError("invalid numstat line counts")
        stats[path.replace("\\", "/")] = (
            0 if binary else int(added_text),
            0 if binary else int(deleted_text),
            binary,
        )
    return stats


def is_dirty(root: Path) -> bool:
    return bool(_run(root, "status", "--porcelain").stdout.strip())


def _run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )
    # Text-mode subprocess pipes normalize CR/CRLF even inside a literal -z
    # filename. Decode explicitly to preserve Git's record bytes.
    decoded = subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )
    if check and result.returncode != 0:
        command = "git " + " ".join(args)
        raise GitError(f"{command} failed: {decoded.stderr.strip()}")
    return decoded


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
            query = f"{revision}:{path}"
            if "\n" in query or "\r" in query:
                # Resolve exceptional paths as a single argv value, then send
                # only the object ID through the newline-delimited protocol.
                resolved = _run(root, "rev-parse", "--verify", "--end-of-options", query,
                                check=False)
                if resolved.returncode != 0:
                    output[path] = None
                    continue
                query = resolved.stdout.strip()
            # Alternate requests and responses: writing every request first can
            # deadlock when both the input and output pipes fill.
            process.stdin.write(query.encode("utf-8") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline()
            if header.endswith(b" missing\n"):
                output[path] = None
                continue
            parts = header.rstrip(b"\n").rsplit(b" ", 2)
            if len(parts) != 3 or not parts[2].isdigit():
                raise GitError("malformed cat-file batch header")
            remaining = int(parts[2])
            digest = hashlib.sha256()
            while remaining:
                chunk = process.stdout.read(min(remaining, 65_536))
                if not chunk:
                    raise GitError("truncated cat-file batch content")
                remaining -= len(chunk)
                if parts[1] == b"blob":
                    digest.update(chunk)
            if process.stdout.read(1) != b"\n":
                raise GitError("invalid cat-file batch terminator")
            # Non-blob bodies must still be consumed to keep the next record aligned.
            output[path] = digest.hexdigest() if parts[1] == b"blob" else None
        process.stdin.close()
        if process.wait(timeout=30) != 0:
            raise GitError("cat-file batch process failed")
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError("cat-file batch could not complete") from exc
    finally:
        with suppress(OSError):
            process.stdin.close()
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait()
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
        with path.open("rb") as handle:
            sample = handle.read(8_192)
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
