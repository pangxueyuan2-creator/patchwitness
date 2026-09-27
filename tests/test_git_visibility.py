"""Evidence and clean-candidate checks must not inherit Git UI hide settings."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from patchwitness.cli import _select_scan_base, main
from patchwitness.config import load_contract
from patchwitness.evidence import capture_evidence, load_evidence, verify_evidence
from patchwitness.git import collect_changes, is_dirty, verification_conflicts
from patchwitness.models import CheckSpec, Contract, GateStatus
from patchwitness.passport import PassportError, derive_change_subject

MODULE = ".github/workflows/vendor"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        encoding="utf-8", timeout=30,
    ).stdout.strip()


def init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Visibility fixture")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.autocrlf", "false")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    init(root)
    (root / ".gitignore").write_text(".patchwitness/\nignored/\n", encoding="utf-8")
    (root / ".patchwitness.toml").write_text(
        'version = 1\n[policy]\nallowed_paths = ["**"]\n'
        'protected_paths = [".github/workflows/**"]\nrequire_tests = false\n',
        encoding="utf-8",
    )
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted base")
    return root


@pytest.fixture
def module_repo(repo: Path, request: pytest.FixtureRequest) -> Path:
    # Use a disposable embedded Git repository: no clone, fetch or network.
    module = repo / MODULE
    init(module)
    (module / "module.txt").write_text("one\n", encoding="utf-8")
    git(module, "add", ".")
    git(module, "commit", "-qm", "module base")
    source = getattr(request, "param", "diff")
    setting = '  ignore = all\n' if source == "gitmodules" else ""
    (repo / ".gitmodules").write_text(
        f'[submodule "fixture"]\n  path = {MODULE}\n  url = ./unused\n{setting}',
        encoding="utf-8",
    )
    git(repo, "add", ".gitmodules", MODULE)
    git(repo, "commit", "-qm", "record synthetic gitlink")
    if source in {"diff", "both"}:
        git(repo, "config", "diff.ignoreSubmodules", "all")
    if source in {"module", "both"}:
        git(repo, "config", "submodule.fixture.ignore", "all")
    return repo


def advance_module(root: Path) -> None:
    (root / MODULE / "module.txt").write_text("two\n", encoding="utf-8")
    git(root / MODULE, "commit", "-qam", "module candidate")


@pytest.mark.parametrize("module_repo", ["diff", "module", "gitmodules", "both"], indirect=True)
@pytest.mark.parametrize("staged", [False, True], ids=["worktree", "index"])
def test_protected_submodule_change_cannot_be_hidden(module_repo: Path, staged: bool) -> None:
    root = module_repo
    advance_module(root)
    if staged:
        git(root, "add", MODULE)
    config = (root / ".git/config").read_bytes()
    attributes = (root / ".gitmodules").read_bytes()
    index = git(root, "ls-files", "--stage", "-z")

    changes = collect_changes(root, "HEAD")
    assert {change.path for change in changes} == {MODULE}
    assert changes[0].status == "M"
    assert (changes[0].additions, changes[0].deletions) == (1, 1)
    pack = capture_evidence(root, load_contract(root / ".patchwitness.toml"), execute_checks=False)
    assert pack.status == GateStatus.FAIL
    assert any(f["rule_id"] == "PW003" and f["path"] == MODULE for f in pack.findings)
    assert pack.repository["dirty"] is True
    assert verify_evidence(pack).status == GateStatus.FAIL
    assert (root / ".git/config").read_bytes() == config
    assert (root / ".gitmodules").read_bytes() == attributes
    assert git(root, "ls-files", "--stage", "-z") == index


@pytest.mark.parametrize("kind", ["tracked", "untracked", "head"])
def test_submodule_worktree_dirt_is_not_clean(module_repo: Path, kind: str) -> None:
    root = module_repo
    if kind == "head":
        advance_module(root)
    else:
        path = "module.txt" if kind == "tracked" else "new.txt"
        (root / MODULE / path).write_text("dirty\n", encoding="utf-8")
    assert is_dirty(root) is True
    assert _select_scan_base(root, None)[0] == "HEAD"
    assert MODULE in {change.path for change in collect_changes(root, "HEAD")}


def test_unchanged_submodule_remains_clean(module_repo: Path) -> None:
    assert is_dirty(module_repo) is False
    assert collect_changes(module_repo, "HEAD") == ()
    assert verification_conflicts(module_repo, "HEAD") == ()
    pack = capture_evidence(
        module_repo, load_contract(module_repo / ".patchwitness.toml"), execute_checks=False,
    )
    assert pack.status == GateStatus.PASS


@pytest.mark.parametrize("clean_room", [False, True])
def test_hidden_index_worktree_submodule_conflict_never_runs_check(
    module_repo: Path, tmp_path: Path, clean_room: bool,
) -> None:
    root = module_repo
    old = git(root / MODULE, "rev-parse", "HEAD")
    advance_module(root)
    git(root, "add", MODULE)
    git(root / MODULE, "checkout", "-q", old)
    assert verification_conflicts(root, "HEAD") == (MODULE,)
    marker = tmp_path / "check-ran"
    script = tmp_path / "check.py"
    script.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n", encoding="utf-8",
    )
    contract = Contract(
        protected_paths=(), require_tests=False,
        checks=(CheckSpec("marker", f'"{sys.executable}" "{script}"'),),
    )
    pack = capture_evidence(root, contract, clean_room_checks=clean_room)
    assert pack.status == GateStatus.FAIL
    assert pack.checks == ()
    assert any(f["rule_id"] == "PW033" and f["path"] == MODULE for f in pack.findings)
    assert not marker.exists()


def test_trusted_cli_gate_records_hidden_submodule_failure(
    module_repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    advance_module(module_repo)
    monkeypatch.chdir(module_repo)
    output = module_repo / ".patchwitness/evidence/visibility.json"
    assert main([
        "gate", "--base", "HEAD", "--policy-ref", "HEAD", "--no-checks", "--output", str(output),
    ]) == 1
    pack = verify_evidence(load_evidence(output))
    assert pack.status == GateStatus.FAIL
    assert {c["path"] for c in pack.changes} == {MODULE}
    assert main(["verify", str(output)]) == 0


@pytest.mark.parametrize("kind", ["untracked", "submodule"])
def test_clean_subject_rejects_hidden_candidate_dirt(
    repo: Path, module_repo: Path, kind: str,
) -> None:
    root = repo if kind == "untracked" else module_repo
    if kind == "untracked":
        git(root, "config", "status.showUntrackedFiles", "no")
        (root / "unrecorded.py").write_text("candidate\n", encoding="utf-8")
    else:
        advance_module(root)
    base = git(root, "rev-parse", "HEAD")
    with pytest.raises(PassportError, match="must be clean"):
        derive_change_subject(root, base_sha=base, head="HEAD", policy_ref=base)


@pytest.mark.parametrize("name", ["new.py", "nested/file.txt", "测试 文件.txt"])
def test_untracked_visibility_setting_cannot_choose_wrong_scan_base(repo: Path, name: str) -> None:
    git(repo, "config", "status.showUntrackedFiles", "no")
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("candidate\n", encoding="utf-8")
    assert is_dirty(repo) is True
    assert _select_scan_base(repo, None)[0] == "HEAD"
    pack = capture_evidence(repo, Contract(require_tests=False), execute_checks=False)
    assert pack.repository["dirty"] is True
    assert {c["path"] for c in pack.changes} == {name}


def test_ignored_outputs_do_not_make_candidate_dirty(repo: Path) -> None:
    git(repo, "config", "status.showUntrackedFiles", "no")
    (repo / "ignored").mkdir()
    (repo / "ignored/output.txt").write_text("generated\n", encoding="utf-8")
    assert is_dirty(repo) is False
    assert collect_changes(repo, "HEAD") == ()


def test_check_cannot_hide_new_submodule_scope(module_repo: Path, tmp_path: Path) -> None:
    root = module_repo
    old = git(root / MODULE, "rev-parse", "HEAD")
    advance_module(root)
    new = git(root / MODULE, "rev-parse", "HEAD")
    git(root / MODULE, "checkout", "-q", old)
    script = tmp_path / "check.py"
    script.write_text(
        "import subprocess\n"
        f"subprocess.run(['git', '-C', {MODULE!r}, 'checkout', '-q', {new!r}], check=True)\n",
        encoding="utf-8",
    )
    pack = capture_evidence(
        root, Contract(require_tests=False, checks=(
            CheckSpec("move-module", f'"{sys.executable}" "{script}"'),
        )), parallel_checks=False,
    )
    assert pack.checks[0]["passed"] is True
    assert pack.status == GateStatus.FAIL
    assert any(f["rule_id"] == "PW032" and f["path"] == MODULE for f in pack.findings)
    assert verify_evidence(pack) == pack


@pytest.mark.parametrize("setting,value", [
    ("diff.ignoreSubmodules", "all"),
    ("submodule.fixture.ignore", "dirty"),
    ("submodule.fixture.ignore", "untracked"),
])
def test_inherited_command_config_cannot_hide_module_dirt(
    module_repo: Path, monkeypatch: pytest.MonkeyPatch, setting: str, value: str,
) -> None:
    (module_repo / MODULE / "new.txt").write_text("new\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", setting)
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", value)
    assert is_dirty(module_repo) is True
    assert MODULE in {change.path for change in collect_changes(module_repo, "HEAD")}
    assert git(module_repo, "config", "--get", setting) == value


def test_smart_scan_of_initial_commit_with_hidden_untracked_file(
    repo: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    git(repo, "config", "status.showUntrackedFiles", "no")
    target = repo / ".github/workflows/new.yml"
    target.parent.mkdir(parents=True)
    target.write_text("name: synthetic\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    output = repo / ".patchwitness/evidence/scan.json"
    assert main(["scan", "--no-checks", "--output", str(output)]) == 1
    pack = verify_evidence(load_evidence(output))
    assert pack.repository["base_revision"] == git(repo, "rev-parse", "HEAD")
    assert pack.repository["dirty"] is True
    assert pack.status == GateStatus.FAIL
    assert any(f["rule_id"] == "PW003" for f in pack.findings)


def test_nested_ignored_files_do_not_dirty_submodule(module_repo: Path) -> None:
    module = module_repo / MODULE
    (module / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    git(module, "add", ".gitignore")
    git(module, "commit", "-qm", "module ignore fixture")
    git(module_repo, "add", MODULE)
    git(module_repo, "commit", "-qm", "updated module baseline")
    (module / "ignored.txt").write_text("generated\n", encoding="utf-8")
    assert is_dirty(module_repo) is False
    assert collect_changes(module_repo, "HEAD") == ()
