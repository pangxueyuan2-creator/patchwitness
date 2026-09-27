"""Use literal Git paths, not the human-readable diff rename notation."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from patchwitness.git import GitError, _batch_git_blob_sha256, _parse_numstat_z, collect_changes
from patchwitness.models import Contract
from patchwitness.policy import evaluate_policy


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        encoding="utf-8", timeout=30,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "core.autocrlf", "false")
    git(tmp_path, "commit", "--allow-empty", "-qm", "base")
    return tmp_path


@pytest.mark.parametrize("path", ["a\tb.py", "old => new.py", "src/{old => new}.py",
                                 " leading.py", "trailing.py ", "测试.py", "line\nbreak.py"])
def test_numstat_preserves_literal_paths(path: str) -> None:
    assert _parse_numstat_z(f"4\t2\t{path}\0") == {path: (4, 2, False)}


@pytest.mark.parametrize("payload", ["1\t2\t\0old\0", "1\t2\0", "-\t1\tfile\0",
                                    "-1\t2\tfile\0", "1\t2\tfile", "1\t2\t\0\0new\0"])
def test_truncated_or_invalid_numstat_fails_closed(payload: str) -> None:
    with pytest.raises(GitError):
        _parse_numstat_z(payload)


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot represent these literal filenames")
@pytest.mark.parametrize("path", ["a\tb.py", "old => new.py", "src/{old => new}.py",
                                 " leading.py", "trailing.py ", "line\nbreak.py", "carriage\r.py"])
def test_real_diff_keeps_counts_and_content_identity(repo: Path, path: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"before\n")
    git(repo, "add", "--", path)
    git(repo, "commit", "-qm", "track file")
    target.write_bytes(b"after\nsecond\n")
    changes = collect_changes(repo, "HEAD")
    assert len(changes) == 1
    change = changes[0]
    assert change.path == path
    assert (change.additions, change.deletions) == (2, 1)
    assert change.before_sha256 == hashlib.sha256(b"before\n").hexdigest()
    assert change.after_sha256 == hashlib.sha256(b"after\nsecond\n").hexdigest()
    findings = evaluate_policy(Contract(max_lines=1, require_tests=False), changes)
    assert any(finding.rule_id == "PW011" for finding in findings)


@pytest.mark.skipif(os.name == "nt", reason="Windows normalizes trailing filename spaces")
@pytest.mark.parametrize("path", [" leading.py", "trailing.py "])
@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_flagged_whitespace_paths_are_not_hidden(repo: Path, path: str, flag: str) -> None:
    (repo / path).write_bytes(b"before\n")
    git(repo, "add", "--", path)
    git(repo, "commit", "-qm", "track file")
    git(repo, "update-index", flag, "--", path)
    (repo / path).write_bytes(b"after\n")
    changes = collect_changes(repo, "HEAD")
    assert len(changes) == 1 and changes[0].path == path
    assert changes[0].before_sha256 == hashlib.sha256(b"before\n").hexdigest()
    assert changes[0].after_sha256 == hashlib.sha256(b"after\n").hexdigest()


def test_non_blob_batch_result_does_not_desynchronize_next_file(repo: Path) -> None:
    (repo / "folder").mkdir()
    (repo / "folder" / "file.py").write_bytes(b"content\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "track tree")
    result = _batch_git_blob_sha256(repo, "HEAD", ["folder", "missing", "folder/file.py"])
    assert result == {"folder": None, "missing": None,
                      "folder/file.py": hashlib.sha256(b"content\n").hexdigest()}


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot represent newline filenames")
@pytest.mark.parametrize("path", ["line\nbreak.py", "carriage\r.py"])
def test_index_hashes_support_line_breaks(repo: Path, path: str) -> None:
    (repo / path).write_bytes(b"staged\n")
    git(repo, "add", "--", path)
    assert _batch_git_blob_sha256(repo, "", ["missing\nfile", path]) == {
        "missing\nfile": None, path: hashlib.sha256(b"staged\n").hexdigest(),
    }
