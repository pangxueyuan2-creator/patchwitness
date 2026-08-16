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


def test_unicode_protected_rename_is_blocked(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "计算.py").write_text("value = 1\n", encoding="utf-8")
    git(tmp_path, "add", "计算.py")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "mv", "计算.py", "calc_cn.py")

    contract = Contract(
        protected_paths=("计算.py",),
        require_tests=False,
        allowed_paths=("**",),
    )
    pack = capture_evidence(tmp_path, contract, execute_checks=False)

    assert len(pack.changes) == 1
    change = pack.changes[0]
    assert change["path"] == "calc_cn.py"
    assert change["previous_path"] == "计算.py"
    assert change["status"].startswith("R")
    assert pack.status == GateStatus.FAIL
    assert any(
        finding["rule_id"] == "PW003" and finding["path"] == "计算.py" for finding in pack.findings
    )


def test_submodule_pointer_change_at_protected_path_is_blocked(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    contract = Contract(
        allowed_paths=("**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    (tmp_path / ".patchwitness.toml").write_text(
        "version = 1\nid = \"submodule\"\n[policy]\n"
        'allowed_paths = ["**"]\nprotected_paths = [".github/workflows/**"]\n'
        "require_tests = false\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")

    submodule = tmp_path.parent / "pw-submodule-fixture"
    submodule.mkdir()
    git(submodule, "init", "-b", "main")
    git(submodule, "config", "user.email", "tests@patchwitness.dev")
    git(submodule, "config", "user.name", "PatchWitness Tests")
    (submodule / "f.txt").write_text("v1\n", encoding="utf-8")
    git(submodule, "add", ".")
    git(submodule, "commit", "-m", "one")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    git(
        tmp_path,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(submodule),
        ".github/workflows/evil",
    )

    pack = capture_evidence(tmp_path, contract, execute_checks=False)
    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW003" for finding in pack.findings)


def test_staged_protected_change_with_clean_worktree_is_blocked(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    contract = Contract(
        allowed_paths=("**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    (tmp_path / ".patchwitness.toml").write_text(
        "version = 1\nid = \"staged\"\n[policy]\n"
        'allowed_paths = ["**"]\nprotected_paths = [".github/workflows/**"]\n'
        "require_tests = false\n",
        encoding="utf-8",
    )
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("on: push\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    # Stage a protected edit, then restore the working tree to base content.
    staged_content = "jobs:\n  evil:\n    runs-on: ubuntu-latest\n"
    workflow.write_text(staged_content, encoding="utf-8")
    git(tmp_path, "add", ".github/workflows/ci.yml")
    workflow.write_text("on: push\n", encoding="utf-8")

    pack = capture_evidence(tmp_path, contract, execute_checks=False)
    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW003" for finding in pack.findings)
    assert [change["path"] for change in pack.changes] == [".github/workflows/ci.yml"]
    assert pack.changes[0]["after_sha256"] is not None


def test_delete_add_mimicking_rename_of_protected_file_is_blocked(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    contract = Contract(
        allowed_paths=("**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    (tmp_path / ".patchwitness.toml").write_text(
        'version = 1\nid = "deladd"\n[policy]\n'
        'allowed_paths = ["**"]\nprotected_paths = [".github/workflows/**"]\n'
        "require_tests = false\n",
        encoding="utf-8",
    )
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("on: push\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    # Mimic a rename with delete + add of identical content at a new path.
    git(tmp_path, "rm", ".github/workflows/ci.yml")
    replacement = tmp_path / ".github" / "workflows" / "replaced.yml"
    replacement.parent.mkdir(parents=True, exist_ok=True)
    replacement.write_text("on: push\n", encoding="utf-8")
    git(tmp_path, "add", ".github/workflows/replaced.yml")

    pack = capture_evidence(tmp_path, contract, execute_checks=False)

    assert pack.status == GateStatus.FAIL
    # The deleted protected path must not disappear behind rename detection.
    assert any(
        finding["rule_id"] == "PW003" and finding["path"] == ".github/workflows/ci.yml"
        for finding in pack.findings
    )
    rename = pack.changes[0]
    assert rename["path"] == ".github/workflows/replaced.yml"
    assert rename["previous_path"] == ".github/workflows/ci.yml"
    assert rename["status"].startswith("R")


def test_filemode_only_change_of_protected_file_is_blocked(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    contract = Contract(
        allowed_paths=("**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    (tmp_path / ".patchwitness.toml").write_text(
        "version = 1\nid = \"filemode\"\n[policy]\n"
        'allowed_paths = ["**"]\nprotected_paths = [".github/workflows/**"]\n'
        "require_tests = false\n",
        encoding="utf-8",
    )
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("on: push\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "update-index", "--chmod=+x", ".github/workflows/ci.yml")

    pack = capture_evidence(tmp_path, contract, execute_checks=False)
    assert pack.status == GateStatus.FAIL
    assert any(finding["rule_id"] == "PW003" for finding in pack.findings)


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
