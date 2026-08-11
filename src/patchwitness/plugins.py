"""Stable analyzer extension surface based on Python entry points."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any, Protocol

from patchwitness.models import Contract, FileChange

ENTRY_POINT_GROUP = "patchwitness.analyzers"


@dataclass(frozen=True, slots=True)
class AnalyzerContext:
    root: Path
    base_revision: str
    contract: Contract
    changes: tuple[FileChange, ...]


class Analyzer(Protocol):
    """Third-party analyzers implement one deterministic method."""

    name: str

    def analyze(self, context: AnalyzerContext) -> dict[str, Any]: ...


def discover_analyzers() -> tuple[EntryPoint, ...]:
    discovered = entry_points(group=ENTRY_POINT_GROUP)
    return tuple(sorted(discovered, key=lambda item: item.name))


def run_analyzers(
    context: AnalyzerContext,
    analyzers: tuple[Analyzer, ...] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    loaded = analyzers if analyzers is not None else _load_discovered()
    for analyzer in loaded:
        name = str(analyzer.name)
        try:
            result = analyzer.analyze(context)
            output[name] = {"ok": True, "result": result}
        except Exception as exc:  # plugins are an explicit isolation boundary
            output[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return output


def _load_discovered() -> tuple[Analyzer, ...]:
    analyzers: list[Analyzer] = []
    for point in discover_analyzers():
        value = point.load()
        instance = value() if isinstance(value, type) else value
        analyzers.append(instance)
    return tuple(analyzers)

