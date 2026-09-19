# Git visibility preferences are not policy (unreleased)

Git's human-facing configuration can hide submodule changes or untracked files.
PatchWitness now explicitly passes `--ignore-submodules=none` to the staged and
working-tree diffs used for path/line evidence and verification conflicts. A
protected gitlink cannot disappear because `diff.ignoreSubmodules=all`,
`submodule.<name>.ignore`, or the matching `.gitmodules` entry hides it in normal
Git output. Command-scope inherited configuration is overridden too. Existing
PW003/PW033/PW032 semantics are unchanged; the collectors now supply the facts
those rules require.

The dirty-candidate predicate uses porcelain-v1 NUL output with
`--untracked-files=all --ignore-submodules=none`. Thus `status.showUntrackedFiles=no`
cannot label a dirty candidate as clean, select the parent commit instead of HEAD
for a smart scan, or bypass Safe Delivery's clean-candidate prerequisite. A clean
initial commit with a new untracked file is scanned against HEAD rather than
incorrectly rejected for lacking a parent. Tracked submodule edits, untracked
submodule files and moved submodule HEADs also count as dirt. Files excluded by
ordinary Git ignore rules remain excluded; ignored build output does not become a
new rejection. No source configuration, `.gitmodules` value or index entry is
rewritten to obtain these results.

Reproduce the real-Git regressions with:

```bash
python -m pytest -q tests/test_git_visibility.py
```

The suite covers four ignore-setting sources across staged/unstaged gitlinks,
true dirty/clean controls, inherited command configuration, trusted CLI gate and
scan behavior, index/worktree disagreement before check execution, and new
submodule scope introduced by a passing check. It uses only disposable local
repositories; no submodule clone/fetch or remote credentials are needed.

This is a visibility fix, **not recursive submodule verification**. The passport
still does not enumerate or authenticate nested submodule contents. In
particular, content/HEAD movement inside an already-reported gitlink does not gain
a new content fingerprint from this change. Existing masked-index behavior,
ignored-file policy, filesystem races, custom Git helpers and general Git
execution limits are not solved here. Keep using separately reviewed check
execution and the existing clean-room boundaries; none of this is a sandbox or
merge authorization. Older passports are not corrected retroactively.

References: [Git diff ignore-submodules](https://git-scm.com/docs/git-diff),
[Git status untracked-files and ignore-submodules](https://git-scm.com/docs/git-status).
