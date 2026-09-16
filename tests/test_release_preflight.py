import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("release_check", ROOT / "scripts/release_check.py")
assert SPEC is not None and SPEC.loader is not None
release_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_check)


def test_artifact_selection_rejects_missing_and_ambiguous_builds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        release_check.distributions(tmp_path)
    wheel = tmp_path / "patchwitness-0.2.2-py3-none-any.whl"
    source = tmp_path / "patchwitness-0.2.2.tar.gz"
    wheel.touch()
    source.touch()
    assert release_check.distributions(tmp_path) == (wheel, source)
    (tmp_path / "patchwitness-0.2.1-py3-none-any.whl").touch()
    with pytest.raises(ValueError, match="exactly one"):
        release_check.distributions(tmp_path)


def test_consumer_environment_drops_source_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "untrusted-source")
    monkeypatch.setenv("PYTHONHOME", "untrusted-runtime")
    python = Path(sys.executable)
    environment = release_check.environment(python)
    assert "PYTHONPATH" not in environment
    assert "PYTHONHOME" not in environment
    assert environment["PATH"].split(os.pathsep)[0] == str(python.parent)
    assert os.environ["PYTHONPATH"] == "untrusted-source"


def test_preflight_propagates_real_process_failure(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="expected 0, got 7"):
        release_check.run(
            [sys.executable, "-c", "raise SystemExit(7)"],
            tmp_path,
            release_check.environment(Path(sys.executable)),
        )


def test_portable_entrypoint_help_without_make(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_check.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--package-only" in result.stdout
