import os
import shutil
import sys
from pathlib import Path

import pytest

from patchwitness.checks import (
    _prefer_project_virtualenv,
    _resolve_trusted_command,
    run_checks,
)
from patchwitness.models import CheckSpec


def python_command(source: str) -> str:
    escaped = source.replace('"', '\\"')
    return f'"{sys.executable}" -c "{escaped}"'


def test_checks_run_in_parallel_and_redact_output(tmp_path: Path) -> None:
    checks = (
        CheckSpec("ok", python_command("print('ok')"), timeout_seconds=5),
        CheckSpec(
            "redacted",
            python_command("print('api_key=abcdefghijklmnopqrstuvwxyz123456')"),
            timeout_seconds=5,
        ),
    )
    results = run_checks(tmp_path, checks, parallel=True)
    assert all(result.passed for result in results)
    assert "abcdefghijklmnopqrstuvwxyz123456" not in results[1].output_excerpt


def test_failed_and_timed_out_checks_are_explicit(tmp_path: Path) -> None:
    failed = run_checks(
        tmp_path,
        [CheckSpec("failed", python_command("raise SystemExit(7)"), timeout_seconds=5)],
    )[0]
    timed_out = run_checks(
        tmp_path,
        [
            CheckSpec(
                "slow",
                python_command("import time; time.sleep(2)"),
                timeout_seconds=1,
            )
        ],
    )[0]
    assert failed.exit_code == 7 and not failed.passed
    assert timed_out.timed_out and timed_out.exit_code is None


def test_project_virtualenv_is_preferred_for_checks(tmp_path: Path) -> None:
    executable_dir = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    executable_dir.mkdir(parents=True)
    env = {"PATH": "existing-path"}

    _prefer_project_virtualenv(tmp_path, env)

    assert env["PATH"].split(os.pathsep)[0] == str(executable_dir)
    assert env["VIRTUAL_ENV"] == str(tmp_path / ".venv")


def test_untrusted_command_resolves_python_to_verifier(tmp_path: Path) -> None:
    resolved = _resolve_trusted_command("python -m pytest -q", tmp_path)
    assert resolved == f'"{Path(sys.executable).resolve()}" -m pytest -q'


def test_untrusted_command_resolves_path_tool_outside_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: sys.executable if name == "pytest" else None)
    resolved = _resolve_trusted_command("pytest -q", tmp_path)
    assert resolved == f'"{Path(sys.executable).resolve()}" -q'


def test_untrusted_command_refuses_tool_inside_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planted = tmp_path / "tools" / ("pytest.exe" if os.name == "nt" else "pytest")
    planted.parent.mkdir()
    shutil.copy(sys.executable, planted)
    monkeypatch.setattr(shutil, "which", lambda name: str(planted) if name == "pytest" else None)

    with pytest.raises(ValueError, match="untrusted worktree"):
        _resolve_trusted_command("pytest -q", tmp_path)


def test_untrusted_command_refuses_compound_shell_syntax(tmp_path: Path) -> None:
    for command in (
        "python -m pytest && python planted.py",
        "python -m pytest | tee results.txt",
        "python -m pytest > results.txt",
        "python -m pytest; python planted.py",
        "python -m pytest $(python planted.py)",
        "python -m pytest `python planted.py`",
    ):
        with pytest.raises(ValueError, match="compound shell syntax"):
            _resolve_trusted_command(command, tmp_path)


def test_untrusted_run_fails_closed_instead_of_raising(tmp_path: Path) -> None:
    result = run_checks(
        tmp_path,
        [CheckSpec("compound", "python -V && python planted.py", timeout_seconds=5)],
        untrusted=True,
    )[0]
    assert result.exit_code == 126
    assert not result.passed
    assert "refused to execute clean-room check" in result.output_excerpt


def test_untrusted_run_does_not_prefer_repository_virtualenv(tmp_path: Path) -> None:
    executable_dir = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    executable_dir.mkdir(parents=True)
    planted = executable_dir / ("python.exe" if os.name == "nt" else "python")
    shutil.copy(sys.executable, planted)

    result = run_checks(
        tmp_path,
        [CheckSpec("python", "python -c \"import sys; print(sys.executable)\"", timeout_seconds=5)],
        untrusted=True,
    )[0]
    assert result.passed
    assert str(tmp_path / ".venv") not in result.output_excerpt
