import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from patchwitness.evidence import load_evidence, verify_evidence


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_cline_task_complete_hook_captures_a_protected_change(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("jobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")
    contract = """\
version = 1
id = "cline-hook-test"
goal = "Protect the verification workflow"
[policy]
allowed_paths = ["src/**"]
protected_paths = [".github/workflows/**"]
require_tests = false
"""
    (tmp_path / ".patchwitness.toml").write_text(contract, encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "trusted base")
    workflow.write_text(
        "jobs:\n  test:\n    runs-on: ubuntu-latest\n    continue-on-error: true\n",
        encoding="utf-8",
    )

    secret_text = "do-not-copy-this-agent-output"
    payload = {
        "hookName": "agent_end",
        "clineVersion": "contract-fixture",
        "timestamp": "2026-08-12T00:00:00Z",
        "taskId": "../../cline-task",
        "workspaceRoots": [str(tmp_path)],
        "userId": "private-user",
        "agent_id": "private-agent",
        "parent_agent_id": None,
        "iteration": 1,
        "turn": {"outputText": secret_text, "status": "completed"},
    }
    hook = Path(__file__).parents[1] / "examples" / "cline-hooks" / "TaskComplete.py"
    installed_executable = shutil.which("patchwitness")
    executable_name = "patchwitness.exe" if os.name == "nt" else "patchwitness"
    patchwitness_executable = (
        Path(installed_executable)
        if installed_executable
        else Path(sysconfig.get_path("scripts")) / executable_name
    )
    assert patchwitness_executable.is_file()
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env={**os.environ, "PATCHWITNESS_EXECUTABLE": str(patchwitness_executable)},
    )

    assert result.returncode == 0
    assert result.stdout == "{}\n"
    assert "FAIL: 1 file(s), 2 finding(s)" in result.stderr
    assert secret_text not in result.stdout + result.stderr
    assert "private-user" not in result.stdout + result.stderr
    evidence_files = list((tmp_path / ".patchwitness" / "evidence").glob("cline-*.json"))
    assert len(evidence_files) == 1
    assert evidence_files[0].parent == tmp_path / ".patchwitness" / "evidence"

    pack = verify_evidence(load_evidence(evidence_files[0]))
    assert pack.summary["status"] == "fail"
    assert any(finding["rule_id"] == "PW003" for finding in pack.findings)
    evidence_text = evidence_files[0].read_text(encoding="utf-8")
    assert secret_text not in evidence_text
    assert "private-user" not in evidence_text


def test_cline_hook_ignores_non_completion_payload() -> None:
    hook = Path(__file__).parents[1] / "examples" / "cline-hooks" / "TaskComplete.py"
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps({"hookName": "tool_result", "workspaceRoots": []}),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stdout == "{}\n"
    assert result.stderr == ""
