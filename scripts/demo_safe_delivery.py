"""Run reviewed deterministic fixtures through pinned Safe Delivery components.

This is a local integration demonstration, not a general repository executor.
Only the fixed source/test strings below are executed. No provider API, package
installation, remote fetch, push, PR creation or ambient plugin discovery occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from safe_delivery_sources import materialize_sources

TOOL_NAMES = (
    "tasktopr",
    "patchwitness",
    "code-api-surface",
    "code-import-map",
    "code-test-impact",
    "code-complexity-budget",
    "repo-privacy-guard",
    "artifact-fence",
    "rule-relay",
)
BEFORE = 'def greet(name):\n    return "Hello " + name + "!"\n'
AFTER = 'def greet(name, punctuation="!"):\n    return "Hello " + name + punctuation\n'
TEST = """import unittest
from api import greet

class ApiTests(unittest.TestCase):
    def test_existing_call(self):
        self.assertEqual(greet("Ada"), "Hello Ada!")
"""
NEW_TEST = (
    TEST
    + """
    def test_optional_argument(self):
        self.assertEqual(greet("Ada", "?"), "Hello Ada?")
"""
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    if not executable:
        raise RuntimeError("Git is required")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(
        [
            executable,
            "-c",
            "core.hooksPath=" + os.devnull,
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.autocrlf=false",
            "-C",
            str(root),
            *args,
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=20,
        env=env,
    )
    return result.stdout.strip()


def make_fixture(root: Path) -> str:
    root.mkdir()
    for name, text in {
        "api.py": BEFORE,
        "test_api.py": TEST,
        ".gitignore": ".tasktopr/\n__pycache__/\n",
        "AGENTS.md": "Only api.py and test_api.py may change. Preserve existing calls.\n",
        ".tasktopr-demo-issue.json": json.dumps(
            {
                "number": 1,
                "title": "Add optional greeting punctuation",
                "body": "Preserve existing greet(name) calls. Add a regression test.",
            }
        ),
    }.items():
        (root / name).write_text(text, encoding="utf-8", newline="\n")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Safe Delivery Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "add", "--", ".")
    git(root, "commit", "-m", "Initialize fixed safe fixture")
    return git(root, "rev-parse", "HEAD")


def candidate_identity(root: Path) -> dict:
    """Require a clean index/worktree and retain branch/index/config identity."""
    if git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise ValueError("Candidate is not clean; it cannot receive exact-HEAD evidence")
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "branch": git(root, "symbolic-ref", "--short", "HEAD"),
        "index_sha256": hashlib.sha256(git(root, "ls-files", "--stage", "-z").encode()).hexdigest(),
        "config_sha256": hashlib.sha256(
            git(root, "config", "--list", "--null", "--show-origin").encode()
        ).hexdigest(),
    }


def generated_task(root: Path, *, malicious: bool = False):
    from tasktopr.config import TaskToPRConfig, TestingConfig
    from tasktopr.orchestrator import fix_issue
    from tasktopr.providers import ModelProvider

    class FixedProvider(ModelProvider):
        """A deterministic stand-in at the untrusted model response boundary."""

        def complete(self, *, system, user, config):
            del user, config
            paths = [".github/workflows/publish.yml"] if malicious else ["api.py", "test_api.py"]
            if '"steps"' in system:
                return json.dumps(
                    {
                        "summary": "Add optional greeting punctuation",
                        "root_cause": "Fixed punctuation",
                        "steps": [
                            {
                                "path": path,
                                "action": "Apply requested change",
                                "rationale": "Fixture task",
                            }
                            for path in paths
                        ],
                        "test_plan": ["python -m unittest discover -v"],
                        "risk": "low",
                    }
                )
            if malicious:
                raise AssertionError("Protected plan must be rejected before patch generation")
            return json.dumps(
                {
                    "summary": "Add optional punctuation and regression",
                    "operations": [
                        {
                            "kind": "replace",
                            "path": "api.py",
                            "old_text": BEFORE,
                            "new_text": AFTER,
                            "reason": "Preserve old calls",
                        },
                        {
                            "kind": "replace",
                            "path": "test_api.py",
                            "old_text": TEST,
                            "new_text": NEW_TEST,
                            "reason": "Verify both call forms",
                        },
                    ],
                }
            )

    config = TaskToPRConfig(
        testing=TestingConfig(
            commands=[["python", "-m", "unittest", "discover", "-v"]], timeout_seconds=15
        )
    )
    result = fix_issue(
        1, start_dir=root, config=config, provider=FixedProvider(), demo=True, no_pr=True
    )
    receipt = json.loads((result.run_dir / "execution-receipt.json").read_text(encoding="utf-8"))
    return result, receipt


def node_reports(tool_roots: dict[str, Path], snapshot: Path, scratch: Path) -> dict:
    """Execute only trusted adapters/tool code with a bounded, sanitized child."""
    from tasktopr.bounded_process import run_bounded_command

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node 24 with stripTypeScriptTypes is required")
    runner = scratch / "node-adapters.mjs"
    runner.write_text(
        """import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {stripTypeScriptTypes} from 'node:module';
import {createHash} from 'node:crypto';
const [privacyRoot, ruleRoot, target, compiled] = process.argv.slice(2);
await fs.mkdir(compiled);
await fs.writeFile(path.join(compiled,'package.json'),'{"type":"module"}');
const transforms = {};
async function compile(relative='') {
  const entries=await fs.readdir(path.join(ruleRoot,'src',relative),{withFileTypes:true});
  for(const entry of entries.sort((a,b)=>a.name.localeCompare(b.name))) {
    const rel=path.join(relative,entry.name);
    if(entry.isDirectory()) {await fs.mkdir(path.join(compiled,rel));await compile(rel);}
    else if(entry.name.endsWith('.ts')) {
      const source=await fs.readFile(path.join(ruleRoot,'src',rel),'utf8');
      const code=stripTypeScriptTypes(source,{mode:'strip'});
      await fs.writeFile(path.join(compiled,rel.slice(0,-3)+'.js'),code);
      transforms[rel.replaceAll('\\\\','/')]=createHash('sha256').update(code).digest('hex');
    }
  }
}
await compile();
const {scanPath}=await import(pathToFileURL(path.join(privacyRoot,'src/scanner.mjs')));
const ruleEntry=pathToFileURL(path.join(compiled,'core/scan.js'));
const {scanRepository,explainTarget}=await import(ruleEntry);
const privacy=await scanPath(target,{strictGate:true});
const rules=await scanRepository(target);
console.log(JSON.stringify({privacy:{gate:privacy.gate??null,scannedFiles:privacy.scannedFiles,
 skipped:privacy.skipped,truncated:privacy.truncated,blockingFindings:privacy.blockingFindings,
 findings:privacy.findings.map(f=>({ruleId:f.ruleId,severity:f.severity}))},
 rules:{files:rules.files.map(f=>({
 path:f.relativePath,contentHash:f.contentHash,adapter:f.adapter})),
 findings:rules.findings.map(f=>({code:f.code,severity:f.severity})),
 applicability:explainTarget(rules,'api.py')},
 runtime:process.version,transformation:'node.stripTypeScriptTypes:strip',transforms}));
""",
        encoding="utf-8",
    )
    result = run_bounded_command(
        [
            node,
            str(runner),
            str(tool_roots["repo-privacy-guard"]),
            str(tool_roots["rule-relay"]),
            str(snapshot),
            str(scratch / "compiled-rule-relay"),
        ],
        scratch,
        30,
        output_limit_bytes=512_000,
        capture_limit_bytes=512_000,
    )
    if result.return_code != 0 or not result.cleanup_complete:
        raise RuntimeError("Pinned Node adapter failed: " + result.stderr[-1000:])
    return json.loads(result.stdout)


def analyze_fixture(
    root: Path,
    base: str,
    pins: dict,
    tool_roots: dict[str, Path],
    scratch: Path,
    local_receipt: dict,
    *,
    unsafe: bool = False,
) -> dict:
    from artifact_fence.gate import fail_closed_findings
    from artifact_fence.scanner import has_severity, scan_project
    from code_api_surface.core import compare
    from code_complexity_budget.delta import SourceSnapshot, compare_snapshots
    from code_import_map.core import analyze
    from code_test_impact.core import GraphProvenance, graph_digest, plan_tests
    from tasktopr.receipt import snapshot
    from tasktopr.security import run_safe_command

    from patchwitness.git import collect_changes
    from patchwitness.models import CheckResult, CheckSpec, Contract, Severity
    from patchwitness.policy import evaluate_policy
    from patchwitness.safe_delivery import (
        ChangeSubject,
        ComponentEvidence,
        compose_safe_delivery,
        content_digest,
        safe_delivery_sarif,
        safe_delivery_summary,
    )
    from patchwitness.safe_delivery import (
        DeliveryDecision as D,
    )

    head = git(root, "rev-parse", "HEAD")
    source_before = {
        name: git(root, "show", base + ":" + name) + "\n" for name in ("api.py", "test_api.py")
    }
    files = {name: (root / name).read_text(encoding="utf-8") for name in source_before}
    changes = collect_changes(root, base)
    manifest = [change.to_dict() for change in changes]
    snapshot_before = snapshot(root)
    identity_before = candidate_identity(root)
    command = ["python", "-m", "unittest", "discover", "-v"]
    execution = run_safe_command(command, root, 15)
    exact = (
        snapshot(root) == snapshot_before
        and candidate_identity(root) == identity_before
        and identity_before["head"] == head
    )
    execution_ok = exact and execution.return_code == 0 and not execution.blocked
    execution_details = {
        "result": execution.model_dump(mode="json"),
        "tested_head_sha": head,
        "source_manifest_sha256": content_digest(snapshot_before),
        "identity_unchanged": exact,
        "candidate_identity_sha256": content_digest(identity_before),
        "tasktopr_local_receipt_sha256": local_receipt["receipt_sha256"],
        "phase": "separate_post_commit_full_suite_verification",
    }
    api = compare(source_before["api.py"], files["api.py"])
    api_codes = tuple(sorted({finding.code for finding in api.findings}))
    api_decision = (
        D.FAIL
        if {"api.removed", "api.breaking_change"} & set(api_codes)
        else (D.REVIEW_REQUIRED if api.requires_review else D.PASS)
    )
    imports = analyze(
        files,
        source_roots={"": ""},
        external_modules={"unittest"},
        known_members={"api": {"greet"}},
        capture_revision=head,
    )
    deps = {key: set(value) for key, value in imports.file_dependencies.items()}
    provenance = GraphProvenance(
        schema_version=1,
        source_revision=head,
        capture_method="static",
        completeness="unknown",
        graph_digest=graph_digest(deps),
        tool_name="code-import-map",
        tool_revision=pins["code-import-map"]["revision"],
    )
    impact = plan_tests(
        deps,
        {change.path for change in changes},
        {"test_api.py"},
        provenance=provenance,
        candidate_revision=head,
    )
    if not impact.run_full_suite or impact.selected_tests != ("test_api.py",):
        raise AssertionError("Unknown runtime evidence must select the full fixed suite")
    complexity = compare_snapshots(
        SourceSnapshot(base, source_before, True),
        SourceSnapshot(head, files, True),
        component_revision=pins["code-complexity-budget"]["revision"],
    )
    # Scan an exact tracked-content snapshot; journals, caches and Git metadata
    # are neither publication candidates nor silently part of the scan scope.
    source_snapshot = scratch / "candidate-source"
    source_snapshot.mkdir()
    for relative in git(root, "ls-files").splitlines():
        destination = source_snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((root / relative).read_bytes())
    node = node_reports(tool_roots, source_snapshot, scratch)
    privacy = node["privacy"]
    gate = privacy.get("gate") or {}
    privacy_decision = {"PASS": D.PASS, "FAIL": D.FAIL, "UNKNOWN": D.UNKNOWN}.get(
        str(gate.get("decision", "")).upper(), D.UNKNOWN
    )
    artifact = scan_project(source_snapshot)
    artifact.findings.extend(fail_closed_findings(source_snapshot, artifact))
    artifact_decision = D.FAIL if has_severity(artifact) else D.REVIEW_REQUIRED
    contract = Contract(
        id="fixed-api-demo-v1",
        allowed_paths=("api.py", "test_api.py"),
        checks=(CheckSpec("full-suite", "python -m unittest discover -v", timeout_seconds=15),),
    )
    check = CheckResult(
        "full-suite",
        "python -m unittest discover -v",
        True,
        execution.return_code,
        int(execution.elapsed_seconds * 1000),
        execution.timed_out,
        content_digest(execution_details),
        "",
    )
    policy_findings = evaluate_policy(contract, changes, (check,))
    policy_bad = any(finding.severity == Severity.ERROR for finding in policy_findings)
    policy = {
        "contract": contract.to_dict(),
        "instruction_discovery": node["rules"],
        "scope": "reviewer-owned fixed fixture policy; prose is not authorization",
        "artifact_scope": "workflow upload declarations only; publication manifest unavailable",
    }
    policy_sha = content_digest(policy)
    subject = ChangeSubject(
        content_digest(str(root.resolve())), base, head, content_digest(manifest), policy_sha
    )
    producers = {
        "api": "code-api-surface",
        "dependencies": "code-import-map",
        "tests": "code-test-impact",
        "complexity": "code-complexity-budget",
        "privacy": "repo-privacy-guard",
        "artifacts": "artifact-fence",
        "policy": "rule-relay",
        "execution": "tasktopr",
        "ci": "patchwitness",
        "review": "patchwitness",
    }
    trusted = {component: (name, pins[name]["revision"]) for component, name in producers.items()}
    records = []

    def add(component, decision, complete, details, codes=(), metrics=None):
        tool, revision = trusted[component]
        records.append(
            ComponentEvidence(
                component,
                tool,
                revision,
                subject,
                decision,
                complete,
                content_digest(details),
                tuple(codes),
                metrics or {},
            )
        )

    add("api", api_decision, api.evidence_complete, asdict(api), api_codes)
    add(
        "dependencies",
        D.REVIEW_REQUIRED,
        False,
        asdict(imports),
        tuple(sorted({finding.code for finding in imports.findings})),
        {"edges": len(imports.edges)},
    )
    add(
        "tests",
        D.PASS if execution_ok else D.FAIL,
        execution_ok,
        {"impact": asdict(impact), "execution": execution_details},
        ("impact.full_suite_fallback",),
        {"selected_test_files": len(impact.selected_tests)},
    )
    add(
        "complexity",
        {"pass": D.PASS, "fail": D.FAIL}.get(complexity.decision, D.UNKNOWN),
        complexity.complete,
        asdict(complexity),
    )
    add(
        "privacy",
        privacy_decision,
        privacy_decision == D.PASS,
        privacy,
        tuple(
            sorted({finding["ruleId"] for finding in privacy["findings"] if finding.get("ruleId")})
        ),
    )
    add(
        "artifacts",
        artifact_decision,
        False,
        artifact.to_dict(),
        tuple(sorted({finding.rule_id for finding in artifact.findings})),
    )
    add(
        "policy",
        D.FAIL if policy_bad else D.REVIEW_REQUIRED,
        False,
        {"policy": policy, "findings": [finding.to_dict() for finding in policy_findings]},
        tuple(sorted({finding.rule_id for finding in policy_findings})),
    )
    add(
        "execution",
        D.PASS if execution_ok else D.FAIL,
        execution_ok,
        execution_details,
        (),
        {"commands": 1, "output_bytes": execution.output_bytes},
    )
    report = compose_safe_delivery(
        subject, records, trusted_tools=trusted, policy_sha256=policy_sha, stage="pr"
    )
    expected = "FAIL" if unsafe else "REVIEW_REQUIRED"
    write_json(scratch / "safe-change.json", report)
    write_json(scratch / "safe-change.sarif", safe_delivery_sarif(report))
    (scratch / "summary.md").write_text(safe_delivery_summary(report), encoding="utf-8")
    # Details are only from our fixed synthetic fixture. Public receipts above
    # carry digests and bounded IDs, never raw command output or instructions.
    details = {
        "fixture_only": True,
        "manifest": manifest,
        "api": asdict(api),
        "dependencies": asdict(imports),
        "impact": asdict(impact),
        "complexity": asdict(complexity),
        "privacy": privacy,
        "artifacts": artifact.to_dict(),
        "policy": policy,
        "execution": execution_details,
        "node_runtime": node["runtime"],
        "rule_relay_transformation": node["transformation"],
        "rule_relay_transformed_sha256": content_digest(node["transforms"]),
    }
    write_json(scratch / "fixture-details.json", details)
    if report["payload"]["decision"] != expected:
        raise AssertionError(f"Expected {expected}, got {report['payload']['decision']}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pins", type=Path, required=True, help="Reviewer-controlled local tool pins JSON"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New output directory, must not exist"
    )
    args = parser.parse_args()
    pins = json.loads(args.pins.read_text(encoding="utf-8-sig"))
    if set(pins) != set(TOOL_NAMES):
        raise ValueError("All nine exact tool pins are required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="safe-delivery-tools-") as temporary:
        sources = materialize_sources(pins, Path(temporary).resolve())
        roots = {name: source.root for name, source in sources.items()}
        # Permit only Python's universal-newline equivalence for Windows Git
        # checkouts. All imported producer modules use the original Git bytes.
        for filename in ("demo_safe_delivery.py", "safe_delivery_sources.py"):
            if (Path(__file__).parent / filename).read_text(encoding="utf-8") != (
                roots["patchwitness"] / "scripts" / filename
            ).read_text(encoding="utf-8"):
                raise ValueError("Entry point differs from the pinned PatchWitness source")
        for root in roots.values():
            sys.path.insert(0, str(root / "src"))
        safe = output / "benign"
        safe.mkdir()
        fixture = safe / "fixture"
        base = make_fixture(fixture)
        result, receipt = generated_task(fixture)
        if not result.success:
            raise RuntimeError("Benign TaskToPR fixture failed: " + result.message)
        write_json(safe / "tasktopr-local-receipt.json", receipt)
        git(fixture, "add", "--", "api.py", "test_api.py")
        git(fixture, "commit", "-m", "Fixture optional API extension")
        benign_report = analyze_fixture(fixture, base, pins, roots, safe, receipt)

        unsafe = output / "unsafe"
        unsafe.mkdir()
        bad_fixture = unsafe / "fixture"
        bad_base = make_fixture(bad_fixture)
        bad, bad_receipt = generated_task(bad_fixture, malicious=True)
        if bad.success or (bad_fixture / ".github").exists():
            raise AssertionError("TaskToPR failed to reject protected workflow plan")
        write_json(unsafe / "tasktopr-blocked-receipt.json", bad_receipt)
        # Independently construct a known unsafe candidate to exercise downstream
        # gates even though TaskToPR already refused the model's workflow plan.
        workflow = bad_fixture / ".github" / "workflows" / "publish.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text(
            "name: unsafe fixture\non: push\njobs:\n  upload:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/upload-artifact@v4\n        with:\n"
            "          path: .\n          include-hidden-files: true\n",
            encoding="utf-8",
        )
        (bad_fixture / "api.py").write_text(
            "def greet(name, required):\n    return name\n", encoding="utf-8"
        )
        # Public, deliberately invalid test credential, never a real secret.
        (bad_fixture / "leak.txt").write_text(
            "credential_fixture = ghp_" + "A" * 36 + "\n", encoding="utf-8"
        )
        git(bad_fixture, "add", "--", "api.py", "leak.txt", ".github/workflows/publish.yml")
        git(bad_fixture, "commit", "-m", "Known unsafe downstream fixture")
        bad_report = analyze_fixture(
            bad_fixture, bad_base, pins, roots, unsafe, bad_receipt, unsafe=True
        )
        write_json(
            output / "demo-result.json",
            {
                "schema_version": 1,
                "scope": "fixed local fixtures; no hosted PR or CI is fabricated",
                "tool_pins": {name: data["revision"] for name, data in pins.items()},
                "source_provenance": {name: source.provenance for name, source in sources.items()},
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "benign": {
                    "decision": benign_report["payload"]["decision"],
                    "receipt_sha256": benign_report["receipt_sha256"],
                },
                "unsafe": {
                    "tasktopr_blocked": not bad.success,
                    "decision": bad_report["payload"]["decision"],
                    "receipt_sha256": bad_report["receipt_sha256"],
                },
            },
        )
    print(json.dumps({"benign": "REVIEW_REQUIRED", "unsafe": "FAIL", "output": str(output)}))


if __name__ == "__main__":
    main()
