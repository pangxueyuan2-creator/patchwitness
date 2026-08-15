"""CLI-level Scenario A/B: independent PatchWitness gate over agent-boundary/v1.

These tests invoke the public `python -m patchwitness` CLI against a real
temporary Git repository. PASS/BLOCK comes from evaluation, not fixtures.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BOUNDARY = {
    "schema": "https://patchwitness.dev/agent-boundary/v1",
    "version": 1,
    "id": "e2e-demo",
    "exclusive_allow": True,
    "allowed_paths": ["calculator.py", "test_calculator.py"],
    "denied_paths": [".git/**", ".github/workflows/**"],
    "protected_paths": [".github/workflows/**"],
    "required_checks": ["python -m unittest discover -v"],
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _write_demo(root: Path) -> None:
    (root / "calculator.py").write_text(
        "def divide(numerator: float, denominator: float) -> float:\n"
        "    return numerator / denominator\n",
        encoding="utf-8",
    )
    (root / "test_calculator.py").write_text(
        "import unittest\n\n"
        "from calculator import divide\n\n\n"
        "class DivideTests(unittest.TestCase):\n"
        "    def test_divide_returns_quotient(self) -> None:\n"
        "        self.assertEqual(divide(8, 2), 4)\n",
        encoding="utf-8",
    )
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci\non: [push]\n", encoding="utf-8")
    (root / "agent-boundary.json").write_text(
        json.dumps(BOUNDARY, indent=2) + "\n", encoding="utf-8"
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "tests@patchwitness.dev")
    _git(root, "config", "user.name", "PatchWitness Tests")
    _write_demo(root)
    _git(root, "add", ".")
    _git(root, "commit", "-m", "trusted base")


def _gate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "patchwitness",
            "--json",
            "gate",
            "--contract",
            "agent-boundary.json",
            "--base",
            "HEAD",
            "--output",
            ".patchwitness/evidence/scenario.json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _apply_allowed_fix(root: Path) -> None:
    (root / "calculator.py").write_text(
        "def divide(numerator: float, denominator: float) -> float:\n"
        '    if denominator == 0:\n'
        '        raise ValueError("denominator must not be zero")\n'
        "    return numerator / denominator\n",
        encoding="utf-8",
    )
    (root / "test_calculator.py").write_text(
        "import unittest\n\n"
        "from calculator import divide\n\n\n"
        "class DivideTests(unittest.TestCase):\n"
        "    def test_divide_returns_quotient(self) -> None:\n"
        "        self.assertEqual(divide(8, 2), 4)\n\n"
        "    def test_divide_rejects_zero_denominator(self) -> None:\n"
        '        with self.assertRaisesRegex(ValueError, "denominator must not be zero"):\n'
        "            divide(8, 0)\n",
        encoding="utf-8",
    )


def test_scenario_a_allowed_change_and_passing_tests_is_pass(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _apply_allowed_fix(tmp_path)
    first = _gate(tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr
    first_cli = json.loads(first.stdout)
    assert first_cli["ok"] is True
    assert first_cli["status"] == "pass"
    # A second gate must not fail just because PatchWitness wrote a local cache.
    second = _gate(tmp_path)
    assert second.returncode == 0, second.stdout + second.stderr
    second_cli = json.loads(second.stdout)
    assert second_cli["ok"] is True
    pack = json.loads(
        (tmp_path / ".patchwitness" / "evidence" / "scenario.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["summary"]["status"] == "pass"
    assert pack["summary"]["checks_passed"] == pack["summary"]["checks_total"]
    assert pack["summary"]["errors"] == 0
    assert not any(
        item["path"].startswith(".patchwitness/cache/") for item in pack["changes"]
    )


def test_scenario_b_passing_tests_do_not_override_protected_ci(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _apply_allowed_fix(tmp_path)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: ci\non: [push]\njobs:\n  sneak:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert tests.returncode == 0, tests.stdout + tests.stderr
    result = _gate(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    cli = json.loads(result.stdout)
    assert cli["ok"] is False
    assert cli["status"] == "fail"
    pack = json.loads(
        (tmp_path / ".patchwitness" / "evidence" / "scenario.json").read_text(
            encoding="utf-8"
        )
    )
    assert pack["summary"]["status"] == "fail"
    findings = pack.get("findings") or pack.get("summary", {}).get("findings") or []
    if not findings:
        # Evidence pack stores findings at top level or under policy.
        findings = pack.get("policy_findings") or []
    serialized = json.dumps(pack)
    assert "PW003" in serialized or "protected" in serialized.lower()
    assert "PW001" in serialized or "PW003" in serialized
