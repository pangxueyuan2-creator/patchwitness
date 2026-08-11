"""Reproducible local benchmark harness; all reported numbers are measured."""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

from patchwitness.git import collect_changes, resolve_revision
from patchwitness.impact import analyze_impact


def run_benchmark(*, files: int = 250, rounds: int = 5) -> dict[str, Any]:
    if files < 10 or rounds < 1:
        raise ValueError("benchmark requires at least 10 files and 1 round")
    with tempfile.TemporaryDirectory(prefix="patchwitness-benchmark-") as raw:
        root = Path(raw)
        _prepare_repository(root, files)
        base = resolve_revision(root, "HEAD")
        change_count = max(1, files // 5)
        for index in range(change_count):
            path = root / "src" / f"module_{index:05d}.py"
            path.write_text(path.read_text(encoding="utf-8") + "CHANGED = True\n", encoding="utf-8")

        collect_samples: list[float] = []
        cold_impact_samples: list[float] = []
        warm_impact_samples: list[float] = []
        for _ in range(rounds):
            changes, elapsed = _measure(lambda: collect_changes(root, base))
            collect_samples.append(elapsed)
            _, elapsed = _measure(partial(analyze_impact, root, changes, use_cache=False))
            cold_impact_samples.append(elapsed)
            analyze_impact(root, changes, use_cache=True)
            _, elapsed = _measure(partial(analyze_impact, root, changes, use_cache=True))
            warm_impact_samples.append(elapsed)

        return {
            "benchmark_version": 1,
            "measured_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "environment": {
                "os": platform.platform(),
                "python": platform.python_version(),
                "machine": platform.machine(),
            },
            "parameters": {
                "repository_files": files,
                "changed_files": change_count,
                "rounds": rounds,
            },
            "results_ms": {
                "git_change_collection": _summary(collect_samples),
                "impact_cold": _summary(cold_impact_samples),
                "impact_warm": _summary(warm_impact_samples),
            },
            "disclaimer": (
                "Local synthetic benchmark; compare only on similar hardware and settings."
            ),
        }


def write_benchmark(result: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output


def _prepare_repository(root: Path, files: int) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "benchmark@patchwitness.dev")
    _git(root, "config", "user.name", "PatchWitness Benchmark")
    source = root / "src"
    source.mkdir()
    for index in range(files):
        dependency = f"from module_{index - 1:05d} import VALUE\n" if index else ""
        (source / f"module_{index:05d}.py").write_text(
            f"{dependency}VALUE = {index}\n", encoding="utf-8"
        )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "benchmark base")


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _measure(function: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    value = function()
    return value, (time.perf_counter() - started) * 1_000


def _summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * 0.95)))
    return {
        "median": round(statistics.median(ordered), 3),
        "p95": round(ordered[p95_index], 3),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
    }
