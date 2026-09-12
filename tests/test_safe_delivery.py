"""Composition contract tests; producer behavior is tested in sibling projects."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from patchwitness.safe_delivery import (
    COMPONENTS,
    ChangeSubject,
    ComponentEvidence,
    compose_safe_delivery,
    content_digest,
    safe_delivery_sarif,
    safe_delivery_summary,
    verify_safe_delivery,
)
from patchwitness.safe_delivery import (
    DeliveryDecision as D,
)

SUBJECT = ChangeSubject("a" * 64, "b" * 40, "c" * 40, "d" * 64)
PINS = {name: (name + "-producer", "e" * 40) for name in COMPONENTS}


def evidence():
    return [
        ComponentEvidence(name, *PINS[name], SUBJECT, D.PASS, True, "f" * 64) for name in COMPONENTS
    ]


def compose(records=None, **kwargs):
    return compose_safe_delivery(
        SUBJECT,
        evidence() if records is None else records,
        trusted_tools=PINS,
        policy_sha256="0" * 64,
        **kwargs,
    )


def test_complete_matching_pinned_evidence_can_pass() -> None:
    report = compose()
    assert verify_safe_delivery(report)["decision"] == "PASS"
    assert report["receipt_sha256"] == content_digest(report["payload"])
    assert safe_delivery_sarif(report)["runs"][0]["results"] == []
    assert "Safe Delivery (merge): PASS" in safe_delivery_summary(report)


@pytest.mark.parametrize("component", COMPONENTS)
def test_missing_component_cannot_pass(component: str) -> None:
    report = compose([r for r in evidence() if r.component != component])
    assert report["payload"]["decision"] == "UNKNOWN"
    assert {f["rule_id"] for f in report["payload"]["findings"]} == {"SD001"}


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("decision", [D.FAIL, D.UNKNOWN, D.REVIEW_REQUIRED])
def test_producer_nonpass_is_preserved(component: str, decision: D) -> None:
    records = [replace(r, decision=decision) if r.component == component else r for r in evidence()]
    assert compose(records)["payload"]["decision"] == decision


@pytest.mark.parametrize("component", COMPONENTS)
def test_incomplete_pass_is_downgraded(component: str) -> None:
    records = [replace(r, complete=False) if r.component == component else r for r in evidence()]
    report = compose(records)
    assert report["payload"]["decision"] == "UNKNOWN"
    assert report["payload"][component]["decision"] == "UNKNOWN"
    assert report["payload"][component]["producer_decision"] == "PASS"


@pytest.mark.parametrize("field", ["repository_sha256", "base_sha", "head_sha", "manifest_sha256"])
def test_mixed_subject_evidence_fails(field: str) -> None:
    records = evidence()
    records[0] = replace(
        records[0], subject=replace(SUBJECT, **{field: "9" * len(getattr(SUBJECT, field))})
    )
    report = compose(records)
    assert report["payload"]["decision"] == "FAIL"
    assert "SD002" in [f["rule_id"] for f in report["payload"]["findings"]]


@pytest.mark.parametrize("field,value", [("tool", "untrusted-tool"), ("tool_revision", "a" * 40)])
def test_unapproved_producer_revision_fails(field: str, value: str) -> None:
    records = evidence()
    records[0] = replace(records[0], **{field: value})
    assert compose(records)["payload"]["decision"] == "FAIL"


def test_failure_dominates_unknown_and_review() -> None:
    records = evidence()
    records[0] = replace(records[0], decision=D.UNKNOWN)
    records[1] = replace(records[1], decision=D.REVIEW_REQUIRED)
    records[2] = replace(records[2], decision=D.FAIL)
    report = compose(records)
    assert report["payload"]["decision"] == "FAIL"
    levels = {item["level"] for item in safe_delivery_sarif(report)["runs"][0]["results"]}
    assert levels == {"warning", "error"}


def test_pr_stage_without_ci_or_review_requires_review() -> None:
    records = [r for r in evidence() if r.component not in {"ci", "review"}]
    assert compose(records, stage="pr")["payload"]["decision"] == "REVIEW_REQUIRED"
    assert compose(records, stage="release")["payload"]["decision"] == "UNKNOWN"


def test_order_does_not_change_receipt() -> None:
    assert compose() == compose(list(reversed(evidence())))


@pytest.mark.parametrize("revision", ["latest", "v1", "a" * 39, "A" * 40, "a" * 41])
def test_nonexact_tool_revision_is_rejected(revision: str) -> None:
    records = evidence()
    records[0] = replace(records[0], tool_revision=revision)
    with pytest.raises(ValueError):
        compose(records)


def test_duplicate_evidence_cannot_overwrite_failure() -> None:
    records = evidence()
    records[-1] = records[0]
    with pytest.raises(ValueError, match="duplicate"):
        compose(records)


@pytest.mark.parametrize(
    "changes",
    [
        {"metrics": {"raw prompt": 1}},
        {"metrics": {"count": True}},
        {"metrics": {"count": 10**10}},
        {"rule_ids": ("SECRET raw output",)},
        {"complete": "true"},
        {"decision": "PASS"},
        {"component": "extra"},
        {"details_sha256": "missing"},
        {"metrics": {"x" * 41: 1}},
    ],
)
def test_malformed_or_unbounded_evidence_is_rejected(changes: dict) -> None:
    records = evidence()
    records[0] = replace(records[0], **changes)
    with pytest.raises(ValueError):
        compose(records)


def test_report_tampering_is_detected() -> None:
    report = compose()
    report["payload"]["decision"] = "FAIL"
    with pytest.raises(ValueError, match="digest"):
        verify_safe_delivery(report)


def test_policy_identity_changes_receipt() -> None:
    report = compose_safe_delivery(SUBJECT, evidence(), trusted_tools=PINS, policy_sha256="1" * 64)
    assert report["receipt_sha256"] != compose()["receipt_sha256"]


def test_public_json_contains_no_arbitrary_raw_text() -> None:
    report = compose()
    text = json.dumps(report)
    assert "stdout" not in text and "command" not in text and "absolutePath" not in text
    assert len(text) < 16_000


@pytest.mark.parametrize("stage", ["", "publish-now", "PASS"])
def test_unknown_stage_is_rejected(stage: str) -> None:
    with pytest.raises(ValueError):
        compose(stage=stage)


def test_unpinned_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        compose_safe_delivery(
            SUBJECT, evidence(), trusted_tools={"api": ("api", "latest")}, policy_sha256="0" * 64
        )
