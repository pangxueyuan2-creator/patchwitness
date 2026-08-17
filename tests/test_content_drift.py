from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from patchwitness.evidence import capture_evidence
from patchwitness.models import CheckSpec, Contract, GateStatus


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def repository(root: Path) -> Path:
    root.mkdir(exist_ok=True)
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "tests@patchwitness.dev")
    git(root, "config", "user.name", "PatchWitness Tests")
    (root / "app.py").write_text("print('base')\n", encoding="utf-8")
    git(root, "add", "app.py")
    git(root, "commit", "-m", "base")
    return root


def mutating_contract(script: Path) -> Contract:
    return Contract(
        require_tests=False,
        checks=(CheckSpec(id="mutator", command=f'"{sys.executable}" "{script}"'),),
    )


def test_check_mutating_recorded_file_fails_closed(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_text("print('candidate')\n", encoding="utf-8")
    script = tmp_path / "mutate.py"
    script.write_text(
        "from pathlib import Path\n"
        "path = Path('app.py')\n"
        "path.write_text(path.read_text(encoding='utf-8') + '# drift\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    pack = capture_evidence(
        root,
        mutating_contract(script),
        execute_checks=True,
        clean_room_checks=False,
    )

    drift = [finding for finding in pack.findings if finding["rule_id"] == "PW032"]
    assert len(drift) == 1
    assert drift[0]["path"] == "app.py"
    assert drift[0]["severity"] == "error"
    assert pack.status == GateStatus.FAIL
    assert pack.summary["errors"] >= 1


def test_check_deleting_recorded_file_fails_closed(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_text("print('candidate')\n", encoding="utf-8")
    script = tmp_path / "delete.py"
    script.write_text("from pathlib import Path\nPath('app.py').unlink()\n", encoding="utf-8")

    pack = capture_evidence(
        root,
        mutating_contract(script),
        execute_checks=True,
        clean_room_checks=False,
    )

    drift_paths = {
        finding["path"] for finding in pack.findings if finding["rule_id"] == "PW032"
    }
    assert "app.py" in drift_paths
    assert pack.status == GateStatus.FAIL


def test_check_created_untracked_artifact_does_not_invalidate_recorded_change(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_text("print('candidate')\n", encoding="utf-8")
    script = tmp_path / "create.py"
    script.write_text(
        "from pathlib import Path\nPath('generated.txt').write_text('new\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    pack = capture_evidence(
        root,
        mutating_contract(script),
        execute_checks=True,
        clean_room_checks=False,
    )

    assert not any(finding["rule_id"] == "PW032" for finding in pack.findings)
    assert pack.status == GateStatus.PASS
    assert pack.repository["dirty"] is True


def test_stable_live_checks_emit_no_pw032(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_text("print('candidate')\n", encoding="utf-8")
    script = tmp_path / "noop.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    pack = capture_evidence(
        root,
        mutating_contract(script),
        execute_checks=True,
        clean_room_checks=False,
    )

    assert not any(finding["rule_id"] == "PW032" for finding in pack.findings)
    assert pack.status == GateStatus.PASS


def test_clean_room_checks_do_not_compare_live_drift(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "app.py").write_text("print('candidate')\n", encoding="utf-8")
    script = tmp_path / "mutate.py"
    script.write_text(
        "from pathlib import Path\n"
        "path = Path('app.py')\n"
        "path.write_text(path.read_text(encoding='utf-8') + '# isolated\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )

    pack = capture_evidence(
        root,
        mutating_contract(script),
        execute_checks=True,
        clean_room_checks=True,
    )

    assert not any(finding["rule_id"] == "PW032" for finding in pack.findings)
