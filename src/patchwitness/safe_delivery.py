"""Pure composition of exact-subject evidence from explicitly pinned producers.

No plugin discovery, command execution or target imports occur here. Producers
and their adapters remain a trust boundary; hashes are not authentication.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

SCHEMA = "patchwitness.dev/safe-delivery/v1"
COMPONENTS = (
    "api",
    "dependencies",
    "tests",
    "complexity",
    "privacy",
    "artifacts",
    "policy",
    "execution",
    "ci",
    "review",
)
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_CODE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}")
_METRIC = re.compile(r"[a-z][a-z0-9_]{0,39}")


class DeliveryDecision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ChangeSubject:
    repository_sha256: str
    base_sha: str
    head_sha: str
    manifest_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "repository_sha256": self.repository_sha256,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "manifest_sha256": self.manifest_sha256,
        }

    def validate(self) -> None:
        if not all(isinstance(v, str) for v in self.to_dict().values()):
            raise ValueError("subject fields must be strings")
        if not _SHA.fullmatch(self.base_sha) or not _SHA.fullmatch(self.head_sha):
            raise ValueError("subject requires exact 40-character Git revisions")
        if not _DIGEST.fullmatch(self.repository_sha256) or not _DIGEST.fullmatch(
            self.manifest_sha256
        ):
            raise ValueError("subject requires repository and manifest SHA-256 identities")


@dataclass(frozen=True)
class ComponentEvidence:
    component: str
    tool: str
    tool_revision: str
    subject: ChangeSubject
    decision: DeliveryDecision
    complete: bool
    details_sha256: str
    rule_ids: tuple[str, ...] = ()
    metrics: Mapping[str, int] = field(default_factory=dict)

    def validate(self) -> None:
        self.subject.validate()
        if self.component not in COMPONENTS or not isinstance(self.decision, DeliveryDecision):
            raise ValueError("unknown component or decision")
        if not isinstance(self.tool, str) or not _CODE.fullmatch(self.tool):
            raise ValueError("invalid producer name")
        if not isinstance(self.tool_revision, str) or not _SHA.fullmatch(self.tool_revision):
            raise ValueError("producer must have an exact Git revision")
        if (
            type(self.complete) is not bool
            or not isinstance(self.details_sha256, str)
            or not _DIGEST.fullmatch(self.details_sha256)
        ):
            raise ValueError("invalid completeness or details digest")
        if len(self.rule_ids) > 100 or any(
            not isinstance(code, str) or not _CODE.fullmatch(code) for code in self.rule_ids
        ):
            raise ValueError("invalid or excessive rule identifiers")
        if len(self.metrics) > 32 or any(
            not isinstance(key, str)
            or not _METRIC.fullmatch(key)
            or type(value) is not int
            or abs(value) > 1_000_000_000
            for key, value in self.metrics.items()
        ):
            raise ValueError("invalid or excessive evidence metrics")

    def public_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "tool_revision": self.tool_revision,
            "decision": self.decision.value,
            "complete": self.complete,
            "details_sha256": self.details_sha256,
            "rule_ids": sorted(set(self.rule_ids)),
            "metrics": dict(sorted(self.metrics.items())),
        }


def content_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def compose_safe_delivery(
    subject: ChangeSubject,
    evidence: Sequence[ComponentEvidence],
    *,
    trusted_tools: Mapping[str, tuple[str, str]],
    policy_sha256: str,
    stage: str = "merge",
) -> dict[str, Any]:
    """Compose facts without upgrading unknown, incomplete or mismatched evidence.

    trusted_tools and policy_sha256 must come from reviewer-controlled policy,
    never from the candidate tree or the producer payload. PR-stage results do
    not authorize merge/release. All output is limited to identifiers/digests and
    bounded numeric metrics; raw prompts, paths and output are not copied.
    """
    subject.validate()
    if (
        stage not in {"pr", "merge", "release"}
        or not isinstance(policy_sha256, str)
        or not _DIGEST.fullmatch(policy_sha256)
    ):
        raise ValueError("invalid delivery stage or policy identity")
    if len(evidence) > len(COMPONENTS) or set(trusted_tools) - set(COMPONENTS):
        raise ValueError("unexpected or excessive components")
    for value in trusted_tools.values():
        if (
            not isinstance(value, tuple)
            or len(value) != 2
            or not all(isinstance(v, str) for v in value)
            or not _CODE.fullmatch(value[0])
            or not _SHA.fullmatch(value[1])
        ):
            raise ValueError("trusted tool policy requires exact producer pins")
    records: dict[str, ComponentEvidence] = {}
    for supplied in evidence:
        supplied.validate()
        if supplied.component in records:
            raise ValueError("duplicate component evidence")
        records[supplied.component] = supplied
    findings: list[dict[str, str]] = []
    decisions = []
    sections: dict[str, Any] = {}
    for name in COMPONENTS:
        record = records.get(name)
        if record is None:
            decision = (
                DeliveryDecision.REVIEW_REQUIRED
                if stage == "pr" and name in {"ci", "review"}
                else DeliveryDecision.UNKNOWN
            )
            sections[name] = {"decision": "UNKNOWN", "complete": False}
            findings.append({"rule_id": "SD001", "component": name, "decision": decision.value})
        else:
            sections[name] = record.public_dict()
            decision = record.decision
            if record.subject != subject:
                decision = DeliveryDecision.FAIL
                findings.append({"rule_id": "SD002", "component": name, "decision": decision.value})
            if trusted_tools.get(name) != (record.tool, record.tool_revision):
                decision = DeliveryDecision.FAIL
                findings.append({"rule_id": "SD003", "component": name, "decision": decision.value})
            if not record.complete and decision == DeliveryDecision.PASS:
                decision = DeliveryDecision.UNKNOWN
                findings.append({"rule_id": "SD004", "component": name, "decision": decision.value})
            if decision != DeliveryDecision.PASS:
                findings.append({"rule_id": "SD005", "component": name, "decision": decision.value})
            sections[name]["producer_decision"] = record.decision.value
            sections[name]["decision"] = decision.value
            sections[name]["subject"] = record.subject.to_dict()
        decisions.append(decision)
    decision = next(
        (
            item
            for item in (
                DeliveryDecision.FAIL,
                DeliveryDecision.UNKNOWN,
                DeliveryDecision.REVIEW_REQUIRED,
            )
            if item in decisions
        ),
        DeliveryDecision.PASS,
    )
    payload = {
        "schema_version": SCHEMA,
        "stage": stage,
        "decision": decision.value,
        **sections,
        "policy_identity_sha256": policy_sha256,
        "provenance": {
            "subject": subject.to_dict(),
            "trusted_tools": {
                key: {"name": value[0], "revision": value[1]}
                for key, value in sorted(trusted_tools.items())
            },
            "hash_semantics": (
                "identity/integrity only; not confidentiality or producer authentication"
            ),
        },
        "findings": findings,
    }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def verify_safe_delivery(report: Mapping[str, Any]) -> dict[str, Any]:
    """Check transport integrity; this cannot authenticate a self-asserted producer."""
    if set(report) != {"payload", "receipt_sha256"} or not isinstance(report["payload"], dict):
        raise ValueError("invalid safe delivery envelope")
    payload = report["payload"]
    if payload.get("schema_version") != SCHEMA or report["receipt_sha256"] != content_digest(
        payload
    ):
        raise ValueError("invalid safe delivery schema or digest")
    return dict(payload)


def safe_delivery_sarif(report: Mapping[str, Any]) -> dict[str, Any]:
    payload = verify_safe_delivery(report)
    results = [
        {
            "ruleId": finding["rule_id"],
            "level": "error" if finding["decision"] == "FAIL" else "warning",
            "message": {"text": f"{finding['component']}: {finding['decision']}"},
        }
        for finding in payload["findings"]
    ]
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PatchWitness Safe Delivery",
                        "rules": [
                            {"id": code} for code in sorted({item["ruleId"] for item in results})
                        ],
                    }
                },
                "results": results,
                "properties": {
                    "decision": payload["decision"],
                    "stage": payload["stage"],
                    "receipt_sha256": report["receipt_sha256"],
                },
            }
        ],
    }


def safe_delivery_summary(report: Mapping[str, Any]) -> str:
    payload = verify_safe_delivery(report)
    lines = [
        f"Safe Delivery ({payload['stage']}): {payload['decision']}",
        f"Receipt: {report['receipt_sha256']}",
    ]
    lines.extend(f"- {name}: {payload[name]['decision']}" for name in COMPONENTS)
    return "\n".join(lines) + "\n"
