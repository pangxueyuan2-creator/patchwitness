import subprocess
from pathlib import Path

from patchwitness.cleanroom import clean_room
from patchwitness.cli import main
from patchwitness.evidence import load_evidence, verify_evidence


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_clean_room_materializes_tracked_and_untracked_changes(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("NEW = True\n", encoding="utf-8")

    with clean_room(tmp_path, "HEAD") as verifier:
        assert (verifier / "app.py").read_text(encoding="utf-8") == "VALUE = 2\n"
        assert (verifier / "new.py").read_text(encoding="utf-8") == "NEW = True\n"
    assert not list(tmp_path.parent.glob("patchwitness-cleanroom-*"))


def test_clean_room_gate_handles_committed_head_diff_and_writes_verifiable_evidence(
    tmp_path: Path, monkeypatch: object
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    contract = (
        "version = 1\n"
        'id = "committed-clean-room"\n'
        'goal = "Verify committed pull-request changes in a disposable worktree"\n'
        "[policy]\n"
        'allowed_paths = ["**"]\n'
        'protected_paths = [".github/workflows/**", ".patchwitness.toml"]\n'
        "require_tests = false\n"
    )
    (tmp_path / ".patchwitness.toml").write_text(contract, encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "trusted base")
    base = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    (tmp_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-m", "committed head change")

    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    assert (
        main(
            [
                "gate",
                "--base",
                base,
                "--policy-ref",
                base,
                "--clean-room",
                "--output",
                "evidence.json",
            ]
        )
        == 0
    )

    evidence = tmp_path / "evidence.json"
    assert evidence.is_file()
    pack = verify_evidence(load_evidence(evidence))
    assert pack.summary["status"] == "pass"
    assert [change["path"] for change in pack.changes] == ["app.py"]
    assert pack.extensions["verification"]["clean_room"] is True
    assert not list(tmp_path.parent.glob("patchwitness-cleanroom-*"))
