"""Evidence capture, canonicalization, atomic persistence, and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import platform
import subprocess
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchwitness import git
from patchwitness._version import __version__
from patchwitness.checks import run_checks
from patchwitness.cleanroom import clean_room
from patchwitness.file_input import FileInputError, read_regular_file
from patchwitness.impact import analyze_impact
from patchwitness.models import Contract, EvidencePack, FileChange, Finding, GateStatus, Severity
from patchwitness.plugins import AnalyzerContext, run_analyzers
from patchwitness.policy import evaluate_policy
from patchwitness.security import scan_changed_files

SCHEMA_VERSION = "patchwitness.dev/evidence/v1"
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024


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
    source_head = git.head_revision(repository)
    source_branch = git.branch_name(repository)
    changes = git.collect_changes(repository, base_revision)
    conflicts = set(git.verification_conflicts(repository, base_revision))
    if execute_checks and clean_room_checks and not conflicts:
        with clean_room(repository, base_revision) as verifier_root:
            check_results = run_checks(
                verifier_root,
                contract.checks,
                parallel=parallel_checks,
                max_workers=max_workers,
                untrusted=True,
            )
    elif execute_checks and not conflicts:
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
    if execute_checks:
        conflicts.update(git.verification_conflicts(repository, base_revision))
    findings += tuple(
        Finding(
            "PW033",
            Severity.ERROR,
            "index and working-tree verification content disagree or cannot be compared safely",
            path,
        )
        for path in sorted(conflicts)
    )
    impact = analyze_impact(repository, changes)
    analyzer_extensions = run_analyzers(
        AnalyzerContext(repository, base_revision, contract, changes)
    )
    if execute_checks:
        current_changes = git.collect_changes(repository, base_revision)
        for drifted in _drifted_paths(
            changes, current_changes, tracked_paths=_tracked_paths(repository)
        ):
            findings += (
                Finding(
                    "PW032",
                    Severity.ERROR,
                    "change scope or content moved during checks; refusing stale evidence",
                    drifted,
                ),
            )
    if (
        git.head_revision(repository) != source_head
        or git.branch_name(repository) != source_branch
    ):
        findings += (
            Finding(
                "PW032",
                Severity.ERROR,
                "repository HEAD or branch moved during capture; refusing stale evidence",
            ),
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
            "head_revision": source_head,
            "branch": source_branch,
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
    recorded: tuple[FileChange, ...],
    current: tuple[FileChange, ...],
    *,
    tracked_paths: frozenset[str],
) -> tuple[str, ...]:
    """Find recorded content drift and newly changed tracked/index paths.

    Newly generated untracked artifacts remain outside the recorded scope.
    FileChange uses "A" for both untracked and staged additions, so status
    alone cannot grant that exception: index membership must be checked.
    Deletions and renames also expand scope even if their old paths are no
    longer in the index. Previously recorded paths never get the exception.
    """

    def fingerprint(change: FileChange) -> tuple[str, str | None, str | None, str | None]:
        return (
            change.status,
            change.previous_path,
            change.before_sha256,
            change.after_sha256,
        )

    recorded_by_path = {change.path: fingerprint(change) for change in recorded}
    current_by_path = {change.path: fingerprint(change) for change in current}
    drifted = {
        path
        for path, recorded_fingerprint in recorded_by_path.items()
        if current_by_path.get(path) != recorded_fingerprint
    }
    drifted.update(
        change.path
        for change in current
        if change.path not in recorded_by_path
        and (change.status != "A" or change.path in tracked_paths)
    )
    return tuple(sorted(drifted))


def _tracked_paths(root: Path) -> frozenset[str]:
    """Read index membership without treating Git failure as an untracked path."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise git.GitError("cannot enumerate tracked paths after checks") from exc
    if result.returncode != 0 or (result.stdout and not result.stdout.endswith("\0")):
        raise git.GitError("cannot enumerate tracked paths after checks")
    # Match the Git adapter's existing path representation without whitespace stripping.
    return frozenset(path.replace("\\", "/") for path in result.stdout.split("\0") if path)


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


def _read_evidence(path: Path) -> bytes:
    try:
        return read_regular_file(path, max_bytes=MAX_EVIDENCE_BYTES, label="evidence")
    except FileInputError as exc:
        raise EvidenceError(str(exc)) from exc


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("evidence contains a duplicate JSON key")
        result[key] = value
    return result


def _finite_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise EvidenceError("evidence contains a non-finite JSON number")
    return number


def load_evidence(path: Path) -> EvidencePack:
    try:
        value = json.loads(
            _read_evidence(path).decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=_finite_number,
            parse_float=_finite_number,
        )
    except EvidenceError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise EvidenceError("cannot load evidence: unreadable or invalid UTF-8 JSON") from exc
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
