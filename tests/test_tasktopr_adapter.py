from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from patchwitness.safe_delivery import ChangeSubject, DeliveryDecision, content_digest
from patchwitness.tasktopr_adapter import adapt_tasktopr_execution_handoff

SUBJECT = ChangeSubject("1" * 64, "a" * 40, "b" * 40, "2" * 64, "3" * 64)


def handoff(schema: str = "tasktopr.dev/safe-delivery/execution/v1") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": schema,
        "component": "execution",
        "producer": {
            "name": "tasktopr",
            "version": "0.1.0",
            "git_revision": "c" * 40,
            "source_sha256": "4" * 64,
        },
        "change": {
            "repository_sha256": "1" * 64,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_file_count": 2,
            "change_scope_sha256": "5" * 64,
        },
        "policy": {"version": "tasktopr-execution-v1", "sha256": "6" * 64},
        "verification": {
            "decision": "REVIEW_REQUIRED",
            "complete": True,
            "tests_status": "pass",
            "tests_count": 3,
            "command_list_sha256": "7" * 64,
            "test_result_sha256": "8" * 64,
            "protected_path_decision": "allow",
        },
        "source_receipt": {"schema_version": 1, "sha256": "9" * 64},
        "trust_boundary": "sanitized local execution evidence",
    }
    if schema.endswith("/v2"):
        payload["source_receipt"]["schema_version"] = 2
        payload["plan_approval"] = {
            "mode": "prompt",
            "decision": "approve",
            "edited": False,
            "original_plan_sha256": "a" * 64,
            "final_plan_sha256": "a" * 64,
            "record_sha256": "b" * 64,
        }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def resign(value: dict[str, Any]) -> None:
    value["receipt_sha256"] = content_digest(value["payload"])


def test_successful_handoff_remains_review_required_and_uses_independent_subject() -> None:
    evidence = adapt_tasktopr_execution_handoff(SUBJECT, handoff())

    assert evidence.decision is DeliveryDecision.REVIEW_REQUIRED
    assert evidence.subject.manifest_sha256 == "2" * 64
    assert evidence.subject.policy_sha256 == "3" * 64
    assert evidence.metrics == {"changed_file_count": 2, "source_schema": 1, "tests_count": 3}
    assert evidence.rule_ids == ()


def test_tasktopr_policy_and_change_scope_do_not_replace_patchwitness_identities() -> None:
    value = handoff()
    value["payload"]["change"]["change_scope_sha256"] = "f" * 64
    value["payload"]["policy"]["sha256"] = "e" * 64
    resign(value)

    evidence = adapt_tasktopr_execution_handoff(SUBJECT, value)

    assert evidence.decision is DeliveryDecision.REVIEW_REQUIRED
    assert evidence.subject == SUBJECT


def test_subject_mismatch_fails_closed() -> None:
    value = handoff()
    value["payload"]["change"]["head_sha"] = "d" * 40
    resign(value)

    evidence = adapt_tasktopr_execution_handoff(SUBJECT, value)

    assert evidence.decision is DeliveryDecision.FAIL
    assert evidence.rule_ids == ("TTA001",)


def test_failed_and_unknown_execution_are_not_upgraded() -> None:
    failed = handoff()
    failed["payload"]["verification"]["decision"] = "FAIL"
    failed["payload"]["verification"]["tests_status"] = "fail"
    resign(failed)
    assert adapt_tasktopr_execution_handoff(SUBJECT, failed).decision is DeliveryDecision.FAIL

    unknown = handoff()
    unknown["payload"]["verification"]["decision"] = "UNKNOWN"
    unknown["payload"]["verification"]["complete"] = False
    unknown["payload"]["verification"]["tests_status"] = "unknown"
    resign(unknown)
    evidence = adapt_tasktopr_execution_handoff(SUBJECT, unknown)
    assert evidence.decision is DeliveryDecision.UNKNOWN
    assert "TTA003" in evidence.rule_ids


def test_claimed_pass_is_rejected() -> None:
    value = handoff()
    value["payload"]["verification"]["decision"] = "PASS"
    resign(value)

    with pytest.raises(ValueError, match="cannot authorize PASS"):
        adapt_tasktopr_execution_handoff(SUBJECT, value)


def test_tampering_and_unknown_fields_are_rejected() -> None:
    tampered = handoff()
    tampered["payload"]["change"]["changed_file_count"] = 999
    with pytest.raises(ValueError, match="digest mismatch"):
        adapt_tasktopr_execution_handoff(SUBJECT, tampered)

    extra = handoff()
    extra["payload"]["secret"] = "x"
    resign(extra)
    with pytest.raises(ValueError, match="unexpected fields"):
        adapt_tasktopr_execution_handoff(SUBJECT, extra)


def test_v2_plan_approval_is_validated() -> None:
    value = handoff("tasktopr.dev/safe-delivery/execution/v2")
    assert adapt_tasktopr_execution_handoff(SUBJECT, value).metrics["source_schema"] == 2

    broken = deepcopy(value)
    broken["payload"]["plan_approval"]["edited"] = True
    resign(broken)
    with pytest.raises(ValueError, match="inconsistent"):
        adapt_tasktopr_execution_handoff(SUBJECT, broken)
