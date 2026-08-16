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


def _patchwitness_executable() -> Path:
    installed_executable = shutil.which("patchwitness")
    executable_name = "patchwitness.exe" if os.name == "nt" else "patchwitness"
    executable = (
        Path(installed_executable)
        if installed_executable
        else Path(sysconfig.get_path("scripts")) / executable_name
    )
    assert executable.is_file()
    return executable


def test_codex_stop_hook_captures_a_protected_change(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("jobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")
    contract = """\
version = 1
id = "codex-hook-test"
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

    secret_text = "do-not-copy-this-codex-output"
    payload = {
        "session_id": "../../codex-session",
        "turn_id": "../../turn-1",
        "cwd": str(tmp_path),
        "hook_event_name": "Stop",
        "model": "fixture-model",
        "transcript_path": "/private/transcript.jsonl",
        "prompt": secret_text,
        "agent_output": secret_text,
    }
    hook = Path(__file__).parents[1] / "examples" / "codex-hooks" / "Stop.py"
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=30,
        env={**os.environ, "PATCHWITNESS_EXECUTABLE": str(_patchwitness_executable())},
    )

    assert result.returncode == 0
    assert "FAIL: 1 file(s), 2 finding(s)" in result.stderr
    assert secret_text not in result.stdout + result.stderr
    assert "/private/transcript.jsonl" not in result.stdout + result.stderr
    evidence_files = list((tmp_path / ".patchwitness" / "evidence").glob("codex-stop-*.json"))
    assert len(evidence_files) == 1
    assert evidence_files[0].parent == tmp_path / ".patchwitness" / "evidence"

    pack = verify_evidence(load_evidence(evidence_files[0]))
    assert pack.summary["status"] == "fail"
    assert any(finding["rule_id"] == "PW003" for finding in pack.findings)
    evidence_text = evidence_files[0].read_text(encoding="utf-8")
    assert secret_text not in evidence_text
    assert "/private/transcript.jsonl" not in evidence_text


def test_codex_stop_hook_handles_non_ascii_workspace_path(tmp_path: Path) -> None:
    workspace = tmp_path / "工作区"
    workspace.mkdir()
    git(workspace, "init", "-b", "main")
    git(workspace, "config", "user.email", "tests@patchwitness.dev")
    git(workspace, "config", "user.name", "PatchWitness Tests")
    contract = """\
version = 1
id = "codex-hook-nonascii"
goal = "Protect the verification workflow"
[policy]
allowed_paths = ["src/**"]
protected_paths = [".github/workflows/**"]
require_tests = false
"""
    (workspace / ".patchwitness.toml").write_text(contract, encoding="utf-8")
    (workspace / "README.md").write_text("base\n", encoding="utf-8")
    git(workspace, "add", ".")
    git(workspace, "commit", "-m", "trusted base")
    (workspace / "src").mkdir()
    (workspace / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    payload = {
        "session_id": "s1",
        "turn_id": "t1",
        "cwd": str(workspace),
        "hook_event_name": "Stop",
        "model": "fixture-model",
        "transcript_path": "/private/transcript.jsonl",
        "prompt": "p",
        "agent_output": "a",
    }
    hook = Path(__file__).parents[1] / "examples" / "codex-hooks" / "Stop.py"
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=30,
        env={**os.environ, "PATCHWITNESS_EXECUTABLE": str(_patchwitness_executable())},
    )

    assert result.returncode == 0
    evidence_files = list((workspace / ".patchwitness" / "evidence").glob("codex-stop-*.json"))
    assert len(evidence_files) == 1
    pack = verify_evidence(load_evidence(evidence_files[0]))
    assert pack.summary["status"] == "pass"


def test_codex_stop_hook_ignores_non_stop_payload() -> None:
    hook = Path(__file__).parents[1] / "examples" / "codex-hooks" / "Stop.py"
    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps({"hook_event_name": "PostToolUse", "cwd": "/"}),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""