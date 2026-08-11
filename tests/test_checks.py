import os
import sys
from pathlib import Path

from patchwitness.checks import _prefer_project_virtualenv, run_checks
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
