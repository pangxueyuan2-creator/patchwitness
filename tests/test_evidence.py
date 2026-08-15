import subprocess
from pathlib import Path

import pytest

from patchwitness import __version__
from patchwitness.evidence import EvidenceError, capture_evidence, verify_evidence
from patchwitness.models import Contract, GateStatus


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def repository(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-m", "base")
    return tmp_path


def test_capture_and_verify_round_trip(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "app.py").write_text("print('after')\n", encoding="utf-8")
    contract = Contract(require_tests=False)
    pack = capture_evidence(root, contract, execute_checks=False)
    assert pack.status == GateStatus.PASS
    assert pack.tool["version"] == __version__
    assert pack.summary["files_changed"] == 1
    assert verify_evidence(pack).payload_sha256 == pack.payload_sha256


def test_detects_tampering(tmp_path: Path) -> None:
    root = repository(tmp_path)
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    value = pack.to_dict()
    value["summary"]["files_changed"] = 99
    with pytest.raises(EvidenceError, match="digest mismatch"):
        verify_evidence(value)


def test_untracked_files_are_included(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "new.py").write_text("value = 1\n", encoding="utf-8")
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    assert [item["path"] for item in pack.changes] == ["new.py"]


def test_rename_records_previous_path_and_both_content_hashes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    git(root, "mv", "app.py", "renamed.py")

    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)

    assert len(pack.changes) == 1
    change = pack.changes[0]
    assert change["path"] == "renamed.py"
    assert change["previous_path"] == "app.py"
    assert change["status"].startswith("R")
    assert change["before_sha256"] is not None
    assert change["after_sha256"] is not None


def test_capture_does_not_follow_untracked_symlink_outside_repository(tmp_path: Path) -> None:
    root = repository(tmp_path)
    outside = tmp_path.parent / "outside-secret.txt"
    token = "sk-" + "abcdefghijklmnopqrstuvwxyz0123456789"
    outside.write_text(f"token = '{token}'\n", encoding="utf-8")
    link = root / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable in this test environment: {exc}")

    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)

    assert [item["path"] for item in pack.changes] == ["outside-link.txt"]
    assert pack.changes[0]["after_sha256"] is None
    assert not any(finding["rule_id"] == "PW030" for finding in pack.findings)
