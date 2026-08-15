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
    trusted: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CheckSpec:
        return cls(
            id=str(value["id"]),
            command=str(value["command"]),
            required=bool(value.get("required", True)),
            timeout_seconds=int(value.get("timeout_seconds", 900)),
            trusted=bool(value.get("trusted", True)),
        )


def _slug_command(command: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in command)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:40] or "check"


def _as_check_specs(raw: Any, *, trusted: bool = True) -> tuple[CheckSpec, ...]:
    checks: list[CheckSpec] = []
    if not raw:
        return ()
    for item in raw:
        if isinstance(item, str):
            checks.append(CheckSpec(id=_slug_command(item), command=item, trusted=trusted))
        elif isinstance(item, dict):
            parsed = CheckSpec.from_dict(item)
            if not trusted:
                parsed = CheckSpec(
                    id=parsed.id,
                    command=parsed.command,
                    required=parsed.required,
                    timeout_seconds=parsed.timeout_seconds,
                    trusted=False,
                )
            checks.append(parsed)
        else:
            raise TypeError(f"unsupported check spec: {item!r}")
    return tuple(checks)


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
    exclusive_allow: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Contract:
        policy = value.get("policy", value)
        checks = _as_check_specs(value.get("checks", ()))
        return cls(
            id=str(value.get("id", "default")),
            goal=str(value.get("goal", "Verify the current repository change")),
            allowed_paths=tuple(str(item) for item in policy.get("allowed_paths", ("**",))),
            denied_paths=tuple(
                str(item)
                for item in policy.get("denied_paths", (".git/**", ".patchwitness/evidence/**"))
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
            exclusive_allow=bool(
                policy.get("exclusive_allow", value.get("exclusive_allow", False))
            ),
        )

    @classmethod
    def from_boundary(cls, value: dict[str, Any]) -> Contract:
        """Load an independent agent-boundary/v1 document.

        Empty allowed_paths means allow-all unless exclusive_allow is set,
        in which case every path is outside scope.
        """
        exclusive = bool(value.get("exclusive_allow", False))
        raw_allowed = value.get("allowed_paths")
        if raw_allowed is None:
            allowed: tuple[str, ...] = () if exclusive else ("**",)
        else:
            allowed = tuple(str(item) for item in raw_allowed)
            if not allowed and not exclusive:
                allowed = ("**",)
        checks = _as_check_specs(
            value.get("required_checks", value.get("checks", ())),
            trusted=False,
        )
        return cls(
            id=str(value.get("id", "default")),
            goal=str(value.get("goal", "Verify the current repository change")),
            allowed_paths=allowed,
            denied_paths=tuple(
                str(item)
                for item in value.get("denied_paths", (".git/**", ".patchwitness/evidence/**"))
            ),
            protected_paths=tuple(
                str(item)
                for item in value.get(
                    "protected_paths",
                    (
                        ".github/workflows/**",
                        ".patchwitness.toml",
                        ".patchwitness/contracts/**",
                    ),
                )
            ),
            max_files=int(value.get("max_files", 50)),
            max_lines=int(value.get("max_lines", 2_000)),
            allow_binary=bool(value.get("allow_binary", False)),
            allow_dependency_changes=bool(value.get("allow_dependency_changes", False)),
            require_tests=bool(value.get("require_tests", bool(checks))),
            checks=checks,
            exclusive_allow=exclusive,
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
    previous_path: str | None = None

    @property
    def changed_lines(self) -> int:
        return self.additions + self.deletions

    @property
    def policy_paths(self) -> tuple[str, ...]:
        if self.previous_path and self.previous_path != self.path:
            return (self.path, self.previous_path)
        return (self.path,)

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
