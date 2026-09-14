"""Synthetic external consumer for an installed PatchWitness wheel."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import patchwitness
from patchwitness.safe_delivery import (
    COMPONENTS,
    ChangeSubject,
    ComponentEvidence,
    DeliveryDecision,
    compose_safe_delivery,
    content_digest,
    verify_safe_delivery,
)

_PRODUCER_REVISION = "e" * 40


def _subject() -> ChangeSubject:
    return ChangeSubject(
        repository_sha256="1" * 64,
        base_sha="a" * 40,
        head_sha="b" * 40,
        manifest_sha256="2" * 64,
        policy_sha256="3" * 64,
    )


def _report(
    *,
    stage: str,
    decisions: dict[str, DeliveryDecision] | None = None,
    omitted: set[str] | None = None,
) -> dict[str, object]:
    subject = _subject()
    overrides = decisions or {}
    skipped = omitted or set()
    records: list[ComponentEvidence] = []
    pins: dict[str, tuple[str, str]] = {}
    for component in COMPONENTS:
        if component in skipped:
            continue
        tool = f"consumer-{component}"
        pins[component] = (tool, _PRODUCER_REVISION)
        records.append(
            ComponentEvidence(
                component=component,
                tool=tool,
                tool_revision=_PRODUCER_REVISION,
                subject=subject,
                decision=overrides.get(component, DeliveryDecision.PASS),
                complete=True,
                details_sha256=content_digest(
                    {"fixture": "external-consumer", "component": component}
                ),
                rule_ids=(f"FIXTURE_{component.upper()}",),
                metrics={"evidence_items": 1},
            )
        )
    report = compose_safe_delivery(
        subject,
        records,
        trusted_tools=pins,
        policy_sha256=subject.policy_sha256,
        stage=stage,
    )
    verify_safe_delivery(report)
    return report


def _write(path: Path, report: dict[str, object]) -> str:
    path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return str(report["receipt_sha256"])


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: safe_delivery_consumer.py <output-directory>")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)

    pass_report = _report(stage="merge")
    fail_report = _report(stage="merge", decisions={"api": DeliveryDecision.FAIL})
    review_report = _report(stage="pr", omitted={"review"})
    decisions = {
        "pass": verify_safe_delivery(pass_report)["decision"],
        "fail": verify_safe_delivery(fail_report)["decision"],
        "review": verify_safe_delivery(review_report)["decision"],
    }
    receipts = {
        "pass": _write(output / "pass.json", pass_report),
        "fail": _write(output / "fail.json", fail_report),
        "review": _write(output / "review.json", review_report),
    }
    print(
        json.dumps(
            {
                "module_file": str(Path(patchwitness.__file__).resolve()),
                "decisions": decisions,
                "receipts": receipts,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
