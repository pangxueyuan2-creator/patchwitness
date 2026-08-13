#!/usr/bin/env python3
"""Reproduce narrow change-risk scenarios with the installed PatchWitness CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Scenario:
    identifier: str
    description: str
    changed_paths: tuple[str, ...]
    no_checks: bool
    expected_status: str
    required_rules: tuple[str, ...]


SCENARIOS = (
    Scenario(
        "A-allowed-product-change",
        "A scoped product change with the recorded check executing successfully.",
        ("src/app.py",),
        False,
        "pass",
        (),
    ),
    Scenario(
        "B-tests-pass-ci-control-plane-change",
        "A product change plus a protected CI workflow edit; the recorded check still passes.",
        ("src/app.py", ".github/workflows/ci.yml"),
        False,
        "fail",
        ("PW003",),
    ),
    Scenario(
        "C-out-of-scope-change",
        "A change outside the approved product path.",
        ("docs/readme.md",),
        False,
        "fail",
        ("PW002",),
    ),
    Scenario(
        "D-required-check-not-executed",
        (
            "An allowed change captured with --no-checks even though the trusted policy "
            "requires a check."
        ),
        ("src/app.py",),
        True,
        "fail",
        ("PW020",),
    ),
    Scenario(
        "E-policy-self-modification",
        (
            "An attempted working-tree policy modification while policy remains loaded "
            "from the trusted base."
        ),
        (".patchwitness.toml",),
        False,
        "fail",
        ("PW003",),
    ),
)

POLICY = '''version = 1
id = "change-risk-benchmark"
goal = "Permit a narrow product patch while preserving verification controls"

[policy]
allowed_paths = ["src/**"]
protected_paths = [".github/workflows/**", ".patchwitness.toml"]
max_files = 8
max_lines = 300
allow_binary = false
allow_dependency_changes = false
require_tests = true

[[checks]]
id = "recorded-safe-check"
command = "python -c \\\"print('known-safe benchmark check')\\\""
required = true
timeout_seconds = 30
'''


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def initialise_repository(root: Path) -> None:
    for command in (
        ("git", "init", "-q"),
        ("git", "config", "user.name", "Change-risk benchmark"),
        ("git", "config", "user.email", "benchmark@example.invalid"),
    ):
        completed = run(*command, cwd=root)
        if completed.returncode:
            raise RuntimeError(completed.stderr)
    write(root / "src/app.py", "def value() -> int:\n    return 1\n")
    write(root / "docs/readme.md", "# Baseline\n")
    write(root / ".github/workflows/ci.yml", "name: ci\non: [push]\n")
    write(root / ".patchwitness.toml", POLICY)
    completed = run("git", "add", ".", cwd=root)
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    completed = run("git", "commit", "-qm", "trusted base", cwd=root)
    if completed.returncode:
        raise RuntimeError(completed.stderr)


def apply_change(root: Path, scenario: Scenario) -> None:
    for path in scenario.changed_paths:
        target = root / path
        if path == ".patchwitness.toml":
            target.write_text(
                POLICY + "\n# Attempted working-tree policy change\n", encoding="utf-8"
            )
        elif path == ".github/workflows/ci.yml":
            target.write_text("name: ci\non: [push]\n# weakened by a patch\n", encoding="utf-8")
        else:
            existing = target.read_text(encoding="utf-8") if target.exists() else ""
            write(target, existing + f"# Benchmark mutation: {scenario.identifier}\n")


def execute_scenario(scenario: Scenario) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="patchwitness-change-risk-") as temporary:
        root = Path(temporary)
        initialise_repository(root)
        apply_change(root, scenario)
        evidence = root / "evidence.json"
        command = [
            "patchwitness",
            "capture",
            "--base",
            "HEAD",
            "--policy-ref",
            "HEAD",
            "--output",
            str(evidence),
            "--serial",
        ]
        if scenario.no_checks:
            command.append("--no-checks")
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if not evidence.is_file():
            raise RuntimeError(f"{scenario.identifier} did not write evidence: {completed.stderr}")
        passport = json.loads(evidence.read_text(encoding="utf-8"))
        status = passport["summary"]["status"]
        rules = sorted({finding["rule_id"] for finding in passport["findings"]})
        if status != scenario.expected_status:
            raise AssertionError(
                f"{scenario.identifier}: expected {scenario.expected_status}, got {status}"
            )
        if not set(scenario.required_rules).issubset(rules):
            raise AssertionError(
                f"{scenario.identifier}: expected {scenario.required_rules}, got {rules}"
            )
        return {
            "scenario": asdict(scenario),
            "capture_exit_code": completed.returncode,
            "status": status,
            "finding_rule_ids": rules,
            "checks_total": passport["summary"]["checks_total"],
            "checks_passed": passport["summary"]["checks_passed"],
        }


def main() -> int:
    if shutil.which("patchwitness") is None:
        raise SystemExit("patchwitness must be installed on PATH")
    results = [execute_scenario(scenario) for scenario in SCENARIOS]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tool": "PatchWitness CLI from PATH",
        "method": "Each scenario uses a fresh temporary Git repository and loads policy from HEAD.",
        "results": results,
    }
    output = Path(__file__).with_name("results") / "latest.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
