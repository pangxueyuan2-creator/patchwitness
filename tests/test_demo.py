import json
import subprocess
import sys
from pathlib import Path


def test_agent_risk_demo_is_real_and_reproducible(tmp_path: Path) -> None:
    project = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, str(project / "demo" / "run_demo.py"), "--output-dir", str(tmp_path)],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests passed, but the risky control-plane change was blocked" in result.stdout
    evidence = json.loads((tmp_path / "change-passport.json").read_text(encoding="utf-8"))
    assert evidence["summary"]["status"] == "fail"
    assert evidence["summary"]["checks_passed"] == evidence["summary"]["checks_total"] == 1
    assert any(finding["rule_id"] == "PW003" for finding in evidence["findings"])
