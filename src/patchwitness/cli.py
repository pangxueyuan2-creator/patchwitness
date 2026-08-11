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
from patchwitness.benchmark import run_benchmark, write_benchmark
from patchwitness.cleanroom import CleanRoomError
from patchwitness.config import (
    ConfigError,
    create_task_contract,
    initialize_project,
    load_contract,
    load_contract_bytes,
)
from patchwitness.evidence import (
    EvidenceError,
    capture_evidence,
    load_evidence,
    verify_evidence,
    write_evidence,
)
from patchwitness.git import (
    GitError,
    collect_changes,
    find_root,
    load_file_at_revision,
    resolve_revision,
)
from patchwitness.impact import analyze_impact
from patchwitness.mcp import MCPServer
from patchwitness.models import EvidencePack, GateStatus
from patchwitness.reporters import (
    explain_rule,
    render_github_annotations,
    render_markdown,
    render_sarif,
    write_report,
)


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
        command.add_argument(
            "--policy-ref",
            help="load the contract from this trusted Git revision instead of the working tree",
        )
        command.add_argument("--output", help="evidence JSON path")
        command.add_argument("--no-checks", action="store_true", help="do not execute checks")
        command.add_argument("--serial", action="store_true", help="run checks sequentially")
        command.add_argument("--max-workers", type=int, default=4)
        command.add_argument(
            "--clean-room",
            action="store_true",
            help="run checks in a disposable base-derived Git worktree",
        )

    verify_parser = subparsers.add_parser("verify", help="verify evidence integrity offline")
    verify_parser.add_argument("evidence", type=Path)

    inspect_parser = subparsers.add_parser(
        "inspect", help="render a human-readable evidence summary"
    )
    inspect_parser.add_argument("evidence", type=Path)
    inspect_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")

    subparsers.add_parser("doctor", help="check local prerequisites and repository state")

    impact_parser = subparsers.add_parser(
        "impact", help="compute deterministic change blast radius"
    )
    impact_parser.add_argument("--base", default="HEAD")
    impact_parser.add_argument("--no-cache", action="store_true")

    mcp_parser = subparsers.add_parser("mcp", help="serve PatchWitness tools over stdio MCP")
    mcp_parser.add_argument("--root", default=".")

    contract_parser = subparsers.add_parser("contract", help="create task-scoped trust contracts")
    contract_commands = contract_parser.add_subparsers(dest="contract_command", required=True)
    contract_new = contract_commands.add_parser("new", help="create a task contract")
    contract_new.add_argument("id")
    contract_new.add_argument("--goal", required=True)
    contract_new.add_argument("--allow", action="append", required=True, dest="allowed")
    contract_new.add_argument("--deny", action="append", default=[], dest="denied")
    contract_new.add_argument("--protect", action="append", default=[], dest="protected")
    contract_new.add_argument(
        "--check", action="append", default=[], help="required check as ID=COMMAND"
    )
    contract_new.add_argument("--max-files", type=int, default=25)
    contract_new.add_argument("--max-lines", type=int, default=1_000)
    contract_new.add_argument("--force", action="store_true")

    report_parser = subparsers.add_parser(
        "report", help="render verified evidence for humans or CI"
    )
    report_parser.add_argument("evidence", type=Path)
    report_parser.add_argument(
        "--format", choices=("markdown", "sarif", "json", "github"), default="markdown"
    )
    report_parser.add_argument("--output", type=Path)

    explain_parser = subparsers.add_parser("explain", help="explain a policy rule")
    explain_parser.add_argument("rule_id")

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="run a real local performance benchmark"
    )
    benchmark_parser.add_argument("--files", type=int, default=250)
    benchmark_parser.add_argument("--rounds", type=int, default=5)
    benchmark_parser.add_argument("--output", type=Path)
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
        if args.command == "impact":
            return _impact(args)
        if args.command == "mcp":
            return MCPServer(Path(args.root)).serve()
        if args.command == "contract":
            return _contract(args)
        if args.command == "report":
            return _report(args)
        if args.command == "explain":
            return _explain(args)
        if args.command == "benchmark":
            return _benchmark(args)
    except (CleanRoomError, ConfigError, EvidenceError, GitError, OSError, ValueError) as exc:
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
    if args.policy_ref:
        if contract_path.is_absolute():
            raise ConfigError("--contract must be repository-relative with --policy-ref")
        policy_revision = resolve_revision(root, args.policy_ref)
        relative = contract_path.as_posix()
        contract = load_contract_bytes(
            load_file_at_revision(root, policy_revision, relative),
            source=f"git:{policy_revision}:{relative}",
        )
        contract_source = f"git:{policy_revision}:{relative}"
    else:
        if not contract_path.is_absolute():
            contract_path = root / contract_path
        contract = load_contract(contract_path)
        contract_source = "working-tree"
    pack = capture_evidence(
        root,
        contract,
        base=args.base,
        execute_checks=not args.no_checks,
        parallel_checks=not args.serial,
        max_workers=max(1, args.max_workers),
        contract_source=contract_source,
        clean_room_checks=bool(args.clean_room),
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


def _impact(args: argparse.Namespace) -> int:
    root = find_root()
    base = resolve_revision(root, args.base)
    result = analyze_impact(
        root,
        collect_changes(root, base),
        use_cache=not args.no_cache,
    )
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"PatchWitness impact: {result['risk_level'].upper()} ({result['risk_score']}/100)")
        print(
            f"  {len(result['direct_dependents'])} direct | "
            f"{len(result['transitive_dependents'])} transitive | "
            f"{len(result['affected_tests'])} tests"
        )
        print(f"  Indexed: {result['files_indexed']} files / {result['edges_indexed']} edges")
    return 0


def _contract(args: argparse.Namespace) -> int:
    if args.contract_command != "new":
        raise ConfigError(f"unknown contract command: {args.contract_command}")
    checks: list[tuple[str, str]] = []
    for value in args.check:
        if "=" not in value:
            raise ConfigError("--check must use ID=COMMAND")
        check_id, command = value.split("=", 1)
        if not check_id.strip() or not command.strip():
            raise ConfigError("--check must use non-empty ID=COMMAND")
        checks.append((check_id.strip(), command.strip()))
    target = create_task_contract(
        find_root(),
        args.id,
        goal=args.goal,
        allowed_paths=args.allowed,
        denied_paths=args.denied,
        protected_paths=args.protected,
        checks=checks,
        max_files=args.max_files,
        max_lines=args.max_lines,
        force=args.force,
    )
    return _emit(
        {"ok": True, "contract": str(target), "message": "Task contract created"},
        json_output=bool(args.json),
    )


def _report(args: argparse.Namespace) -> int:
    pack = verify_evidence(load_evidence(args.evidence))
    if args.output:
        write_report(
            pack,
            args.output,
            report_format=args.format,
            evidence_path=str(args.evidence),
        )
        return _emit(
            {"ok": True, "report": str(args.output), "message": "Report written"},
            json_output=bool(args.json),
        )
    if args.format == "markdown":
        print(render_markdown(pack), end="")
    elif args.format == "sarif":
        print(json.dumps(render_sarif(pack, evidence_path=str(args.evidence)), indent=2))
    elif args.format == "json":
        print(json.dumps(pack.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_github_annotations(pack), end="")
    return 0


def _explain(args: argparse.Namespace) -> int:
    title, description = explain_rule(args.rule_id)
    return _emit(
        {
            "ok": True,
            "rule_id": args.rule_id.upper(),
            "title": title,
            "description": description,
            "message": f"{args.rule_id.upper()}: {title}",
        },
        json_output=bool(args.json),
    )


def _benchmark(args: argparse.Namespace) -> int:
    result = run_benchmark(files=args.files, rounds=args.rounds)
    if args.output:
        write_benchmark(result, args.output)
        print(f"Benchmark written: {args.output}")
    elif args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        parameters = result["parameters"]
        values = result["results_ms"]
        print(
            f"PatchWitness benchmark: {parameters['repository_files']} files | "
            f"{parameters['changed_files']} changed | {parameters['rounds']} rounds"
        )
        for name, summary in values.items():
            print(f"  {name}: median {summary['median']} ms | p95 {summary['p95']} ms")
    return 0


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
        f"  {pack.summary['files_changed']} files | {pack.summary['lines_changed']} lines | "
        f"{pack.summary['checks_passed']}/{pack.summary['checks_total']} checks"
    )
    impact = dict(pack.extensions.get("impact", {}))
    if impact:
        print(
            f"  Risk: {str(impact.get('risk_level', 'unknown')).upper()} "
            f"({impact.get('risk_score', 'n/a')}/100) | "
            f"{len(impact.get('direct_dependents', []))} direct dependents"
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
    return render_markdown(pack)


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
