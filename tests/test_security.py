from pathlib import Path

from patchwitness.models import FileChange
from patchwitness.security import MAX_SCAN_BYTES, scan_changed_files


def test_secret_finding_never_contains_the_value(tmp_path: Path) -> None:
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
    (tmp_path / "config.py").write_text(f"TOKEN = '{secret}'\n", encoding="utf-8")
    change = FileChange("config.py", "A", 1, 0, False, None, "after")
    findings = scan_changed_files(tmp_path, [change])
    assert len(findings) == 1
    assert findings[0].rule_id == "PW030"
    assert findings[0].line == 1
    assert secret not in findings[0].message


def test_oversized_file_is_skipped_with_pw031_info_finding(tmp_path: Path) -> None:
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz0123456789"
    (tmp_path / "big.log").write_bytes(
        f"token = '{secret}'".encode() + b"\n" + b"a" * MAX_SCAN_BYTES
    )
    change = FileChange("big.log", "A", 1, 0, False, None, "after")
    findings = scan_changed_files(tmp_path, [change])
    assert [finding.rule_id for finding in findings] == ["PW031"]
    assert findings[0].severity.value == "info"
    assert findings[0].path == "big.log"
    assert findings[0].line is None
    assert str(MAX_SCAN_BYTES) in findings[0].message
    assert secret not in findings[0].message


def test_file_exactly_at_scan_limit_is_still_scanned(tmp_path: Path) -> None:
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
    prefix = f"TOKEN = '{secret}'\n".encode()
    assert len(prefix) <= MAX_SCAN_BYTES
    (tmp_path / "edge.py").write_bytes(prefix + b"#" * (MAX_SCAN_BYTES - len(prefix)))
    assert (tmp_path / "edge.py").stat().st_size == MAX_SCAN_BYTES
    change = FileChange("edge.py", "A", 1, 0, False, None, "after")
    findings = scan_changed_files(tmp_path, [change])
    assert [finding.rule_id for finding in findings] == ["PW030"]
    assert findings[0].line == 1
    assert secret not in findings[0].message
