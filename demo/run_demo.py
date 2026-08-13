"""Run PatchWitness against a real, intentionally risky coding-agent patch.

The demo creates a disposable Git repository. The simulated agent adds a correct
feature and passing test, but also makes CI failures non-blocking. PatchWitness
loads policy from the trusted base commit, runs the real tests, and rejects the
protected workflow change with PW003.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(
    command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def require(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        raise RuntimeError(f"{label} failed ({result.returncode}):\n{output}")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def build_base(repo: Path) -> str:
    require(run(["git", "init", "-b", "main"], cwd=repo), "git init")
    require(run(["git", "config", "user.name", "PatchWitness Demo"], cwd=repo), "git config")
    require(
        run(["git", "config", "user.email", "demo@patchwitness.dev"], cwd=repo),
        "git config",
    )
    write(
        repo / ".patchwitness.toml",
        """\
version = 1
id = "agent-risk-demo"
goal = "Allow the pricing feature without weakening verification"

[policy]
allowed_paths = ["src/**", "tests/**"]
denied_paths = [".git/**", ".patchwitness/evidence/**"]
protected_paths = [".github/workflows/**", ".patchwitness.toml"]
max_files = 10
max_lines = 200
allow_binary = false
allow_dependency_changes = false
require_tests = true

[[checks]]
id = "tests"
command = "python -m unittest discover -s tests -q"
required = true
timeout_seconds = 60
""",
    )
    write(
        repo / "src" / "pricing.py",
        """\
def total(values: list[float]) -> float:
    return round(sum(values), 2)
""",
    )
    write(
        repo / "tests" / "test_pricing.py",
        """\
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pricing import total


class PricingTests(unittest.TestCase):
    def test_total(self) -> None:
        self.assertEqual(total([10.0, 2.5]), 12.5)


if __name__ == "__main__":
    unittest.main()
""",
    )
    write(
        repo / ".github" / "workflows" / "ci.yml",
        """\
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
      - run: python -m unittest discover -s tests -q
""",
    )
    require(run(["git", "add", "."], cwd=repo), "git add")
    require(run(["git", "commit", "-m", "trusted base"], cwd=repo), "git commit")
    revision = run(["git", "rev-parse", "HEAD"], cwd=repo)
    require(revision, "git rev-parse")
    return revision.stdout.strip()


def apply_agent_patch(repo: Path) -> None:
    write(
        repo / "src" / "pricing.py",
        """\
def total(values: list[float]) -> float:
    return round(sum(values), 2)


def discount(amount: float, percent: int) -> float:
    return round(amount * (100 - percent) / 100, 2)
""",
    )
    write(
        repo / "tests" / "test_pricing.py",
        """\
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from pricing import discount, total


class PricingTests(unittest.TestCase):
    def test_total(self) -> None:
        self.assertEqual(total([10.0, 2.5]), 12.5)

    def test_discount(self) -> None:
        self.assertEqual(discount(100.0, 15), 85.0)


if __name__ == "__main__":
    unittest.main()
""",
    )
    write(
        repo / ".github" / "workflows" / "ci.yml",
        """\
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    continue-on-error: true  # Agent made failures non-blocking.
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
      - run: python -m unittest discover -s tests -q
""",
    )


def normalized(text: str, *, work: Path, output: Path) -> str:
    """Normalize only machine-specific paths; preserve command results verbatim."""
    return text.replace(str(work), "$DEMO_REPO").replace(str(output), "$CHANGE_PASSPORT")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "demo" / "output",
        help="directory for the generated passport and transcript",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="also refresh the committed demo artifacts (maintainers only)",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    passport = output_dir / "change-passport.json"
    transcript = output_dir / "terminal-output.txt"
    work = Path(tempfile.mkdtemp(prefix="patchwitness-agent-risk-"))
    env = os.environ.copy()
    source = str(PROJECT_ROOT / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    command = [sys.executable, "-m", "patchwitness"]

    try:
        base = build_base(work)
        apply_agent_patch(work)

        tests = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=work,
            env=env,
        )
        require(tests, "agent patch tests")

        gate = run(
            [
                *command,
                "gate",
                "--base",
                base,
                "--policy-ref",
                base,
                "--clean-room",
                "--output",
                str(passport),
            ],
            cwd=work,
            env=env,
        )
        if gate.returncode != 1:
            gate_details = (gate.stdout + gate.stderr).strip()
            raise RuntimeError(
                f"expected PatchWitness to block the patch, got {gate.returncode}:\n{gate_details}"
            )

        evidence = json.loads(passport.read_text(encoding="utf-8"))
        rules = {finding["rule_id"] for finding in evidence["findings"]}
        if "PW003" not in rules:
            raise RuntimeError(f"expected PW003, got {sorted(rules)}")
        if evidence["summary"]["checks_passed"] != evidence["summary"]["checks_total"]:
            raise RuntimeError(
                "the risk demo requires tests to pass before policy blocks the patch"
            )

        verify = run([*command, "verify", str(passport)], cwd=work, env=env)
        require(verify, "passport verification")

        test_output = (tests.stdout + tests.stderr).strip()
        gate_output = (gate.stdout + gate.stderr).strip()
        verify_output = (verify.stdout + verify.stderr).strip()
        rendered = "\n".join(
            [
                "PatchWitness real risk demo",
                "===========================",
                "",
                "[1/4] Coding agent patch",
                "  M src/pricing.py                 adds discount()",
                "  M tests/test_pricing.py          adds a passing test",
                "  M .github/workflows/ci.yml       makes CI failures non-blocking",
                "",
                "[2/4] Repository tests",
                test_output,
                "",
                "[3/4] Independent PatchWitness gate",
                gate_output,
                "",
                "[4/4] Offline passport verification",
                verify_output,
                "",
                "Result: tests passed, but the risky control-plane change was blocked.",
            ]
        )
        rendered = normalized(rendered, work=work, output=passport)
        transcript.write_text(rendered + "\n", encoding="utf-8", newline="\n")

        if args.record:
            artifacts = PROJECT_ROOT / "demo" / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            shutil.copy2(passport, artifacts / "risk-change-passport.json")
            shutil.copy2(transcript, artifacts / "terminal-output.txt")

        print(rendered)
        print(f"\nGenerated passport: {passport}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
