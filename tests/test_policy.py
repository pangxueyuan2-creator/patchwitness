from patchwitness.models import CheckResult, CheckSpec, Contract, FileChange
from patchwitness.policy import evaluate_policy


def change(
    path: str, *, additions: int = 1, deletions: int = 0, binary: bool = False
) -> FileChange:
    return FileChange(path, "M", additions, deletions, binary, "before", "after")


def test_rejects_out_of_scope_and_protected_changes() -> None:
    contract = Contract(
        allowed_paths=("src/**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    findings = evaluate_policy(
        contract,
        [change("src/app.py"), change("docs/readme.md"), change(".github/workflows/ci.yml")],
    )
    pairs = {(finding.rule_id, finding.path) for finding in findings}
    assert ("PW002", "docs/readme.md") in pairs
    assert ("PW003", ".github/workflows/ci.yml") in pairs


def test_rejects_missing_and_failed_required_checks() -> None:
    spec = CheckSpec("tests", "pytest")
    contract = Contract(checks=(spec,))
    missing = evaluate_policy(contract, [])
    assert [finding.rule_id for finding in missing] == ["PW020"]

    failed = CheckResult("tests", "pytest", True, 1, 3, False, "hash", "failed")
    findings = evaluate_policy(contract, [], [failed])
    assert [finding.rule_id for finding in findings] == ["PW021"]


def test_enforces_budgets_and_dependency_surface() -> None:
    contract = Contract(max_files=1, max_lines=3, require_tests=False)
    findings = evaluate_policy(
        contract,
        [change("src/app.py", additions=4), change("package-lock.json")],
    )
    assert {finding.rule_id for finding in findings} == {"PW005", "PW010", "PW011"}
