"""Clean-room patch paths must not inherit human-facing Git diff prefixes."""

import subprocess
from pathlib import Path

import pytest

from patchwitness.cleanroom import clean_room
from patchwitness.cli import main
from patchwitness.evidence import load_evidence, verify_evidence

PREFIX_SETTINGS = [
    pytest.param((), id="default"),
    pytest.param((("diff.noprefix", "true"),), id="no-prefix"),
    pytest.param(
        (("diff.srcPrefix", "before/tree/"), ("diff.dstPrefix", "after/tree/")),
        id="multi-component-prefixes",
    ),
    pytest.param((("diff.mnemonicPrefix", "true"),), id="mnemonic-prefixes"),
]


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def make_repository(root: Path) -> str:
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "PatchWitness Tests")
    git(root, "config", "user.email", "tests@patchwitness.dev")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "diff.noprefix", "false")
    git(root, "config", "diff.mnemonicPrefix", "false")
    git(root, "config", "diff.srcPrefix", "a/")
    git(root, "config", "diff.dstPrefix", "b/")
    (root / "src").mkdir()
    # Equal contents make a wrongly stripped patch apply successfully to the decoy.
    for path in ("src/value.txt", "value.txt"):
        (root / path).write_bytes(b"old\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "trusted fixture base")
    return git(root, "rev-parse", "HEAD").strip()


def set_prefixes(root: Path, settings: tuple[tuple[str, str], ...]) -> None:
    for key, value in settings:
        git(root, "config", key, value)


@pytest.mark.parametrize("settings", PREFIX_SETTINGS)
@pytest.mark.parametrize("state", ["unstaged", "staged", "committed"])
def test_clean_room_preserves_paths_independently_of_diff_prefixes(
    tmp_path: Path, settings: tuple[tuple[str, str], ...], state: str
) -> None:
    base = make_repository(tmp_path)
    (tmp_path / "src/value.txt").write_bytes(b"new\n")
    if state != "unstaged":
        git(tmp_path, "add", "src/value.txt")
    if state == "committed":
        git(tmp_path, "commit", "-m", "candidate change")
    set_prefixes(tmp_path, settings)
    original_status = git(tmp_path, "status", "--porcelain=v1", "-z")
    original_config = (tmp_path / ".git/config").read_bytes()
    original_worktrees = git(tmp_path, "worktree", "list", "--porcelain")

    with clean_room(tmp_path, base) as verifier:
        assert (verifier / "src/value.txt").read_bytes() == b"new\n"
        assert (verifier / "value.txt").read_bytes() == b"old\n"
    assert not verifier.exists()
    assert (tmp_path / "src/value.txt").read_bytes() == b"new\n"
    assert (tmp_path / "value.txt").read_bytes() == b"old\n"
    assert git(tmp_path, "status", "--porcelain=v1", "-z") == original_status
    assert (tmp_path / ".git/config").read_bytes() == original_config
    assert git(tmp_path, "worktree", "list", "--porcelain") == original_worktrees


@pytest.mark.parametrize("settings", PREFIX_SETTINGS)
def test_clean_room_preserves_binary_add_delete_and_rename_paths(
    tmp_path: Path, settings: tuple[tuple[str, str], ...]
) -> None:
    make_repository(tmp_path)
    for path, content in {
        "src/blob.bin": b"\x00old\xff",
        "blob.bin": b"\x00old\xff",
        "src/remove.txt": b"remove me\n",
        "remove.txt": b"remove me\n",
        "src/rename.txt": b"rename me\n",
        "rename.txt": b"rename me\n",
    }.items():
        (tmp_path / path).write_bytes(content)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "base with binary and rename fixtures")
    base = git(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "src/blob.bin").write_bytes(b"\x00new\xfe")
    (tmp_path / "src/remove.txt").unlink()
    git(tmp_path, "mv", "src/rename.txt", "src/renamed.txt")
    (tmp_path / "src/added.txt").write_bytes(b"added\n")
    git(tmp_path, "add", "-A")
    # Unstaged build outputs still retain their existing copy behavior.
    (tmp_path / "src/untracked.txt").write_bytes(b"untracked\n")
    set_prefixes(tmp_path, settings)
    original_status = git(tmp_path, "status", "--porcelain=v1", "-z")

    with clean_room(tmp_path, base) as verifier:
        assert (verifier / "src/blob.bin").read_bytes() == b"\x00new\xfe"
        assert (verifier / "blob.bin").read_bytes() == b"\x00old\xff"
        assert not (verifier / "src/remove.txt").exists()
        assert (verifier / "remove.txt").read_bytes() == b"remove me\n"
        assert not (verifier / "src/rename.txt").exists()
        assert (verifier / "src/renamed.txt").read_bytes() == b"rename me\n"
        assert (verifier / "rename.txt").read_bytes() == b"rename me\n"
        assert (verifier / "src/added.txt").read_bytes() == b"added\n"
        assert not (verifier / "added.txt").exists()
        assert not (verifier / "renamed.txt").exists()
        assert (verifier / "src/untracked.txt").read_bytes() == b"untracked\n"
    assert not verifier.exists()
    assert git(tmp_path, "status", "--porcelain=v1", "-z") == original_status


@pytest.mark.parametrize("no_prefix", [False, True], ids=["default", "no-prefix"])
def test_clean_room_gate_checks_candidate_not_the_old_nested_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_prefix: bool
) -> None:
    make_repository(tmp_path)
    (tmp_path / ".patchwitness.toml").write_text(
        'version = 1\nid = "prefix-regression"\n'
        '[policy]\nallowed_paths = ["src/**"]\nrequire_tests = true\n'
        '[[checks]]\nid = "value-check"\ncommand = "python check_value.py"\n',
        encoding="utf-8",
    )
    (tmp_path / "check_value.py").write_text(
        'from pathlib import Path\n'
        'value = Path("src/value.txt").read_text(encoding="utf-8").strip()\n'
        'print("checked-src=" + value)\n'
        'raise SystemExit(0 if value == "old" else 1)\n',
        encoding="utf-8",
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "trusted policy and check")
    base = git(tmp_path, "rev-parse", "HEAD").strip()
    (tmp_path / "src/value.txt").write_bytes(b"new\n")
    git(tmp_path, "config", "diff.noprefix", str(no_prefix).lower())
    monkeypatch.chdir(tmp_path)
    output = tmp_path / ".patchwitness/evidence/prefix.json"

    exit_code = main(
        [
            "gate", "--base", base, "--policy-ref", base,
            "--clean-room", "--serial", "--output", str(output),
        ]
    )
    pack = verify_evidence(load_evidence(output))
    assert exit_code == 1
    assert pack.summary["status"] == "fail"
    assert [change["path"] for change in pack.changes] == ["src/value.txt"]
    assert len(pack.checks) == 1
    assert pack.checks[0]["exit_code"] == 1
    assert "checked-src=new" in pack.checks[0]["output_excerpt"]
    assert "PW021" in {finding["rule_id"] for finding in pack.findings}
    assert pack.extensions["verification"]["clean_room"] is True
    # Integrity verification is not approval of the failed policy decision.
    assert main(["verify", str(output)]) == 0
    assert (tmp_path / "src/value.txt").read_bytes() == b"new\n"
    assert (tmp_path / "value.txt").read_bytes() == b"old\n"
