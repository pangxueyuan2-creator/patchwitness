"""Bounded, pure normalization of reviewer-supplied GitHub collector snapshots.

The caller must authenticate the collector, its repository/PR association, freshness,
pagination, and reviewer-owned policy. This module performs no network access and
does not turn a JSON assertion or digest into authenticated GitHub evidence.
Unknown fields are rejected; raw names, authors, titles, and output are never copied
to ComponentEvidence. Check-run IDs order reruns within an app/name pair only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .safe_delivery import ChangeSubject, ComponentEvidence, DeliveryDecision, content_digest

MAX_RECORDS = 1000
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,99}\Z")
_BASE = {"schema_version", "head_sha", "policy_sha256", "complete", "truncated"}
_CHECK = {"name", "app_id", "id", "head_sha", "status", "conclusion"}
_REVIEW = {"id", "author", "commit_id", "state"}
_STATUSES = {"queued", "in_progress", "completed", "waiting", "pending", "requested"}
_CONCLUSIONS = {
    "success", "failure", "cancelled", "timed_out", "action_required", "startup_failure",
    "skipped", "neutral", "stale",
}
_FAILURES = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED", "COMMENTED", "PENDING"}


@dataclass(frozen=True)
class RequiredCheck:
    name: str
    app_id: int


def _text(value: object, *, maximum: int = 200) -> bool:
    return (
        isinstance(value, str) and 1 <= len(value) <= maximum
        and all(32 <= ord(char) < 127 for char in value)
    )


def _integer(value: object, *, positive: bool = True) -> bool:
    return type(value) is int and (1 if positive else 0) <= value <= 2**63 - 1


def _mapping(value: object, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > len(allowed) or set(value) - allowed:
        raise ValueError("malformed hosted snapshot fields")
    result = dict(value)
    for name, item in result.items():
        if name in {"checks", "reviews"}:
            if not isinstance(item, list) or len(item) > MAX_RECORDS:
                raise ValueError("invalid or excessive hosted records")
        elif item is not None and (
            type(item) not in {str, int, bool}
            or (isinstance(item, str) and not _text(item))
            or (type(item) is int and not -(2**63) <= item <= 2**63 - 1)
        ):
            raise ValueError("invalid or oversized hosted scalar")
    return result


def _base(
    subject: ChangeSubject, snapshot: Mapping[str, object], policy_sha256: str, extras: set[str],
) -> tuple[dict[str, Any], set[str], bool]:
    subject.validate()
    if not isinstance(policy_sha256, str) or not _DIGEST.fullmatch(policy_sha256):
        raise ValueError("reviewer policy requires a SHA-256 identity")
    if policy_sha256 != subject.policy_sha256:
        raise ValueError("subject does not match reviewer-owned policy")
    data = _mapping(snapshot, _BASE | extras)
    reasons: set[str] = set()
    if not data.keys() >= _BASE:
        reasons.add("HE001")
    if "schema_version" in data and (
        type(data["schema_version"]) is not int or data["schema_version"] != 1
    ):
        raise ValueError("unsupported hosted snapshot schema")
    for name in ("complete", "truncated"):
        if name in data and type(data[name]) is not bool:
            raise ValueError("snapshot completeness must be explicit booleans")
    for name, pattern in (("head_sha", _SHA), ("policy_sha256", _DIGEST)):
        if name in data and (
            not isinstance(data[name], str) or not pattern.fullmatch(data[name])
        ):
            raise ValueError("invalid hosted evidence identity")
    if data.get("head_sha", subject.head_sha) != subject.head_sha:
        reasons.add("HE002")
    if data.get("policy_sha256", policy_sha256) != policy_sha256:
        reasons.add("HE003")
    complete = data.keys() >= _BASE and data["complete"] and not data["truncated"]
    if not complete:
        reasons.add("HE001")
    return data, reasons, bool(complete)


def _records(data: dict[str, Any], name: str, allowed: set[str]) -> list[dict[str, Any]]:
    values = data.get(name, [])
    if not isinstance(values, list) or len(values) > MAX_RECORDS:
        raise ValueError("invalid or excessive hosted records")
    return [_mapping(item, allowed) for item in values]


def _evidence(
    component: str, subject: ChangeSubject, data: dict[str, Any], reasons: set[str],
    complete: bool, tool_revision: str, metrics: dict[str, int], policy: dict[str, Any],
) -> ComponentEvidence:
    decision = DeliveryDecision.PASS
    if reasons & {"HE002", "HE003", "HE006", "HE013"}:
        decision = DeliveryDecision.FAIL
    elif reasons & {"HE001", "HE004", "HE005", "HE007", "HE008", "HE010"}:
        decision = DeliveryDecision.UNKNOWN
    elif reasons:
        decision = DeliveryDecision.REVIEW_REQUIRED
    result = ComponentEvidence(
        component=component, tool="patchwitness-hosted", tool_revision=tool_revision,
        subject=subject, decision=decision, complete=complete,
        details_sha256=content_digest({"snapshot": data, "normalizer_policy": policy}),
        rule_ids=tuple(sorted(reasons)), metrics=metrics,
    )
    result.validate()
    return result


def normalize_ci(
    subject: ChangeSubject, snapshot: Mapping[str, object], *,
    required_checks: Sequence[RequiredCheck], policy_sha256: str, tool_revision: str,
) -> ComponentEvidence:
    """Require completed success for each reviewer-owned name/app, at the exact head.

    Missing checks/completeness and ambiguous duplicate IDs remain UNKNOWN. The
    newest run ID in each required app/name pair supersedes earlier attempts.
    Neutral/skipped conclusions do not satisfy this conservative success policy.
    """
    if not 1 <= len(required_checks) <= MAX_RECORDS:
        raise ValueError("reviewer must provide a bounded nonempty check policy")
    required: set[tuple[str, int]] = set()
    for requirement in required_checks:
        if (
            not isinstance(requirement, RequiredCheck)
            or not _text(requirement.name) or not _integer(requirement.app_id)
        ):
            raise ValueError("required checks must pin a bounded name and app ID")
        pair = (requirement.name, requirement.app_id)
        if pair in required:
            raise ValueError("duplicate required check policy")
        required.add(pair)
    data, reasons, complete = _base(subject, snapshot, policy_sha256, {"checks"})
    if "checks" not in data:
        reasons.add("HE001")
        complete = False
    checks = _records(data, "checks", _CHECK)
    newest: dict[tuple[str, int], dict[str, Any]] = {}
    seen: dict[int, dict[str, Any]] = {}
    for check in checks:
        missing = set(check) != _CHECK
        if missing:
            reasons.add("HE001")
            complete = False
            check = {
                "name": "missing", "app_id": 1, "id": 1, "head_sha": subject.head_sha,
                "status": "completed", "conclusion": None,
            } | check
        if (
            not _text(check["name"]) or not _integer(check["app_id"])
            or not _integer(check["id"]) or not isinstance(check["head_sha"], str)
            or not _SHA.fullmatch(check["head_sha"])
            or not isinstance(check["status"], str) or check["status"] not in _STATUSES
            or (check["conclusion"] is not None and (
                not isinstance(check["conclusion"], str) or check["conclusion"] not in _CONCLUSIONS
            ))
            or (check["status"] != "completed" and check["conclusion"] is not None)
        ):
            raise ValueError("malformed check-run metadata")
        if missing:
            continue
        if check["head_sha"] != subject.head_sha:
            reasons.add("HE002")
        if check["id"] in seen:
            reasons.add("HE008")
            complete = False
        seen[check["id"]] = check
        pair = (check["name"], check["app_id"])
        if pair in required and (pair not in newest or newest[pair]["id"] < check["id"]):
            newest[pair] = check
    for pair in sorted(required):
        selected = newest.get(pair)
        if selected is None:
            reasons.add("HE004")
        elif selected["status"] != "completed" or selected["conclusion"] is None:
            reasons.add("HE005")
        elif selected["conclusion"] in _FAILURES:
            reasons.add("HE006")
        elif selected["conclusion"] != "success":
            reasons.add("HE007")
    return _evidence("ci", subject, data, reasons, complete, tool_revision, {
        "record_count": len(checks), "required_count": len(required), "matched_count": len(newest),
    }, {"required_checks": sorted(required)})


def normalize_review(
    subject: ChangeSubject, snapshot: Mapping[str, object], *,
    required_approvals: int, policy_sha256: str, tool_revision: str,
) -> ComponentEvidence:
    """Require an approved GitHub decision, no unresolved threads and non-author approvals.

    Reviewer eligibility/identity and GitHub approval rules are collector obligations;
    login metadata alone does not prove human identity or authority to approve.
    Exact-head, latest substantive non-author reviews are counted; comment/pending
    records cannot approve or dismiss an earlier request for changes. A dismissed
    latest review withdraws that reviewer's approval. No self-review is counted.
    """
    if type(required_approvals) is not int or not 1 <= required_approvals <= MAX_RECORDS:
        raise ValueError("reviewer policy requires a bounded positive approval count")
    fields = {"author", "review_decision", "unresolved_threads", "reviews"}
    data, reasons, complete = _base(subject, snapshot, policy_sha256, fields)
    if not fields <= data.keys():
        reasons.add("HE001")
        complete = False
    if "author" in data and (
        not isinstance(data["author"], str) or not _LOGIN.fullmatch(data["author"])
    ):
        raise ValueError("invalid pull request author")
    if "review_decision" in data and (
        not isinstance(data["review_decision"], str)
        or data["review_decision"] not in {"APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED"}
    ):
        raise ValueError("invalid GitHub review decision")
    if "unresolved_threads" in data and (
        not _integer(data["unresolved_threads"], positive=False)
        or data["unresolved_threads"] > MAX_RECORDS
    ):
        raise ValueError("invalid or excessive unresolved thread count")
    reviews = _records(data, "reviews", _REVIEW)
    newest: dict[str, dict[str, Any]] = {}
    seen: set[int] = set()
    for review in reviews:
        missing = set(review) != _REVIEW
        if missing:
            reasons.add("HE001")
            complete = False
            review = {
                "id": 1, "author": "missing", "commit_id": subject.head_sha, "state": "PENDING",
            } | review
        if (
            not _integer(review["id"]) or not isinstance(review["author"], str)
            or not _LOGIN.fullmatch(review["author"])
            or not isinstance(review["commit_id"], str) or not _SHA.fullmatch(review["commit_id"])
            or not isinstance(review["state"], str) or review["state"] not in _STATES
        ):
            raise ValueError("malformed review metadata")
        if missing:
            continue
        if review["id"] in seen:
            reasons.add("HE008")
            complete = False
        seen.add(review["id"])
        if review["commit_id"] != subject.head_sha:
            reasons.add("HE010")
            continue
        author = review["author"].casefold()
        if author == str(data.get("author", "")).casefold():
            continue
        if review["state"] in {"COMMENTED", "PENDING"}:
            continue
        if author not in newest or newest[author]["id"] < review["id"]:
            newest[author] = review
    approvals = sum(review["state"] == "APPROVED" for review in newest.values())
    if data.get("review_decision") == "CHANGES_REQUESTED" or any(
        review["state"] == "CHANGES_REQUESTED" for review in newest.values()
    ):
        reasons.add("HE013")
    if data.get("unresolved_threads", 0) > 0:
        reasons.add("HE011")
    if approvals < required_approvals or data.get("review_decision") != "APPROVED":
        reasons.add("HE012")
    return _evidence("review", subject, data, reasons, complete, tool_revision, {
        "record_count": len(reviews), "approval_count": approvals,
        "required_approvals": required_approvals,
    }, {"required_approvals": required_approvals})
