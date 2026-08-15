import os
import subprocess
import sys
from pathlib import Path

from patchwitness.cli import main
from patchwitness.config import DEFAULT_CONFIG
from patchwitness.evidence import load_evidence


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_policy_ref_uses_trusted_git_contract(tmp_path: Path, monkeypatch: object) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    trusted = """\
id = "trusted"
goal = "Only source changes are authorized"
[policy]
allowed_paths = ["src/**"]
protected_paths = [".patchwitness.toml"]
require_tests = false
"""
    (tmp_path / ".patchwitness.toml").write_text(trusted, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "trusted base")

    weakened = trusted.replace('allowed_paths = ["src/**"]', 'allowed_paths = ["**"]')
    (tmp_path / ".patchwitness.toml").write_text(weakened, encoding="utf-8")
    (tmp_path / "outside.md").write_text("out of scope\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = main(
        [
            "gate",
            "--base",
            "HEAD",
            "--policy-ref",
            "HEAD",
            "--no-checks",
            "--output",
            "evidence.json",
        ]
    )
    assert result == 1


def test_cli_capture_verify_report_and_explain(tmp_path: Path, monkeypatch: object) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    config = DEFAULT_CONFIG.replace("require_tests = true", "require_tests = false").split(
        "[[checks]]", 1
    )[0]
    (tmp_path / ".patchwitness.toml").write_text(config, encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    assert main(["capture", "--no-checks", "--output", "evidence.json"]) == 0
    assert main(["verify", "evidence.json"]) == 0
    assert main(["report", "evidence.json", "--format", "sarif", "--output", "gate.sarif"]) == 0
    assert main(["explain", "PW003"]) == 0
    assert main(["impact", "--base", "HEAD", "--no-cache"]) == 0
    assert (tmp_path / "gate.sarif").is_file()


def test_smart_scan_runs_detected_tests_without_a_contract(
    tmp_path: Path, monkeypatch: object
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="demo"\n', encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_demo.py").write_text("def test_demo(): assert True\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setenv(  # type: ignore[attr-defined]
        "PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    )

    result = main(["scan", "--output", "evidence.json"])

    assert result == 0
    pack = load_evidence(tmp_path / "evidence.json")
    assert pack.contract["source"] == "auto-detected-preview"
    assert pack.summary["checks_passed"] == 1
    assert pack.summary["checks_total"] == 1
    assert [change["path"] for change in pack.changes] == ["app.py"]


def test_smart_scan_uses_latest_commit_when_worktree_is_clean(
    tmp_path: Path, monkeypatch: object
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "change")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = main(["scan", "--no-checks", "--output", "evidence.json"])

    assert result == 0
    pack = load_evidence(tmp_path / "evidence.json")
    assert [change["path"] for change in pack.changes] == ["app.py"]


def test_smart_scan_on_single_commit_repo_falls_back_to_head(
    tmp_path: Path, monkeypatch: object
) -> None:
    """A brand-new (non-shallow) repo with no parent must not crash; base becomes HEAD."""

    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "only commit")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]

    result = main(["scan", "--no-checks", "--output", "evidence.json"])

    assert result == 0
    pack = load_evidence(tmp_path / "evidence.json")
    assert pack.repository["base_revision"]  # resolved SHA, not empty
    # no parent available → empty or structural-only change set is acceptable
    assert pack.summary["checks_total"] == 0


def test_smart_scan_fails_closed_on_shallow_clone_missing_parent(
    tmp_path: Path, monkeypatch: object
) -> None:
    """A depth-1 checkout of longer history is one local commit plus .git/shallow.

    Local ``git clone --depth 1`` can still resolve HEAD^ when objects are
    hardlinked from the source. Mark the tip as shallow so the missing-parent
    case is deterministic on every platform.
    """

    from patchwitness.git import GitError, is_shallow_repository, resolve_revision

    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "only visible commit")
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    (tmp_path / ".git" / "shallow").write_text(head + "\n", encoding="utf-8")

    assert is_shallow_repository(tmp_path)
    try:
        resolve_revision(tmp_path, "HEAD^")
        raise AssertionError("HEAD^ should be missing in the shallow fixture")
    except GitError:
        pass

    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    result = main(["scan", "--no-checks", "--output", "evidence.json"])

    assert result == 2
    assert not (tmp_path / "evidence.json").exists()
