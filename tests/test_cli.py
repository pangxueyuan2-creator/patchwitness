import subprocess
from pathlib import Path

from patchwitness.cli import main


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_policy_ref_uses_trusted_git_contract(tmp_path: Path, monkeypatch: object) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    trusted = '''\
id = "trusted"
goal = "Only source changes are authorized"
[policy]
allowed_paths = ["src/**"]
protected_paths = [".patchwitness.toml"]
require_tests = false
'''
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

