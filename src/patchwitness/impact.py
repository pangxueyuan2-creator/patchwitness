"""Fast, language-aware file dependency and change blast-radius analysis."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from patchwitness.models import FileChange

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
TEST_MARKERS = ("test_", "_test.", ".test.", ".spec.", "/tests/", "/test/")
IGNORED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".patchwitness",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "vendor",
}

_PY_IMPORT = re.compile(r"^\s*(?:from\s+([.\w]+)\s+import\s+|import\s+([\w.]+))", re.MULTILINE)
_JS_IMPORT = re.compile(r"(?:from\s+|import\s*\(\s*|require\s*\(\s*)['\"]([^'\"]+)['\"]")


def analyze_impact(
    root: Path,
    changes: Iterable[FileChange],
    *,
    max_depth: int = 6,
    use_cache: bool = True,
) -> dict[str, Any]:
    repository = root.resolve()
    source_files = _source_files(repository)
    fingerprint = _fingerprint(repository, source_files)
    cache_path = repository / ".patchwitness" / "cache" / "impact-v1.json"
    cache_hit = False
    graph: dict[str, list[str]]
    if use_cache:
        cached = _read_cache(cache_path)
        if cached and cached.get("fingerprint") == fingerprint:
            graph = {str(key): list(value) for key, value in cached["graph"].items()}
            cache_hit = True
        else:
            graph = _build_graph(repository, source_files)
            _write_cache(cache_path, {"fingerprint": fingerprint, "graph": graph})
    else:
        graph = _build_graph(repository, source_files)

    reverse: dict[str, set[str]] = defaultdict(set)
    for source, dependencies in graph.items():
        for dependency in dependencies:
            reverse[dependency].add(source)

    changed_paths = sorted(
        change.path
        for change in changes
        if PurePosixPath(change.path).suffix.lower() in SOURCE_SUFFIXES
    )
    direct: set[str] = set()
    transitive: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    for path in changed_paths:
        for dependent in reverse.get(path, ()):
            direct.add(dependent)
            queue.append((dependent, 1))
    visited = set(changed_paths) | direct
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for dependent in reverse.get(current, ()):
            if dependent in visited:
                continue
            visited.add(dependent)
            transitive.add(dependent)
            queue.append((dependent, depth + 1))

    affected = direct | transitive
    affected_tests = sorted(path for path in affected if _is_test(path))
    changed_lines = sum(change.changed_lines for change in changes)
    score = min(
        100,
        len(changed_paths) * 4
        + min(changed_lines // 10, 25)
        + len(direct) * 5
        + len(transitive) * 2
        + len(affected_tests),
    )
    level = (
        "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
    )
    return {
        "version": 1,
        "files_indexed": len(source_files),
        "edges_indexed": sum(len(dependencies) for dependencies in graph.values()),
        "changed_source_files": changed_paths,
        "direct_dependents": sorted(direct),
        "transitive_dependents": sorted(transitive),
        "affected_tests": affected_tests,
        "risk_score": score,
        "risk_level": level,
        "max_depth": max_depth,
        "cache_hit": cache_hit,
    }


def _source_files(root: Path) -> list[Path]:
    output: list[Path] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            directory for directory in directories if directory not in IGNORED_DIRECTORIES
        )
        base = Path(current)
        for filename in sorted(files):
            path = base / filename
            if path.suffix.lower() in SOURCE_SUFFIXES:
                output.append(path)
    return output


def _fingerprint(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def _build_graph(root: Path, files: Iterable[Path]) -> dict[str, list[str]]:
    paths = {path.relative_to(root).as_posix(): path for path in files}
    module_index = _python_module_index(paths)
    graph: dict[str, list[str]] = {}
    for relative, absolute in paths.items():
        try:
            if absolute.stat().st_size > 2_000_000:
                graph[relative] = []
                continue
            text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError:
            graph[relative] = []
            continue
        if absolute.suffix.lower() == ".py":
            dependencies = _python_dependencies(relative, text, module_index)
        else:
            dependencies = _javascript_dependencies(relative, text, paths)
        graph[relative] = sorted(dependencies - {relative})
    return graph


def _python_module_index(paths: dict[str, Path]) -> dict[str, str]:
    index: dict[str, str] = {}
    for relative in paths:
        if not relative.endswith(".py"):
            continue
        path = PurePosixPath(relative)
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        if module:
            index[module] = relative
        if "src" in parts:
            position = parts.index("src") + 1
            shortened = ".".join(parts[position:])
            if shortened:
                index.setdefault(shortened, relative)
    return index


def _python_dependencies(relative: str, text: str, modules: dict[str, str]) -> set[str]:
    dependencies: set[str] = set()
    current_parts = list(PurePosixPath(relative).with_suffix("").parts[:-1])
    for match in _PY_IMPORT.finditer(text):
        imported = match.group(1) or match.group(2)
        if not imported:
            continue
        if imported.startswith("."):
            level = len(imported) - len(imported.lstrip("."))
            suffix = imported.lstrip(".").split(".") if imported.lstrip(".") else []
            prefix = current_parts[: max(0, len(current_parts) - level + 1)]
            imported = ".".join(prefix + suffix)
        candidate = imported
        while candidate:
            target = modules.get(candidate)
            if target:
                dependencies.add(target)
                break
            candidate = candidate.rpartition(".")[0]
    return dependencies


def _javascript_dependencies(relative: str, text: str, paths: dict[str, Path]) -> set[str]:
    dependencies: set[str] = set()
    parent = PurePosixPath(relative).parent
    for match in _JS_IMPORT.finditer(text):
        specifier = match.group(1)
        if not specifier.startswith("."):
            continue
        base = _collapse(parent / specifier)
        candidates = [
            str(base),
            *(str(base) + suffix for suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")),
            *(str(base / ("index" + suffix)) for suffix in (".ts", ".tsx", ".js", ".jsx")),
        ]
        for candidate in candidates:
            if candidate in paths:
                dependencies.add(candidate)
                break
    return dependencies


def _collapse(path: PurePosixPath) -> PurePosixPath:
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return PurePosixPath(*parts)


def _is_test(path: str) -> bool:
    lowered = f"/{path.lower()}"
    name = PurePosixPath(lowered).name
    return any(marker in lowered or marker in name for marker in TEST_MARKERS)


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) and isinstance(value.get("graph"), dict) else None


def _write_cache(path: Path, value: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError:
        return
