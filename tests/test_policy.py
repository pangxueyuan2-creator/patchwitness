import patchwitness.policy as policy_mod
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


def test_single_star_does_not_cross_directories() -> None:
    contract = Contract(allowed_paths=("src/*.py",), require_tests=False)
    findings = evaluate_policy(
        contract,
        [change("src/app.py"), change("src/nested/deep.py"), change("docs/readme.md")],
    )
    paths = {finding.path for finding in findings if finding.rule_id == "PW002"}
    assert "src/app.py" not in paths
    assert "src/nested/deep.py" in paths
    assert "docs/readme.md" in paths


def test_exclusive_empty_allow_denies_every_path() -> None:
    contract = Contract(allowed_paths=(), exclusive_allow=True, require_tests=False)
    findings = evaluate_policy(contract, [change("src/app.py")])
    assert any(finding.rule_id == "PW002" for finding in findings)


def test_rename_from_protected_path_is_blocked() -> None:
    contract = Contract(
        allowed_paths=("src/**", "helper.py"),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    renamed = FileChange(
        "helper.py",
        "R100",
        0,
        0,
        False,
        "before",
        "after",
        ".github/workflows/ci.yml",
    )
    findings = evaluate_policy(contract, [renamed])
    assert any(
        finding.rule_id == "PW003" and finding.path == ".github/workflows/ci.yml"
        for finding in findings
    )


def test_rename_out_of_allowed_source_is_blocked() -> None:
    contract = Contract(allowed_paths=("src/**",), require_tests=False)
    renamed = FileChange(
        "src/helper.py",
        "R100",
        0,
        0,
        False,
        "before",
        "after",
        "docs/secret.md",
    )
    findings = evaluate_policy(contract, [renamed])
    assert any(finding.rule_id == "PW002" and finding.path == "docs/secret.md" for finding in findings)


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


def _src_exclusive_contract() -> Contract:
    return Contract(
        allowed_paths=("src/**",),
        denied_paths=(".github/workflows/**", ".git/**"),
        protected_paths=(".github/workflows/**",),
        exclusive_allow=True,
        require_tests=False,
    )


def test_windows_casefold_blocks_mixed_case_workflow(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: True)
    findings = evaluate_policy(
        _src_exclusive_contract(),
        [change(".GITHUB/WORKFLOWS/ci.yml")],
    )
    codes = {finding.rule_id for finding in findings}
    assert "PW001" in codes
    assert "PW003" in codes


def test_windows_casefold_allows_mixed_case_src(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: True)
    findings = evaluate_policy(_src_exclusive_contract(), [change("SRC/app.py")])
    assert findings == ()


def test_windows_casefold_blocks_mixed_case_git_dir(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: True)
    findings = evaluate_policy(_src_exclusive_contract(), [change(".GIT/config")])
    assert any(finding.rule_id == "PW001" for finding in findings)


def test_windows_casefold_blocks_mixed_case_rename_source(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: True)
    renamed = FileChange(
        "src/ci.yml",
        "R100",
        0,
        0,
        False,
        "before",
        "after",
        previous_path=".GITHUB/WORKFLOWS/ci.yml",
    )
    findings = evaluate_policy(_src_exclusive_contract(), [renamed])
    pairs = {(finding.rule_id, finding.path) for finding in findings}
    assert ("PW001", ".GITHUB/WORKFLOWS/ci.yml") in pairs
    assert ("PW003", ".GITHUB/WORKFLOWS/ci.yml") in pairs


def test_posix_case_sensitive_mixed_case_workflow_is_not_protected(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: False)
    findings = evaluate_policy(
        _src_exclusive_contract(),
        [change(".GITHUB/WORKFLOWS/ci.yml")],
    )
    codes = {finding.rule_id for finding in findings}
    assert "PW002" in codes
    assert "PW001" not in codes
    assert "PW003" not in codes


def test_posix_case_sensitive_mixed_case_src_is_outside_scope(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: False)
    findings = evaluate_policy(_src_exclusive_contract(), [change("SRC/app.py")])
    assert any(finding.rule_id == "PW002" for finding in findings)


def test_star_glob_folds_case_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "case_insensitive_paths", lambda: True)
    contract = Contract(allowed_paths=("src/*.py",), require_tests=False)
    findings = evaluate_policy(
        contract,
        [change("SRC/APP.PY"), change("SRC/nested/DEEP.PY")],
    )
    paths = {finding.path for finding in findings if finding.rule_id == "PW002"}
    assert "SRC/APP.PY" not in paths
    assert "SRC/nested/DEEP.PY" in paths
