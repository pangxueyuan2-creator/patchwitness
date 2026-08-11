from pathlib import Path

from patchwitness.models import FileChange
from patchwitness.security import scan_changed_files


def test_secret_finding_never_contains_the_value(tmp_path: Path) -> None:
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
    (tmp_path / "config.py").write_text(f"TOKEN = '{secret}'\n", encoding="utf-8")
    change = FileChange("config.py", "A", 1, 0, False, None, "after")
    findings = scan_changed_files(tmp_path, [change])
    assert len(findings) == 1
    assert findings[0].rule_id == "PW030"
    assert findings[0].line == 1
    assert secret not in findings[0].message
