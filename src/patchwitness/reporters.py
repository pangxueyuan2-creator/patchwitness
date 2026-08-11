"""Human and machine report renderers for one verified Evidence Pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchwitness.models import EvidencePack

RULES: dict[str, tuple[str, str]] = {
    "PW001": ("Denied path", "A changed path matches an explicit deny pattern."),
    "PW002": ("Outside approved scope", "A changed path is not covered by allowed_paths."),
    "PW003": (
        "Protected control plane",
        "The change modifies policy, CI, or another protected verification surface.",
    ),
    "PW004": ("Binary change", "The contract does not permit opaque binary changes."),
    "PW005": (
        "Dependency surface",
        "A manifest or lockfile changed without allow_dependency_changes.",
    ),
    "PW010": ("File budget", "The number of changed files exceeds max_files."),
    "PW011": ("Line budget", "Added plus deleted lines exceed max_lines."),
    "PW020": ("Missing check", "A required check was not executed."),
    "PW021": ("Failed check", "A required command failed or timed out."),
    "PW022": ("No test definition", "Tests are required but the contract defines no checks."),
    "PW030": ("Possible secret", "A changed file contains a high-confidence secret shape."),
}


def render_markdown(pack: EvidencePack) -> str:
    impact = dict(pack.extensions.get("impact", {}))
    risk_level = str(impact.get("risk_level", "unknown")).upper()
    risk_score = impact.get("risk_score", "n/a")
    lines = [
        "## PatchWitness Change Passport",
        "",
        f"**Gate:** `{pack.status.value.upper()}` | **Risk:** `{risk_level} ({risk_score}/100)`  ",
        f"**Evidence:** `{pack.payload_sha256}`  ",
        f"**Base:** `{pack.repository['base_revision']}`  ",
        f"**Contract:** `{pack.contract['id']}` from `{pack.contract['source']}`",
        "",
        "| Signal | Result |",
        "|---|---:|",
        f"| Files changed | {pack.summary['files_changed']} |",
        f"| Lines changed | {pack.summary['lines_changed']} |",
        f"| Checks passed | {pack.summary['checks_passed']}/{pack.summary['checks_total']} |",
        f"| Direct dependents | {len(impact.get('direct_dependents', []))} |",
        f"| Transitive dependents | {len(impact.get('transitive_dependents', []))} |",
        f"| Affected tests | {len(impact.get('affected_tests', []))} |",
        "",
    ]
    if pack.findings:
        lines.extend(["### Findings", ""])
        for finding in pack.findings:
            location = f" (`{finding['path']}`)" if finding.get("path") else ""
            lines.append(f"- **{finding['rule_id']}** {finding['message']}{location}")
    else:
        lines.append("No policy violations were found.")
    if pack.checks:
        lines.extend(["", "### Checks", "", "| Check | Result | Duration |", "|---|---|---:|"])
        for check in pack.checks:
            result = "PASS" if check["passed"] else "FAIL"
            lines.append(f"| `{check['id']}` | {result} | {check['duration_ms']} ms |")
    lines.extend(
        [
            "",
            "<sub>Generated deterministically by PatchWitness. Verify with "
            "`patchwitness verify evidence.json`.</sub>",
        ]
    )
    return "\n".join(lines) + "\n"


def render_sarif(pack: EvidencePack, *, evidence_path: str | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for finding in pack.findings:
        result: dict[str, Any] = {
            "ruleId": finding["rule_id"],
            "level": _sarif_level(str(finding["severity"])),
            "message": {"text": finding["message"]},
            "properties": {"evidenceSha256": pack.payload_sha256},
        }
        if finding.get("path"):
            region: dict[str, int] = {}
            if finding.get("line"):
                region["startLine"] = int(finding["line"])
            location: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {"uri": str(finding["path"]).replace("\\", "/")}
                }
            }
            if region:
                location["physicalLocation"]["region"] = region
            result["locations"] = [location]
        results.append(result)
    rules = [
        {
            "id": rule_id,
            "name": title.replace(" ", ""),
            "shortDescription": {"text": title},
            "fullDescription": {"text": description},
            "helpUri": (
                "https://github.com/pangxueyuan2-creator/patchwitness/"
                f"blob/main/docs/rules.md#{rule_id.lower()}"
            ),
        }
        for rule_id, (title, description) in RULES.items()
    ]
    invocation: dict[str, Any] = {
        "executionSuccessful": pack.status.value == "pass",
        "properties": {"evidenceSha256": pack.payload_sha256},
    }
    if evidence_path:
        invocation["properties"]["evidencePath"] = evidence_path
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "PatchWitness",
                        "version": str(pack.tool["version"]),
                        "informationUri": "https://github.com/pangxueyuan2-creator/patchwitness",
                        "rules": rules,
                    }
                },
                "invocations": [invocation],
                "results": results,
            }
        ],
    }


def render_github_annotations(pack: EvidencePack) -> str:
    lines: list[str] = []
    for finding in pack.findings:
        level = "error" if finding["severity"] == "error" else "warning"
        properties: list[str] = []
        if finding.get("path"):
            properties.append(f"file={_escape_property(str(finding['path']))}")
        if finding.get("line"):
            properties.append(f"line={finding['line']}")
        suffix = " " + ",".join(properties) if properties else ""
        message = _escape_message(f"{finding['rule_id']}: {finding['message']}")
        lines.append(f"::{level}{suffix}::{message}")
    return "\n".join(lines) + ("\n" if lines else "")


def write_report(
    pack: EvidencePack,
    output: Path,
    *,
    report_format: str,
    evidence_path: str | None = None,
) -> Path:
    if report_format == "markdown":
        content = render_markdown(pack)
    elif report_format == "sarif":
        content = json.dumps(
            render_sarif(pack, evidence_path=evidence_path),
            indent=2,
            sort_keys=True,
        ) + "\n"
    elif report_format == "json":
        content = json.dumps(pack.to_dict(), indent=2, sort_keys=True) + "\n"
    elif report_format == "github":
        content = render_github_annotations(pack)
    else:
        raise ValueError(f"unsupported report format: {report_format}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    return output


def explain_rule(rule_id: str) -> tuple[str, str]:
    try:
        return RULES[rule_id.upper()]
    except KeyError as exc:
        raise ValueError(f"unknown rule: {rule_id}") from exc


def _sarif_level(severity: str) -> str:
    return "error" if severity == "error" else "warning" if severity == "warning" else "note"


def _escape_property(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _escape_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
