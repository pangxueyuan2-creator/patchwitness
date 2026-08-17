"""Deterministic policy evaluation; no LLM and no network access."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterable
from functools import cache
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
        policy_paths = (item.path,) + (
            (item.previous_path,)
            if item.previous_path is not None and item.previous_path != item.path
            else ()
        )
        for policy_path in policy_paths:
            if _matches_any(policy_path, contract.denied_paths):
                findings.append(
                    Finding("PW001", Severity.ERROR, "path matches a denied pattern", policy_path)
                )
            if contract.allowed_paths and not _matches_any(policy_path, contract.allowed_paths):
                findings.append(
                    Finding(
                        "PW002", Severity.ERROR, "path is outside the approved scope", policy_path
                    )
                )
            if _matches_any(policy_path, contract.protected_paths):
                findings.append(
                    Finding(
                        "PW003",
                        Severity.ERROR,
                        "protected verification or control-plane file changed",
                        policy_path,
                    )
                )
        if item.binary and not contract.allow_binary:
            findings.append(
                Finding("PW004", Severity.ERROR, "binary changes are not allowed", item.path)
            )
        if not contract.allow_dependency_changes:
            for policy_path in policy_paths:
                if PurePosixPath(policy_path.lower()).name in DEPENDENCY_FILES:
                    findings.append(
                        Finding(
                            "PW005",
                            Severity.ERROR,
                            "dependency surface changed without explicit permission",
                            policy_path,
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


def _glob_match(path: str, pattern: str) -> bool:
    """Match POSIX path segments, with ** spanning zero or more segments."""
    path_parts = tuple(path.split("/"))
    pattern_parts = tuple(pattern.split("/"))

    @cache
    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        token = pattern_parts[pattern_index]
        if token == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        if path_index >= len(path_parts):
            return False
        return fnmatch.fnmatchcase(path_parts[path_index], token) and match(
            path_index + 1, pattern_index + 1
        )

    return match(0, 0)


def _matches(path: str, pattern: str) -> bool:
    """Match a repository-relative path against a policy pattern.

    Patterns are treated as POSIX-style. Leading ./ is ignored. Directory
    patterns ending with / or /** match the directory itself and everything
    under it. A single-star glob never crosses a path separator; ** is the
    recursive form and may span zero or more complete path segments. Plain
    * / ** still match everything. Empty patterns match nothing; malformed
    configuration must never widen a security scope.
    """
    normalized = pattern.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return False
    if normalized in {"*", "**", "**/*"}:
        return True

    # directory form: "src/" or "src/**"
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        if not prefix:
            return True
        return path == prefix or path.startswith(prefix + "/")
    if normalized.endswith("/"):
        prefix = normalized.rstrip("/")
        if not prefix:
            return True
        return path == prefix or path.startswith(prefix + "/")

    # exact path
    if "*" not in normalized and "?" not in normalized and "[" not in normalized:
        return path == normalized or path.startswith(normalized + "/")

    # Python's fnmatch treats '/' like any other character. Match path
    # segments explicitly so ordinary wildcards stay within one segment while
    # ** can span zero or more segments (for example src/**/*.py also matches
    # src/app.py).
    return _glob_match(path, normalized)


def _deduplicate(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str | None, str]] = set()
    output: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.path, finding.message)
        if key not in seen:
            output.append(finding)
            seen.add(key)
    return output
