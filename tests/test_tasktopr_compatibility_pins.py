from __future__ import annotations

from copy import deepcopy

import pytest

from patchwitness.passport import build_parser
from patchwitness.safe_delivery import ChangeSubject, content_digest
from patchwitness.tasktopr import (
    TASKTOPR_HANDOFF_SCHEMA_V1,
    TASKTOPR_HANDOFF_SCHEMA_V2,
    TASKTOPR_TRUST_BOUNDARY,
    TaskToPREvidenceError,
    adapt_tasktopr_execution,
)

SUBJECT = ChangeSubject("6" * 64, "a" * 40, "b" * 40, "d" * 64, "0" * 64)
TRUSTED_REVISION = "e" * 40
TRUSTED_VERSION = "0.1.0"


def _handoff() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": TASKTOPR_HANDOFF_SCHEMA_V2,
        "component": "execution",
        "producer": {
            "name": "tasktopr",
            "version": TRUSTED_VERSION,
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
        "plan_approval": {
            "mode": "prompt",
            "decision": "approve",
            "edited": False,
            "original_plan_sha256": "5" * 64,
            "final_plan_sha256": "5" * 64,
            "record_sha256": "7" * 64,
        },
        "source_receipt": {"schema_version": 2, "sha256": "4" * 64},
        "trust_boundary": TASKTOPR_TRUST_BOUNDARY,
    }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def test_exact_version_and_schema_pins_are_recorded() -> None:
    record = adapt_tasktopr_execution(
        _handoff(),
        subject=SUBJECT,
        trusted_revision=TRUSTED_REVISION,
        trusted_version=TRUSTED_VERSION,
        required_schema=TASKTOPR_HANDOFF_SCHEMA_V2,
    )

    assert "TASKTOPR_PRODUCER_VERSION_PINNED" in record.rule_ids
    assert "TASKTOPR_HANDOFF_SCHEMA_PINNED" in record.rule_ids
    assert record.metrics["producer_version_pin_satisfied"] == 1
    assert record.metrics["handoff_schema_pin_satisfied"] == 1


def test_version_pin_mismatch_fails_closed() -> None:
    with pytest.raises(TaskToPREvidenceError, match="version does not match reviewer pin"):
        adapt_tasktopr_execution(
            _handoff(),
            subject=SUBJECT,
            trusted_revision=TRUSTED_REVISION,
            trusted_version="0.2.0",
        )


def test_schema_pin_mismatch_fails_closed() -> None:
    with pytest.raises(TaskToPREvidenceError, match="schema does not match reviewer pin"):
        adapt_tasktopr_execution(
            _handoff(),
            subject=SUBJECT,
            trusted_revision=TRUSTED_REVISION,
            required_schema=TASKTOPR_HANDOFF_SCHEMA_V1,
        )


@pytest.mark.parametrize("value", ["", "bad version", "!invalid"])
def test_invalid_reviewer_version_pin_is_rejected(value: str) -> None:
    with pytest.raises(TaskToPREvidenceError, match="trusted TaskToPR version is invalid"):
        adapt_tasktopr_execution(
            _handoff(),
            subject=SUBJECT,
            trusted_revision=TRUSTED_REVISION,
            trusted_version=value,
        )


def test_unknown_reviewer_schema_pin_is_rejected() -> None:
    with pytest.raises(
        TaskToPREvidenceError,
        match="required TaskToPR handoff schema is unsupported",
    ):
        adapt_tasktopr_execution(
            _handoff(),
            subject=SUBJECT,
            trusted_revision=TRUSTED_REVISION,
            required_schema="tasktopr.dev/safe-delivery/execution/v3",
        )


def test_omitted_compatibility_pins_preserve_existing_metadata() -> None:
    record = adapt_tasktopr_execution(
        deepcopy(_handoff()),
        subject=SUBJECT,
        trusted_revision=TRUSTED_REVISION,
    )

    assert "TASKTOPR_PRODUCER_VERSION_PINNED" not in record.rule_ids
    assert "TASKTOPR_HANDOFF_SCHEMA_PINNED" not in record.rule_ids
    assert "producer_version_pin_satisfied" not in record.metrics
    assert "handoff_schema_pin_satisfied" not in record.metrics


def test_safe_delivery_cli_exposes_reviewer_compatibility_pins() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "tasktopr",
            "--handoff",
            "handoff.json",
            "--tasktopr-revision",
            TRUSTED_REVISION,
            "--tasktopr-version",
            TRUSTED_VERSION,
            "--tasktopr-schema",
            TASKTOPR_HANDOFF_SCHEMA_V2,
            "--base",
            "a" * 40,
            "--policy-ref",
            "a" * 40,
            "--output",
            "passport.json",
        ]
    )

    assert args.tasktopr_version == TRUSTED_VERSION
    assert args.tasktopr_schema == TASKTOPR_HANDOFF_SCHEMA_V2
