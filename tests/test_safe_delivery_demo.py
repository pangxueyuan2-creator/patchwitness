"""Test the fixed demo's identity boundary without importing its nine producers."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from test_safe_delivery_sources import git, revision
from test_safe_delivery_sources import repo as repo


@pytest.fixture
def demo(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("demo_safe_delivery")


def test_clean_identity_is_stable_and_matches_commit(repo: Path, demo: ModuleType) -> None:
    identity = demo.candidate_identity(repo)
    assert identity == demo.candidate_identity(repo)
    assert identity["head"] == revision(repo)
    assert len(identity["index_sha256"]) == len(identity["config_sha256"]) == 64


@pytest.mark.parametrize("kind", ["worktree", "staged", "untracked", "deleted", "replacement"])
def test_dirty_candidate_cannot_receive_exact_head_identity(
    repo: Path,
    demo: ModuleType,
    kind: str,
) -> None:
    if kind in {"worktree", "staged"}:
        (repo / "tracked.py").write_bytes(b"different from committed content\n")
        if kind == "staged":
            git(repo, "add", "tracked.py")
    elif kind == "untracked":
        (repo / "unexpected.py").write_bytes(b"new file\n")
    elif kind == "deleted":
        (repo / "tracked.py").unlink()
    else:
        git(repo, "rm", "tracked.py")
        (repo / "tracked.py").write_bytes(b"replacement after staged deletion\n")
    with pytest.raises(ValueError, match="not clean"):
        demo.candidate_identity(repo)


def test_branch_move_at_same_commit_changes_identity(repo: Path, demo: ModuleType) -> None:
    before = demo.candidate_identity(repo)
    git(repo, "switch", "-c", "different-branch")
    after = demo.candidate_identity(repo)
    assert after["head"] == before["head"]
    assert after["branch"] != before["branch"]
    assert after != before


def test_configuration_change_at_same_commit_changes_identity(repo: Path, demo: ModuleType) -> None:
    before = demo.candidate_identity(repo)
    git(repo, "config", "safe-delivery-fixture.changed", "true")
    after = demo.candidate_identity(repo)
    assert after["head"] == before["head"]
    assert after["index_sha256"] == before["index_sha256"]
    assert after["config_sha256"] != before["config_sha256"]


def test_committed_index_and_head_drift_changes_identity(repo: Path, demo: ModuleType) -> None:
    before = demo.candidate_identity(repo)
    (repo / "tracked.py").write_bytes(b"committed replacement\n")
    git(repo, "add", "tracked.py")
    git(repo, "commit", "-qm", "change both commit and index")
    after = demo.candidate_identity(repo)
    assert after["head"] != before["head"]
    assert after["index_sha256"] != before["index_sha256"]


def test_empty_commit_drift_changes_identity(repo: Path, demo: ModuleType) -> None:
    before = demo.candidate_identity(repo)
    git(repo, "commit", "--allow-empty", "-qm", "same content new head")
    after = demo.candidate_identity(repo)
    assert after["head"] != before["head"]
    assert after["index_sha256"] == before["index_sha256"]


def test_detached_head_fails_closed(repo: Path, demo: ModuleType) -> None:
    git(repo, "switch", "--detach", revision(repo))
    with pytest.raises(subprocess.CalledProcessError):
        demo.candidate_identity(repo)
