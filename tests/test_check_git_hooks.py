"""Exercise real Git hook dispatch, not merely a claimed environment value."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from patchwitness.checks import run_checks
from patchwitness.evidence import capture_evidence, verify_evidence
from patchwitness.models import CheckSpec, Contract


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, timeout=15
    ).stdout


def fixture_repo(tmp_path: Path, location: str) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Hook fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / "app.py").write_text("value = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic base")
    hooks = root / ".git/hooks" if location == "default" else tmp_path / "configured hooks"
    hooks.mkdir(exist_ok=True)
    marker = tmp_path / "hook-ran"
    hook = hooks / "post-checkout"
    hook.write_text(
        '#!/bin/sh\nprintf hook > "' + marker.as_posix() + '"\n', encoding="utf-8"
    )
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if location == "local":
        git(root, "config", "core.hooksPath", hooks.as_posix())
    return root, marker, hooks


def check_script(tmp_path: Path, *, config_assertions: bool = False) -> CheckSpec:
    script = tmp_path / "check.py"
    text = "import subprocess\n"
    if config_assertions:
        text += (
            "assert subprocess.check_output(['git','config','pw.numbered']).strip() == b'kept'\n"
            "assert subprocess.check_output(['git','config','pw.inherited']).strip() == b'kept'\n"
        )
    text += "subprocess.run(['git','checkout','--detach','HEAD'],check=True,capture_output=True)\n"
    script.write_text(text, encoding="utf-8")
    return CheckSpec(id="git-child", command=f'"{sys.executable}" "{script}"')


@pytest.mark.parametrize("location", ["default", "local", "environment"])
@pytest.mark.parametrize("isolated", [True, False])
def test_real_git_children_obey_clean_room_hook_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str, isolated: bool
) -> None:
    # These cases own their input config, even when pytest itself is a
    # clean-room check. Live-mode inheritance is tested separately below.
    monkeypatch.delenv("GIT_CONFIG_PARAMETERS", raising=False)
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    root, marker, hooks = fixture_repo(tmp_path, location)
    if location == "environment":
        monkeypatch.setenv("GIT_CONFIG_COUNT", "2")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "pw.numbered")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", "kept")
        monkeypatch.setenv("GIT_CONFIG_KEY_1", "core.hooksPath")
        monkeypatch.setenv("GIT_CONFIG_VALUE_1", hooks.as_posix())
        monkeypatch.setenv(
            "GIT_CONFIG_PARAMETERS",
            "'pw.inherited'='kept' 'core.hooksPath'='" + hooks.as_posix() + "'",
        )
    spec = check_script(tmp_path, config_assertions=location == "environment")
    config = (root / ".git/config").read_bytes()
    index_entries = git(root, "ls-files", "--stage", "-v", "-z")
    head = git(root, "rev-parse", "HEAD")
    env = dict(os.environ)
    worktrees = git(root, "worktree", "list", "--porcelain")
    (root / "app.py").write_text("value = 2\n", encoding="utf-8")

    pack = verify_evidence(capture_evidence(
        root, Contract(require_tests=False, checks=(spec,)), clean_room_checks=isolated
    ))

    assert pack.checks[0]["passed"] is True
    assert pack.extensions["verification"]["git_hooks_disabled"] is isolated
    assert marker.exists() is not isolated
    assert (root / ".git/config").read_bytes() == config
    assert git(root, "rev-parse", "HEAD") == head
    assert dict(os.environ) == env
    if isolated:
        assert git(root, "worktree", "list", "--porcelain") == worktrees
        # Git may refresh stat-cache bytes; tracked entries and flags must not change.
        assert git(root, "ls-files", "--stage", "-v", "-z") == index_entries


@pytest.mark.parametrize("parallel", [True, False])
def test_each_check_has_its_own_temporary_empty_hook_directory(
    tmp_path: Path, parallel: bool
) -> None:
    root, marker, _ = fixture_repo(tmp_path, "local")
    specs = []
    for i in range(2):
        script = tmp_path / f"child-{i}.py"
        output = tmp_path / f"directory-{i}.json"
        script.write_text(
            "import json,subprocess\nfrom pathlib import Path\n"
            "p=Path(subprocess.check_output(['git','config','core.hooksPath']).decode().strip())\n"
            "assert p.is_dir() and not list(p.iterdir())\n"
            f"Path({str(output)!r}).write_text(json.dumps(str(p)),encoding='utf-8')\n"
            "subprocess.run(['git','hook','run','--ignore-missing',"
            "'post-checkout','--'],check=True)\n",
            encoding="utf-8",
        )
        specs.append(CheckSpec(id=str(i), command=f'"{sys.executable}" "{script}"'))
    results = run_checks(root, specs, parallel=parallel, untrusted=True)
    assert all(result.passed for result in results)
    paths = [Path(json.loads((tmp_path / f"directory-{i}.json").read_text())) for i in range(2)]
    assert paths[0] != paths[1]
    assert all(not path.exists() for path in paths)
    assert not marker.exists()


@pytest.mark.parametrize("exit_code", [0, 7])
def test_exit_codes_and_hook_directory_cleanup_are_preserved(
    tmp_path: Path, exit_code: int
) -> None:
    root, marker, _ = fixture_repo(tmp_path, "local")
    record = tmp_path / "hooks-path"
    script = tmp_path / "exit.py"
    script.write_text(
        "import subprocess\nfrom pathlib import Path\n"
        f"Path({str(record)!r}).write_bytes("
        "subprocess.check_output(['git','config','core.hooksPath']))\n"
        f"raise SystemExit({exit_code})\n", encoding="utf-8",
    )
    result, = run_checks(
        root, (CheckSpec(id="exit", command=f'"{sys.executable}" "{script}"'),), untrusted=True
    )
    assert result.exit_code == exit_code
    assert result.passed is (exit_code == 0)
    assert not Path(record.read_text().strip()).exists()
    assert not marker.exists()


def test_temporary_hook_path_preserves_quotes_spaces_and_unicode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from functools import partial
    from tempfile import TemporaryDirectory

    parent = tmp_path / "quoted's ! \u6d4b\u8bd5"
    parent.mkdir()
    monkeypatch.setattr(
        "patchwitness.checks.TemporaryDirectory", partial(TemporaryDirectory, dir=parent)
    )
    root, marker, _ = fixture_repo(tmp_path, "local")
    spec = check_script(tmp_path)
    result, = run_checks(root, (spec,), untrusted=True)
    assert result.passed
    assert not marker.exists()
    assert not list(parent.iterdir())


def test_timeout_still_cleans_the_temporary_hook_directory(tmp_path: Path) -> None:
    root, marker, _ = fixture_repo(tmp_path, "local")
    record = tmp_path / "timeout-hooks"
    script = tmp_path / "sleep.py"
    script.write_text(
        "import subprocess,time\nfrom pathlib import Path\n"
        f"Path({str(record)!r}).write_bytes("
        "subprocess.check_output(['git','config','core.hooksPath']))\n"
        "time.sleep(30)\n", encoding="utf-8",
    )
    result, = run_checks(root, (CheckSpec(
        id="timeout", command=f'"{sys.executable}" "{script}"', timeout_seconds=3
    ),), untrusted=True)
    assert result.timed_out and not result.passed
    assert not Path(record.read_text().strip()).exists()
    assert not marker.exists()


def test_explicit_child_override_is_not_an_os_sandbox(tmp_path: Path) -> None:
    root, marker, hooks = fixture_repo(tmp_path, "local")
    script = tmp_path / "explicit.py"
    script.write_text(
        "import subprocess\n"
        f"subprocess.run(['git','-c',{('core.hooksPath=' + hooks.as_posix())!r},"
        "'checkout','--detach','HEAD'],check=True,capture_output=True)\n",
        encoding="utf-8",
    )
    result, = run_checks(root, (CheckSpec(
        id="explicit", command=f'"{sys.executable}" "{script}"'
    ),), untrusted=True)
    assert result.passed
    assert marker.exists()  # Documented boundary: explicit child -c overrides inherited config.


def test_live_checks_preserve_inherited_hook_suppression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, marker, _ = fixture_repo(tmp_path, "local")
    outer_hooks = tmp_path / "outer-empty-hooks"
    outer_hooks.mkdir()
    monkeypatch.setenv(
        "GIT_CONFIG_PARAMETERS", "'core.hooksPath'='" + outer_hooks.as_posix() + "'"
    )
    spec = check_script(tmp_path)
    environment = dict(os.environ)
    result, = run_checks(root, (spec,), untrusted=False)
    assert result.passed
    assert not marker.exists()
    assert outer_hooks.is_dir()  # The caller, not this check, owns its lifetime.
    assert dict(os.environ) == environment
