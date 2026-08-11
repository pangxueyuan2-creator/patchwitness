from pathlib import Path

from patchwitness.config import create_task_contract, load_contract


def test_creates_loadable_task_contract(tmp_path: Path) -> None:
    target = create_task_contract(
        tmp_path,
        "TASK-123",
        goal="Fix token refresh",
        allowed_paths=("src/auth/**", "tests/auth/**"),
        checks=(("tests", "python -m pytest tests/auth"),),
        max_files=8,
    )
    contract = load_contract(target)
    assert contract.id == "TASK-123"
    assert contract.allowed_paths == ("src/auth/**", "tests/auth/**")
    assert contract.checks[0].id == "tests"
