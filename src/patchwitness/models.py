"""Typed domain models for contracts, findings, checks, and evidence packs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class GateStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class CheckSpec:
    id: str
    command: str
    required: bool = True
    timeout_seconds: int = 900

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CheckSpec:
        return cls(
            id=str(value["id"]),
            command=str(value["command"]),
            required=bool(value.get("required", True)),
            timeout_seconds=int(value.get("timeout_seconds", 900)),
        )


@dataclass(frozen=True, slots=True)
class Contract:
    id: str = "default"
    goal: str = "Verify the current repository change"
    allowed_paths: tuple[str, ...] = ("**",)
    denied_paths: tuple[str, ...] = (".git/**", ".patchwitness/evidence/**")
    protected_paths: tuple[str, ...] = (
        ".github/workflows/**",
        ".patchwitness.toml",
        ".patchwitness/contracts/**",
    )
    max_files: int = 50
    max_lines: int = 2_000
    allow_binary: bool = False
    allow_dependency_changes: bool = False
    require_tests: bool = True
    checks: tuple[CheckSpec, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Contract:
        policy = value.get("policy", value)
        checks = tuple(CheckSpec.from_dict(item) for item in value.get("checks", ()))
        return cls(
            id=str(value.get("id", "default")),
            goal=str(value.get("goal", "Verify the current repository change")),
            allowed_paths=tuple(str(item) for item in policy.get("allowed_paths", ("**",))),
            denied_paths=tuple(
                str(item)
                for item in policy.get(
                    "denied_paths", (".git/**", ".patchwitness/evidence/**")
                )
            ),
            protected_paths=tuple(
                str(item)
                for item in policy.get(
                    "protected_paths",
                    (
                        ".github/workflows/**",
                        ".patchwitness.toml",
                        ".patchwitness/contracts/**",
                    ),
                )
            ),
            max_files=int(policy.get("max_files", 50)),
            max_lines=int(policy.get("max_lines", 2_000)),
            allow_binary=bool(policy.get("allow_binary", False)),
            allow_dependency_changes=bool(policy.get("allow_dependency_changes", False)),
            require_tests=bool(policy.get("require_tests", True)),
            checks=checks,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    status: str
    additions: int
    deletions: int
    binary: bool
    before_sha256: str | None
    after_sha256: str | None

    @property
    def changed_lines(self) -> int:
        return self.additions + self.deletions

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CheckResult:
    id: str
    command: str
    required: bool
    exit_code: int | None
    duration_ms: int
    timed_out: bool
    output_sha256: str
    output_excerpt: str

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["passed"] = self.passed
        return value


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidencePack:
    schema_version: str
    tool: dict[str, Any]
    repository: dict[str, Any]
    contract: dict[str, Any]
    changes: tuple[dict[str, Any], ...]
    checks: tuple[dict[str, Any], ...]
    findings: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    captured_at: str
    payload_sha256: str
    extensions: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> GateStatus:
        return GateStatus(str(self.summary["status"]))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvidencePack:
        return cls(
            schema_version=str(value["schema_version"]),
            tool=dict(value["tool"]),
            repository=dict(value["repository"]),
            contract=dict(value["contract"]),
            changes=tuple(value["changes"]),
            checks=tuple(value["checks"]),
            findings=tuple(value["findings"]),
            summary=dict(value["summary"]),
            captured_at=str(value["captured_at"]),
            payload_sha256=str(value["payload_sha256"]),
            extensions=dict(value.get("extensions", {})),
        )

