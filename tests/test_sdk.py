import subprocess
from pathlib import Path

from patchwitness.config import DEFAULT_CONFIG
from patchwitness.sdk import PatchWitness


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_sdk_capture_verify_and_impact(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    config = DEFAULT_CONFIG.replace("require_tests = true", "require_tests = false").split(
        "[[checks]]", 1
    )[0]
    (tmp_path / ".patchwitness.toml").write_text(config, encoding="utf-8")
    (tmp_path / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base")
    (tmp_path / "core.py").write_text("VALUE = 2\n", encoding="utf-8")

    sdk = PatchWitness(tmp_path)
    pack = sdk.capture(execute_checks=False)
    assert pack.summary["files_changed"] == 1
    assert sdk.impact(pack)["changed_source_files"] == ["core.py"]
