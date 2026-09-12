from __future__ import annotations

import copy
import json

import pytest

from patchwitness.hosted_evidence import RequiredCheck, normalize_ci, normalize_review
from patchwitness.safe_delivery import ChangeSubject, DeliveryDecision

HEAD = "a" * 40
POLICY = "b" * 64
TOOL = "c" * 40
SUBJECT = ChangeSubject("d" * 64, "e" * 40, HEAD, "f" * 64, POLICY)
REQUIRED = [RequiredCheck("trusted-ci", 15368)]


def check(**updates):
    return dict(name="trusted-ci", app_id=15368, id=20, head_sha=HEAD,
                status="completed", conclusion="success") | updates


def ci(**updates):
    return dict(schema_version=1, head_sha=HEAD, policy_sha256=POLICY,
                complete=True, truncated=False, checks=[check()]) | updates


def review_record(**updates):
    return dict(id=10, author="reviewer", commit_id=HEAD, state="APPROVED") | updates


def review(**updates):
    return dict(schema_version=1, head_sha=HEAD, policy_sha256=POLICY, complete=True,
                truncated=False, author="candidate-author", review_decision="APPROVED",
                unresolved_threads=0, reviews=[review_record()]) | updates


def normalize(snapshot):
    return normalize_ci(SUBJECT, snapshot, required_checks=REQUIRED,
                        policy_sha256=POLICY, tool_revision=TOOL)


def normalize_r(snapshot, **updates):
    args = dict(required_approvals=1, policy_sha256=POLICY, tool_revision=TOOL) | updates
    return normalize_review(SUBJECT, snapshot, **args)


def test_exact_head_app_bound_success_passes_without_copying_metadata():
    result = normalize(ci())
    assert result.decision == DeliveryDecision.PASS and result.complete
    encoded = json.dumps(result.public_dict())
    assert "trusted-ci" not in encoded and HEAD not in encoded
    assert result.metrics == {"record_count": 1, "required_count": 1, "matched_count": 1}


@pytest.mark.parametrize("field", ["complete", "truncated", "head_sha", "policy_sha256",
                                    "schema_version", "checks"])
def test_missing_ci_snapshot_metadata_is_unknown(field):
    data = ci()
    del data[field]
    result = normalize(data)
    assert result.decision == DeliveryDecision.UNKNOWN
    assert "HE001" in result.rule_ids and not result.complete


@pytest.mark.parametrize("updates", [{"complete": False}, {"truncated": True}])
def test_incomplete_or_truncated_ci_is_unknown(updates):
    assert normalize(ci(**updates)).decision == DeliveryDecision.UNKNOWN


@pytest.mark.parametrize("updates", [{"head_sha": "1" * 40}, {"policy_sha256": "2" * 64}])
def test_stale_ci_subject_or_wrong_policy_fails(updates):
    result = normalize(ci(**updates))
    assert result.decision == DeliveryDecision.FAIL
    assert set(result.rule_ids) & {"HE002", "HE003"}


def test_stale_check_run_fails_even_with_matching_snapshot():
    result = normalize(ci(checks=[check(head_sha="1" * 40)]))
    assert result.decision == DeliveryDecision.FAIL and "HE002" in result.rule_ids


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending"])
def test_queued_or_running_checks_are_unknown(status):
    result = normalize(ci(checks=[check(status=status, conclusion=None)]))
    assert result.decision == DeliveryDecision.UNKNOWN and "HE005" in result.rule_ids


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "action_required",
                                         "startup_failure", "stale"])
def test_failed_exact_head_check_fails(conclusion):
    result = normalize(ci(checks=[check(conclusion=conclusion)]))
    assert result.decision == DeliveryDecision.FAIL and "HE006" in result.rule_ids


@pytest.mark.parametrize("conclusion", [None, "neutral", "skipped"])
def test_completed_check_without_success_is_unknown(conclusion):
    assert normalize(ci(checks=[check(conclusion=conclusion)])).decision == DeliveryDecision.UNKNOWN


def test_spoofed_same_name_different_app_cannot_satisfy_policy():
    result = normalize(ci(checks=[check(app_id=999)]))
    assert result.decision == DeliveryDecision.UNKNOWN and "HE004" in result.rule_ids


def test_latest_rerun_is_deterministic_and_cannot_hide_new_failure():
    old, new = check(id=10), check(id=20, conclusion="failure")
    for records in ([old, new], [new, old]):
        result = normalize(ci(checks=records))
        assert result.decision == DeliveryDecision.FAIL and "HE006" in result.rule_ids
    old["conclusion"], new["conclusion"] = "failure", "success"
    assert normalize(ci(checks=[new, old])).decision == DeliveryDecision.PASS


def test_duplicate_run_ids_are_unknown_even_when_identical():
    result = normalize(ci(checks=[check(), check()]))
    assert result.decision == DeliveryDecision.UNKNOWN and "HE008" in result.rule_ids
    assert not result.complete


def test_missing_check_field_is_unknown():
    record = check()
    del record["app_id"]
    assert normalize(ci(checks=[record])).decision == DeliveryDecision.UNKNOWN


@pytest.mark.parametrize("value", [True, "15368", -1, 0, 2**64])
def test_malformed_app_ids_rejected(value):
    with pytest.raises(ValueError):
        normalize(ci(checks=[check(app_id=value)]))


@pytest.mark.parametrize("updates", [{"complete": "true"}, {"checks": "all green"},
    {"schema_version": True}, {"schema_version": 2}, {"head_sha": "main"},
    {"title": "secret"}, {"checks": [check(output="secret")]},
    {"checks": [check(name="x" * 201)]}, {"checks": [check(status="queued")]},
    {"checks": [{}] * 1001}, {"checks": [{"name": {"nested": "unbounded"}}]}])
def test_malformed_or_excessive_snapshot_is_rejected(updates):
    with pytest.raises(ValueError):
        normalize(ci(**updates))


def test_check_policy_requires_unique_names_with_app_pin():
    for checks in ([], REQUIRED * 2, [RequiredCheck("trusted-ci", True)]):
        with pytest.raises(ValueError):
            normalize_ci(SUBJECT, ci(), required_checks=checks, policy_sha256=POLICY,
                         tool_revision=TOOL)


def test_normalizer_policy_is_bound_into_details_digest():
    one = normalize_r(review())
    two = normalize_r(review(), required_approvals=2)
    assert one.details_sha256 != two.details_sha256
    with pytest.raises(ValueError):
        normalize_r(review(), policy_sha256="1" * 64)


def test_approved_complete_exact_head_review_passes():
    result = normalize_r(review())
    assert result.decision == DeliveryDecision.PASS
    assert "reviewer" not in json.dumps(result.public_dict())
    assert result.metrics["approval_count"] == 1


@pytest.mark.parametrize("field", ["author", "reviews", "review_decision", "unresolved_threads",
                                    "complete", "truncated"])
def test_missing_review_metadata_is_unknown(field):
    data = review()
    del data[field]
    result = normalize_r(data)
    assert result.decision == DeliveryDecision.UNKNOWN and "HE001" in result.rule_ids


def test_unresolved_review_threads_require_review():
    result = normalize_r(review(unresolved_threads=1))
    assert result.decision == DeliveryDecision.REVIEW_REQUIRED and "HE011" in result.rule_ids


def test_self_review_never_counts_as_approval():
    result = normalize_r(review(reviews=[review_record(author="CANDIDATE-AUTHOR")]))
    assert result.decision == DeliveryDecision.REVIEW_REQUIRED and "HE012" in result.rule_ids
    assert result.metrics["approval_count"] == 0


def test_changes_requested_fails_despite_forged_approved_aggregate():
    result = normalize_r(review(reviews=[review_record(state="CHANGES_REQUESTED")]))
    assert result.decision == DeliveryDecision.FAIL and "HE013" in result.rule_ids


def test_latest_substantive_review_controls_approval_and_comments_do_not_dismiss():
    old = review_record(state="CHANGES_REQUESTED")
    comment = review_record(id=20, state="COMMENTED")
    assert normalize_r(review(reviews=[old, comment])).decision == DeliveryDecision.FAIL
    approved = review_record(id=30)
    assert normalize_r(review(reviews=[approved, old, comment])).decision == DeliveryDecision.PASS
    dismissed = review_record(id=40, state="DISMISSED")
    result = normalize_r(review(reviews=[approved, dismissed]))
    assert result.decision == DeliveryDecision.REVIEW_REQUIRED


def test_approval_at_older_commit_is_unknown():
    result = normalize_r(review(reviews=[review_record(commit_id="1" * 40)]))
    assert result.decision == DeliveryDecision.UNKNOWN and "HE010" in result.rule_ids


def test_stale_review_snapshot_fails():
    result = normalize_r(review(head_sha="1" * 40))
    assert result.decision == DeliveryDecision.FAIL and "HE002" in result.rule_ids


@pytest.mark.parametrize("updates", [{"unresolved_threads": -1}, {"unresolved_threads": True},
    {"unresolved_threads": 1001}, {"review_decision": "GREEN"}, {"author": []},
    {"reviews": [{}] * 1001}, {"reviews": [review_record(state="APPROVAL")]},
    {"reviews": [review_record(author="x" * 101)]}])
def test_malformed_review_is_rejected(updates):
    with pytest.raises(ValueError):
        normalize_r(review(**updates))


def test_inputs_are_unchanged_and_duplicate_reviews_are_unknown():
    data = review(reviews=[review_record(), review_record()])
    before = copy.deepcopy(data)
    result = normalize_r(data)
    assert data == before
    assert result.decision == DeliveryDecision.UNKNOWN and "HE008" in result.rule_ids


def test_malformed_present_field_is_not_hidden_by_missing_metadata():
    with pytest.raises(ValueError):
        normalize(ci(checks=[{"id": "invalid"}]))
    with pytest.raises(ValueError):
        normalize_r(review(reviews=[{"id": "invalid"}]))


def test_check_policy_alteration_changes_evidence_digest():
    original = normalize(ci())
    changed = normalize_ci(
        SUBJECT, ci(), required_checks=[RequiredCheck("trusted-ci", 999)],
        policy_sha256=POLICY, tool_revision=TOOL,
    )
    assert original.details_sha256 != changed.details_sha256
    assert changed.decision == DeliveryDecision.UNKNOWN
