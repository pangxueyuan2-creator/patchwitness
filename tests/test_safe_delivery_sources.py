from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts import safe_delivery_sources as sources


def git(repo: Path, *arguments: str, data: bytes | None = None) -> bytes:
    executable = shutil.which("git")
    assert executable is not None
    return subprocess.run(
        [executable, "-C", str(repo), *arguments],
        input=data,
        check=True,
        capture_output=True,
        env=sources._git_environment(),
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / "tracked.py").write_bytes(b"raise RuntimeError('must never import target')\n")
    git(root, "add", "tracked.py")
    git(root, "commit", "-qm", "fixture")
    return root


def revision(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").decode()


def raw_commit(repo: Path, entries: list[tuple[bytes, bytes, bytes]]) -> str:
    tree_data = b"".join(mode + b" " + name + b"\0" + oid for name, mode, oid in entries)
    tree = git(repo, "hash-object", "-t", "tree", "--literally", "-w", "--stdin", data=tree_data)
    return git(repo, "commit-tree", tree.decode(), "-m", "raw fixture").decode()


def blob(repo: Path, value: bytes = b"source\n") -> bytes:
    return bytes.fromhex(git(repo, "hash-object", "-w", "--stdin", data=value).decode())


def materialize(
    repo: Path, destination: Path, sha: str | None = None
) -> sources.MaterializedSource:
    return sources.materialize_sources(
        {"producer": {"repository": repo, "revision": sha or revision(repo)}},
        destination,
    )["producer"]


def test_exact_commit_bytes_ignore_dirty_worktree_index_untracked_and_filters(
    repo: Path,
    tmp_path: Path,
) -> None:
    expected = (repo / "tracked.py").read_bytes()
    sha = revision(repo)
    (repo / "tracked.py").write_bytes(b"index replacement\r\n")
    git(repo, "add", "tracked.py")
    (repo / "tracked.py").write_bytes(b"working tree replacement\n")
    (repo / "untracked.py").write_bytes(b"untracked\n")
    git(repo, "config", "filter.evil.smudge", "definitely-not-a-command")
    (repo / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
    result = materialize(repo, tmp_path, sha)
    assert (result.root / "tracked.py").read_bytes() == expected
    assert sorted(path.name for path in result.root.iterdir()) == ["tracked.py"]
    assert result.provenance["git_revision"] == sha
    assert result.provenance["total_bytes"] == len(expected)
    assert result.provenance["execution"] == "none"
    assert str(repo) not in repr(result.provenance)


def test_git_environment_replace_refs_and_executable_modes_are_ignored(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = blob(repo, b"original\r\n")
    replacement = blob(repo, b"replacement\n")
    sha = raw_commit(repo, [(b"script.py", b"100755", original)])
    git(repo, "replace", original.hex(), replacement.hex())
    git(repo, "config", "core.fsmonitor", "definitely-not-a-command")
    git(repo, "config", "core.hooksPath", "definitely-not-a-directory")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nonexistent.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "wrong-tree"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "definitely-not-a-command")
    result = materialize(repo, tmp_path, sha)
    assert (result.root / "script.py").read_bytes() == b"original\r\n"
    if os.name != "nt":
        assert not (result.root / "script.py").stat().st_mode & 0o111


def test_nested_paths_and_deterministic_provenance(repo: Path, tmp_path: Path) -> None:
    (repo / "src").mkdir()
    (repo / "src" / "module.py").write_bytes(b"answer = 42\n")
    git(repo, "add", "src/module.py")
    git(repo, "commit", "-qm", "nested")
    first = materialize(repo, tmp_path)
    second = materialize(repo, tmp_path)
    assert first.root != second.root
    assert first.provenance == second.provenance
    assert (first.root / "src" / "module.py").read_bytes() == b"answer = 42\n"
    assert first.provenance["file_count"] == 2


@pytest.mark.parametrize("sha", ["HEAD", "main", "a" * 39, "A" * 40, "f" * 40, "a" * 40 + "\n"])
def test_rejects_nonexact_or_missing_commit(repo: Path, tmp_path: Path, sha: str) -> None:
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path, sha)
    assert not list(tmp_path.glob("pinned-sources-*"))


def test_blob_and_annotated_tag_are_not_commit_pins(repo: Path, tmp_path: Path) -> None:
    git(repo, "tag", "-a", "tagged", "-m", "fixture")
    for sha in (blob(repo).hex(), git(repo, "rev-parse", "tagged").decode()):
        with pytest.raises(sources.SourceMaterializationError):
            materialize(repo, tmp_path, sha)


@pytest.mark.parametrize("mode", [b"120000", b"160000"])
def test_rejects_symlinks_and_gitlinks(repo: Path, tmp_path: Path, mode: bytes) -> None:
    oid = blob(repo, b"../outside") if mode == b"120000" else bytes.fromhex(revision(repo))
    sha = raw_commit(repo, [(b"linked", mode, oid)])
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path, sha)


@pytest.mark.parametrize(
    "name",
    [
        b"../escape",
        b"/absolute",
        b"a\\b",
        b"C:drive",
        b".git",
        b"NUL.txt",
        b"com1",
        b"trailing.",
        b"trailing ",
        b"control\nname",
        b"x:y",
        b"a//b",
        b"./name",
        b"bad\xff",
        "e\u0301.py".encode(),
        b"a" * 256,
    ],
)
def test_rejects_nonportable_git_paths(repo: Path, tmp_path: Path, name: bytes) -> None:
    sha = raw_commit(repo, [(name, b"100644", blob(repo))])
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path, sha)
    assert not list(tmp_path.glob("pinned-sources-*"))


def test_case_aliases_and_directory_file_conflicts_are_rejected(repo: Path, tmp_path: Path) -> None:
    oid = blob(repo)
    for paths in [(b"One", b"one"), (b"dir/a", b"DIR/b"), (b"file", b"file/child")]:
        sha = raw_commit(repo, [(path, b"100644", oid) for path in paths])
        with pytest.raises(sources.SourceMaterializationError):
            materialize(repo, tmp_path, sha)


@pytest.mark.parametrize(
    "budget,value", [("MAX_FILES", 0), ("MAX_FILE_BYTES", 1), ("MAX_TOTAL_BYTES", 1)]
)
def test_resource_budgets(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: str, value: int
) -> None:
    monkeypatch.setattr(sources, budget, value)
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path)


def test_resource_budgets_apply_across_all_pins(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sources, "MAX_FILES", 1)
    pin = sources.SourcePin(repo, revision(repo))
    with pytest.raises(sources.SourceMaterializationError, match="Combined"):
        sources.materialize_sources({"one": pin, "two": pin}, tmp_path)
    assert not list(tmp_path.glob("pinned-sources-*"))


def test_missing_blob_fails_without_partial_output(repo: Path, tmp_path: Path) -> None:
    sha = raw_commit(repo, [(b"missing", b"100644", b"\x12" * 20)])
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path, sha)
    assert not list(tmp_path.glob("pinned-sources-*"))


def test_batch_failure_removes_only_owned_stage(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    original = sources._git

    def broken(*args: Any, **kwargs: Any) -> bytes:
        if "cat-file" in args[2]:
            return b"invalid blob data\n"
        return original(*args, **kwargs)

    monkeypatch.setattr(sources, "_git", broken)
    with pytest.raises(sources.SourceMaterializationError):
        materialize(repo, tmp_path)
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert (repo / "tracked.py").is_file()
    assert not list(tmp_path.glob("pinned-sources-*"))


def test_git_output_budget_is_enforced(repo: Path) -> None:
    executable = shutil.which("git")
    assert executable is not None
    with pytest.raises(sources.SourceMaterializationError, match="budget"):
        sources._git(Path(executable), repo, ["show", "HEAD:tracked.py"], 1)


def test_pin_shapes_names_and_directories(repo: Path, tmp_path: Path) -> None:
    pin = sources.SourcePin(repo, revision(repo))
    invalid: list[Any] = [
        {},
        {"../bad": pin},
        {"nul": pin},
        {"one": pin, "ONE": pin},
        {"one": {"repository": repo, "revision": pin.revision, "extra": True}},
        {"one": sources.SourcePin(Path("relative"), pin.revision)},
    ]
    for pins in invalid:
        with pytest.raises(sources.SourceMaterializationError):
            sources.materialize_sources(pins, tmp_path)
    with pytest.raises(sources.SourceMaterializationError):
        sources.materialize_sources({"one": pin}, Path("relative"))


def test_provenance_manifest_uses_exact_blob_bytes(repo: Path, tmp_path: Path) -> None:
    result = materialize(repo, tmp_path)
    content = (repo / "tracked.py").read_bytes()
    assert (
        result.provenance["repository_path_sha256"]
        == hashlib.sha256(
            str(repo.resolve()).encode(),
        ).hexdigest()
    )
    assert result.provenance["total_bytes"] == len(content)
    assert len(str(result.provenance["manifest_sha256"])) == 64


def test_directory_and_depth_budgets(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(sources.SourceMaterializationError, match="depth"):
        sources._portable_path(b"/".join([b"directory"] * 33))
    monkeypatch.setattr(sources, "MAX_DIRECTORIES", 0)
    sha = raw_commit(repo, [(b"directory/module.py", b"100644", blob(repo))])
    with pytest.raises(sources.SourceMaterializationError, match="budget"):
        materialize(repo, tmp_path, sha)


def test_output_symlink_is_rejected(repo: Path, tmp_path: Path) -> None:
    link = tmp_path / "linked-output"
    try:
        link.symlink_to(repo, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this Windows account")
    with pytest.raises(sources.SourceMaterializationError, match="links"):
        materialize(repo, link)


def test_child_environment_excludes_loader_hooks_and_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "GIT_DIR", "GH_TOKEN", "NODE_OPTIONS"):
        monkeypatch.setenv(name, "fixture-value")
    environment = sources._git_environment()
    assert not {
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "GIT_DIR",
        "GH_TOKEN",
        "NODE_OPTIONS",
        "PATH",
    } & (set(environment))
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
