from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from patchwitness.safe_delivery import ChangeSubject, DeliveryDecision, content_digest
from patchwitness.tasktopr import (
    TASKTOPR_HANDOFF_SCHEMA,
    TASKTOPR_TRUST_BOUNDARY,
    TaskToPREvidenceError,
    adapt_tasktopr_execution,
    load_tasktopr_handoff,
)

SUBJECT = ChangeSubject("6" * 64, "a" * 40, "b" * 40, "d" * 64, "0" * 64)
TRUSTED_REVISION = "e" * 40


def _handoff() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": TASKTOPR_HANDOFF_SCHEMA,
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
        "policy": {"version": "tasktopr-execution-v1", "sha256": "7" * 64},
        "verification": {
            "decision": "REVIEW_REQUIRED",
            "complete": True,
            "tests_status": "pass",
            "tests_count": 2,
            "command_list_sha256": "2" * 64,
            "test_result_sha256": "3" * 64,
            "protected_path_decision": "allow",
        },
        "source_receipt": {"schema_version": 1, "sha256": "4" * 64},
        "trust_boundary": TASKTOPR_TRUST_BOUNDARY,
    }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def _payload(report: dict[str, object]) -> dict[str, object]:
    payload = report["payload"]
    assert isinstance(payload, dict)
    return payload


def _rehash(report: dict[str, object]) -> None:
    report["receipt_sha256"] = content_digest(_payload(report))


def test_adapter_promotes_verified_execution_facts_under_patchwitness_subject() -> None:
    record = adapt_tasktopr_execution(
        _handoff(), subject=SUBJECT, trusted_revision=TRUSTED_REVISION
    )
    assert record.component == "execution"
    assert record.tool == "tasktopr"
    assert record.tool_revision == TRUSTED_REVISION
    assert record.subject == SUBJECT
    assert record.decision == DeliveryDecision.PASS
    assert record.complete is True
    assert record.rule_ids == ("TASKTOPR_VERIFIED_HEAD",)
    assert record.metrics == {"changed_file_count": 2, "tests_count": 2}


def test_tasktopr_scope_and_execution_policy_do_not_replace_patchwitness_identities() -> None:
    report = _handoff()
    payload = _payload(report)
    change = payload["change"]
    policy = payload["policy"]
    assert isinstance(change, dict) and isinstance(policy, dict)
    assert change["change_scope_sha256"] != SUBJECT.manifest_sha256
    assert policy["sha256"] != SUBJECT.policy_sha256
    record = adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)
    assert record.subject.manifest_sha256 == SUBJECT.manifest_sha256
    assert record.subject.policy_sha256 == SUBJECT.policy_sha256


@pytest.mark.parametrize("field", ["repository_sha256", "base_sha", "head_sha"])
def test_adapter_rejects_a_different_change_subject(field: str) -> None:
    report = _handoff()
    change = _payload(report)["change"]
    assert isinstance(change, dict)
    current = change[field]
    assert isinstance(current, str)
    change[field] = "f" * len(current)
    _rehash(report)
    with pytest.raises(TaskToPREvidenceError, match="different change subject"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_adapter_rejects_unreviewed_producer_revision() -> None:
    with pytest.raises(TaskToPREvidenceError, match="reviewer pin"):
        adapt_tasktopr_execution(_handoff(), subject=SUBJECT, trusted_revision="f" * 40)


@pytest.mark.parametrize(
    "section,field,value,match",
    [
        ("verification", "decision", "PASS", "verified-head"),
        ("verification", "complete", False, "verified-head"),
        ("verification", "tests_status", "fail", "verified-head"),
        ("verification", "protected_path_decision", "deny", "verified-head"),
        ("verification", "tests_count", 0, "test count"),
        ("change", "changed_file_count", 10_001, "changed-file count"),
        ("producer", "source_sha256", "raw-source", "SHA-256"),
        ("policy", "sha256", "raw-policy", "SHA-256"),
    ],
)
def test_adapter_rejects_nonfinal_or_unbounded_evidence(
    section: str, field: str, value: object, match: str
) -> None:
    report = _handoff()
    target = _payload(report)[section]
    assert isinstance(target, dict)
    target[field] = value
    _rehash(report)
    with pytest.raises(TaskToPREvidenceError, match=match):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_adapter_rejects_tampering_and_raw_extra_fields() -> None:
    report = _handoff()
    report["receipt_sha256"] = "f" * 64
    with pytest.raises(TaskToPREvidenceError, match="digest"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)

    report = _handoff()
    _payload(report)["raw_output"] = "PRIVATE TEST OUTPUT"
    _rehash(report)
    with pytest.raises(TaskToPREvidenceError, match="unexpected fields"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_adapter_requires_the_declared_tasktopr_trust_boundary() -> None:
    report = _handoff()
    _payload(report)["trust_boundary"] = "merge authorized"
    _rehash(report)
    with pytest.raises(TaskToPREvidenceError, match="trust-boundary"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)


def test_load_handoff_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "handoff.json"
    path.write_text('{"payload":{},"payload":{},"receipt_sha256":"' + "a" * 64 + '"}')
    with pytest.raises(TaskToPREvidenceError, match="duplicate JSON key"):
        load_tasktopr_handoff(path)


def test_load_handoff_round_trips_valid_json(tmp_path: Path) -> None:
    report = _handoff()
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    loaded = load_tasktopr_handoff(path)
    assert loaded == report
    assert adapt_tasktopr_execution(
        loaded, subject=SUBJECT, trusted_revision=TRUSTED_REVISION
    ).details_sha256 == report["receipt_sha256"]


def test_load_handoff_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text(json.dumps(_handoff()), encoding="utf-8")
    link = tmp_path / "handoff.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(TaskToPREvidenceError, match="non-symlink"):
        load_tasktopr_handoff(link)


def test_nested_extra_fields_cannot_be_hidden_by_rehashing() -> None:
    report = deepcopy(_handoff())
    producer = _payload(report)["producer"]
    assert isinstance(producer, dict)
    producer["prompt"] = "secret"
    _rehash(report)
    with pytest.raises(TaskToPREvidenceError, match="unexpected fields"):
        adapt_tasktopr_execution(report, subject=SUBJECT, trusted_revision=TRUSTED_REVISION)
