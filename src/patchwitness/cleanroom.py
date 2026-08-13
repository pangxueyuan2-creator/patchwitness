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
                ["git", "-C", str(worktree), "apply", "--binary", "--whitespace=nowarn"],
                input=patch.stdout,
                capture_output=True,
                check=False,
            )
            if applied.returncode != 0:
                detail = applied.stderr.decode("utf-8", errors="replace").strip()
                raise CleanRoomError(f"cannot apply patch in clean worktree: {detail}")
        _copy_untracked(root, worktree)
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
    for raw in result.stdout.split("\0"):
        if not raw or raw.startswith(".patchwitness/evidence/"):
            continue
        source = root / raw
        target = worktree / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            raise CleanRoomError(f"untracked symlinks are not accepted in clean room: {raw}")
        if source.is_file():
            shutil.copy2(source, target)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
