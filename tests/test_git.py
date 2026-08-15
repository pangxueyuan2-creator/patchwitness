import subprocess
from pathlib import Path

from patchwitness.git import collect_changes, is_untracked_noise
from patchwitness.models import Contract
from patchwitness.policy import evaluate_policy


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "tests@patchwitness.dev")
    git(tmp_path, "config", "user.name", "PatchWitness Tests")
    return tmp_path


def test_collects_rename_previous_path(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    git(root, "mv", ".github/workflows/ci.yml", "helper.py")

    changes = collect_changes(root, "HEAD")
    renamed = next(item for item in changes if item.path == "helper.py")
    assert renamed.previous_path == ".github/workflows/ci.yml"
    assert renamed.status.startswith("R")
    assert renamed.before_sha256
    assert renamed.after_sha256

    contract = Contract(
        allowed_paths=("src/**", "helper.py"),
        protected_paths=(".github/workflows/**",),
        require_tests=False,
    )
    findings = evaluate_policy(contract, changes)
    assert any(
        finding.rule_id == "PW003" and finding.path == ".github/workflows/ci.yml"
        for finding in findings
    )


def test_nul_terminated_paths_with_spaces_and_unicode(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "keep.py").write_text("ok\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    (root / "my file 安全.py").write_text("print('hi')\n", encoding="utf-8")

    changes = collect_changes(root, "HEAD")
    paths = {item.path for item in changes}
    assert "my file 安全.py" in paths
    added = next(item for item in changes if item.path == "my file 安全.py")
    assert added.status.startswith("A")
    assert added.previous_path is None


def test_copy_and_rename_both_paths_are_policy_subjects(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    src = root / "src"
    src.mkdir()
    (src / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    git(root, "mv", "src/app.py", "src/renamed app.py")

    changes = collect_changes(root, "HEAD")
    renamed = next(item for item in changes if item.path == "src/renamed app.py")
    assert renamed.previous_path == "src/app.py"
    assert renamed.policy_paths == ("src/renamed app.py", "src/app.py")
    assert renamed.before_sha256
    assert renamed.after_sha256


def test_untracked_cache_and_tool_evidence_are_not_review_surface(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "keep.py").write_text("ok\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "base")
    (root / "keep.py").write_text("ok\nchanged\n", encoding="utf-8")
    (root / "sneaky.py").write_text("print('new')\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "evil.yml").write_text("name: evil\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "keep.cpython-314.pyc").write_bytes(b"\0pyc")
    (root / ".tasktopr" / "runs" / "demo").mkdir(parents=True)
    (root / ".tasktopr" / "runs" / "demo" / "summary.md").write_text("local\n", encoding="utf-8")
    (root / ".pytest_cache").mkdir()
    (root / ".pytest_cache" / "v").write_text("cache\n", encoding="utf-8")
    (root / ".patchwitness" / "cache").mkdir(parents=True)
    (root / ".patchwitness" / "cache" / "impact-v1.json").write_text("{}\n", encoding="utf-8")
    (root / ".patchwitness" / "contracts").mkdir(parents=True)
    (root / ".patchwitness" / "contracts" / "task.toml").write_text("id = 'x'\n", encoding="utf-8")

    changes = collect_changes(root, "HEAD")
    paths = {item.path for item in changes}
    assert "keep.py" in paths
    assert "sneaky.py" in paths
    assert ".github/workflows/evil.yml" in paths
    assert not any(path.startswith("__pycache__/") for path in paths)
    assert not any(path.startswith(".tasktopr/") for path in paths)
    assert not any(path.startswith(".pytest_cache/") for path in paths)
    assert ".patchwitness/cache/impact-v1.json" not in paths
    assert ".patchwitness/contracts/task.toml" in paths
    assert is_untracked_noise("__pycache__/keep.cpython-314.pyc")
    assert is_untracked_noise(".tasktopr/runs/demo/summary.md")
    assert not is_untracked_noise("sneaky.py")
    assert not is_untracked_noise(".github/workflows/evil.yml")
    assert not is_untracked_noise(".tasktopr.toml")
    assert is_untracked_noise(".patchwitness/cache/impact-v1.json")
    assert is_untracked_noise(".patchwitness/evidence/run.json")
    assert not is_untracked_noise(".patchwitness/contracts/task.toml")
