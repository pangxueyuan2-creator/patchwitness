"""Installed two-product smoke for TaskToPR -> PatchWitness Safe Delivery."""

from __future__ import annotations

import json
import sys

from patchwitness.safe_delivery import (
    COMPONENTS,
    ChangeSubject,
    ComponentEvidence,
    DeliveryDecision,
    compose_safe_delivery,
    verify_safe_delivery,
)
from patchwitness.tasktopr import TaskToPREvidenceError, adapt_tasktopr_execution
from tasktopr.handoff import build_execution_handoff, content_digest as tasktopr_digest


def _execution_receipt() -> dict[str, object]:
    manifest = [
        {"path_sha256": "1" * 64, "before": "2" * 64, "after": "3" * 64},
        {"path_sha256": "4" * 64, "before": None, "after": "5" * 64},
    ]
    payload: dict[str, object] = {
        "schema_version": 1,
        "run_id": "not-exported",
        "started_at": "2026-09-14T00:00:00+00:00",
        "repository_identity": {"kind": "local-root-sha256", "sha256": "6" * 64},
        "base_sha": "a" * 40,
        "result_head_sha": "b" * 40,
        "tested_head_sha": "b" * 40,
        "policy": {"version": "tasktopr-execution-v1", "sha256": "7" * 64},
        "tool": {"name": "tasktopr", "version": "0.1.0", "source_sha256": "8" * 64},
        "task_sha256": "9" * 64,
        "patch_sha256": "a" * 64,
        "command_list_sha256": "b" * 64,
        "test_result_sha256": "c" * 64,
        "changed_file_manifest": manifest,
        "protected_path_decision": "allow",
        "tests": {"status": "pass", "count": 2},
        "ci": "unknown",
        "human_review": "unknown",
        "decision": "REVIEW_REQUIRED",
        "trust_boundary": "local observation",
        "phase": "pr_created",
        "branch_sha256": "d" * 64,
    }
    return {"payload": payload, "receipt_sha256": tasktopr_digest(payload)}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: tasktopr_safe_delivery_smoke.py <tasktopr-git-revision>")
    producer_revision = sys.argv[1]
    subject = ChangeSubject("6" * 64, "a" * 40, "b" * 40, "d" * 64, "0" * 64)
    handoff = build_execution_handoff(_execution_receipt(), tool_revision=producer_revision)
    execution = adapt_tasktopr_execution(
        handoff,
        subject=subject,
        trusted_revision=producer_revision,
    )

    synthetic_revision = "f" * 40
    records = [execution]
    pins: dict[str, tuple[str, str]] = {"execution": ("tasktopr", producer_revision)}
    for component in COMPONENTS:
        if component == "execution":
            continue
        tool = f"smoke-{component}"
        pins[component] = (tool, synthetic_revision)
        records.append(
            ComponentEvidence(
                component=component,
                tool=tool,
                tool_revision=synthetic_revision,
                subject=subject,
                decision=DeliveryDecision.PASS,
                complete=True,
                details_sha256="e" * 64,
            )
        )
    report = compose_safe_delivery(
        subject,
        records,
        trusted_tools=pins,
        policy_sha256=subject.policy_sha256,
        stage="merge",
    )
    payload = verify_safe_delivery(report)
    if payload["decision"] != "PASS":
        raise AssertionError("installed two-product evidence did not compose to PASS")

    wrong_subject = ChangeSubject(
        subject.repository_sha256,
        subject.base_sha,
        "c" * 40,
        subject.manifest_sha256,
        subject.policy_sha256,
    )
    try:
        adapt_tasktopr_execution(
            handoff,
            subject=wrong_subject,
            trusted_revision=producer_revision,
        )
    except TaskToPREvidenceError:
        pass
    else:
        raise AssertionError("stale TaskToPR handoff was accepted for a different exact HEAD")

    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "execution_tool": payload["execution"]["tool"],
                "execution_revision": payload["execution"]["tool_revision"],
                "receipt_sha256": report["receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
