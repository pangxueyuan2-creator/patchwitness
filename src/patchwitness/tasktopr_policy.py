"""Consumer-side policy for TaskToPR plan-approval provenance."""

from __future__ import annotations

from typing import Any

from patchwitness.safe_delivery import verify_safe_delivery


class TaskToPRApprovalPolicyError(ValueError):
    """Raised when reviewer-required TaskToPR plan approval is not proven."""


def require_tasktopr_plan_approval(report: dict[str, Any]) -> None:
    """Fail closed unless a verified TaskToPR human plan approval is present.

    The Safe Delivery envelope has already been built from a strictly validated TaskToPR
    handoff. This consumer policy checks only bounded public execution evidence and never
    upgrades plan approval into merge or release authorization.
    """
    payload = verify_safe_delivery(report)
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        raise TaskToPRApprovalPolicyError(
            "TaskToPR human plan approval is required but unavailable"
        )
    metrics = execution.get("metrics")
    rule_ids = execution.get("rule_ids")
    if (
        execution.get("decision") != "PASS"
        or not isinstance(metrics, dict)
        or metrics.get("plan_approval_required") != 1
        or metrics.get("plan_approval_satisfied") != 1
        or not isinstance(rule_ids, list)
        or "TASKTOPR_PLAN_APPROVED" not in rule_ids
    ):
        raise TaskToPRApprovalPolicyError(
            "TaskToPR human plan approval is required but not proven"
        )
