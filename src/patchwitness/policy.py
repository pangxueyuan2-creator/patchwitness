"""Deterministic policy evaluation; no LLM and no network access."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from pathlib import PurePosixPath

from patchwitness.models import CheckResult, Contract, FileChange, Finding, Severity

DEPENDENCY_FILES = {
    "bun.lock",
    "bun.lockb",
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
    "go.mod",
    "go.sum",
    "package-lock.json",
    "package.json",
    "pdm.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "yarn.lock",
}


def evaluate_policy(
    contract: Contract,
    changes: Iterable[FileChange],
    checks: Iterable[CheckResult] = (),
) -> tuple[Finding, ...]:
    changed = tuple(changes)
    results = tuple(checks)
    findings: list[Finding] = []

    for item in changed:
        if _matches_any(item.path, contract.denied_paths):
            findings.append(
                Finding("PW001", Severity.ERROR, "path matches a denied pattern", item.path)
            )
        if contract.allowed_paths and not _matches_any(item.path, contract.allowed_paths):
            findings.append(
                Finding("PW002", Severity.ERROR, "path is outside the approved scope", item.path)
            )
        if _matches_any(item.path, contract.protected_paths):
            findings.append(
                Finding(
                    "PW003",
                    Severity.ERROR,
                    "protected verification or control-plane file changed",
                    item.path,
                )
            )
        if item.binary and not contract.allow_binary:
            findings.append(
                Finding("PW004", Severity.ERROR, "binary changes are not allowed", item.path)
            )
        if (
            PurePosixPath(item.path.lower()).name in DEPENDENCY_FILES
            and not contract.allow_dependency_changes
        ):
            findings.append(
                Finding(
                    "PW005",
                    Severity.ERROR,
                    "dependency surface changed without explicit permission",
                    item.path,
                )
            )

    if len(changed) > contract.max_files:
        findings.append(
            Finding(
                "PW010",
                Severity.ERROR,
                f"file budget exceeded: {len(changed)} > {contract.max_files}",
            )
        )
    total_lines = sum(item.changed_lines for item in changed)
    if total_lines > contract.max_lines:
        findings.append(
            Finding(
                "PW011",
                Severity.ERROR,
                f"line budget exceeded: {total_lines} > {contract.max_lines}",
            )
        )

    by_id = {result.id: result for result in results}
    for spec in contract.checks:
        result = by_id.get(spec.id)
        if result is None and spec.required:
            findings.append(
                Finding("PW020", Severity.ERROR, f"required check did not run: {spec.id}")
            )
        elif result is not None and spec.required and not result.passed:
            suffix = "timed out" if result.timed_out else f"exited {result.exit_code}"
            findings.append(
                Finding("PW021", Severity.ERROR, f"required check failed: {spec.id} ({suffix})")
            )

    if contract.require_tests and not contract.checks:
        findings.append(
            Finding("PW022", Severity.ERROR, "contract requires tests but defines no checks")
        )
    return tuple(_deduplicate(findings))


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(_matches(normalized, pattern) for pattern in patterns)


def _matches(path: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in {"*", "**", "**/*"}:
        return True
    if normalized.endswith("/**") and path == normalized[:-3].rstrip("/"):
        return True
    return fnmatch.fnmatchcase(path, normalized)


def _deduplicate(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str | None, str]] = set()
    output: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.path, finding.message)
        if key not in seen:
            output.append(finding)
            seen.add(key)
    return output
