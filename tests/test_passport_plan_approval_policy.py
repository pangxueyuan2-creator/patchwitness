from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from patchwitness.passport_policy import main, require_tasktopr_plan_approval
from patchwitness.safe_delivery import content_digest
from patchwitness.tasktopr import (
    TASKTOPR_HANDOFF_SCHEMA_V1,
    TASKTOPR_HANDOFF_SCHEMA_V2,
    TASKTOPR_TRUST_BOUNDARY,
)

TASKTOPR_REVISION = "2" * 40


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Approval Policy Fixture")
    _git(root, "config", "user.email", "approval-policy@example.invalid")
    (root / ".patchwitness.toml").write_text(
        'id = "reviewed-policy"\ngoal = "verify the exact candidate"\n', encoding="utf-8"
    )
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "--", ".patchwitness.toml", "app.py")
    _git(root, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(root, "add", "--", "app.py")
    _git(root, "commit", "-m", "candidate")
    return root, base, _git(root, "rev-parse", "HEAD")


def _handoff(
    root: Path,
    base: str,
    head: str,
    *,
    schema: str,
    approval: str = "approve",
) -> dict[str, object]:
    source_schema = 2 if schema == TASKTOPR_HANDOFF_SCHEMA_V2 else 1
    payload: dict[str, object] = {
        "schema_version": schema,
        "component": "execution",
        "producer": {
            "name": "tasktopr",
            "version": "0.2.0",
            "git_revision": TASKTOPR_REVISION,
            "source_sha256": "a" * 64,
        },
        "change": {
            "repository_sha256": content_digest(str(root.resolve())),
            "base_sha": base,
            "head_sha": head,
            "changed_file_count": 1,
            "change_scope_sha256": "b" * 64,
        },
        "policy": {"version": "tasktopr-execution-v1", "sha256": "c" * 64},
        "verification": {
            "decision": "REVIEW_REQUIRED",
            "complete": True,
            "tests_status": "pass",
            "tests_count": 3,
            "command_list_sha256": "d" * 64,
            "test_result_sha256": "e" * 64,
            "protected_path_decision": "allow",
        },
        "source_receipt": {"schema_version": source_schema, "sha256": "f" * 64},
        "trust_boundary": TASKTOPR_TRUST_BOUNDARY,
    }
    if schema == TASKTOPR_HANDOFF_SCHEMA_V2:
        if approval == "off":
            payload["plan_approval"] = {
                "mode": "off",
                "decision": "not_required",
                "edited": False,
                "original_plan_sha256": None,
                "final_plan_sha256": None,
                "record_sha256": None,
            }
        else:
            original = "1" * 64
            final = "2" * 64 if approval == "edit" else original
            payload["plan_approval"] = {
                "mode": "prompt",
                "decision": approval,
                "edited": original != final,
                "original_plan_sha256": original,
                "final_plan_sha256": final,
                "record_sha256": "3" * 64,
            }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def _write(path: Path, report: dict[str, object]) -> None:
    path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")


def _run(
    root: Path,
    base: str,
    handoff: Path,
    output: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    require: bool,
) -> int:
    monkeypatch.chdir(root)
    argv = [
        "--json",
        "tasktopr",
        "--handoff",
        str(handoff),
        "--tasktopr-revision",
        TASKTOPR_REVISION,
        "--base",
        base,
        "--policy-ref",
        base,
        "--output",
        str(output),
    ]
    if require:
        argv.append("--require-plan-approval")
    return main(argv)


def test_default_mode_keeps_legacy_v1_compatibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, base, head = _repository(tmp_path)
    handoff = tmp_path / "legacy.json"
    output = tmp_path / "passport.json"
    _write(handoff, _handoff(root, base, head, schema=TASKTOPR_HANDOFF_SCHEMA_V1))

    assert _run(root, base, handoff, output, monkeypatch, require=False) == 0
    assert output.is_file()


def test_required_approval_rejects_legacy_and_v2_off_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base, head = _repository(tmp_path)
    for name, report in (
        ("legacy", _handoff(root, base, head, schema=TASKTOPR_HANDOFF_SCHEMA_V1)),
        (
            "off",
            _handoff(root, base, head, schema=TASKTOPR_HANDOFF_SCHEMA_V2, approval="off"),
        ),
    ):
        handoff = tmp_path / f"{name}.json"
        output = tmp_path / f"{name}-passport.json"
        _write(handoff, report)
        assert _run(root, base, handoff, output, monkeypatch, require=True) == 2
        result = json.loads(capsys.readouterr().out)
        assert result["ok"] is False
        assert "plan approval" in result["error"]
        assert not output.exists()


@pytest.mark.parametrize("decision", ["approve", "edit"])
def test_required_approval_accepts_verified_v2_decisions(
    decision: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, base, head = _repository(tmp_path)
    handoff = tmp_path / f"{decision}.json"
    output = tmp_path / f"{decision}-passport.json"
    _write(
        handoff,
        _handoff(root, base, head, schema=TASKTOPR_HANDOFF_SCHEMA_V2, approval=decision),
    )

    assert _run(root, base, handoff, output, monkeypatch, require=True) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    require_tasktopr_plan_approval(report)
