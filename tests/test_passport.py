from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from patchwitness.passport import (
    MAX_PASSPORT_BYTES,
    PassportError,
    build_tasktopr_passport,
    derive_change_subject,
    exact_manifest_sha256,
    load_passport,
    main,
)
from patchwitness.safe_delivery import content_digest, verify_safe_delivery
from patchwitness.tasktopr import TASKTOPR_HANDOFF_SCHEMA, TASKTOPR_TRUST_BOUNDARY

TASKTOPR_REVISION = "2" * 40


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Passport Fixture")
    _git(root, "config", "user.email", "passport@example.invalid")
    (root / ".patchwitness.toml").write_text(
        'id = "reviewed-policy"\ngoal = "verify the exact candidate"\n', encoding="utf-8"
    )
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", "--", ".patchwitness.toml", "app.py")
    _git(root, "commit", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(root, "add", "--", "app.py")
    _git(root, "commit", "-m", "candidate")
    head = _git(root, "rev-parse", "HEAD")
    return root, base, head


def _handoff(root: Path, base: str, head: str) -> dict[str, object]:
    payload = {
        "schema_version": TASKTOPR_HANDOFF_SCHEMA,
        "component": "execution",
        "producer": {
            "name": "tasktopr",
            "version": "0.2.0",
            "git_revision": TASKTOPR_REVISION,
            "source_sha256": "a" * 64,
        },
        "change": {
            "repository_sha256": content_digest(str(root.resolve())),
            "base_sha": base,
            "head_sha": head,
            "changed_file_count": 1,
            "change_scope_sha256": "b" * 64,
        },
        "policy": {"version": "tasktopr-execution-v1", "sha256": "c" * 64},
        "verification": {
            "decision": "REVIEW_REQUIRED",
            "complete": True,
            "tests_status": "pass",
            "tests_count": 3,
            "command_list_sha256": "d" * 64,
            "test_result_sha256": "e" * 64,
            "protected_path_decision": "allow",
        },
        "source_receipt": {"schema_version": 1, "sha256": "f" * 64},
        "trust_boundary": TASKTOPR_TRUST_BOUNDARY,
    }
    return {"payload": payload, "receipt_sha256": content_digest(payload)}


def _write_handoff(path: Path, report: dict[str, object]) -> None:
    path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")


def test_subject_is_derived_from_exact_git_and_reviewed_policy(tmp_path: Path) -> None:
    root, base, head = _repository(tmp_path)
    subject = derive_change_subject(root, base_sha=base, head="HEAD", policy_ref=base)

    assert subject.repository_sha256 == content_digest(str(root.resolve()))
    assert subject.base_sha == base
    assert subject.head_sha == head
    assert subject.manifest_sha256 == exact_manifest_sha256(root, base, head)
    policy = (root / ".patchwitness.toml").read_bytes()
    assert subject.policy_sha256 == hashlib.sha256(policy).hexdigest()


def test_tasktopr_passport_keeps_missing_independent_components_unknown(tmp_path: Path) -> None:
    root, base, head = _repository(tmp_path)
    handoff = tmp_path / "tasktopr.json"
    _write_handoff(handoff, _handoff(root, base, head))

    report = build_tasktopr_passport(
        root,
        handoff_path=handoff,
        tasktopr_revision=TASKTOPR_REVISION,
        base_sha=base,
        policy_ref=base,
    )
    payload = verify_safe_delivery(report)

    assert payload["stage"] == "pr"
    assert payload["decision"] == "UNKNOWN"
    assert payload["execution"]["decision"] == "PASS"
    assert payload["execution"]["tool_revision"] == TASKTOPR_REVISION
    assert payload["api"] == {"decision": "UNKNOWN", "complete": False}
    assert payload["ci"] == {"decision": "UNKNOWN", "complete": False}


def test_tasktopr_passport_rejects_stale_head(tmp_path: Path) -> None:
    root, base, head = _repository(tmp_path)
    report = _handoff(root, base, head)
    payload = report["payload"]
    assert isinstance(payload, dict)
    change = payload["change"]
    assert isinstance(change, dict)
    change["head_sha"] = base
    report["receipt_sha256"] = content_digest(payload)
    handoff = tmp_path / "stale.json"
    _write_handoff(handoff, report)

    with pytest.raises(ValueError, match="different change subject"):
        build_tasktopr_passport(
            root,
            handoff_path=handoff,
            tasktopr_revision=TASKTOPR_REVISION,
            base_sha=base,
            policy_ref=base,
        )


def test_passport_rejects_dirty_candidate_and_policy_traversal(tmp_path: Path) -> None:
    root, base, _head = _repository(tmp_path)
    (root / "untracked.txt").write_text("drift\n", encoding="utf-8")
    with pytest.raises(PassportError, match="must be clean"):
        derive_change_subject(root, base_sha=base, head="HEAD", policy_ref=base)

    (root / "untracked.txt").unlink()
    with pytest.raises(PassportError, match="repository-relative"):
        derive_change_subject(
            root,
            base_sha=base,
            head="HEAD",
            policy_ref=base,
            policy_path="../policy.toml",
        )


def test_cli_writes_verifiable_passport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, base, head = _repository(tmp_path)
    handoff = tmp_path / "handoff.json"
    output = tmp_path / "passport.json"
    _write_handoff(handoff, _handoff(root, base, head))
    monkeypatch.chdir(root)

    status = main(
        [
            "--json",
            "tasktopr",
            "--handoff",
            str(handoff),
            "--tasktopr-revision",
            TASKTOPR_REVISION,
            "--base",
            base,
            "--policy-ref",
            base,
            "--output",
            str(output),
        ]
    )

    assert status == 0
    verify_safe_delivery(json.loads(output.read_text(encoding="utf-8")))


def test_offline_loader_rejects_duplicate_keys_oversize_and_symlink(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"payload":{},"payload":{},"receipt_sha256":"' + "0" * 64 + '"}\n',
        encoding="utf-8",
    )
    with pytest.raises(PassportError, match="duplicate JSON key: payload"):
        load_passport(duplicate)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (MAX_PASSPORT_BYTES + 1))
    with pytest.raises(PassportError, match="byte budget"):
        load_passport(oversized)

    regular = tmp_path / "regular.json"
    regular.write_text("{}\n", encoding="utf-8")
    symlink = tmp_path / "passport-link.json"
    try:
        symlink.symlink_to(regular)
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")
    with pytest.raises(PassportError, match="non-symlink"):
        load_passport(symlink)


def test_verify_cli_reports_decision_and_rejects_tampering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base, head = _repository(tmp_path)
    handoff = tmp_path / "handoff.json"
    passport = tmp_path / "passport.json"
    _write_handoff(handoff, _handoff(root, base, head))
    report = build_tasktopr_passport(
        root,
        handoff_path=handoff,
        tasktopr_revision=TASKTOPR_REVISION,
        base_sha=base,
        policy_ref=base,
    )
    passport.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    assert main(["--json", "verify", str(passport)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["ok"] is True
    assert verified["decision"] == "UNKNOWN"
    assert verified["components"]["execution"] == "PASS"
    assert verified["components"]["review"] == "UNKNOWN"

    report["receipt_sha256"] = "0" * 64
    passport.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    assert main(["--json", "verify", str(passport)]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["ok"] is False
    assert "mismatch" in rejected["error"]
