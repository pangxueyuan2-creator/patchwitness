"""Reject mistyped TOML before coercion can change a maintainer's policy."""

import subprocess
from pathlib import Path

import pytest

from patchwitness.cli import main
from patchwitness.config import ConfigError, load_contract_bytes, render_starter_config
from patchwitness.models import Contract, FileChange
from patchwitness.policy import evaluate_policy


@pytest.mark.parametrize(
    "raw",
    [
        'version = 2',
        'version = true',
        'version = "1"',
        'id = 12',
        'goal = false',
        'policy = "SYNTHETIC_CONFIG_SENTINEL"',
        'checks = "SYNTHETIC_CONFIG_SENTINEL"',
        'checks = [false]',
        '[policy]\nallowed_paths = "src/**"',
        '[policy]\ndenied_paths = [false]',
        '[policy]\nprotected_paths = [123]',
        '[policy]\nallow_binary = "false"',
        '[policy]\nallow_dependency_changes = "false"',
        '[policy]\nrequire_tests = 0',
        '[policy]\nmax_files = true',
        '[policy]\nmax_lines = 1.5',
        '[[checks]]\nid = 12\ncommand = "echo ok"',
        '[[checks]]\nid = "x"\ncommand = false',
        '[[checks]]\nid = "x"\ncommand = "echo ok"\nrequired = "false"',
        '[[checks]]\nid = "x"\ncommand = "echo ok"\ntimeout_seconds = "900"',
        '[[checks]]\nid = "x"\ncommand = "echo ok"\ntimeout_seconds = true',
    ],
)
def test_mistyped_toml_is_a_safe_configuration_error(raw: str) -> None:
    with pytest.raises(ConfigError) as caught:
        load_contract_bytes(raw.encode(), source="synthetic.toml")
    assert "SYNTHETIC_CONFIG_SENTINEL" not in str(caught.value)
    assert "synthetic.toml" in str(caught.value)


@pytest.mark.parametrize("nested", [False, True])
def test_well_typed_legacy_flat_and_table_forms_keep_decisions(nested: bool) -> None:
    raw = 'id="typed"\ngoal="synthetic"\n' + ('[policy]\n' if nested else '')
    raw += (
        'allowed_paths=["src/**"]\ndenied_paths=[]\nprotected_paths=[]\n'
        'allow_binary=false\nallow_dependency_changes=false\nrequire_tests=false\n'
        'max_files=3\nmax_lines=10\n'
    )
    contract = load_contract_bytes(raw.encode())
    changes = [FileChange("outside.bin", "M", 1, 0, True, "a", "b")]
    assert [f.rule_id for f in evaluate_policy(contract, changes)] == ["PW002", "PW004"]
    assert Contract.from_dict(contract.to_dict()) == contract


def test_defaults_and_generated_contracts_remain_loadable() -> None:
    assert load_contract_bytes(b"") == Contract()
    for checks in ([], [("tests", "python -m pytest")]):
        contract = load_contract_bytes(render_starter_config(checks).encode())
        assert contract.require_tests is bool(checks)
        assert [item.id for item in contract.checks] == [item[0] for item in checks]


@pytest.mark.parametrize("bad_policy", ['allow_binary = "false"', 'allowed_paths = "src/**"'])
def test_trusted_mistyped_policy_rejected_before_commands_and_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    bad_policy: str,
) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True,
            text=True, timeout=10,
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Synthetic Maintainer")
    git("config", "user.email", "synthetic@example.invalid")
    (tmp_path / "check.py").write_text(
        'from pathlib import Path\nPath("check-ran").write_text("executed")\n', encoding="utf-8"
    )
    (tmp_path / ".patchwitness.toml").write_text(
        'version=1\n[policy]\n' + bad_policy + '\nrequire_tests=true\n'
        '[[checks]]\nid="synthetic"\ncommand="python check.py"\n', encoding="utf-8"
    )
    (tmp_path / "outside.txt").write_text("before\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "trusted synthetic policy")
    base = git("rev-parse", "HEAD")
    (tmp_path / "outside.txt").write_text("after\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "result.json"
    assert main(["gate", "--base", base, "--policy-ref", base, "--output", str(output)]) == 2
    assert "invalid contract" in capsys.readouterr().err
    assert not (tmp_path / "check-ran").exists()
    assert not output.exists()
