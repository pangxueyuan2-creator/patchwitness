"""Reviewer policy wrapper for the installed Safe Delivery passport CLI.

The underlying passport module owns exact-subject composition and offline verification.
This wrapper adds one opt-in consumer policy: require TaskToPR v2 proof that a human
approved or edited the pre-mutation plan before any passport is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from patchwitness.passport import (
    PassportError,
    build_tasktopr_passport,
    load_passport,
    write_passport,
)
from patchwitness.safe_delivery import COMPONENTS, verify_safe_delivery


def require_tasktopr_plan_approval(report: dict[str, Any]) -> None:
    """Fail closed unless a verified TaskToPR human plan approval is present.

    This is deliberately a consumer-side policy. It never upgrades plan approval into
    merge or release authorization; it only requires the already validated execution
    component to prove that TaskToPR ran in prompt mode and received approve/edit.
    """
    payload = verify_safe_delivery(report)
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        raise PassportError("TaskToPR human plan approval is required but unavailable")
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
        raise PassportError("TaskToPR human plan approval is required but not proven")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchwitness-safe-delivery",
        description="Compose and independently verify exact-subject Safe Delivery passports.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    commands = parser.add_subparsers(dest="command", required=True)
    tasktopr = commands.add_parser(
        "tasktopr",
        help="compose a PR-stage passport from a TaskToPR execution handoff",
    )
    tasktopr.add_argument("--handoff", required=True, type=Path)
    tasktopr.add_argument("--tasktopr-revision", required=True)
    tasktopr.add_argument("--base", required=True, dest="base_sha")
    tasktopr.add_argument("--head", default="HEAD")
    tasktopr.add_argument("--policy-ref", required=True)
    tasktopr.add_argument("--policy-path", default=".patchwitness.toml")
    tasktopr.add_argument("--output", required=True, type=Path)
    tasktopr.add_argument("--force", action="store_true")
    tasktopr.add_argument(
        "--require-plan-approval",
        action="store_true",
        help="require verified TaskToPR v2 prompt-mode human approve/edit provenance",
    )
    verify = commands.add_parser(
        "verify",
        help="verify a saved Safe Delivery passport offline without trusting its decision",
    )
    verify.add_argument("passport", type=Path)
    return parser


def _verification_result(report: dict[str, Any], passport: Path) -> dict[str, Any]:
    payload = verify_safe_delivery(report)
    return {
        "ok": True,
        "decision": payload["decision"],
        "stage": payload["stage"],
        "receipt_sha256": report["receipt_sha256"],
        "passport": str(passport),
        "head_sha": payload["provenance"]["subject"]["head_sha"],
        "components": {name: payload[name]["decision"] for name in COMPONENTS},
    }


def _error(exc: Exception, *, json_output: bool) -> int:
    if json_output:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
    else:
        print(f"patchwitness-safe-delivery: error: {exc}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Installed Safe Delivery CLI with optional reviewer-enforced plan approval."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        try:
            result = _verification_result(load_passport(args.passport), args.passport)
        except (OSError, PassportError, ValueError) as exc:
            return _error(exc, json_output=bool(args.json))
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(f"Safe Delivery passport verified: {result['decision']} ({result['stage']})")
            print(f"  Head:    {result['head_sha']}")
            print(f"  Receipt: {result['receipt_sha256']}")
            print(f"  Input:   {result['passport']}")
            print("  Meaning: integrity/semantics verified; producer identity is not authenticated")
        return 0

    if args.command != "tasktopr":
        parser.error(f"unknown command: {args.command}")
    try:
        report = build_tasktopr_passport(
            Path.cwd(),
            handoff_path=args.handoff,
            tasktopr_revision=args.tasktopr_revision,
            base_sha=args.base_sha,
            head=args.head,
            policy_ref=args.policy_ref,
            policy_path=args.policy_path,
        )
        if args.require_plan_approval:
            require_tasktopr_plan_approval(report)
        output = write_passport(args.output, report, force=bool(args.force))
    except (OSError, PassportError, ValueError) as exc:
        return _error(exc, json_output=bool(args.json))

    payload = report["payload"]
    result = {
        "ok": True,
        "decision": payload["decision"],
        "stage": payload["stage"],
        "receipt_sha256": report["receipt_sha256"],
        "output": str(output),
        "head_sha": payload["provenance"]["subject"]["head_sha"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"Safe Delivery passport written: {result['decision']} ({result['stage']})")
        print(f"  Head:    {result['head_sha']}")
        print(f"  Receipt: {result['receipt_sha256']}")
        print(f"  Output:  {result['output']}")
        print("  Meaning: execution evidence composed; merge/release authorization remains separate")
    return 0
