"""Regression tests for the bytes actually presented to clean-room checks."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

import patchwitness.cleanroom as cleanroom_module
from patchwitness.cleanroom import CleanRoomError, _copy_untracked, clean_room
from patchwitness.cli import main
from patchwitness.evidence import capture_evidence, verify_evidence
from patchwitness.models import CheckSpec, Contract, GateStatus


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True
    ).stdout


def repository(root: Path) -> Path:
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "tests@patchwitness.dev")
    git(root, "config", "user.name", "PatchWitness Tests")
    (root / "app.py").write_text('print("BASE PASSES")\n', encoding="utf-8")
    (root / ".gitattributes").write_text("app.py diff=constant\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    return root


def contract() -> Contract:
    return Contract(
        require_tests=False,
        checks=(CheckSpec(id="runtime", command=f'"{sys.executable}" app.py'),),
    )


def enable_flags(root: Path, flags: tuple[str, ...]) -> None:
    for flag in flags:
        git(root, "update-index", flag, "app.py")


MASKS = [
    pytest.param(("--assume-unchanged",), id="assume-unchanged"),
    pytest.param(("--skip-worktree",), id="skip-worktree"),
    pytest.param(("--assume-unchanged", "--skip-worktree"), id="both"),
]


@pytest.mark.parametrize("flags", MASKS)
@pytest.mark.parametrize("state", ["modified", "missing", "unchanged"])
def test_masked_index_is_rejected_without_changing_source(
    tmp_path: Path, flags: tuple[str, ...], state: str
) -> None:
    root = repository(tmp_path / "repo")
    enable_flags(root, flags)
    if state == "modified":
        (root / "app.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    elif state == "missing":
        (root / "app.py").unlink()
    index = root / ".git" / "index"
    original_index = index.read_bytes()
    original_worktrees = git(root, "worktree", "list", "--porcelain")

    with (
        pytest.raises(CleanRoomError, match="assume-unchanged|skip-worktree"),
        clean_room(root, "HEAD"),
    ):
        pytest.fail("masked source must not yield an unverifiable check workspace")

    assert index.read_bytes() == original_index
    assert git(root, "worktree", "list", "--porcelain") == original_worktrees


@pytest.mark.parametrize("flags", MASKS)
def test_capture_cannot_report_passing_old_code_for_masked_candidate(
    tmp_path: Path, flags: tuple[str, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "repo")
    enable_flags(root, flags)
    (root / "app.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    calls: list[object] = []

    def forbidden_checks(*args: object, **kwargs: object) -> tuple[()]:
        calls.append(args)
        return ()

    monkeypatch.setattr("patchwitness.evidence.run_checks", forbidden_checks)
    with pytest.raises(CleanRoomError, match="assume-unchanged|skip-worktree"):
        capture_evidence(root, contract(), clean_room_checks=True)
    assert not calls


@pytest.mark.parametrize("flags", MASKS)
def test_live_checks_still_observe_masked_candidate(tmp_path: Path, flags: tuple[str, ...]) -> None:
    root = repository(tmp_path / "repo")
    enable_flags(root, flags)
    (root / "app.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    pack = capture_evidence(root, contract(), clean_room_checks=False)
    assert pack.status == GateStatus.FAIL
    assert pack.checks[0]["exit_code"] == 7


@pytest.mark.parametrize("flags", MASKS)
def test_cli_masked_clean_room_returns_error_without_receipt(
    tmp_path: Path, flags: tuple[str, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "repo")
    enable_flags(root, flags)
    (root / "app.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    (root / ".patchwitness.toml").write_text(
        'version = 1\nid = "fidelity"\n[policy]\nrequire_tests = false\n', encoding="utf-8"
    )
    monkeypatch.chdir(root)
    assert main(["gate", "--clean-room", "--output", "receipt.json"]) == 2
    assert not (root / "receipt.json").exists()


def test_no_checks_does_not_require_clean_room_materialization(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    enable_flags(root, ("--assume-unchanged",))
    (root / "app.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
    pack = capture_evidence(
        root, Contract(require_tests=False), execute_checks=False, clean_room_checks=True
    )
    assert pack.status == GateStatus.PASS
    assert not pack.checks


@pytest.mark.parametrize("candidate", ['print("CANDIDATE")\n', "raise SystemExit(7)\n"])
def test_textconv_cannot_replace_candidate_with_display_text(
    tmp_path: Path, candidate: str
) -> None:
    root = repository(tmp_path / "repo")
    marker = tmp_path / "textconv-ran.txt"
    converter = tmp_path / "textconv.py"
    converter.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('unexpected execution', encoding='utf-8')\n"
        "print('CONSTANT DISPLAY')\n", encoding="utf-8"
    )
    git(root, "config", "diff.constant.textconv", f'"{sys.executable}" "{converter}"')
    (root / "app.py").write_text(candidate, encoding="utf-8")

    with clean_room(root, "HEAD") as verifier:
        assert (verifier / "app.py").read_text(encoding="utf-8") == candidate
    assert not marker.exists()

    pack = verify_evidence(capture_evidence(root, contract(), clean_room_checks=True))
    assert pack.changes[0]["after_sha256"] == hashlib.sha256(candidate.encode()).hexdigest()
    assert pack.checks[0]["exit_code"] == (7 if "SystemExit" in candidate else 0)
    assert pack.status == (GateStatus.FAIL if "SystemExit" in candidate else GateStatus.PASS)
    assert not marker.exists()


@pytest.mark.skipif(os.name == "nt", reason="CR/LF are not Windows filename characters")
@pytest.mark.parametrize("name", ["carriage\rreturn.txt", "windows\r\nline.txt", "new\nline.txt"])
def test_copy_untracked_preserves_literal_cr_lf_paths(tmp_path: Path, name: str) -> None:
    root = repository(tmp_path / "repo")
    worktree = tmp_path / "target"
    worktree.mkdir()
    (root / name).write_bytes(b"literal source\x00\xff\n")
    alias = name.replace("\r\n", "\n").replace("\r", "\n")
    if alias != name:
        (root / alias).write_bytes(b"different file\n")
    _copy_untracked(root, worktree)
    assert (worktree / name).read_bytes() == b"literal source\x00\xff\n"
    if alias != name:
        assert (worktree / alias).read_bytes() == b"different file\n"


@pytest.mark.skipif(os.name == "nt", reason="non-UTF-8 POSIX pathname fixture")
def test_non_utf8_listing_is_rejected_not_aliased(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    worktree = tmp_path / "target"
    worktree.mkdir()
    bad_name = os.fsencode(root) + b"/bad-\xff.txt"
    with open(bad_name, "wb") as handle:
        handle.write(b"original")
    (root / "bad-\ufffd.txt").write_bytes(b"replacement alias")
    with pytest.raises(CleanRoomError, match="UTF-8"):
        _copy_untracked(root, worktree)
    assert not list(worktree.iterdir())


@pytest.mark.parametrize("payload", ["file.txt", "file.txt\0\0", "\0"])
def test_malformed_untracked_listing_is_rejected_before_copy(
    tmp_path: Path, payload: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (root / "file.txt").write_text("data", encoding="utf-8")
    monkeypatch.setattr(
        cleanroom_module, "_git",
        lambda *_: subprocess.CompletedProcess(["git"], 0, stdout=payload, stderr=""),
    )
    with pytest.raises(CleanRoomError, match="listing"):
        _copy_untracked(root, target)
    assert not list(target.iterdir())


def test_nested_untracked_repository_is_not_silently_omitted(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    nested = repository(root / "nested")
    assert nested.is_dir()
    with pytest.raises(CleanRoomError, match="regular file"), clean_room(root, "HEAD"):
        pytest.fail("untracked nested repository was silently omitted")
    assert git(root, "worktree", "list", "--porcelain").count(b"worktree ") == 1


@pytest.mark.parametrize("payload", ["H app.py", "H app.py\0\0", "X app.py\0", "H\0",
                                      "H \0", "H-app.py\0"])
def test_invalid_index_listing_is_rejected_before_setup(
    tmp_path: Path, payload: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(["git"], 0, stdout=payload, stderr="")

    monkeypatch.setattr(cleanroom_module, "_git", fake_git)
    with pytest.raises(CleanRoomError, match="index listing"), clean_room(tmp_path, "HEAD"):
        pytest.fail("malformed listing must not permit setup")
    assert calls == [("ls-files", "--cached", "-v", "-z")]


def test_failed_index_read_is_not_treated_as_an_empty_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cleanroom_module, "_git",
        lambda *_: subprocess.CompletedProcess(["git"], 128, stdout="", stderr="index error"),
    )
    with pytest.raises(CleanRoomError, match="cannot inspect"), clean_room(tmp_path, "HEAD"):
        pytest.fail("unreadable index must not permit setup")


def test_flags_introduced_during_materialization_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "repo")
    original_copy = cleanroom_module._copy_untracked

    def mask_after_copy(source: Path, target: Path) -> None:
        original_copy(source, target)
        enable_flags(source, ("--assume-unchanged",))

    monkeypatch.setattr(cleanroom_module, "_copy_untracked", mask_after_copy)
    with (
        pytest.raises(CleanRoomError, match="assume-unchanged"),
        clean_room(root, "HEAD"),
    ):
        pytest.fail("newly masked paths must not permit checks")
    assert git(root, "worktree", "list", "--porcelain").count(b"worktree ") == 1
    assert git(root, "ls-files", "-v", "app.py").startswith(b"h ")


@pytest.mark.parametrize("name", [" spaced name.txt", "测试 %25 #1.txt", "plain.txt"])
def test_supported_untracked_files_keep_exact_bytes(tmp_path: Path, name: str) -> None:
    root = repository(tmp_path / "repo")
    (root / name).write_bytes(b"\x00\xff\r\nliteral\n")
    with clean_room(root, "HEAD") as verifier:
        assert (verifier / name).read_bytes() == b"\x00\xff\r\nliteral\n"


@pytest.mark.skipif(os.name == "nt", reason="FIFO is a POSIX file type")
def test_listed_fifo_is_rejected_without_opening_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    target = tmp_path / "target"
    root.mkdir()
    target.mkdir()
    os.mkfifo(root / "pipe")
    monkeypatch.setattr(
        cleanroom_module, "_git",
        lambda *_: subprocess.CompletedProcess(["git"], 0, stdout="pipe\0", stderr=""),
    )
    with pytest.raises(CleanRoomError, match="regular file"):
        _copy_untracked(root, target)
    assert not (target / "pipe").exists()


def test_untracked_copy_error_is_contained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "repo")
    (root / "new.txt").write_text("candidate", encoding="utf-8")

    def failed_copy(*args: object, **kwargs: object) -> None:
        raise PermissionError("synthetic denied read")

    monkeypatch.setattr(cleanroom_module.shutil, "copy2", failed_copy)
    with pytest.raises(CleanRoomError, match="cannot copy"), clean_room(root, "HEAD"):
        pytest.fail("a failed copy must not yield a workspace")
    assert git(root, "worktree", "list", "--porcelain").count(b"worktree ") == 1


def test_missing_git_executable_is_a_clean_room_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("synthetic missing Git")

    monkeypatch.setattr(cleanroom_module.subprocess, "run", unavailable)
    with pytest.raises(CleanRoomError, match="cannot run Git"):
        cleanroom_module._git(tmp_path, "ls-files", "-z")


def test_non_path_git_output_does_not_require_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cleanroom_module.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            ["git"], 0, stdout=b"HEAD is now at 1234 subject \xff\n", stderr=b""
        ),
    )
    result = cleanroom_module._git(tmp_path, "worktree", "add", "repo", "HEAD")
    assert result.returncode == 0
    assert "subject" in result.stdout
