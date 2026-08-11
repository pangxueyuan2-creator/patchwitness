import subprocess
from pathlib import Path

from patchwitness.evidence import capture_evidence
from patchwitness.models import Contract
from patchwitness.reporters import render_markdown, render_sarif


def repository(root: Path) -> Path:
    subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "tests@patchwitness.dev"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "PatchWitness Tests"],
        check=True,
    )
    (root / "app.py").write_text("print('before')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "app.py"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", "base"], check=True)
    return root


def test_markdown_and_sarif_are_useful_and_valid(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "outside.md").write_text("change\n", encoding="utf-8")
    pack = capture_evidence(
        root,
        Contract(allowed_paths=("src/**",), require_tests=False),
        execute_checks=False,
    )
    markdown = render_markdown(pack)
    sarif = render_sarif(pack)
    assert "PatchWitness Change Passport" in markdown
    assert "PW002" in markdown
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "PW002"
