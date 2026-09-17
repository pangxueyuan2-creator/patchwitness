"""Directory glob policy regressions, including actual Git/CLI evidence."""

from __future__ import annotations

import fnmatch
import itertools
import json
import subprocess
from pathlib import Path

import pytest

from patchwitness.cli import main
from patchwitness.models import Contract, FileChange
from patchwitness.policy import _glob_match, _matches, evaluate_policy


def changed(path: str, previous: str | None = None) -> FileChange:
    return FileChange(path, "R100" if previous else "M", 1, 0, False, "old", "new", previous)


@pytest.mark.parametrize(
    ("pattern", "accepted", "rejected"),
    [
        ("packages/*/generated/**", "packages/api/generated/out.txt", "packages/api/src/out.txt"),
        (
            "packages/*/generated/",
            "packages/api/generated/nested/out.txt",
            "packages/api/generated-old/x",
        ),
        (
            "packages/?/generated/**",
            "packages/a/generated/out.txt",
            "packages/ab/generated/out.txt",
        ),
        (
            "packages/[ab]/generated/",
            "packages/b/generated/out.txt",
            "packages/c/generated/out.txt",
        ),
        ("**/.github/workflows/**", ".github/workflows/ci.yml", ".github/actions/ci.yml"),
        (
            "**/.github/workflows/",
            "pkg/.github/workflows/ci.yml",
            "pkg/.github/workflows-old/ci.yml",
        ),
        ("packages/*/generated/**", "packages/api/generated", "packages/a/b/generated/out.txt"),
        ("./packages/*/generated/**", "packages/服务/generated/输出.txt", "other/服务/generated/x"),
    ],
)
def test_directory_globs_apply_to_allow_deny_and_protected(
    pattern: str, accepted: str, rejected: str
) -> None:
    changes = [changed(accepted), changed(rejected)]
    for field, rule_id, expected in (
        ("allowed_paths", "PW002", rejected),
        ("denied_paths", "PW001", accepted),
        ("protected_paths", "PW003", accepted),
    ):
        options = {"allowed_paths": ("**",), "denied_paths": (), "protected_paths": ()}
        options[field] = (pattern,)
        findings = evaluate_policy(Contract(**options, require_tests=False), changes)
        assert [(finding.rule_id, finding.path) for finding in findings] == [(rule_id, expected)]


def test_recursive_directory_matches_zero_or_many_segments_without_widening_star() -> None:
    for path in ("src/generated", "src/generated/x", "src/a/b/generated/x"):
        assert _matches(path, "src/**/generated/**")
    for path in ("src/generated-old/x", "other/src/generated/x", "src/a/b/generated/x"):
        assert not _matches(path, "src/*/generated/**")


def test_rename_checks_both_sides_of_wildcard_protection() -> None:
    contract = Contract(protected_paths=("packages/*/generated/**",), require_tests=False)
    paths = ("packages/api/generated/out.txt", "src/out.txt")
    for previous, current in (paths, paths[::-1]):
        findings = evaluate_policy(contract, [changed(current, previous)])
        assert [(finding.rule_id, finding.path) for finding in findings] == [("PW003", paths[0])]


def test_legacy_literal_directories_and_universal_patterns_are_preserved() -> None:
    for pattern in ("src", "src/", "src/**", "./src/", "src\\"):
        assert _matches("src", pattern)
        assert _matches("src/nested/app.py", pattern)
        assert not _matches("src-old/app.py", pattern)
    for pattern in ("*", "**", "**/*"):
        assert _matches("src/nested/.hidden", pattern)
    for pattern in ("", " ", "./"):
        assert not _matches("src/app.py", pattern)


def test_deep_recursive_patterns_do_not_depend_on_python_recursion_limit() -> None:
    # Test the matcher, not OS path limits: no deep directories are created.
    path = "/".join(["a"] * 1500 + ["target.txt"])
    assert _matches(path, "**/target.txt")
    assert not _matches(path, "**/missing.txt")
    assert _matches(path, "**/a/**")
    assert _matches("leaf", "/".join(["**"] * 1500 + ["leaf"]))


def test_segment_matcher_agrees_with_small_exhaustive_reference() -> None:
    # Deliberately recursive oracle only for tiny inputs; unlike production DP.
    def reference(path: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
        if not pattern:
            return not path
        if pattern[0] == "**":
            return reference(path, pattern[1:]) or (bool(path) and reference(path[1:], pattern))
        return bool(path) and fnmatch.fnmatchcase(path[0], pattern[0]) and reference(
            path[1:], pattern[1:]
        )

    for path_size in range(1, 4):
        for path in itertools.product(("a", "b", "aa"), repeat=path_size):
            for pattern_size in range(1, 4):
                tokens = ("a", "*", "?", "[ab]", "**")
                for pattern in itertools.product(tokens, repeat=pattern_size):
                    actual = _glob_match("/".join(path), "/".join(pattern))
                    assert actual == reference(path, pattern)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


@pytest.mark.parametrize("field,rule", [("protected_paths", "PW003"), ("denied_paths", "PW001")])
@pytest.mark.parametrize("committed", [False, True])
def test_trusted_base_directory_glob_gate_records_failure_and_verifiable_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, rule: str, committed: bool
) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    git(tmp_path, "config", "user.name", "Synthetic Maintainer")
    config = tmp_path / ".patchwitness.toml"
    config.write_text(
        'version = 1\nid = "directory-glob"\n[policy]\nallowed_paths = ["**"]\n'
        f'{field} = ["packages/*/generated/**"]\nrequire_tests = false\n', encoding="utf-8"
    )
    target = tmp_path / "packages/api/generated/out.txt"
    target.parent.mkdir(parents=True)
    target.write_text("before\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "trusted baseline")
    base = git(tmp_path, "rev-parse", "HEAD")
    target.write_text("after\n", encoding="utf-8")
    if committed:
        git(tmp_path, "add", ".")
        git(tmp_path, "commit", "-m", "candidate")
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "receipt.json"
    args = [
        "gate", "--base", base, "--policy-ref", base, "--no-checks", "--output", str(output)
    ]
    assert main(args) == 1
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["summary"]["status"] == "fail"
    assert [(f["rule_id"], f["path"]) for f in receipt["findings"]] == [
        (rule, "packages/api/generated/out.txt")
    ]
    assert main(["verify", str(output)]) == 0  # Integrity is not policy approval.
