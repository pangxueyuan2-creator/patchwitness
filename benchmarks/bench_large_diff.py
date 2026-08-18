"""Benchmark change collection and evidence capture on a synthetic large diff.

Usage: python benchmarks/bench_large_diff.py [--lines 100000] [--runs 3]
Creates a disposable repository, generates one large modified file, and times
collect_changes and capture_evidence (checks disabled).
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from patchwitness.evidence import capture_evidence
from patchwitness.git import collect_changes
from patchwitness.models import Contract


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def build_repo(lines: int) -> tuple[Path, str]:
    root = Path(tempfile.mkdtemp(prefix="pw-bench-"))
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "bench@example.invalid")
    git(root, "config", "user.name", "Bench")
    (root / ".patchwitness.toml").write_text(
        (
            'version = 1\nid = "bench"\n[policy]\nallowed_paths = ["**"]\n'
            "protected_paths = []\nrequire_tests = false\n"
        ),
        encoding="utf-8",
    )
    target = root / "big.py"
    target.write_text("".join(f"old line {i}\n" for i in range(lines)), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    base = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    target.write_text("".join(f"new line {i}\n" for i in range(lines)), encoding="utf-8")
    return root, base


def time_once(function: object, *args: object) -> float:
    start = time.perf_counter()
    function(*args)  # type: ignore[operator]
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lines", type=int, default=100_000)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    root, base = build_repo(args.lines)
    try:
        contract = Contract(allowed_paths=("**",), protected_paths=(), require_tests=False)
        collect_times = [time_once(collect_changes, root, base) for _ in range(args.runs)]
        capture_times = [
            time_once(partial(capture_evidence, root, contract, execute_checks=False))
            for _ in range(args.runs)
        ]
        print(
            f"lines={args.lines} runs={args.runs} | "
            f"collect_changes median {statistics.median(collect_times):.2f}s | "
            f"capture_evidence median {statistics.median(capture_times):.2f}s"
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
