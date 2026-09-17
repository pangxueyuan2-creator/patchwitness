"""Changes introduced during verification must not inherit an earlier PASS."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from patchwitness import evidence
from patchwitness.cli import main
from patchwitness.config import load_contract
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence
from patchwitness.git import GitError
from patchwitness.models import GateStatus


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        timeout=30,
    )


@pytest.fixture
def fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    script = tmp_path / "check.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    (root / "src").mkdir()
    (root / "src/app.py").write_text("value = 1\n", encoding="utf-8")
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/workflows/ci.yml").write_text("name: fixture\n", encoding="utf-8")
    (root / ".gitignore").write_text(".patchwitness/\n", encoding="utf-8")
    (root / ".patchwitness.toml").write_text(
        'version = 1\nid = "scope-drift"\n'
        '[policy]\nallowed_paths = ["src/**"]\n'
        'protected_paths = [".github/workflows/**", ".patchwitness.toml"]\n'
        'require_tests = true\n[[checks]]\nid = "fixture"\n'
        f"command = {json.dumps(command)}\ntimeout_seconds = 10\n",
        encoding="utf-8",
    )
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "PatchWitness fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.hooksPath", str(tmp_path / "no-hooks"))
    git(root, "add", ".")
    git(root, "commit", "-m", "trusted synthetic base")
    return root, script


OPERATIONS = [
    (
        "modify",
        "Path('.github/workflows/ci.yml').write_text('name: changed\\n', encoding='utf-8')",
        ".github/workflows/ci.yml",
    ),
    ("delete", "Path('.github/workflows/ci.yml').unlink()", ".github/workflows/ci.yml"),
    (
        "rename",
        "subprocess.run(['git', 'mv', '.github/workflows/ci.yml', "
        "'.github/workflows/renamed.yml'], check=True)",
        ".github/workflows/renamed.yml",
    ),
    (
        "stage-addition",
        "Path('src/new.py').write_text('value = 3\\n', encoding='utf-8')\n"
        "subprocess.run(['git', 'add', 'src/new.py'], check=True)",
        "src/new.py",
    ),
]


@pytest.mark.parametrize("dirty", [False, True], ids=["empty-scope", "existing-scope"])
@pytest.mark.parametrize("_name,operation,expected", OPERATIONS, ids=[x[0] for x in OPERATIONS])
def test_check_cannot_expand_tracked_scope(
    fixture: tuple[Path, Path], dirty: bool, _name: str, operation: str, expected: str
) -> None:
    root, script = fixture
    if dirty:
        (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    script.write_text(
        "from pathlib import Path\nimport subprocess\n" + operation + "\n", encoding="utf-8"
    )

    pack = capture_evidence(
        root, load_contract(root / ".patchwitness.toml"), parallel_checks=False
    )

    assert pack.checks[0]["passed"] is True
    assert {change["path"] for change in pack.changes} == ({"src/app.py"} if dirty else set())
    drift = [finding for finding in pack.findings if finding["rule_id"] == "PW032"]
    assert {finding["path"] for finding in drift} == {expected}
    assert all(finding["severity"] == "error" for finding in drift)
    assert pack.status == GateStatus.FAIL
    assert verify_evidence(pack).status == GateStatus.FAIL


@pytest.mark.parametrize("path", ["generated.txt", "build/result.txt", "new tests/测试.txt"])
def test_new_untracked_outputs_remain_outside_recorded_scope(
    fixture: tuple[Path, Path], path: str
) -> None:
    root, script = fixture
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    script.write_text(
        f"from pathlib import Path\np = Path({path!r})\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_text('generated\\n', encoding='utf-8')\n", encoding="utf-8",
    )

    pack = capture_evidence(
        root, load_contract(root / ".patchwitness.toml"), parallel_checks=False
    )

    assert pack.checks[0]["passed"] is True
    assert pack.status == GateStatus.PASS
    assert {change["path"] for change in pack.changes} == {"src/app.py"}
    assert not any(finding["rule_id"] == "PW032" for finding in pack.findings)


def test_clean_room_source_scope_movement_is_still_detected(fixture: tuple[Path, Path]) -> None:
    root, script = fixture
    target = root / ".github/workflows/ci.yml"
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    script.write_text(
        f"from pathlib import Path\nPath({str(target)!r}).unlink()\n", encoding="utf-8"
    )

    pack = capture_evidence(
        root, load_contract(root / ".patchwitness.toml"),
        parallel_checks=False, clean_room_checks=True,
    )

    assert pack.checks[0]["passed"] is True
    assert pack.status == GateStatus.FAIL
    assert any(
        finding["rule_id"] == "PW032" and finding["path"] == ".github/workflows/ci.yml"
        for finding in pack.findings
    )


def test_isolated_clean_room_writes_do_not_move_source_scope(fixture: tuple[Path, Path]) -> None:
    root, script = fixture
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    script.write_text(
        "from pathlib import Path\nPath('.github/workflows/ci.yml').unlink()\n", encoding="utf-8"
    )

    pack = capture_evidence(
        root, load_contract(root / ".patchwitness.toml"),
        parallel_checks=False, clean_room_checks=True,
    )

    assert pack.checks[0]["passed"] is True
    assert pack.status == GateStatus.PASS
    assert (root / ".github/workflows/ci.yml").exists()
    assert not any(finding["rule_id"] == "PW032" for finding in pack.findings)


def test_trusted_base_cli_fails_instead_of_issuing_stale_pass(
    fixture: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, script = fixture
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    script.write_text("from pathlib import Path\n" + OPERATIONS[0][1] + "\n", encoding="utf-8")
    monkeypatch.chdir(root)
    output = root / ".patchwitness/evidence/gate.json"

    exit_code = main(
        ["gate", "--base", "HEAD", "--policy-ref", "HEAD", "--serial", "--output", str(output)]
    )

    assert exit_code == 1
    pack = verify_evidence(load_evidence(output))
    assert pack.status == GateStatus.FAIL
    assert pack.checks[0]["passed"] is True
    assert any(
        finding["rule_id"] == "PW032" and finding["path"] == ".github/workflows/ci.yml"
        for finding in pack.findings
    )
    assert main(["verify", str(output)]) == 0


def test_new_staged_and_untracked_outputs_are_distinguished(fixture: tuple[Path, Path]) -> None:
    root, script = fixture
    script.write_text(
        "from pathlib import Path\nimport subprocess\n"
        + OPERATIONS[3][1]
        + "\nPath('generated.txt').write_text('output', encoding='utf-8')\n",
        encoding="utf-8",
    )

    pack = capture_evidence(
        root, load_contract(root / ".patchwitness.toml"), parallel_checks=False
    )

    assert pack.checks[0]["passed"] is True
    assert pack.status == GateStatus.FAIL
    assert {f["path"] for f in pack.findings if f["rule_id"] == "PW032"} == {"src/new.py"}


def test_optional_check_cannot_expand_scope(fixture: tuple[Path, Path]) -> None:
    root, script = fixture
    script.write_text("from pathlib import Path\n" + OPERATIONS[0][1] + "\n", encoding="utf-8")
    contract = load_contract(root / ".patchwitness.toml")
    contract = replace(contract, checks=(replace(contract.checks[0], required=False),))

    pack = capture_evidence(root, contract, parallel_checks=False)

    assert pack.checks[0]["passed"] is True
    assert pack.checks[0]["required"] is False
    assert pack.status == GateStatus.FAIL
    assert any(f["rule_id"] == "PW032" for f in pack.findings)


@pytest.mark.parametrize(
    "outcome",
    [
        OSError("private OS detail"),
        subprocess.TimeoutExpired("git", 30),
        subprocess.CompletedProcess([], 1, "", "private Git detail"),
        subprocess.CompletedProcess([], 0, "truncated-path", ""),
    ],
    ids=["unavailable", "timeout", "nonzero", "truncated-output"],
)
def test_index_enumeration_failures_are_not_untracked_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: OSError | subprocess.TimeoutExpired | subprocess.CompletedProcess[str],
) -> None:
    def result(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(evidence.subprocess, "run", result)
    with pytest.raises(GitError, match=r"^cannot enumerate tracked paths after checks$"):
        evidence._tracked_paths(tmp_path)


@pytest.mark.parametrize("output", ["", "src/app.py\0 leading space.txt\0测试.txt\0"])
def test_index_enumeration_keeps_path_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    def result(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, output, "")

    monkeypatch.setattr(evidence.subprocess, "run", result)
    assert evidence._tracked_paths(tmp_path) == frozenset(p for p in output.split("\0") if p)


def test_failed_scope_observation_makes_cli_error_without_new_receipt(
    fixture: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _script = fixture
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    monkeypatch.chdir(root)
    output = root / ".patchwitness/evidence/gate.json"

    def unavailable(_root: Path) -> frozenset[str]:
        raise GitError("cannot enumerate tracked paths after checks")

    monkeypatch.setattr(evidence, "_tracked_paths", unavailable)
    assert main(
        ["gate", "--base", "HEAD", "--policy-ref", "HEAD", "--serial", "--output", str(output)]
    ) == 2
    assert "cannot enumerate tracked paths after checks" in capsys.readouterr().err
    assert not output.exists()


def test_no_checks_does_not_require_a_post_execution_index_query(
    fixture: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _script = fixture
    contract = replace(load_contract(root / ".patchwitness.toml"), checks=(), require_tests=False)

    def unexpected(_root: Path) -> frozenset[str]:
        pytest.fail("post-execution query should not run with execute_checks=False")

    monkeypatch.setattr(evidence, "_tracked_paths", unexpected)
    assert capture_evidence(root, contract, execute_checks=False).status == GateStatus.PASS
