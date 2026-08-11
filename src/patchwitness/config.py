"""Contract loading and safe project initialization."""

from __future__ import annotations

import tomllib
from pathlib import Path

from patchwitness.models import Contract

DEFAULT_CONFIG = '''\
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
'''


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
        contract = Contract.from_dict(value)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"invalid contract {source}: {exc}") from exc
    _validate(contract, source)
    return contract


def _validate(contract: Contract, source: str) -> None:
    if not contract.id.strip():
        raise ConfigError(f"invalid contract {source}: id cannot be empty")
    if contract.max_files < 0 or contract.max_lines < 0:
        raise ConfigError(f"invalid contract {source}: budgets cannot be negative")
    seen: set[str] = set()
    for check in contract.checks:
        if not check.id.strip() or not check.command.strip():
            raise ConfigError(f"invalid contract {source}: checks need id and command")
        if check.id in seen:
            raise ConfigError(f"invalid contract {source}: duplicate check id {check.id!r}")
        if check.timeout_seconds < 1:
            raise ConfigError(f"invalid contract {source}: timeout must be positive")
        seen.add(check.id)


def initialize_project(root: Path, *, force: bool = False) -> Path:
    target = root / ".patchwitness.toml"
    if target.exists() and not force:
        raise ConfigError(f"{target} already exists; use --force to replace it")
    target.write_text(DEFAULT_CONFIG, encoding="utf-8", newline="\n")
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

