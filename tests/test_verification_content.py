"""Checks must not verify different content from the recorded index change."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from patchwitness import git as repository_git
from patchwitness.checks import run_checks
from patchwitness.evidence import capture_evidence, verify_evidence
from patchwitness.models import CheckResult, CheckSpec, Contract, GateStatus


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def repository(root: Path) -> Path:
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "PatchWitness Tests")
    git(root, "config", "user.email", "tests@patchwitness.dev")
    git(root, "config", "core.autocrlf", "false")
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    git(root, "add", "app.py")
    git(root, "commit", "-m", "base")
    return root


@pytest.mark.parametrize("clean_room", [False, True])
def test_divergent_staged_content_cannot_receive_passing_check_evidence(
    tmp_path: Path, clean_room: bool
) -> None:
    root = repository(tmp_path / "repo")
    app = root / "app.py"
    app.write_text("VALUE = 2\n", encoding="utf-8", newline="\n")
    git(root, "add", "app.py")
    app.write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    check = tmp_path / "check.py"
    check.write_text(
        "from pathlib import Path\n"
        "assert Path('app.py').read_text(encoding='utf-8') == 'VALUE = 1\\n'\n",
        encoding="utf-8",
    )
    contract = Contract(checks=(CheckSpec("tests", f'"{sys.executable}" "{check}"'),))

    pack = capture_evidence(root, contract, clean_room_checks=clean_room)

    assert pack.status == GateStatus.FAIL
    assert {finding["rule_id"] for finding in pack.findings} >= {"PW020", "PW033"}
    assert pack.checks == ()
    assert verify_evidence(pack) == pack


@pytest.mark.parametrize("execute_checks", [False, True])
def test_staged_deletion_with_replacement_requires_reconciliation(
    tmp_path: Path, execute_checks: bool
) -> None:
    root = repository(tmp_path / "repo")
    git(root, "rm", "--cached", "app.py")

    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=execute_checks)

    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW033" for finding in pack.findings)


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_masked_staged_content_fails_closed(tmp_path: Path, flag: str) -> None:
    root = repository(tmp_path / "repo")
    app = root / "app.py"
    app.write_text("VALUE = 2\n", encoding="utf-8", newline="\n")
    git(root, "add", "app.py")
    git(root, "update-index", flag, "app.py")
    app.write_text("VALUE = 1\n", encoding="utf-8", newline="\n")

    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)

    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW033" for finding in pack.findings)


@pytest.mark.parametrize("clean_room", [False, True])
def test_matching_staged_content_passes_real_check_and_matches_receipt(
    tmp_path: Path, clean_room: bool
) -> None:
    import hashlib

    root = repository(tmp_path / "repo")
    candidate = b"VALUE = 2\n"
    (root / "app.py").write_bytes(candidate)
    git(root, "add", "app.py")
    check = tmp_path / "check.py"
    check.write_text(
        "from pathlib import Path\n"
        "import hashlib\n"
        f"assert hashlib.sha256(Path('app.py').read_bytes()).hexdigest() == "
        f"{hashlib.sha256(candidate).hexdigest()!r}\n",
        encoding="utf-8",
    )
    contract = Contract(checks=(CheckSpec("tests", f'"{sys.executable}" "{check}"'),))

    pack = capture_evidence(root, contract, clean_room_checks=clean_room)

    assert pack.status == GateStatus.PASS
    assert pack.changes[0]["after_sha256"] == hashlib.sha256(candidate).hexdigest()
    assert pack.checks[0]["passed"] is True


def test_git_line_ending_conversion_is_not_content_ambiguity(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    git(root, "config", "core.autocrlf", "true")
    (root / "app.py").write_bytes(b"VALUE = 2\r\n")
    git(root, "add", "app.py")

    assert repository_git.verification_conflicts(root, "HEAD") == ()


def test_rewriting_identical_staged_content_is_not_ambiguity(tmp_path: Path) -> None:
    import os

    root = repository(tmp_path / "repo")
    app = root / "app.py"
    app.write_bytes(b"VALUE = 2\n")
    git(root, "add", "app.py")
    app.write_bytes(b"VALUE = 2\n")
    os.utime(app, (1_700_000_000, 1_700_000_000))

    assert repository_git.verification_conflicts(root, "HEAD") == ()


def test_unstaged_only_change_remains_supported(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_bytes(b"VALUE = 2\n")

    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)

    assert pack.status == GateStatus.PASS


def test_missing_required_check_proof_cannot_pass(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_bytes(b"VALUE = 2\n")
    contract = Contract(checks=(CheckSpec("tests", "unused-command"),))

    pack = capture_evidence(root, contract, execute_checks=False)

    assert pack.status == GateStatus.FAIL
    assert {finding["rule_id"] for finding in pack.findings} == {"PW020"}


def test_check_created_index_worktree_divergence_fails_closed(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_bytes(b"VALUE = 2\n")
    git(root, "add", "app.py")
    check = tmp_path / "mutate.py"
    check.write_text(
        "from pathlib import Path\nPath('app.py').write_bytes(b'VALUE = 3\\n')\n",
        encoding="utf-8",
    )
    contract = Contract(checks=(CheckSpec("tests", f'"{sys.executable}" "{check}"'),))

    pack = capture_evidence(root, contract)

    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW033" for finding in pack.findings)


def test_unicode_renamed_path_retains_conflict_identity(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    renamed = "计算 文件.py"
    git(root, "mv", "app.py", renamed)
    (root / renamed).write_bytes(b"VALUE = 2\n")

    assert repository_git.verification_conflicts(root, "HEAD") == (renamed,)


def test_clean_room_source_index_and_worktree_moving_together_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_bytes(b"VALUE = 2\n")
    git(root, "add", "app.py")
    check = tmp_path / "check.py"
    check.write_text(
        "from pathlib import Path\nassert Path('app.py').read_bytes() == b'VALUE = 2\\n'\n",
        encoding="utf-8",
    )
    spec = CheckSpec("tests", f'"{sys.executable}" "{check}"')

    def runner(
        verifier: Path,
        specs: tuple[CheckSpec, ...],
        *,
        parallel: bool,
        max_workers: int,
        untrusted: bool,
    ) -> tuple[CheckResult, ...]:
        assert verifier != root
        results = run_checks(
            verifier, specs, parallel=parallel, max_workers=max_workers, untrusted=untrusted
        )
        assert all(result.passed for result in results)
        (root / "app.py").write_bytes(b"VALUE = 3\n")
        git(root, "add", "app.py")
        return results

    monkeypatch.setattr("patchwitness.evidence.run_checks", runner)
    pack = capture_evidence(root, Contract(checks=(spec,)), clean_room_checks=True)

    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW032" for finding in pack.findings)
    assert repository_git.verification_conflicts(root, "HEAD") == ()


@pytest.mark.parametrize("move", ["head", "branch"])
@pytest.mark.parametrize("clean_room", [False, True])
def test_repository_identity_movement_cannot_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, move: str, clean_room: bool
) -> None:
    root = repository(tmp_path / "repo")
    original_head = git(root, "rev-parse", "HEAD")

    def runner(
        _verifier: Path,
        _specs: tuple[CheckSpec, ...],
        *,
        parallel: bool,
        max_workers: int,
        untrusted: bool = False,
    ) -> tuple[CheckResult, ...]:
        if move == "head":
            git(root, "commit", "--allow-empty", "-m", "concurrent head move")
        else:
            git(root, "switch", "-c", "concurrent-branch")
        return ()

    monkeypatch.setattr("patchwitness.evidence.run_checks", runner)
    pack = capture_evidence(root, Contract(require_tests=False), clean_room_checks=clean_room)

    assert pack.status == GateStatus.FAIL
    assert pack.repository["head_revision"] == original_head
    assert pack.repository["branch"] == "main"
    assert any(finding["rule_id"] == "PW032" for finding in pack.findings)
