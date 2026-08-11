from pathlib import Path

import pytest

from patchwitness.config import ConfigError, initialize_project, load_contract


def test_initialize_project_is_safe_and_idempotence_requires_force(tmp_path: Path) -> None:
    target = initialize_project(tmp_path)
    contract = load_contract(target)
    assert contract.id == "default"
    assert ".patchwitness/evidence/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    with pytest.raises(ConfigError, match="already exists"):
        initialize_project(tmp_path)


def test_rejects_duplicate_check_ids(tmp_path: Path) -> None:
    target = tmp_path / ".patchwitness.toml"
    target.write_text(
        '[[checks]]\nid="tests"\ncommand="one"\n[[checks]]\nid="tests"\ncommand="two"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="duplicate"):
        load_contract(target)

