"""Strict adapter for sanitized TaskToPR Safe Delivery execution handoffs.

TaskToPR supplies execution facts only. PatchWitness owns the candidate subject,
manifest identity, reviewer policy, and producer pin used for composition.
"""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from patchwitness.safe_delivery import (
    ChangeSubject,
    ComponentEvidence,
    DeliveryDecision,
    content_digest,
)

TASKTOPR_HANDOFF_SCHEMA_V1 = "tasktopr.dev/safe-delivery/execution/v1"
TASKTOPR_HANDOFF_SCHEMA_V2 = "tasktopr.dev/safe-delivery/execution/v2"
SUPPORTED_TASKTOPR_HANDOFF_SCHEMAS = frozenset(
    {TASKTOPR_HANDOFF_SCHEMA_V1, TASKTOPR_HANDOFF_SCHEMA_V2}
)
# Backward-compatible alias for callers that imported the original schema constant.
TASKTOPR_HANDOFF_SCHEMA = TASKTOPR_HANDOFF_SCHEMA_V1
TASKTOPR_TRUST_BOUNDARY = (
    "sanitized TaskToPR execution evidence; identity/integrity only; "
    "not confidentiality, a signature, producer authentication, or merge authorization"
)
MAX_HANDOFF_BYTES = 512 * 1024
MAX_TESTS = 10_000
MAX_CHANGED_FILES = 10_000
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}\Z")


class TaskToPREvidenceError(ValueError):
    """Raised when TaskToPR execution evidence cannot be trusted as input."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TaskToPREvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TaskToPREvidenceError(f"{name} must be a JSON object")
    return cast(dict[str, Any], value)


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TaskToPREvidenceError(f"{name} must be a string")
    return value


def _digest(value: Any, name: str) -> str:
    text = _string(value, name)
    if not _DIGEST.fullmatch(text):
        raise TaskToPREvidenceError(f"{name} must be a lowercase SHA-256 digest")
    return text


def _revision(value: Any, name: str) -> str:
    text = _string(value, name)
    if not _SHA.fullmatch(text):
        raise TaskToPREvidenceError(f"{name} must be an exact lowercase Git SHA-1")
    return text


def _plan_approval(value: Any) -> tuple[bool, bool]:
    """Validate v2 approval provenance and return (required, satisfied)."""
    approval = _object(value, "plan_approval")
    if set(approval) != {
        "mode",
        "decision",
        "edited",
        "original_plan_sha256",
        "final_plan_sha256",
        "record_sha256",
    }:
        raise TaskToPREvidenceError("TaskToPR plan approval has unexpected fields")
    mode = _string(approval["mode"], "plan_approval.mode")
    decision = _string(approval["decision"], "plan_approval.decision")
    edited = approval["edited"]
    if type(edited) is not bool:
        raise TaskToPREvidenceError("TaskToPR plan approval edited flag must be boolean")

    if mode == "off":
        if (
            decision != "not_required"
            or edited
            or approval["original_plan_sha256"] is not None
            or approval["final_plan_sha256"] is not None
            or approval["record_sha256"] is not None
        ):
            raise TaskToPREvidenceError("TaskToPR disabled plan approval is inconsistent")
        return False, False

    if mode != "prompt" or decision not in {"approve", "edit"}:
        raise TaskToPREvidenceError("TaskToPR plan approval is not a completed human decision")
    original = _digest(approval["original_plan_sha256"], "plan_approval.original_plan_sha256")
    final = _digest(approval["final_plan_sha256"], "plan_approval.final_plan_sha256")
    _digest(approval["record_sha256"], "plan_approval.record_sha256")
    if edited != (original != final):
        raise TaskToPREvidenceError("TaskToPR plan approval edit identity is inconsistent")
    if decision == "approve" and edited:
        raise TaskToPREvidenceError("TaskToPR approve decision cannot replace the plan")
    return True, True


def load_tasktopr_handoff(path: Path) -> dict[str, Any]:
    """Load one bounded regular handoff file and reject duplicate keys or read races."""
    try:
        before = path.lstat()
    except OSError as exc:
        raise TaskToPREvidenceError(f"unable to stat TaskToPR handoff: {exc}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise TaskToPREvidenceError("TaskToPR handoff must be a regular non-symlink file")
    if before.st_size > MAX_HANDOFF_BYTES:
        raise TaskToPREvidenceError("TaskToPR handoff exceeds the byte budget")
    try:
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise TaskToPREvidenceError(f"unable to read TaskToPR handoff: {exc}") from exc
    if len(data) > MAX_HANDOFF_BYTES:
        raise TaskToPREvidenceError("TaskToPR handoff exceeds the byte budget")
    if path.is_symlink() or (before.st_size, before.st_mtime_ns, before.st_mode) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    ):
        raise TaskToPREvidenceError("TaskToPR handoff changed while it was being read")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskToPREvidenceError("TaskToPR handoff is not valid UTF-8 JSON") from exc
    return _object(value, "TaskToPR handoff")


def adapt_tasktopr_execution(
    report: Mapping[str, Any],
    *,
    subject: ChangeSubject,
    trusted_revision: str,
    trusted_version: str | None = None,
    required_schema: str | None = None,
) -> ComponentEvidence:
    """Convert a validated TaskToPR handoff into PatchWitness execution evidence.

    Only repository/base/head identity is allowed to bind TaskToPR to the supplied
    PatchWitness subject. TaskToPR's change-scope digest and execution-policy digest
    are producer provenance; they never replace PatchWitness's independently derived
    manifest identity or reviewer-owned policy identity. Optional version/schema pins
    are reviewer-controlled compatibility constraints and fail closed on mismatch.
    """
    subject.validate()
    if not _SHA.fullmatch(trusted_revision):
        raise TaskToPREvidenceError("trusted TaskToPR revision must be an exact Git SHA-1")
    if trusted_version is not None and not _VERSION.fullmatch(trusted_version):
        raise TaskToPREvidenceError("trusted TaskToPR version is invalid")
    if required_schema is not None and required_schema not in SUPPORTED_TASKTOPR_HANDOFF_SCHEMAS:
        raise TaskToPREvidenceError("required TaskToPR handoff schema is unsupported")
    if set(report) != {"payload", "receipt_sha256"}:
        raise TaskToPREvidenceError("TaskToPR handoff envelope has unexpected fields")
    payload = _object(report["payload"], "TaskToPR handoff payload")
    receipt_sha256 = _digest(report["receipt_sha256"], "receipt_sha256")
    if content_digest(payload) != receipt_sha256:
        raise TaskToPREvidenceError("TaskToPR handoff digest does not match its payload")

    schema = payload.get("schema_version")
    common_fields = {
        "schema_version",
        "component",
        "producer",
        "change",
        "policy",
        "verification",
        "source_receipt",
        "trust_boundary",
    }
    if schema == TASKTOPR_HANDOFF_SCHEMA_V1:
        if set(payload) != common_fields:
            raise TaskToPREvidenceError("TaskToPR handoff payload has unexpected fields")
        source_schema = 1
        approval_required = False
        approval_satisfied = False
    elif schema == TASKTOPR_HANDOFF_SCHEMA_V2:
        if set(payload) != common_fields | {"plan_approval"}:
            raise TaskToPREvidenceError("TaskToPR handoff payload has unexpected fields")
        source_schema = 2
        approval_required, approval_satisfied = _plan_approval(payload["plan_approval"])
    else:
        raise TaskToPREvidenceError("unsupported TaskToPR execution handoff schema")
    if required_schema is not None and schema != required_schema:
        raise TaskToPREvidenceError("TaskToPR handoff schema does not match reviewer pin")
    if payload["component"] != "execution":
        raise TaskToPREvidenceError("unsupported TaskToPR execution handoff schema")
    if payload["trust_boundary"] != TASKTOPR_TRUST_BOUNDARY:
        raise TaskToPREvidenceError("TaskToPR trust-boundary declaration changed")

    producer = _object(payload["producer"], "producer")
    if set(producer) != {"name", "version", "git_revision", "source_sha256"}:
        raise TaskToPREvidenceError("TaskToPR producer identity has unexpected fields")
    if producer["name"] != "tasktopr":
        raise TaskToPREvidenceError("unexpected execution producer")
    version = _string(producer["version"], "producer.version")
    if not _VERSION.fullmatch(version):
        raise TaskToPREvidenceError("TaskToPR producer version is invalid")
    if trusted_version is not None and version != trusted_version:
        raise TaskToPREvidenceError("TaskToPR producer version does not match reviewer pin")
    producer_revision = _revision(producer["git_revision"], "producer.git_revision")
    if producer_revision != trusted_revision:
        raise TaskToPREvidenceError("TaskToPR producer revision does not match reviewer pin")
    _digest(producer["source_sha256"], "producer.source_sha256")

    change = _object(payload["change"], "change")
    if set(change) != {
        "repository_sha256",
        "base_sha",
        "head_sha",
        "changed_file_count",
        "change_scope_sha256",
    }:
        raise TaskToPREvidenceError("TaskToPR change identity has unexpected fields")
    repository_sha256 = _digest(change["repository_sha256"], "change.repository_sha256")
    base_sha = _revision(change["base_sha"], "change.base_sha")
    head_sha = _revision(change["head_sha"], "change.head_sha")
    if (repository_sha256, base_sha, head_sha) != (
        subject.repository_sha256,
        subject.base_sha,
        subject.head_sha,
    ):
        raise TaskToPREvidenceError("TaskToPR handoff belongs to a different change subject")
    changed_file_count = change["changed_file_count"]
    if type(changed_file_count) is not int or not 0 <= changed_file_count <= MAX_CHANGED_FILES:
        raise TaskToPREvidenceError("TaskToPR changed-file count is outside the budget")
    _digest(change["change_scope_sha256"], "change.change_scope_sha256")

    policy = _object(payload["policy"], "policy")
    if set(policy) != {"version", "sha256"}:
        raise TaskToPREvidenceError("TaskToPR execution policy has unexpected fields")
    policy_version = _string(policy["version"], "policy.version")
    if not _VERSION.fullmatch(policy_version):
        raise TaskToPREvidenceError("TaskToPR execution policy version is invalid")
    _digest(policy["sha256"], "policy.sha256")

    verification = _object(payload["verification"], "verification")
    if set(verification) != {
        "decision",
        "complete",
        "tests_status",
        "tests_count",
        "command_list_sha256",
        "test_result_sha256",
        "protected_path_decision",
    }:
        raise TaskToPREvidenceError("TaskToPR verification evidence has unexpected fields")
    if (
        verification["decision"] != "REVIEW_REQUIRED"
        or verification["complete"] is not True
        or verification["tests_status"] != "pass"
        or verification["protected_path_decision"] != "allow"
    ):
        raise TaskToPREvidenceError("TaskToPR execution is not a complete verified-head result")
    tests_count = verification["tests_count"]
    if type(tests_count) is not int or not 1 <= tests_count <= MAX_TESTS:
        raise TaskToPREvidenceError("TaskToPR test count is outside the budget")
    _digest(verification["command_list_sha256"], "verification.command_list_sha256")
    _digest(verification["test_result_sha256"], "verification.test_result_sha256")

    source_receipt = _object(payload["source_receipt"], "source_receipt")
    if (
        set(source_receipt) != {"schema_version", "sha256"}
        or source_receipt["schema_version"] != source_schema
    ):
        raise TaskToPREvidenceError("TaskToPR source receipt identity is invalid")
    _digest(source_receipt["sha256"], "source_receipt.sha256")

    rule_ids = ["TASKTOPR_VERIFIED_HEAD"]
    metrics = {"changed_file_count": changed_file_count, "tests_count": tests_count}
    if schema == TASKTOPR_HANDOFF_SCHEMA_V2:
        metrics["plan_approval_required"] = int(approval_required)
        metrics["plan_approval_satisfied"] = int(approval_satisfied)
        if approval_satisfied:
            rule_ids.append("TASKTOPR_PLAN_APPROVED")
    if trusted_version is not None:
        rule_ids.append("TASKTOPR_PRODUCER_VERSION_PINNED")
        metrics["producer_version_pin_satisfied"] = 1
    if required_schema is not None:
        rule_ids.append("TASKTOPR_HANDOFF_SCHEMA_PINNED")
        metrics["handoff_schema_pin_satisfied"] = 1

    return ComponentEvidence(
        component="execution",
        tool="tasktopr",
        tool_revision=trusted_revision,
        subject=subject,
        decision=DeliveryDecision.PASS,
        complete=True,
        details_sha256=receipt_sha256,
        rule_ids=tuple(rule_ids),
        metrics=metrics,
    )
