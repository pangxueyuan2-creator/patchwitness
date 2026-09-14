from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONSUMER_FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "safe_delivery_consumer.py"


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )


def _clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def test_built_wheel_external_consumer_verifies_all_decision_states(tmp_path: Path) -> None:
    distributions = tmp_path / "dist"
    distributions.mkdir()
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(distributions),
            str(REPOSITORY_ROOT),
        ],
        cwd=tmp_path,
    )
    wheels = list(distributions.glob("patchwitness-*.whl"))
    assert len(wheels) == 1

    environment = tmp_path / "venv"
    _run([sys.executable, "-m", "venv", str(environment)], cwd=tmp_path)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-deps",
            str(wheels[0]),
        ],
        cwd=tmp_path,
    )

    cli = shutil.which("patchwitness-safe-delivery", path=str(scripts))
    assert cli is not None
    external = tmp_path / "external-consumer"
    external.mkdir()
    consumer = external / "consumer.py"
    shutil.copyfile(CONSUMER_FIXTURE, consumer)
    output = external / "passports"
    clean_env = _clean_environment()

    produced = _run(
        [str(python), str(consumer), str(output)],
        cwd=external,
        env=clean_env,
    )
    metadata = json.loads(produced.stdout)
    assert metadata["decisions"] == {
        "fail": "FAIL",
        "pass": "PASS",
        "review": "REVIEW_REQUIRED",
    }
    installed_module = Path(metadata["module_file"])
    assert not installed_module.is_relative_to(REPOSITORY_ROOT)

    for name, expected in (
        ("pass", "PASS"),
        ("fail", "FAIL"),
        ("review", "REVIEW_REQUIRED"),
    ):
        verified = _run(
            [cli, "--json", "verify", str(output / f"{name}.json")],
            cwd=external,
            env=clean_env,
        )
        result = json.loads(verified.stdout)
        assert result["ok"] is True
        assert result["decision"] == expected
        assert result["receipt_sha256"] == metadata["receipts"][name]
        assert result["head_sha"] == "b" * 40

    tampered = json.loads((output / "pass.json").read_text(encoding="utf-8"))
    tampered["receipt_sha256"] = "0" * 64
    tampered_path = output / "tampered.json"
    tampered_path.write_text(json.dumps(tampered, sort_keys=True) + "\n", encoding="utf-8")
    rejected = _run(
        [cli, "--json", "verify", str(tampered_path)],
        cwd=external,
        env=clean_env,
        check=False,
    )
    assert rejected.returncode == 2
    error = json.loads(rejected.stdout)
    assert error["ok"] is False
    assert "mismatch" in error["error"]
