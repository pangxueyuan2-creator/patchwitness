from patchwitness.models import CheckResult, CheckSpec, Contract, FileChange
from patchwitness.policy import evaluate_policy


def change(
    path: str, *, additions: int = 1, deletions: int = 0, binary: bool = False
) -> FileChange:
    return FileChange(path, "M", additions, deletions, binary, "before", "after")


def test_empty_pattern_matches_nothing_instead_of_everything() -> None:
    contract = Contract(allowed_paths=("",), require_tests=False)
    findings = evaluate_policy(contract, [change("secret.txt")])
    assert [finding.rule_id for finding in findings] == ["PW002"]


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


def test_directory_patterns_and_trailing_slash() -> None:
    # "src/" and "src/**" should both cover the directory tree
    for pattern in ("src/", "src/**"):
        contract = Contract(allowed_paths=(pattern,), require_tests=False)
        findings = evaluate_policy(
            contract,
            [change("src/app.py"), change("src/utils/helper.py"), change("docs/readme.md")],
        )
        paths = {f.path for f in findings if f.rule_id == "PW002"}
        assert "docs/readme.md" in paths
        assert "src/app.py" not in paths
        assert "src/utils/helper.py" not in paths


def test_exact_path_and_nested_prefix() -> None:
    contract = Contract(allowed_paths=("src/app.py",), require_tests=False)
    findings = evaluate_policy(
        contract,
        [change("src/app.py"), change("src/app.py.bak"), change("src/other.py")],
    )
    paths = {f.path for f in findings if f.rule_id == "PW002"}
    assert "src/app.py" not in paths
    assert "src/app.py.bak" in paths
    assert "src/other.py" in paths


def test_protected_directory_blocks_nested() -> None:
    contract = Contract(
        protected_paths=(".github/",),
        require_tests=False,
    )
    findings = evaluate_policy(
        contract,
        [change(".github/workflows/ci.yml"), change(".github/CODEOWNERS")],
    )
    assert all(f.rule_id == "PW003" for f in findings)
    assert {f.path for f in findings} == {".github/workflows/ci.yml", ".github/CODEOWNERS"}


def test_rename_cannot_move_a_protected_path_into_allowed_scope() -> None:
    contract = Contract(
        allowed_paths=("src/**",),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    renamed = FileChange(
        "src/ci.yml",
        "R100",
        0,
        0,
        False,
        "before",
        "after",
        previous_path=".github/workflows/ci.yml",
    )

    findings = evaluate_policy(contract, [renamed])

    assert {(finding.rule_id, finding.path) for finding in findings} == {
        ("PW002", ".github/workflows/ci.yml"),
        ("PW003", ".github/workflows/ci.yml"),
    }
