from __future__ import annotations

from copy import deepcopy

import pytest

from patchwitness.safe_delivery import ChangeSubject, DeliveryDecision, content_digest
from patchwitness.tasktopr import (
    TASKTOPR_HANDOFF_SCHEMA_V2,
    TASKTOPR_TRUST_BOUNDARY,
    TaskToPREvidenceError,
    adapt_tasktopr_execution,
)

SUBJECT = ChangeSubject("6" * 64, "a" * 40, "b" * 40, "d" * 64, "0" * 64)
TRUSTED_REVISION = "e" * 40


def _handoff(*, mode: str = "prompt", decision: str = "approve") -> dict[str, object]:
    original = "5" * 64
    final = "6" * 64 if decision == "edit" else original
    if mode == "off":
        approval: dict[str, object] = {
            "mode": "off",
            "decision": "not_required",
            "edited": False,
            "original_plan_sha256": None,
            "final_plan_sha256": None,
            "record_sha256": None,
        }
    else:
        approval = {
            "mode": mode,
            "decision": decision,
            "edited": original != final,
            "original_plan_sha256": original,
            "final_plan_sha256": final,
            "record_sha256": "7" * 64,
        }
    payload: dict[str, object] = {
        "schema_version": TASKTOPR_HANDOFF_SCHEMA_V2,
        "component": "execution",
        "producer": {
            "name": "tasktopr",
            "version": "0.1.0",
            "git_revision": TRUSTED_REVISION,
            "source_sha256": "8" * 64,
        },
        "change": {
            "repository_sha256": SUBJECT.repository_sha256,
            "base_sha": SUBJECT.base_sha,
            "head_sha": SUBJECT.head_sha,
            "changed_file_count": 2,
            "change_scope_sha256": "1" * 64,
        },
        "policy": {"version": "tasktopr-execution-v1", "sha256": "9" * 64},
        "verification": {
            "decision": "REVIEW_REQUIRED",
            "complete": True,
            "tests_status": "pass",
            "tests_count": 2,
            "command_list_sha256": "2" * 64,
            "test_result_sha256": "3" * 64,
            "protected_path_decision": "allow",
        },
        "plan_approval": approval,
        "source_receipt": {"schema_version": 2, "sha256": "4" * 64},
        "trust_boundary": TASKTOPR_TRUST_BOUNDARY,
    }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def _payload(report: dict[str, object]) -> dict[str, object]:
    payload = report["payload"]
    assert isinstance(payload, dict)
    return payload


def _rehash(report: dict[str, object]) -> None:
    report["receipt_sha256"] = content_digest(_payload(report))


def test_v2_prompt_approval_is_explicit_bounded_execution_provenance() -> None:
    record = adapt_tasktopr_execution(
        _handoff(), subject=SUBJECT, trusted_revision=TRUSTED_REVISION
    )

    assert record.decision == DeliveryDecision.PASS
    assert record.rule_ids == ("TASKTOPR_VERIFIED_HEAD", "TASKTOPR_PLAN_APPROVED")
    assert record.metrics == {
        "changed_file_count": 2,
        "tests_count": 2,
        "plan_approval_required": 1,
        "plan_approval_satisfied": 1,
    }


def test_v2_edit_approval_is_accepted_when_plan_identity_changes() -> None:
    record = adapt_tasktopr_execution(
        _handoff(decision="edit"), subject=SUBJECT, trusted_revision=TRUSTED_REVISION
    )
    assert "TASKTOPR_PLAN_APPROVED" in record.rule_ids
    assert record.metrics["plan_approval_satisfied"] == 1


def test_v2_off_mode_never_claims_human_approval() -> None:
    record = adapt_tasktopr_execution(
        _handoff(mode="off"), subject=SUBJECT, trusted_revision=TRUSTED_REVISION
    )

    assert record.rule_ids == ("TASKTOPR_VERIFIED_HEAD",)
    assert record.metrics["plan_approval_required"] == 0
    assert record.metrics["plan_approval_satisfied"] == 0


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("decision", "reject", "completed human decision"),
        ("decision", "pending", "completed human decision"),
        ("record_sha256", None, "SHA-256"),
        ("edited", True, "edit identity"),
    ],
)
def test_v2_incomplete_or_inconsistent_approval_fails_closed(
    field: str, value: object, match: str
) -> None:
    report = deepcopy(_handoff())
    approval = _payload(report)["plan_approval"]
    assert isinstance(approval, dict)
    approval[field] = value
    _rehash(report)

    with pytest.raises(TaskToPREvidenceError, match=match):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_v2_off_mode_rejects_hidden_approval_identity() -> None:
    report = _handoff(mode="off")
    approval = _payload(report)["plan_approval"]
    assert isinstance(approval, dict)
    approval["record_sha256"] = "7" * 64
    _rehash(report)

    with pytest.raises(TaskToPREvidenceError, match="disabled plan approval is inconsistent"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_v2_source_receipt_schema_is_bound() -> None:
    report = _handoff()
    source = _payload(report)["source_receipt"]
    assert isinstance(source, dict)
    source["schema_version"] = 1
    _rehash(report)

    with pytest.raises(TaskToPREvidenceError, match="source receipt identity"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)
