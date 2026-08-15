import os
import sys
from pathlib import Path

from patchwitness.checks import (
    _prefer_project_virtualenv,
    resolve_check_executable,
    run_checks,
    split_check_command,
    validate_policy_check,
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


def test_shell_metacharacters_do_not_run_a_second_command(tmp_path: Path) -> None:
    marker = tmp_path / "pwned.txt"
    payload = f"open(r'{marker}', 'w').write('pwned')"
    if os.name == "nt":
        command = f"{python_command('print(1)')} & {python_command(payload)}"
    else:
        command = f"{python_command('print(1)')} ; {python_command(payload)}"

    result = run_checks(tmp_path, [CheckSpec("inject", command, timeout_seconds=5)])[0]

    assert not marker.exists()
    assert result.exit_code != 126 or "refused" in result.output_excerpt


def test_policy_originated_inline_payload_is_refused(tmp_path: Path) -> None:
    marker = tmp_path / "pwned.txt"
    result = run_checks(
        tmp_path,
        [
            CheckSpec(
                "evil",
                python_command(f"open(r'{marker}', 'w').write('pwned')"),
                timeout_seconds=5,
                trusted=False,
            )
        ],
    )[0]
    assert result.exit_code == 126
    assert not result.passed
    assert not marker.exists()
    assert "inline interpreter" in result.output_excerpt


def test_policy_originated_unittest_command_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "test_ok.py").write_text(
        "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
        encoding="utf-8",
    )
    result = run_checks(
        tmp_path,
        [
            CheckSpec(
                "unit",
                "python -m unittest discover -v",
                timeout_seconds=15,
                trusted=False,
            )
        ],
    )[0]
    assert result.passed, result.output_excerpt


def test_split_check_command_keeps_windows_paths_and_quoted_payloads() -> None:
    argv = split_check_command(r'"C:\Program Files\Python\python.exe" -c "print(1)"')
    assert argv == [r"C:\Program Files\Python\python.exe", "-c", "print(1)"]
    spaced = split_check_command(python_command("print('ok')"))
    assert Path(spaced[0]).name.lower().startswith("python")
    assert spaced[1] == "-c"
    assert "print('ok')" in spaced[2]
    chained = split_check_command(r'"C:\py.exe" -c "print(1)" & "C:\py.exe" -c "evil"')
    assert chained[0] == r"C:\py.exe"
    assert "&" in chained
    assert chained.count(r"C:\py.exe") == 2


def test_validate_policy_check_refuses_shell_and_inline_payloads() -> None:
    validate_policy_check(["python", "-m", "unittest", "discover", "-v"])
    try:
        validate_policy_check([r"C:\venv\Scripts\python.exe", "-c", "print(1)"])
    except ValueError as exc:
        assert "inline interpreter" in str(exc)
    else:
        raise AssertionError("inline payload must be refused")
    try:
        validate_policy_check(["python", "-m", "pytest", "&&", "curl", "evil"])
    except ValueError as exc:
        assert "shell metacharacters" in str(exc)
    else:
        raise AssertionError("shell tokens must be refused")


def test_bare_python_resolves_through_path_not_windows_alias(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv(  # type: ignore[attr-defined]
        "PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    )
    resolved = resolve_check_executable(["python", "-m", "pytest"], os.environ.copy())
    assert Path(resolved[0]).resolve() == Path(sys.executable).resolve()
    result = run_checks(
        tmp_path,
        [CheckSpec("py", 'python -c "import sys; print(sys.prefix)"', timeout_seconds=5)],
    )[0]
    assert result.passed, result.output_excerpt
    assert Path(sys.prefix).name in result.output_excerpt or str(sys.prefix) in result.output_excerpt


def test_missing_executable_is_a_check_failure_not_an_exception(tmp_path: Path) -> None:
    result = run_checks(
        tmp_path,
        [CheckSpec("missing", "definitely-not-a-real-check-binary-xyz", timeout_seconds=5)],
    )[0]
    assert not result.passed
    assert result.exit_code == 127
    assert "not found" in result.output_excerpt.lower()


def test_project_virtualenv_is_preferred_for_checks(tmp_path: Path) -> None:
    executable_dir = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    executable_dir.mkdir(parents=True)
    env = {"PATH": "existing-path"}

    _prefer_project_virtualenv(tmp_path, env)

    assert env["PATH"].split(os.pathsep)[0] == str(executable_dir)
    assert env["VIRTUAL_ENV"] == str(tmp_path / ".venv")


def test_running_interpreter_is_preferred_when_repo_has_no_venv(tmp_path: Path) -> None:
    env = {"PATH": "existing-path"}
    _prefer_project_virtualenv(tmp_path, env)
    if sys.prefix != sys.base_prefix:
        assert env["PATH"].split(os.pathsep)[0] == str(Path(sys.executable).parent)
    else:
        assert env["PATH"] == "existing-path"
