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


def test_trusted_command_resolution_substitutes_outside_tools(
    tmp_path: Path, monkeypatch: object
) -> None:
    from patchwitness.checks import _resolve_trusted_command

    substituted = _resolve_trusted_command("python -m pytest", tmp_path)
    assert substituted == f'"{sys.executable}" -m pytest'

    monkeypatch.setattr(
        "shutil.which", lambda name: sys.executable if name == "pytest" else None
    )
    resolved_pytest = _resolve_trusted_command("pytest -q", tmp_path)
    assert resolved_pytest == f'"{sys.executable}" -q'

    complex_command = "cd src && pytest -q"
    assert _resolve_trusted_command(complex_command, tmp_path) == complex_command


def test_trusted_command_resolution_refuses_inside_tree_tools(
    tmp_path: Path, monkeypatch: object
) -> None:
    import shutil

    from patchwitness.checks import _resolve_trusted_command

    planted = tmp_path / "tools" / ("pytest.exe" if os.name == "nt" else "pytest")
    planted.parent.mkdir()
    shutil.copy(sys.executable, planted)
    monkeypatch.setattr("shutil.which", lambda name: str(planted) if name == "pytest" else None)

    import pytest

    with pytest.raises(ValueError, match="untrusted worktree"):
        _resolve_trusted_command("pytest -q", tmp_path)


def test_clean_room_gate_never_runs_planted_executables(
    tmp_path: Path, monkeypatch: object
) -> None:
    import shutil
    import subprocess

    from patchwitness.cli import main
    from patchwitness.evidence import load_evidence, verify_evidence

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )

    git("init", "-b", "main")
    git("config", "user.email", "tests@patchwitness.dev")
    git("config", "user.name", "PatchWitness Tests")
    contract = (
        "version = 1\n"
        'id = "planted-shadow"\n'
        "[policy]\n"
        'allowed_paths = ["**"]\n'
        "require_tests = true\n\n"
        "[[checks]]\n"
        'id = "tests"\n'
        'command = "python echo_python.py"\n'
        "required = true\n"
        "timeout_seconds = 60\n"
    )
    (tmp_path / ".patchwitness.toml").write_text(contract, encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "echo_python.py").write_text(
        "import sys\nprint(sys.executable)\n", encoding="utf-8"
    )
    venv_bin = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    venv_bin.mkdir(parents=True)
    planted_name = "python.exe" if os.name == "nt" else "python"
    shutil.copy(sys.executable, venv_bin / planted_name)
    shutil.copy(sys.executable, tmp_path / planted_name)
    git("add", ".")
    git("add", "-f", ".venv")
    git("add", "-f", planted_name)
    git("commit", "-m", "base")

    monkeypatch.chdir(tmp_path)
    main(
        [
            "gate",
            "--base",
            "HEAD",
            "--policy-ref",
            "HEAD",
            "--clean-room",
            "--output",
            "evidence.json",
        ]
    )

    evidence = tmp_path / "evidence.json"
    assert evidence.is_file()
    pack = verify_evidence(load_evidence(evidence))
    assert pack.checks
    excerpt_text = pack.checks[0]["output_excerpt"]
    # The planted copies are bare interpreter files: they die with a
    # pyvenv.cfg error before printing anything. The real interpreter runs
    # the tracked script and prints its own executable path.
    assert "pyvenv.cfg" not in excerpt_text
    assert excerpt_text.strip().endswith(("python.exe", "python"))
    assert ".venv" not in excerpt_text
