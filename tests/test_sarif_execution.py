"""Successful SARIF analysis is not approval of a proposed change."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from patchwitness.cli import main
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence, write_evidence
from patchwitness.models import Contract
from patchwitness.reporters import render_sarif


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, timeout=30
    )


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "SARIF fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.hooksPath", str(tmp_path / "no-hooks"))
    (root / "src").mkdir()
    (root / "src/app.py").write_text("value = 1\n", encoding="utf-8")
    (root / ".gitignore").write_text(".patchwitness/\n", encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("scenario", "expected_status", "expected_rule"),
    [
        ("passing-check", "pass", None),
        ("protected-file", "fail", "PW003"),
        ("failed-check", "fail", "PW021"),
        ("timed-out-check", "fail", "PW021"),
        ("skipped-check", "fail", "PW020"),
        ("missing-check", "fail", "PW022"),
        ("optional-failure", "pass", None),
        ("source-drift", "fail", "PW032"),
    ],
)
def test_real_gate_and_report_keep_analysis_and_policy_outcomes_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scenario: str,
    expected_status: str,
    expected_rule: str | None,
) -> None:
    root = repository(tmp_path)
    script = tmp_path / "check.py"
    code = "print('ok')\n"
    if scenario in {"failed-check", "optional-failure"}:
        code = "raise SystemExit(7)\n"
    elif scenario == "timed-out-check":
        code = "import time\ntime.sleep(5)\n"
    elif scenario == "source-drift":
        code = "from pathlib import Path\nPath('src/app.py').write_text('moved\\n')\n"
    script.write_text(code, encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    protected = '["src/**"]' if scenario == "protected-file" else "[]"
    require_tests = "false" if scenario == "optional-failure" else "true"
    policy = (
        'version = 1\n[policy]\nallowed_paths = ["src/**"]\n'
        f"protected_paths = {protected}\nrequire_tests = {require_tests}\n"
    )
    if scenario != "missing-check":
        required = "false" if scenario == "optional-failure" else "true"
        timeout = 1 if scenario == "timed-out-check" else 10
        policy += (
            f'[[checks]]\nid = "fixture"\ncommand = {json.dumps(command)}\n'
            f"required = {required}\ntimeout_seconds = {timeout}\n"
        )
    (root / ".patchwitness.toml").write_text(policy, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "trusted synthetic base")
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    monkeypatch.chdir(root)
    evidence = root / ".patchwitness/evidence/result.json"
    args = ["gate", "--base", "HEAD", "--policy-ref", "HEAD", "--serial", "--output", str(evidence)]
    if scenario == "skipped-check":
        args.append("--no-checks")

    assert main(args) == (0 if expected_status == "pass" else 1)
    original = evidence.read_bytes()
    pack = verify_evidence(load_evidence(evidence))
    assert pack.status.value == expected_status
    if expected_rule:
        assert expected_rule in {finding["rule_id"] for finding in pack.findings}
    if scenario == "timed-out-check":
        assert pack.checks[0]["timed_out"] is True
    elif scenario in {"failed-check", "optional-failure"}:
        assert pack.checks[0]["exit_code"] == 7
        assert pack.checks[0]["passed"] is False
    elif scenario in {"skipped-check", "missing-check"}:
        assert pack.checks == ()

    capsys.readouterr()
    assert main(["report", str(evidence), "--format", "sarif"]) == 0
    output = capsys.readouterr()
    assert not output.err
    report = json.loads(output.out)
    run = report["runs"][0]
    invocation = run["invocations"][0]
    assert invocation["executionSuccessful"] is True
    assert invocation["properties"] == {
        "evidenceSha256": pack.payload_sha256,
        "evidencePath": str(evidence),
        "gateStatus": expected_status,
    }
    # Never invent a historical capture exit code: capture and gate differ.
    assert "exitCode" not in invocation
    assert [(r["ruleId"], r["level"]) for r in run["results"]] == [
        (f["rule_id"], "note" if f["severity"] == "info" else f["severity"])
        for f in pack.findings
    ]
    assert all(r["properties"]["evidenceSha256"] == pack.payload_sha256 for r in run["results"])
    written = root / ".patchwitness/report.sarif"
    assert main(["report", str(evidence), "--format", "sarif", "--output", str(written)]) == 0
    assert json.loads(written.read_text(encoding="utf-8")) == report
    assert main(["verify", str(evidence)]) == 0
    assert evidence.read_bytes() == original
    assert verify_evidence(load_evidence(evidence)).status.value == expected_status


@pytest.fixture
def recorded(tmp_path: Path) -> Path:
    root = repository(tmp_path)
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic base")
    (root / "src/app.py").write_text("value = 2\n", encoding="utf-8")
    pack = capture_evidence(root, Contract(require_tests=False), execute_checks=False)
    return write_evidence(pack, tmp_path / "evidence.json")


@pytest.mark.parametrize("kind", ["tampered", "invalid-json", "unknown", "review_required"])
@pytest.mark.parametrize("destination_exists", [False, True])
def test_rejected_evidence_never_emits_or_overwrites_a_successful_report(
    recorded: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    kind: str, destination_exists: bool,
) -> None:
    value = json.loads(recorded.read_text(encoding="utf-8"))
    if kind == "tampered":
        value["summary"]["status"] = "fail"
    elif kind in {"unknown", "review_required"}:
        value["summary"]["status"] = kind
        value.pop("payload_sha256")
        # Synthetic integrity-valid but unsupported native-v1 status, not approval.
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        value["payload_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    recorded.write_text("{" if kind == "invalid-json" else json.dumps(value), encoding="utf-8")
    output = tmp_path / "report.sarif"
    if destination_exists:
        output.write_bytes(b"existing report must survive")

    assert main(["report", str(recorded), "--format", "sarif", "--output", str(output)]) == 2
    captured = capsys.readouterr()
    assert captured.err and not captured.out
    if destination_exists:
        assert output.read_bytes() == b"existing report must survive"
    else:
        assert not output.exists()
    assert main(["report", str(recorded), "--format", "sarif"]) == 2
    captured = capsys.readouterr()
    assert captured.err and not captured.out


def test_report_output_failure_is_not_success(
    recorded: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parent = tmp_path / "not-a-directory"
    parent.write_text("sentinel", encoding="utf-8")
    assert main([
        "report", str(recorded), "--format", "sarif", "--output", str(parent / "report.sarif")
    ]) == 2
    output = capsys.readouterr()
    assert output.err and not output.out
    assert parent.read_text(encoding="utf-8") == "sentinel"


def test_renderer_retains_warning_results_without_mutating_evidence(recorded: Path) -> None:
    pack = verify_evidence(load_evidence(recorded))
    pack = replace(pack, findings=({
        "rule_id": "PW010", "severity": "warning", "message": "review change", "path": None,
    },))
    original = pack.to_dict()
    run = render_sarif(pack)["runs"][0]
    assert run["invocations"][0]["properties"]["gateStatus"] == "pass"
    assert run["invocations"][0]["executionSuccessful"] is True
    assert run["results"][0]["level"] == "warning"
    assert run["results"][0]["message"]["text"] == "review change"
    assert pack.to_dict() == original
