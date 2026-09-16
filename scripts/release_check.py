"""Portable release preflight; run with an interpreter containing .[dev].

Build outputs, consumer environments, and synthetic repositories live in a
fresh temporary directory. This script does not publish or tag a release.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def environment(python: Path) -> dict[str, str]:
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    *,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"command failed (expected {expected}, got {result.returncode}): {command}\n"
            + result.stdout
            + result.stderr
        )
    return result


def distributions(directory: Path) -> tuple[Path, Path]:
    wheels = list(directory.glob("patchwitness-*.whl"))
    sdists = list(directory.glob("patchwitness-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("expected exactly one PatchWitness wheel and one source distribution")
    return wheels[0], sdists[0]


def installed_smoke(python: Path, work: Path) -> None:
    """Exercise actual installed behavior on public synthetic Git changes."""
    work.mkdir()
    env = environment(python)
    # -I blocks source-tree/PYTHONPATH leakage; the new venv has no editable install.
    command = [str(python), "-I", "-m", "patchwitness"]
    run(
        [
            str(python),
            "-I",
            "-c",
            "import pathlib,sys,patchwitness; "
            "assert pathlib.Path(patchwitness.__file__).resolve().is_relative_to("
            "pathlib.Path(sys.prefix).resolve())",
        ],
        work,
        env,
    )
    run([*command, "--version"], work, env)
    git = ["git", "-c", f"core.hooksPath={work / 'no-hooks'}"]
    for args in (
        ["init", "-b", "main"],
        ["config", "user.name", "Release fixture"],
        ["config", "user.email", "release@example.invalid"],
        ["config", "commit.gpgsign", "false"],
    ):
        run([*git, *args], work, env)
    (work / "src").mkdir()
    (work / "src/app.py").write_text("value = 1\n", encoding="utf-8")
    (work / ".github/workflows").mkdir(parents=True)
    workflow = work / ".github/workflows/ci.yml"
    workflow.write_text("name: fixture\n", encoding="utf-8")
    (work / ".gitignore").write_text(".patchwitness/\n", encoding="utf-8")
    (work / ".patchwitness.toml").write_text(
        'version = 1\nid = "release-fixture"\ngoal = "verify installed policy behavior"\n'
        '[policy]\nallowed_paths = ["src/**"]\n'
        'protected_paths = [".github/workflows/**", ".patchwitness.toml"]\n'
        "require_tests = false\n",
        encoding="utf-8",
    )
    run([*git, "add", "."], work, env)
    run([*git, "commit", "-m", "trusted synthetic base"], work, env)
    (work / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    passport = work / ".patchwitness/evidence/release.json"
    gate = [
        *command,
        "gate",
        "--base",
        "HEAD",
        "--policy-ref",
        "HEAD",
        "--no-checks",
        "--output",
        str(passport),
    ]
    run(gate, work, env)
    run([*command, "verify", str(passport)], work, env)
    workflow.write_text("name: changed-fixture\n", encoding="utf-8")
    run(gate, work, env, expected=1)
    evidence = json.loads(passport.read_text(encoding="utf-8"))
    if "PW003" not in {finding["rule_id"] for finding in evidence["findings"]}:
        raise RuntimeError("installed gate failed without detecting protected workflow change")
    run([*command, "verify", str(passport)], work, env)
    evidence["summary"]["status"] = "pass"
    passport.write_text(json.dumps(evidence), encoding="utf-8")
    rejected = run([*command, "verify", str(passport)], work, env, expected=2)
    if "payload digest mismatch" not in rejected.stderr:
        raise RuntimeError("tampered Passport was not rejected for an integrity mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-only",
        action="store_true",
        help="validate artifacts only; does not certify source checks",
    )
    args = parser.parse_args(argv)
    python = Path(sys.executable)
    env = environment(python)
    try:
        with tempfile.TemporaryDirectory(prefix="patchwitness-release-") as directory:
            work = Path(directory)
            if not args.package_only:
                checks = [
                    [
                        str(python),
                        "-m",
                        "pytest",
                        "--cov=patchwitness",
                        "--cov-report=term-missing",
                        "--cov-fail-under=80",
                    ],
                    [str(python), "-m", "ruff", "check", "src", "tests"],
                    [str(python), "-m", "mypy", "src"],
                    [str(python), "demo/run_demo.py", "--output-dir", str(work / "demo")],
                    [
                        str(python),
                        "-c",
                        "import runpy; m = runpy.run_path('benchmarks/change-risk/run.py'); "
                        "[m['execute_scenario'](s) for s in m['SCENARIOS']]",
                    ],
                ]
                for check in checks:
                    print(f"Checking: {' '.join(check[1:])}", flush=True)
                    result = run(check, ROOT, env)
                    print(result.stdout + result.stderr, flush=True)
            else:
                print(
                    "Artifact-only validation: source tests/lint/types/demo were not run.",
                    flush=True,
                )
            output = work / "dist"
            print("Building wheel and source distribution", flush=True)
            run([str(python), "-m", "build", "--outdir", str(output)], ROOT, env)
            artifacts = distributions(output)
            run([str(python), "-m", "twine", "check", *map(str, artifacts)], ROOT, env)
            for index, artifact in enumerate(artifacts):
                print(f"Validating installed artifact: {artifact.name}", flush=True)
                consumer = work / f"consumer-{index}"
                venv.EnvBuilder(with_pip=True).create(consumer)
                executable = consumer / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                run(
                    [
                        str(executable),
                        "-I",
                        "-m",
                        "pip",
                        "--isolated",
                        "install",
                        "--disable-pip-version-check",
                        "--no-deps",
                        str(artifact),
                    ],
                    work,
                    environment(executable),
                )
                installed_smoke(executable, work / f"fixture-{index}")
            label = "Artifact-only checks" if args.package_only else "Full release preflight"
            print(f"{label} passed; nothing was published or tagged.", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"release-check: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
