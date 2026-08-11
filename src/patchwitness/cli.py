"""PatchWitness command-line interface."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from patchwitness import __version__
from patchwitness.config import ConfigError, initialize_project, load_contract
from patchwitness.evidence import (
    EvidenceError,
    capture_evidence,
    load_evidence,
    verify_evidence,
    write_evidence,
)
from patchwitness.git import GitError, find_root
from patchwitness.models import EvidencePack, GateStatus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchwitness",
        description="Independent evidence and policy gates for AI-generated code changes.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a safe starter contract")
    init_parser.add_argument("--force", action="store_true", help="replace an existing contract")

    for name, help_text in (
        ("capture", "capture a Change Passport without enforcing its result"),
        ("gate", "capture evidence and fail closed when policy or checks fail"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--base", default="HEAD", help="trusted base revision (default: HEAD)")
        command.add_argument(
            "--contract", default=".patchwitness.toml", help="path to the TOML contract"
        )
        command.add_argument("--output", help="evidence JSON path")
        command.add_argument("--no-checks", action="store_true", help="do not execute checks")
        command.add_argument("--serial", action="store_true", help="run checks sequentially")
        command.add_argument("--max-workers", type=int, default=4)

    verify_parser = subparsers.add_parser("verify", help="verify evidence integrity offline")
    verify_parser.add_argument("evidence", type=Path)

    inspect_parser = subparsers.add_parser(
        "inspect", help="render a human-readable evidence summary"
    )
    inspect_parser.add_argument("evidence", type=Path)
    inspect_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")

    subparsers.add_parser("doctor", help="check local prerequisites and repository state")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return _init(args)
        if args.command in {"capture", "gate"}:
            return _capture(args, enforce=args.command == "gate")
        if args.command == "verify":
            return _verify(args)
        if args.command == "inspect":
            return _inspect(args)
        if args.command == "doctor":
            return _doctor(args)
    except (ConfigError, EvidenceError, GitError, OSError) as exc:
        return _error(str(exc), json_output=bool(args.json))
    parser.error(f"unknown command: {args.command}")
    return 2


def _init(args: argparse.Namespace) -> int:
    root = find_root()
    target = initialize_project(root, force=bool(args.force))
    return _emit(
        {"ok": True, "contract": str(target), "message": "PatchWitness initialized"},
        json_output=bool(args.json),
    )


def _capture(args: argparse.Namespace, *, enforce: bool) -> int:
    root = find_root()
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = root / contract_path
    contract = load_contract(contract_path)
    pack = capture_evidence(
        root,
        contract,
        base=args.base,
        execute_checks=not args.no_checks,
        parallel_checks=not args.serial,
        max_workers=max(1, args.max_workers),
    )
    output = Path(args.output) if args.output else _default_output(root)
    if not output.is_absolute():
        output = root / output
    write_evidence(pack, output)
    _print_pack(pack, output=output, json_output=bool(args.json))
    if enforce and pack.status == GateStatus.FAIL:
        return 1
    return 0


def _verify(args: argparse.Namespace) -> int:
    pack = verify_evidence(load_evidence(args.evidence))
    return _emit(
        {
            "ok": True,
            "status": pack.status.value,
            "payload_sha256": pack.payload_sha256,
            "message": "evidence integrity verified",
        },
        json_output=bool(args.json),
    )


def _inspect(args: argparse.Namespace) -> int:
    pack = verify_evidence(load_evidence(args.evidence))
    if args.format == "json":
        print(json.dumps(pack.to_dict(), indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(_render_markdown(pack))
    else:
        _print_pack(pack, output=args.evidence, json_output=False)
    return 0


def _doctor(args: argparse.Namespace) -> int:
    diagnostics: dict[str, object] = {
        "python": sys.version.split()[0],
        "git": shutil.which("git"),
        "repository": None,
        "contract": False,
    }
    ok = diagnostics["git"] is not None
    try:
        root = find_root()
        diagnostics["repository"] = str(root)
        diagnostics["contract"] = (root / ".patchwitness.toml").exists()
    except GitError:
        ok = False
    diagnostics["ok"] = ok
    _emit(diagnostics, json_output=bool(args.json))
    return 0 if ok else 1


def _default_output(root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return root / ".patchwitness" / "evidence" / f"{stamp}.json"


def _print_pack(pack: EvidencePack, *, output: Path, json_output: bool) -> None:
    if json_output:
        print(
            json.dumps(
                {"ok": True, "evidence": str(output), **pack.summary},
                sort_keys=True,
            )
        )
        return
    marker = "PASS" if pack.status == GateStatus.PASS else "FAIL"
    print(f"PatchWitness {marker}")
    print(
        f"  {pack.summary['files_changed']} files · {pack.summary['lines_changed']} lines · "
        f"{pack.summary['checks_passed']}/{pack.summary['checks_total']} checks"
    )
    for finding in pack.findings:
        location = f" [{finding['path']}]" if finding.get("path") else ""
        print(
            f"  {str(finding['severity']).upper()} {finding['rule_id']}"
            f"{location}: {finding['message']}"
        )
    print(f"  Evidence: {output}")
    print(f"  SHA-256:  {pack.payload_sha256}")


def _render_markdown(pack: EvidencePack) -> str:
    lines = [
        "## PatchWitness Change Passport",
        "",
        f"**Status:** `{pack.status.value.upper()}`  ",
        f"**Evidence:** `{pack.payload_sha256}`  ",
        f"**Base:** `{pack.repository['base_revision']}`",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Files changed | {pack.summary['files_changed']} |",
        f"| Lines changed | {pack.summary['lines_changed']} |",
        f"| Checks | {pack.summary['checks_passed']}/{pack.summary['checks_total']} |",
        f"| Errors | {pack.summary['errors']} |",
        "",
    ]
    if pack.findings:
        lines.extend(["### Findings", ""])
        for finding in pack.findings:
            path = f" (`{finding['path']}`)" if finding.get("path") else ""
            lines.append(
                f"- **{finding['rule_id']}** {finding['message']}{path}"
            )
    else:
        lines.append("No policy violations were found.")
    return "\n".join(lines)


def _emit(value: dict[str, object], *, json_output: bool) -> int:
    if json_output:
        print(json.dumps(value, sort_keys=True))
    else:
        print(str(value.get("message", "PatchWitness diagnostics")))
        for key, item in value.items():
            if key not in {"message"}:
                print(f"  {key}: {item}")
    return 0


def _error(message: str, *, json_output: bool) -> int:
    if json_output:
        print(json.dumps({"ok": False, "error": message}, sort_keys=True))
    else:
        print(f"patchwitness: error: {message}", file=sys.stderr)
    return 2
