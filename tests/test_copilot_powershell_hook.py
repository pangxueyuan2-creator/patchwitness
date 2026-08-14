import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import pytest

from patchwitness.evidence import load_evidence, verify_evidence


@pytest.mark.skipif(os.name != "nt", reason="PowerShell hook requires Windows")
def test_copilot_powershell_hook_writes_an_advisory_passport(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "main")
    git("config", "user.email", "tests@patchwitness.dev")
    git("config", "user.name", "PatchWitness Tests")
    (tmp_path / "README.md").write_text("trusted base\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "trusted base")
    (tmp_path / "README.md").write_text("uncommitted hook smoke change\n", encoding="utf-8")

    hook = (
        Path(__file__).parents[1]
        / "examples"
        / "copilot-cli-hooks"
        / ".github"
        / "hooks"
        / "patchwitness-safe-scan.ps1"
    )
    installed_executable = shutil.which("patchwitness")
    patchwitness_executable = (
        Path(installed_executable)
        if installed_executable
        else Path(sysconfig.get_path("scripts")) / "patchwitness.exe"
    )
    assert patchwitness_executable.is_file()

    result = subprocess.run(
        [
            "pwsh",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "$ErrorActionPreference = 'Stop'; & $args[0]; exit $LASTEXITCODE",
            str(hook),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env={
            **os.environ,
            "PATH": str(patchwitness_executable.parent) + os.pathsep + os.environ["PATH"],
        },
    )

    assert result.returncode == 0
    assert "PatchWitness hook: local advisory passport:" in result.stderr
    evidence_files = list(
        (tmp_path / ".patchwitness" / "evidence").glob("copilot-safe-scan-*.json")
    )
    assert len(evidence_files) == 1
    pack = verify_evidence(load_evidence(evidence_files[0]))
    assert pack.summary["status"] == "pass"
