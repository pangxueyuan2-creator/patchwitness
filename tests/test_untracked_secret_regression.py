import subprocess
from pathlib import Path

from patchwitness.evidence import capture_evidence
from patchwitness.models import Contract, GateStatus


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_untracked_file_with_secret_is_scanned_and_fails_gate(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("print('base')\n", encoding="utf-8")
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-m", "base")

    token = "sk-" + "abcdefghijklmnopqrstuvwxyz0123456789"
    (tmp_path / "new-secret.txt").write_text(f"token = '{token}'\n", encoding="utf-8")

    pack = capture_evidence(tmp_path, Contract(require_tests=False), execute_checks=False)

    assert pack.status == GateStatus.FAIL
    change = next(item for item in pack.changes if item["path"] == "new-secret.txt")
    assert change["after_sha256"] is not None
    assert any(
        finding["rule_id"] == "PW030" and finding["path"] == "new-secret.txt"
        for finding in pack.findings
    )
