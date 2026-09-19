"""Disposable Git worktrees for verifier execution with hooks disabled."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path


class CleanRoomError(RuntimeError):
    """Raised when a clean verifier worktree cannot be materialized."""


@contextmanager
def clean_room(root: Path, base_revision: str) -> Iterator[Path]:
    _require_unmasked_index(root)
    parent = Path(tempfile.mkdtemp(prefix="patchwitness-cleanroom-"))
    worktree = parent / "repo"
    empty_hooks = parent / "hooks-disabled"
    empty_hooks.mkdir()
    added = False
    try:
        add = _git(
            root,
            "-c",
            f"core.hooksPath={empty_hooks}",
            "worktree",
            "add",
            "--detach",
            "--force",
            str(worktree),
            base_revision,
        )
        if add.returncode != 0:
            raise CleanRoomError(f"cannot create clean worktree: {add.stderr.strip()}")
        added = True
        # Pair canonical diff prefixes with apply -p1; user display settings must
        # never redirect a patch to a different path inside the verifier worktree.
        patch = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--no-color",
                "--binary",
                "--full-index",
                "--no-ext-diff",
                "--no-textconv",
                "--src-prefix=a/",
                "--dst-prefix=b/",
                base_revision,
                "--",
            ],
            capture_output=True,
            check=False,
        )
        if patch.returncode != 0:
            detail = patch.stderr.decode("utf-8", errors="replace").strip()
            raise CleanRoomError(f"cannot capture repository patch: {detail}")
        if patch.stdout:
            applied = subprocess.run(
                ["git", "-C", str(worktree), "apply", "-p1", "--binary", "--whitespace=nowarn"],
                input=patch.stdout,
                capture_output=True,
                check=False,
            )
            if applied.returncode != 0:
                detail = applied.stderr.decode("utf-8", errors="replace").strip()
                raise CleanRoomError(f"cannot apply patch in clean worktree: {detail}")
        _copy_untracked(root, worktree)
        _require_unmasked_index(root)
        yield worktree
    finally:
        if added:
            _git(root, "worktree", "remove", "--force", str(worktree))
            _git(root, "worktree", "prune")
        with suppress(OSError):
            shutil.rmtree(parent)


def _copy_untracked(root: Path, worktree: Path) -> None:
    result = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if result.returncode != 0:
        raise CleanRoomError(f"cannot enumerate untracked files: {result.stderr.strip()}")
    repository_root = root.resolve(strict=True)
    worktree_root = worktree.resolve(strict=True)
    for raw in _nul_records(result.stdout, "untracked"):
        if raw.startswith(".patchwitness/evidence/"):
            continue
        source = root / raw
        target = worktree / raw
        if source.is_symlink():
            raise CleanRoomError(f"untracked symlinks are not accepted in clean room: {raw}")
        try:
            resolved_source = source.resolve(strict=True)
            resolved_source.relative_to(repository_root)
        except (OSError, ValueError):
            detail = "untracked path resolves outside repository and is not accepted in clean room"
            raise CleanRoomError(f"{detail}: {raw}") from None
        try:
            resolved_parent = target.parent.resolve(strict=False)
            resolved_parent.relative_to(worktree_root)
        except (OSError, ValueError):
            detail = "untracked target resolves outside clean room and is not accepted"
            raise CleanRoomError(f"{detail}: {raw}") from None
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            raise CleanRoomError(f"untracked target symlinks are not accepted in clean room: {raw}")
        try:
            resolved_target = target.resolve(strict=False)
            resolved_target.relative_to(worktree_root)
        except (OSError, ValueError):
            detail = "untracked target resolves outside clean room and is not accepted"
            raise CleanRoomError(f"{detail}: {raw}") from None
        if not resolved_source.is_file():
            raise CleanRoomError(f"untracked path is not a regular file: {raw!r}")
        try:
            shutil.copy2(resolved_source, target)
        except OSError as exc:
            raise CleanRoomError(f"cannot copy untracked file: {raw!r}") from exc


def _nul_records(payload: str, label: str) -> list[str]:
    """Validate the complete listing before a caller starts materializing it."""
    if not payload:
        return []
    if not payload.endswith("\0"):
        raise CleanRoomError(f"incomplete {label} listing")
    records = payload[:-1].split("\0")
    if any(not record for record in records):
        raise CleanRoomError(f"invalid {label} listing")
    return records


def _require_unmasked_index(root: Path) -> None:
    """Do not test base bytes when index flags may hide worktree content.

    Reject even unchanged masked entries: a diff cannot establish that these
    paths represent the candidate. Never clear flags or edit the caller's index.
    Sparse checkouts with skip-worktree entries need a full verification checkout.
    """
    result = _git(root, "ls-files", "--cached", "-v", "-z")
    if result.returncode != 0:
        raise CleanRoomError(f"cannot inspect clean-room index: {result.stderr.strip()}")
    for entry in _nul_records(result.stdout, "index"):
        if len(entry) < 3 or entry[1] != " " or entry[0] not in "HSMRCK?Uhsmrcku":
            raise CleanRoomError("invalid index listing")
        if entry[0].islower() or entry[0] == "S":
            raise CleanRoomError(
                "clean-room checks cannot use assume-unchanged or skip-worktree "
                f"index entries: {entry[2:]!r}; clear the flags or use a full checkout"
            )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # Text-mode universal-newline conversion would alias distinct Git paths.
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise CleanRoomError("cannot run Git for clean-room materialization") from exc
    try:
        # Other Git stdout may include commit subjects, not filenames.
        errors = "strict" if args[:1] == ("ls-files",) else "replace"
        stdout = result.stdout.decode("utf-8", errors=errors)
    except UnicodeDecodeError as exc:
        raise CleanRoomError("clean-room Git output must contain UTF-8 paths") from exc
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        stdout=stdout,
        stderr=result.stderr.decode("utf-8", errors="replace"),
    )
