"""Deterministic policy evaluation; no LLM and no network access."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from functools import lru_cache
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
        for policy_path in item.policy_paths:
            if _matches_any(policy_path, contract.denied_paths):
                findings.append(
                    Finding("PW001", Severity.ERROR, "path matches a denied pattern", policy_path)
                )
            if contract.exclusive_allow and not contract.allowed_paths:
                findings.append(
                    Finding(
                        "PW002",
                        Severity.ERROR,
                        "path is outside the approved scope",
                        policy_path,
                    )
                )
            elif contract.allowed_paths and not _matches_any(policy_path, contract.allowed_paths):
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
            for policy_path in item.policy_paths:
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


def case_insensitive_paths() -> bool:
    """Return True when policy globs must fold case like the host filesystem.

    Windows default volumes treat ``.GITHUB/WORKFLOWS/ci.yml`` as the same
    file as ``.github/workflows/ci.yml``. Matching case-sensitively there
    lets a denied workflow PASS and an allowed ``SRC/app.py`` fail PW002.
    Linux stays case-sensitive: those spellings are different paths.
    """

    return os.name == "nt"


def _fold(text: str) -> str:
    return text.casefold() if case_insensitive_paths() else text


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(_matches(normalized, pattern) for pattern in patterns)


def _matches(path: str, pattern: str) -> bool:
    """Match a repository-relative path against a policy pattern.

    Patterns are treated as POSIX-style. Leading ./ is ignored. Directory
    patterns ending with / or /** match the directory itself and everything
    under it. A single * or ? never crosses a path separator; use ** to
    match across directories. On Windows the comparison folds case.
    """
    normalized = pattern.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized in {"*", "**", "**/*"}:
        return True

    path_cmp = _fold(path)

    # directory form: "src/" or "src/**"
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        if not prefix:
            return True
        prefix_cmp = _fold(prefix)
        return path_cmp == prefix_cmp or path_cmp.startswith(prefix_cmp + "/")
    if normalized.endswith("/") and "*" not in normalized and "?" not in normalized:
        prefix = normalized.rstrip("/")
        if not prefix:
            return True
        prefix_cmp = _fold(prefix)
        return path_cmp == prefix_cmp or path_cmp.startswith(prefix_cmp + "/")

    if "*" not in normalized and "?" not in normalized:
        exact = _fold(normalized)
        return path_cmp == exact or path_cmp.startswith(exact + "/")

    return _glob_regex(normalized, case_insensitive_paths()).fullmatch(path) is not None


@lru_cache(maxsize=256)
def _glob_regex(pattern: str, ignore_case: bool = False) -> re.Pattern[str]:
    """Compile a policy glob where * and ? do not cross '/'."""

    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    pieces.append("(?:.*/)?")
                    index += 1
                else:
                    pieces.append(".*")
            else:
                pieces.append("[^/]*")
                index += 1
        elif character == "?":
            pieces.append("[^/]")
            index += 1
        else:
            pieces.append(re.escape(character))
            index += 1
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile("^" + "".join(pieces) + "$", flags)


def _deduplicate(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str | None, str]] = set()
    output: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.path, finding.message)
        if key not in seen:
            output.append(finding)
            seen.add(key)
    return output
