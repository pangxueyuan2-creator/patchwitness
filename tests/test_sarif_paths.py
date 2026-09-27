"""SARIF artifact URIs must retain the identity of repository filenames."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from patchwitness.cli import main
from patchwitness.models import EvidencePack
from patchwitness.reporters import render_sarif, write_report


def synthetic_pack(path: str | None) -> EvidencePack:
    # Renderer unit fixture; the separate CLI test uses real verified evidence.
    return EvidencePack(
        schema_version="1.0",
        tool={"version": "test"},
        repository={},
        contract={},
        changes=(),
        checks=(),
        findings=(
            {"rule_id": "PW002", "severity": "error", "message": "outside scope",
             "path": path, "line": 3},
        ),
        summary={"status": "fail"},
        captured_at="2026-01-01T00:00:00Z",
        payload_sha256="0" * 64,
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/app.py", "src/app.py"),
        ("src/space name.py", "src/space%20name.py"),
        ("src/hash#part.py", "src/hash%23part.py"),
        ("src/query?part.py", "src/query%3Fpart.py"),
        ("src/literal%2Fname.py", "src/literal%252Fname.py"),
        ("scheme:file.py", "scheme%3Afile.py"),
        ("src/测.py", "src/%E6%B5%8B.py"),
        ("src/tab\tline\nname.py", "src/tab%09line%0Aname.py"),
        (r"src\space #1.py", "src/space%20%231.py"),
    ],
)
def test_artifact_uri_roundtrips_without_reinterpreting_filename(
    path: str, expected: str,
) -> None:
    pack = synthetic_pack(path)
    original = pack.to_dict()
    run = render_sarif(pack)["runs"][0]
    result = run["results"][0]
    location = result["locations"][0]["physicalLocation"]
    uri = location["artifactLocation"]["uri"]
    parsed = urlsplit(uri)
    assert uri == expected
    assert not any((parsed.scheme, parsed.netloc, parsed.query, parsed.fragment))
    assert unquote(parsed.path) == path.replace("\\", "/")
    assert uri.isascii()
    assert location["region"] == {"startLine": 3}
    assert result["ruleId"] == "PW002" and result["level"] == "error"
    assert result["properties"]["evidenceSha256"] == pack.payload_sha256
    assert pack.to_dict() == original
    # Successful analysis/reporting does not approve this failing gate result.
    assert run["invocations"][0]["executionSuccessful"] is True
    assert run["invocations"][0]["properties"]["gateStatus"] == "fail"


def test_no_location_and_written_report_keep_existing_semantics(tmp_path: Path) -> None:
    pack = synthetic_pack(None)
    assert "locations" not in render_sarif(pack)["runs"][0]["results"][0]
    pack = synthetic_pack("src/literal%23name.py")
    output = tmp_path / "report.sarif"
    write_report(pack, output, report_format="sarif", evidence_path="evidence.json")
    assert json.loads(output.read_text()) == render_sarif(pack, evidence_path="evidence.json")


def test_real_git_cli_report_preserves_unicode_hash_and_percent_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-c", f"core.hooksPath={tmp_path / 'no-hooks'}", *args],
            cwd=tmp_path, check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Synthetic reviewer")
    git("config", "user.email", "review@example.invalid")
    git("config", "commit.gpgsign", "false")
    (tmp_path / "src").mkdir()
    path = "src/测 #100%25.py"
    target = tmp_path / path
    target.write_text("before\n", encoding="utf-8")
    (tmp_path / ".patchwitness.toml").write_text(
        'version=1\n[policy]\nrequire_tests=false\nprotected_paths=["src/**"]\n',
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text(".patchwitness/evidence/\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "trusted synthetic base")
    target.write_text("after\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    output = tmp_path / ".patchwitness/evidence/result.json"
    assert main([
        "gate", "--base", "HEAD", "--policy-ref", "HEAD", "--no-checks", "--output",
        str(output),
    ]) == 1
    original = output.read_bytes()
    assert main(["verify", str(output)]) == 0
    report = tmp_path / "result.sarif"
    assert main(["report", str(output), "--format", "sarif", "--output", str(report)]) == 0
    results = json.loads(report.read_text(encoding="utf-8"))["runs"][0]["results"]
    assert len(results) == 1 and results[0]["ruleId"] == "PW003"
    uri = results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert uri == "src/%E6%B5%8B%20%23100%2525.py"
    assert unquote(urlsplit(uri).path) == path
    assert output.read_bytes() == original
    assert json.loads(original)["summary"]["status"] == "fail"
