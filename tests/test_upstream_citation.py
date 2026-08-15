import json
import subprocess
from pathlib import Path

from patchwitness.evidence import capture_evidence
from patchwitness.models import Contract, GateStatus


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    _git(tmp_path, "config", "user.name", "PatchWitness Tests")
    (tmp_path / "app.py").write_text("print('before')\n", encoding="utf-8")
    _git(tmp_path, "add", "app.py")
    _git(tmp_path, "commit", "-m", "base")
    return tmp_path


def test_absent_decision_omits_upstream(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "app.py").write_text("print('after')\n", encoding="utf-8")
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    assert pack.status == GateStatus.PASS
    assert "upstream" not in pack.extensions


def test_present_decision_is_cited_without_changing_pass(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "app.py").write_text("print('after')\n", encoding="utf-8")
    (root / ".guardspec-check.json").write_text(
        json.dumps(
            {
                "schema_version": "guardspec.check.v1",
                "policy_digest": "abc123",
                "decision": "deny",
                "matched_rules": ["deny-app"],
                "protected_paths": ["app.py"],
            }
        ),
        encoding="utf-8",
    )
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    assert pack.status == GateStatus.PASS
    assert pack.extensions["upstream"] == {
        "status": "present",
        "schema_version": "guardspec.check.v1",
        "policy_digest": "abc123",
        "decision": "deny",
        "path": str(root / ".guardspec-check.json"),
    }


def test_unreadable_env_path_is_cited_without_changing_pass(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path)
    (root / "app.py").write_text("print('after')\n", encoding="utf-8")
    missing = root / "missing-check.json"
    monkeypatch.setenv("GUARDSPEC_CHECK_JSON", str(missing))
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    assert pack.status == GateStatus.PASS
    assert pack.extensions["upstream"]["status"] == "unreadable"
    assert pack.extensions["upstream"]["reason"] == "missing"


def test_malformed_decision_json_is_cited_as_unreadable(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "app.py").write_text("print('after')\n", encoding="utf-8")
    (root / ".guardspec-check.json").write_text("{not-json", encoding="utf-8")
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    assert pack.status == GateStatus.PASS
    assert pack.extensions["upstream"]["status"] == "unreadable"
