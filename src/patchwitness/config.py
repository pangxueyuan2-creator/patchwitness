"""Contract loading and safe project initialization."""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from patchwitness.detection import detect_project
from patchwitness.models import Contract

DEFAULT_CONFIG = """\
version = 1
id = "default"
goal = "Keep AI-generated changes inside an explicit, reviewable boundary"

[policy]
allowed_paths = ["**"]
denied_paths = [".git/**", ".patchwitness/evidence/**"]
protected_paths = [
  ".github/workflows/**",
  ".patchwitness.toml",
  ".patchwitness/contracts/**",
]
max_files = 50
max_lines = 2000
allow_binary = false
allow_dependency_changes = false
require_tests = true

[[checks]]
id = "tests"
command = "python -m pytest"
required = true
timeout_seconds = 900
"""


class ConfigError(ValueError):
    """Raised when a contract cannot be loaded safely."""


def load_contract(path: Path) -> Contract:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read contract {path}: {exc}") from exc
    return load_contract_bytes(raw, source=str(path))


def load_contract_bytes(raw: bytes, *, source: str = "<memory>") -> Contract:
    try:
        value = tomllib.loads(raw.decode("utf-8"))
        _validate_raw_contract(value)
        contract = Contract.from_dict(value)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"invalid contract {source}: {exc}") from exc
    _validate(contract, source)
    return contract


def _require_raw_type(
    value: object, expected: type[object], field: str, description: str
) -> None:
    if type(value) is not expected:
        # Field names are controlled by this validator; never echo rejected data.
        raise ValueError(f"{field} must be {description}")


def _validate_raw_contract(value: dict[str, Any]) -> None:
    """Validate TOML types before the shared model's legacy coercions run."""
    if "version" in value:
        _require_raw_type(value["version"], int, "version", "the integer 1")
        if value["version"] != 1:
            raise ValueError("unsupported contract version; expected 1")
    for field in ("id", "goal"):
        if field in value:
            _require_raw_type(value[field], str, field, "a string")

    # Retain the legacy flat form and defaults when [policy] is absent.
    policy = value.get("policy", value)
    _require_raw_type(policy, dict, "policy", "a TOML table")
    for field in ("allowed_paths", "denied_paths", "protected_paths"):
        if field in policy:
            patterns = policy[field]
            _require_raw_type(patterns, list, field, "an array of strings")
            if any(type(pattern) is not str for pattern in patterns):
                raise ValueError(f"{field} must be an array of strings")
    for field in ("allow_binary", "allow_dependency_changes", "require_tests"):
        if field in policy:
            _require_raw_type(policy[field], bool, field, "a boolean")
    for field in ("max_files", "max_lines"):
        if field in policy:
            _require_raw_type(policy[field], int, field, "an integer")

    checks = value.get("checks", [])
    _require_raw_type(checks, list, "checks", "an array of TOML tables")
    for index, check in enumerate(checks):
        label = f"checks[{index}]"
        _require_raw_type(check, dict, label, "a TOML table")
        for field in ("id", "command"):
            if field not in check:
                raise ValueError(f"{label} requires {field}")
            _require_raw_type(check[field], str, f"{label}.{field}", "a string")
        if "required" in check:
            _require_raw_type(check["required"], bool, f"{label}.required", "a boolean")
        if "timeout_seconds" in check:
            _require_raw_type(
                check["timeout_seconds"], int, f"{label}.timeout_seconds", "an integer"
            )


def _validate(contract: Contract, source: str) -> None:
    if not contract.id.strip():
        raise ConfigError(f"invalid contract {source}: id cannot be empty")
    if contract.max_files < 0 or contract.max_lines < 0:
        raise ConfigError(f"invalid contract {source}: budgets cannot be negative")
    for field, patterns in (
        ("allowed_paths", contract.allowed_paths),
        ("denied_paths", contract.denied_paths),
        ("protected_paths", contract.protected_paths),
    ):
        for pattern in patterns:
            if not pattern.strip():
                raise ConfigError(
                    f"invalid contract {source}: {field} contains an empty pattern"
                )
    seen: set[str] = set()
    for check in contract.checks:
        if not check.id.strip() or not check.command.strip():
            raise ConfigError(f"invalid contract {source}: checks need id and command")
        if check.id in seen:
            raise ConfigError(f"invalid contract {source}: duplicate check id {check.id!r}")
        if check.timeout_seconds < 1:
            raise ConfigError(f"invalid contract {source}: timeout must be positive")
        seen.add(check.id)


def initialize_project(
    root: Path,
    *,
    force: bool = False,
    checks: Iterable[tuple[str, str]] | None = None,
) -> Path:
    target = root / ".patchwitness.toml"
    if target.exists() and not force:
        raise ConfigError(f"{target} already exists; use --force to replace it")
    check_specs = (
        tuple(checks)
        if checks is not None
        else tuple((check.id, check.command) for check in detect_project(root).checks)
    )
    target.write_text(render_starter_config(check_specs), encoding="utf-8", newline="\n")
    evidence = root / ".patchwitness" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    gitignore = root / ".gitignore"
    marker = ".patchwitness/evidence/"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if marker not in existing.splitlines():
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        with gitignore.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{prefix}{marker}\n")
    return target


def render_starter_config(checks: Iterable[tuple[str, str]]) -> str:
    check_specs = tuple(checks)
    lines = [
        "version = 1",
        'id = "default"',
        'goal = "Keep AI-generated changes inside an explicit, reviewable boundary"',
        "",
        "[policy]",
        'allowed_paths = ["**"]',
        'denied_paths = [".git/**", ".patchwitness/evidence/**"]',
        "protected_paths = [",
        '  ".github/workflows/**",',
        '  ".patchwitness.toml",',
        '  ".patchwitness/contracts/**",',
        "]",
        "max_files = 50",
        "max_lines = 2000",
        "allow_binary = false",
        "allow_dependency_changes = false",
        f"require_tests = {'true' if check_specs else 'false'}",
    ]
    for check_id, command in check_specs:
        lines.extend(
            [
                "",
                "[[checks]]",
                f"id = {_toml_string(check_id)}",
                f"command = {_toml_string(command)}",
                "required = true",
                "timeout_seconds = 900",
            ]
        )
    return "\n".join(lines) + "\n"


def create_task_contract(
    root: Path,
    contract_id: str,
    *,
    goal: str,
    allowed_paths: Iterable[str],
    denied_paths: Iterable[str] = (),
    protected_paths: Iterable[str] = (),
    checks: Iterable[tuple[str, str]] = (),
    max_files: int = 25,
    max_lines: int = 1_000,
    force: bool = False,
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", contract_id):
        raise ConfigError("contract id must be 1-100 safe filename characters")
    allowed = tuple(allowed_paths)
    check_specs = tuple(checks)
    if not allowed:
        raise ConfigError("at least one --allow pattern is required")
    target = root / ".patchwitness" / "contracts" / f"{contract_id}.toml"
    if target.exists() and not force:
        raise ConfigError(f"{target} already exists; use --force to replace it")
    default_protected = (
        ".github/workflows/**",
        ".patchwitness.toml",
        ".patchwitness/contracts/**",
    )
    lines = [
        "version = 1",
        f"id = {_toml_string(contract_id)}",
        f"goal = {_toml_string(goal)}",
        "",
        "[policy]",
        f"allowed_paths = {_toml_array(allowed)}",
        f"denied_paths = {_toml_array(tuple(denied_paths))}",
        f"protected_paths = {_toml_array(tuple(protected_paths) or default_protected)}",
        f"max_files = {max_files}",
        f"max_lines = {max_lines}",
        "allow_binary = false",
        "allow_dependency_changes = false",
        f"require_tests = {'true' if check_specs else 'false'}",
    ]
    for check_id, command in check_specs:
        lines.extend(
            [
                "",
                "[[checks]]",
                f"id = {_toml_string(check_id)}",
                f"command = {_toml_string(command)}",
                "required = true",
                "timeout_seconds = 900",
            ]
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return target


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: Iterable[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"
