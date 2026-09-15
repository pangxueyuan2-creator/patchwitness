"""User-facing composition and offline verification of Safe Delivery passports.

This module intentionally produces a PR-stage Safe Delivery passport containing
only the TaskToPR execution component. Missing independent components remain
UNKNOWN/REVIEW_REQUIRED; this command never upgrades execution evidence into
merge or release authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any, cast

from patchwitness.git import (
    find_root,
    head_revision,
    is_dirty,
    load_file_at_revision,
    resolve_revision,
)
from patchwitness.safe_delivery import (
    COMPONENTS,
    ChangeSubject,
    compose_safe_delivery,
    content_digest,
    verify_safe_delivery,
)
from patchwitness.tasktopr import adapt_tasktopr_execution, load_tasktopr_handoff
from patchwitness.tasktopr_policy import require_tasktopr_plan_approval

MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_POLICY_BYTES = 1024 * 1024
MAX_PASSPORT_BYTES = 2 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 30
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_MANIFEST_DOMAIN = b"patchwitness-exact-commit-manifest-v1\0"


class PassportError(ValueError):
    """Raised when exact candidate or passport inputs are ambiguous or unsafe."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PassportError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PassportError(f"{name} must be a JSON object")
    return cast(dict[str, Any], value)


def _exact_revision(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise PassportError(f"{name} must be an exact lowercase 40-character Git SHA")
    return value


def _policy_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise PassportError("policy path must be a portable repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PassportError("policy path must be a portable repository-relative path")
    return path.as_posix()


def _git(
    root: Path,
    *arguments: str,
    limit: int = MAX_MANIFEST_BYTES,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    command = [
        "git",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "protocol.allow=never",
        "-C",
        str(root),
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PassportError("trusted Git metadata read failed") from exc
    if len(result.stdout) > limit or len(result.stderr) > 64 * 1024:
        raise PassportError("trusted Git metadata exceeded its byte budget")
    if result.returncode not in allowed_returncodes:
        raise PassportError("trusted Git metadata read failed")
    return result


def _require_ancestor(root: Path, base_sha: str, head_sha: str) -> None:
    result = _git(
        root,
        "merge-base",
        "--is-ancestor",
        base_sha,
        head_sha,
        limit=1024,
        allowed_returncodes=(0, 1),
    )
    if result.returncode != 0:
        raise PassportError("base revision is not an ancestor of the candidate HEAD")


def exact_manifest_sha256(root: Path, base_sha: str, head_sha: str) -> str:
    """Hash a bounded, exact-commit raw Git manifest without reading the worktree."""
    _exact_revision(base_sha, "base revision")
    _exact_revision(head_sha, "head revision")
    raw = _git(
        root,
        "diff-tree",
        "-r",
        "--raw",
        "-z",
        "--no-commit-id",
        "--no-renames",
        "--full-index",
        "--no-abbrev",
        base_sha,
        head_sha,
        "--",
    ).stdout
    return hashlib.sha256(
        _MANIFEST_DOMAIN
        + base_sha.encode("ascii")
        + b"\0"
        + head_sha.encode("ascii")
        + b"\0"
        + raw
    ).hexdigest()


def derive_change_subject(
    root: Path,
    *,
    base_sha: str,
    head: str,
    policy_ref: str,
    policy_path: str = ".patchwitness.toml",
) -> ChangeSubject:
    """Derive PatchWitness-owned subject identity from a clean exact Git candidate."""
    root = find_root(root)
    if is_dirty(root):
        raise PassportError("candidate repository must be clean before passport composition")
    base_sha = _exact_revision(base_sha, "base revision")
    policy_ref = _exact_revision(policy_ref, "policy revision")
    resolved_base = resolve_revision(root, base_sha)
    resolved_head = resolve_revision(root, head)
    resolved_policy = resolve_revision(root, policy_ref)
    if resolved_base != base_sha or resolved_policy != policy_ref:
        raise PassportError("reviewer-controlled revisions did not resolve exactly")
    current_head = head_revision(root)
    if current_head is None or resolved_head != current_head:
        raise PassportError("candidate head must resolve to the repository's current exact HEAD")
    _exact_revision(resolved_head, "candidate HEAD")
    _require_ancestor(root, base_sha, resolved_head)

    relative_policy = _policy_path(policy_path)
    policy_bytes = load_file_at_revision(root, resolved_policy, relative_policy)
    if len(policy_bytes) > MAX_POLICY_BYTES:
        raise PassportError("reviewer policy exceeds the byte budget")
    subject = ChangeSubject(
        repository_sha256=content_digest(str(root.resolve())),
        base_sha=base_sha,
        head_sha=resolved_head,
        manifest_sha256=exact_manifest_sha256(root, base_sha, resolved_head),
        policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
    )
    subject.validate()
    return subject


def build_tasktopr_passport(
    root: Path,
    *,
    handoff_path: Path,
    tasktopr_revision: str,
    base_sha: str,
    head: str = "HEAD",
    policy_ref: str,
    policy_path: str = ".patchwitness.toml",
) -> dict[str, Any]:
    """Compose one exact-subject PR-stage passport from TaskToPR execution evidence."""
    tasktopr_revision = _exact_revision(tasktopr_revision, "TaskToPR revision")
    root = find_root(root)
    subject = derive_change_subject(
        root,
        base_sha=base_sha,
        head=head,
        policy_ref=policy_ref,
        policy_path=policy_path,
    )
    execution = adapt_tasktopr_execution(
        load_tasktopr_handoff(handoff_path),
        subject=subject,
        trusted_revision=tasktopr_revision,
    )
    report = compose_safe_delivery(
        subject,
        [execution],
        trusted_tools={"execution": ("tasktopr", tasktopr_revision)},
        policy_sha256=subject.policy_sha256,
        stage="pr",
    )
    verify_safe_delivery(report)
    if is_dirty(root) or head_revision(root) != subject.head_sha:
        raise PassportError("candidate changed while the passport was being composed")
    return report


def load_passport(path: Path) -> dict[str, Any]:
    """Load and semantically verify one bounded, regular Safe Delivery JSON file."""
    try:
        before = path.lstat()
    except OSError as exc:
        raise PassportError(f"unable to stat Safe Delivery passport: {exc}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise PassportError("Safe Delivery passport must be a regular non-symlink file")
    if before.st_size > MAX_PASSPORT_BYTES:
        raise PassportError("Safe Delivery passport exceeds the byte budget")
    try:
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise PassportError(f"unable to read Safe Delivery passport: {exc}") from exc
    if len(data) > MAX_PASSPORT_BYTES:
        raise PassportError("Safe Delivery passport exceeds the byte budget")
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    )
    if path.is_symlink() or before_identity != after_identity:
        raise PassportError("Safe Delivery passport changed while it was being read")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PassportError("Safe Delivery passport is not valid UTF-8 JSON") from exc
    report = _json_object(value, "Safe Delivery passport")
    verify_safe_delivery(report)
    return report


def _safe_output_parent(path: Path) -> Path:
    parent = path.parent if path.parent != Path("") else Path(".")
    try:
        parent = parent.resolve(strict=True)
    except OSError as exc:
        raise PassportError("passport output directory must already exist") from exc
    if not parent.is_dir():
        raise PassportError("passport output parent must be a directory")
    for item in (parent, *parent.parents):
        try:
            info = item.lstat()
        except OSError as exc:
            raise PassportError("passport output directory cannot be inspected") from exc
        if stat.S_ISLNK(info.st_mode):
            raise PassportError("passport output directory must not contain symlinks")
    return parent


def write_passport(path: Path, report: dict[str, Any], *, force: bool = False) -> Path:
    """Atomically write verified Safe Delivery JSON into an existing local directory."""
    verify_safe_delivery(report)
    target = Path(path)
    parent = _safe_output_parent(target)
    target = parent / target.name
    if target.is_symlink():
        raise PassportError("passport output must not be a symlink")
    if target.exists():
        if not force:
            raise PassportError("passport output already exists; pass --force to replace it")
        if not target.is_file():
            raise PassportError("passport output must be a regular file")
    descriptor, temporary = tempfile.mkstemp(prefix=".patchwitness-passport-", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, sort_keys=True, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if target.is_symlink():
            raise PassportError("passport output became a symlink during composition")
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchwitness-safe-delivery",
        description=(
            "Compose and independently verify exact-subject Safe Delivery passports."
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    commands = parser.add_subparsers(dest="command", required=True)
    tasktopr = commands.add_parser(
        "tasktopr",
        help="compose a PR-stage passport from a TaskToPR execution handoff",
    )
    tasktopr.add_argument("--handoff", required=True, type=Path)
    tasktopr.add_argument("--tasktopr-revision", required=True)
    tasktopr.add_argument("--base", required=True, dest="base_sha")
    tasktopr.add_argument("--head", default="HEAD")
    tasktopr.add_argument("--policy-ref", required=True)
    tasktopr.add_argument("--policy-path", default=".patchwitness.toml")
    tasktopr.add_argument("--output", required=True, type=Path)
    tasktopr.add_argument("--force", action="store_true")
    tasktopr.add_argument(
        "--require-plan-approval",
        action="store_true",
        help="require verified TaskToPR v2 prompt-mode human approve/edit provenance",
    )
    verify = commands.add_parser(
        "verify",
        help="verify a saved Safe Delivery passport offline without trusting its decision",
    )
    verify.add_argument("passport", type=Path)
    return parser


def _verification_result(report: dict[str, Any], passport: Path) -> dict[str, Any]:
    payload = verify_safe_delivery(report)
    return {
        "ok": True,
        "decision": payload["decision"],
        "stage": payload["stage"],
        "receipt_sha256": report["receipt_sha256"],
        "passport": str(passport),
        "head_sha": payload["provenance"]["subject"]["head_sha"],
        "components": {name: payload[name]["decision"] for name in COMPONENTS},
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Installed console entry point for cross-product Safe Delivery composition."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        try:
            result = _verification_result(load_passport(args.passport), args.passport)
        except (OSError, PassportError, ValueError) as exc:
            if args.json:
                print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
            else:
                print(f"patchwitness-safe-delivery: error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(f"Safe Delivery passport verified: {result['decision']} ({result['stage']})")
            print(f"  Head:    {result['head_sha']}")
            print(f"  Receipt: {result['receipt_sha256']}")
            print(f"  Input:   {result['passport']}")
            print("  Meaning: integrity/semantics verified; producer identity is not authenticated")
        return 0

    if args.command != "tasktopr":
        parser.error(f"unknown command: {args.command}")
    try:
        report = build_tasktopr_passport(
            Path.cwd(),
            handoff_path=args.handoff,
            tasktopr_revision=args.tasktopr_revision,
            base_sha=args.base_sha,
            head=args.head,
            policy_ref=args.policy_ref,
            policy_path=args.policy_path,
        )
        if args.require_plan_approval:
            require_tasktopr_plan_approval(report)
        output = write_passport(args.output, report, force=bool(args.force))
    except (OSError, PassportError, ValueError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        else:
            print(f"patchwitness-safe-delivery: error: {exc}", file=sys.stderr)
        return 2
    payload = report["payload"]
    result = {
        "ok": True,
        "decision": payload["decision"],
        "stage": payload["stage"],
        "receipt_sha256": report["receipt_sha256"],
        "output": str(output),
        "head_sha": payload["provenance"]["subject"]["head_sha"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"Safe Delivery passport: {result['decision']} ({result['stage']})")
        print(f"  Head:    {result['head_sha']}")
        print(f"  Receipt: {result['receipt_sha256']}")
        print(f"  Output:  {result['output']}")
        print("  Scope:   TaskToPR execution only; missing independent components stay unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
