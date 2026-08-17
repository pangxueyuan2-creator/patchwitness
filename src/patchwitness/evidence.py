"""Evidence capture, canonicalization, atomic persistence, and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchwitness import git
from patchwitness._version import __version__
from patchwitness.checks import run_checks
from patchwitness.cleanroom import clean_room
from patchwitness.impact import analyze_impact
from patchwitness.models import Contract, EvidencePack, FileChange, Finding, GateStatus, Severity
from patchwitness.plugins import AnalyzerContext, run_analyzers
from patchwitness.policy import evaluate_policy
from patchwitness.security import scan_changed_files

SCHEMA_VERSION = "patchwitness.dev/evidence/v1"


class EvidenceError(ValueError):
    """Raised when evidence is malformed or fails integrity checks."""


def capture_evidence(
    root: Path,
    contract: Contract,
    *,
    base: str = "HEAD",
    execute_checks: bool = True,
    parallel_checks: bool = True,
    max_workers: int = 4,
    contract_source: str = "working-tree",
    clean_room_checks: bool = False,
) -> EvidencePack:
    repository = git.find_root(root)
    base_revision = git.resolve_revision(repository, base)
    changes = git.collect_changes(repository, base_revision)
    if execute_checks and clean_room_checks:
        with clean_room(repository, base_revision) as verifier_root:
            check_results = run_checks(
                verifier_root,
                contract.checks,
                parallel=parallel_checks,
                max_workers=max_workers,
                untrusted=True,
            )
    elif execute_checks:
        check_results = run_checks(
            repository,
            contract.checks,
            parallel=parallel_checks,
            max_workers=max_workers,
        )
    else:
        check_results = ()
    findings = evaluate_policy(contract, changes, check_results) + scan_changed_files(
        repository, changes
    )
    if execute_checks and not clean_room_checks:
        current_changes = git.collect_changes(repository, base_revision)
        for drifted in _drifted_paths(changes, current_changes):
            findings += (
                Finding(
                    "PW032",
                    Severity.ERROR,
                    "repository content changed while checks were running; refusing stale evidence",
                    drifted,
                ),
            )
    impact = analyze_impact(repository, changes)
    analyzer_extensions = run_analyzers(
        AnalyzerContext(repository, base_revision, contract, changes)
    )
    status = (
        GateStatus.FAIL
        if any(finding.severity == Severity.ERROR for finding in findings)
        else GateStatus.PASS
    )
    total_lines = sum(change.changed_lines for change in changes)
    captured_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    unsigned: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "patchwitness", "version": __version__},
        "repository": {
            "root_name": repository.name,
            "base_revision": base_revision,
            "head_revision": git.head_revision(repository),
            "branch": git.branch_name(repository),
            "remote": git.remote_url(repository),
            "dirty": git.is_dirty(repository),
        },
        "contract": {
            **contract.to_dict(),
            "source": contract_source,
        },
        "changes": [change.to_dict() for change in changes],
        "checks": [result.to_dict() for result in check_results],
        "findings": [finding.to_dict() for finding in findings],
        "summary": {
            "status": status.value,
            "files_changed": len(changes),
            "lines_changed": total_lines,
            "checks_passed": sum(result.passed for result in check_results),
            "checks_total": len(check_results),
            "errors": sum(finding.severity == Severity.ERROR for finding in findings),
            "warnings": sum(finding.severity == Severity.WARNING for finding in findings),
        },
        "captured_at": captured_at,
        "extensions": {
            "impact": impact,
            "analyzers": analyzer_extensions,
            "verification": {
                "clean_room": clean_room_checks,
                "git_hooks_disabled": clean_room_checks,
            },
            "environment": {
                "os": platform.system(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
            },
        },
    }
    payload_sha256 = _digest(unsigned)
    return EvidencePack.from_dict({**unsigned, "payload_sha256": payload_sha256})


def _drifted_paths(
    recorded: tuple[FileChange, ...], current: tuple[FileChange, ...]
) -> tuple[str, ...]:
    """Return paths whose commit-relevant change state moved during verification."""

    def fingerprint(change: FileChange) -> tuple[str, str | None, str | None, str | None]:
        return (
            change.status,
            change.previous_path,
            change.before_sha256,
            change.after_sha256,
        )

    recorded_by_path = {change.path: fingerprint(change) for change in recorded}
    current_by_path = {change.path: fingerprint(change) for change in current}
    all_paths = recorded_by_path.keys() | current_by_path.keys()
    return tuple(
        sorted(path for path in all_paths if recorded_by_path.get(path) != current_by_path.get(path))
    )


def verify_evidence(pack: EvidencePack | dict[str, Any]) -> EvidencePack:
    evidence = pack if isinstance(pack, EvidencePack) else EvidencePack.from_dict(pack)
    if evidence.schema_version != SCHEMA_VERSION:
        raise EvidenceError(f"unsupported schema version: {evidence.schema_version}")
    value = evidence.to_dict()
    expected = str(value.pop("payload_sha256"))
    actual = _digest(value)
    if not hmac.compare_digest(expected, actual):
        raise EvidenceError(f"payload digest mismatch: expected {expected}, computed {actual}")
    return evidence


def load_evidence(path: Path) -> EvidencePack:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot load evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"invalid evidence {path}: root must be an object")
    try:
        return EvidencePack.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid evidence {path}: {exc}") from exc


def write_evidence(pack: EvidencePack, path: Path) -> Path:
    verified = verify_evidence(pack)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(verified.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary)
        raise
    return path


def _digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
