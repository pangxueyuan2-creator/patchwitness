"""Strict Safe Delivery adapter for sanitized TaskToPR execution handoffs.

The adapter never treats TaskToPR's change-scope or execution-policy digests as
PatchWitness's independently derived manifest or reviewer-owned policy identity.
It validates the portable handoff, binds it to an independently supplied
``ChangeSubject`` and emits only bounded ``ComponentEvidence``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .safe_delivery import ChangeSubject, ComponentEvidence, DeliveryDecision, content_digest

_SCHEMA_V1 = "tasktopr.dev/safe-delivery/execution/v1"
_SCHEMA_V2 = "tasktopr.dev/safe-delivery/execution/v2"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}\Z")


def _mapping(value: object, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} has unexpected fields")
    return dict(value)


def _text(value: object, name: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError(f"invalid {name}")
    if pattern is not None and not pattern.fullmatch(value):
        raise ValueError(f"invalid {name}")
    return value


def _digest(value: object, name: str) -> str:
    return _text(value, name, _DIGEST)


def _sha(value: object, name: str) -> str:
    return _text(value, name, _SHA)


def _bounded_count(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= 10_000:
        raise ValueError(f"invalid {name}")
    return value


def _validate_plan_approval(value: object) -> None:
    approval = _mapping(
        value,
        {
            "mode",
            "decision",
            "edited",
            "original_plan_sha256",
            "final_plan_sha256",
            "record_sha256",
        },
        "plan approval",
    )
    mode = _text(approval["mode"], "plan approval mode")
    decision = _text(approval["decision"], "plan approval decision")
    if type(approval["edited"]) is not bool:
        raise ValueError("invalid plan approval edited flag")
    if mode == "off":
        if (
            decision != "not_required"
            or approval["edited"]
            or any(
                approval[field] is not None
                for field in ("original_plan_sha256", "final_plan_sha256", "record_sha256")
            )
        ):
            raise ValueError("inconsistent disabled plan approval")
        return
    if mode != "prompt" or decision not in {"approve", "edit"}:
        raise ValueError("invalid completed plan approval")
    original = _digest(approval["original_plan_sha256"], "original plan digest")
    final = _digest(approval["final_plan_sha256"], "final plan digest")
    _digest(approval["record_sha256"], "plan approval record digest")
    edited = bool(approval["edited"])
    if edited != (original != final) or (decision == "approve" and edited):
        raise ValueError("inconsistent plan approval identities")


def adapt_tasktopr_execution_handoff(
    subject: ChangeSubject, handoff: Mapping[str, object]
) -> ComponentEvidence:
    """Validate a TaskToPR handoff and adapt it to Safe Delivery execution evidence.

    ``subject`` must be derived independently by the PatchWitness-side caller.
    TaskToPR's ``change_scope_sha256`` and execution-policy digest are validated and
    included in the details digest, but they never replace ``subject.manifest_sha256``
    or ``subject.policy_sha256``.
    """

    subject.validate()
    envelope = _mapping(handoff, {"payload", "receipt_sha256"}, "TaskToPR handoff")
    payload = envelope["payload"]
    if not isinstance(payload, Mapping):
        raise ValueError("TaskToPR handoff payload must be an object")
    payload_dict = dict(payload)
    receipt_sha256 = _digest(envelope["receipt_sha256"], "handoff receipt digest")
    if content_digest(payload_dict) != receipt_sha256:
        raise ValueError("TaskToPR handoff digest mismatch")

    schema = payload_dict.get("schema_version")
    fields = {
        "schema_version",
        "component",
        "producer",
        "change",
        "policy",
        "verification",
        "source_receipt",
        "trust_boundary",
    }
    if schema == _SCHEMA_V2:
        fields.add("plan_approval")
    elif schema != _SCHEMA_V1:
        raise ValueError("unsupported TaskToPR handoff schema")
    payload_dict = _mapping(payload_dict, fields, "TaskToPR handoff payload")
    if payload_dict["component"] != "execution":
        raise ValueError("TaskToPR handoff is not execution evidence")

    producer = _mapping(
        payload_dict["producer"],
        {"name", "version", "git_revision", "source_sha256"},
        "TaskToPR producer",
    )
    if producer["name"] != "tasktopr":
        raise ValueError("unexpected TaskToPR producer name")
    _text(producer["version"], "TaskToPR version", _VERSION)
    tool_revision = _sha(producer["git_revision"], "TaskToPR producer revision")
    _digest(producer["source_sha256"], "TaskToPR source digest")

    change = _mapping(
        payload_dict["change"],
        {"repository_sha256", "base_sha", "head_sha", "changed_file_count", "change_scope_sha256"},
        "TaskToPR change",
    )
    repository_sha256 = _digest(change["repository_sha256"], "repository identity")
    base_sha = _sha(change["base_sha"], "base revision")
    head_sha = _sha(change["head_sha"], "head revision")
    changed_file_count = _bounded_count(change["changed_file_count"], "changed-file count")
    _digest(change["change_scope_sha256"], "TaskToPR change-scope digest")

    policy = _mapping(payload_dict["policy"], {"version", "sha256"}, "TaskToPR policy")
    _text(policy["version"], "TaskToPR policy version", _VERSION)
    _digest(policy["sha256"], "TaskToPR execution-policy digest")

    verification = _mapping(
        payload_dict["verification"],
        {
            "decision",
            "complete",
            "tests_status",
            "tests_count",
            "command_list_sha256",
            "test_result_sha256",
            "protected_path_decision",
        },
        "TaskToPR verification",
    )
    producer_decision = _text(verification["decision"], "TaskToPR verification decision")
    if producer_decision == "PASS":
        raise ValueError("TaskToPR execution handoff cannot authorize PASS")
    if producer_decision not in {"FAIL", "REVIEW_REQUIRED", "UNKNOWN"}:
        raise ValueError("invalid TaskToPR verification decision")
    if type(verification["complete"]) is not bool:
        raise ValueError("TaskToPR verification completeness must be boolean")
    tests_status = _text(verification["tests_status"], "TaskToPR tests status")
    if tests_status not in {"pass", "fail", "unknown"}:
        raise ValueError("invalid TaskToPR tests status")
    tests_count = _bounded_count(verification["tests_count"], "test count")
    _digest(verification["command_list_sha256"], "command-list digest")
    _digest(verification["test_result_sha256"], "test-result digest")
    protected = _text(verification["protected_path_decision"], "protected-path decision")
    if protected not in {"allow", "deny", "unknown"}:
        raise ValueError("invalid protected-path decision")

    source_receipt = _mapping(
        payload_dict["source_receipt"], {"schema_version", "sha256"}, "TaskToPR source receipt"
    )
    source_schema = source_receipt["schema_version"]
    expected_source_schema = 2 if schema == _SCHEMA_V2 else 1
    if type(source_schema) is not int or source_schema != expected_source_schema:
        raise ValueError("TaskToPR handoff/source schema mismatch")
    _digest(source_receipt["sha256"], "TaskToPR source receipt digest")
    _text(payload_dict["trust_boundary"], "TaskToPR trust boundary")
    if schema == _SCHEMA_V2:
        _validate_plan_approval(payload_dict["plan_approval"])

    decision = DeliveryDecision(producer_decision)
    complete = bool(verification["complete"])
    rules: set[str] = set()
    if (
        repository_sha256 != subject.repository_sha256
        or base_sha != subject.base_sha
        or head_sha != subject.head_sha
    ):
        decision = DeliveryDecision.FAIL
        rules.add("TTA001")
    if producer_decision == "FAIL" or tests_status == "fail" or protected == "deny":
        decision = DeliveryDecision.FAIL
        rules.add("TTA002")
    elif decision != DeliveryDecision.FAIL and (
        producer_decision == "UNKNOWN"
        or tests_status == "unknown"
        or protected == "unknown"
        or not complete
    ):
        decision = DeliveryDecision.UNKNOWN
        rules.add("TTA003")

    evidence = ComponentEvidence(
        component="execution",
        tool="tasktopr",
        tool_revision=tool_revision,
        subject=subject,
        decision=decision,
        complete=complete,
        details_sha256=content_digest(
            {"handoff": payload_dict, "receipt_sha256": receipt_sha256}
        ),
        rule_ids=tuple(sorted(rules)),
        metrics={
            "changed_file_count": changed_file_count,
            "source_schema": expected_source_schema,
            "tests_count": tests_count,
        },
    )
    evidence.validate()
    return evidence
