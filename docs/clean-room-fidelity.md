# Clean-room materialization fidelity

A passing check is useful only when the disposable worktree contains the candidate
being verified, not an older version or a human-readable representation of it.
These unreleased source changes tighten that boundary without changing the
Evidence v1 schema, check commands, rule IDs, policy permissions or version.

## Git index flags

Clean-room checks reject a source index containing `assume-unchanged` or
`skip-worktree` entries, including unchanged entries and combinations of both
flags. Git can omit these paths from the worktree diff used to construct the
verification patch. Previously, a changed `app.py` could be recorded in evidence
while the clean-room check ran the passing base version instead.

The index is inspected before creating the disposable worktree and again before
handing it to checks. A failed, malformed or incomplete listing is an error, not
an empty index. PatchWitness does not clear the flags, rewrite the source index
or silently fall back to live checks. The CLI returns an operational error
(exit 2) without writing a new evidence receipt for that failed capture.

Use `git ls-files -v` to inspect the flags. After reviewing the affected paths,
clear a manually set flag on the relevant path and re-capture, for example:

```sh
git update-index --no-assume-unchanged -- path/to/file
git update-index --no-skip-worktree -- path/to/file
```

For a sparse checkout with skip-worktree entries, use a separate full checkout
for verification rather than bulk-clearing its flags. Unchanged masked entries
are deliberately rejected as well: the patch-only materializer cannot establish
that their worktree content is the candidate. This is a compatibility restriction,
not a claim that every sparse checkout is malicious. Live checks and explicit
`--no-checks` capture retain their existing behavior; neither substitutes for
successful isolated verification.

## Raw patches, not textconv output

The clean-room patch command now passes `--no-textconv` alongside `--no-ext-diff`,
`--binary`, `--full-index` and explicit path prefixes. A configured textconv driver
can map different file contents to the same display text. It must not make a
candidate change disappear or execute as part of patch construction.

The regression fixture changes a passing Python file to `raise SystemExit(7)`
and configures a constant-output converter. The original implementation tested
the base and reported PASS. With the fix, the converter is not invoked, the
candidate bytes reach the worktree, and its check fails with exit code 7.
This disables diff text conversion, not every Git filter or repository command.

## Untracked file identity and explicit failures

Clean-room Git path listings use strict UTF-8 without universal-newline
translation. Literal CR/LF path characters on supported filesystems stay distinct;
invalid UTF-8 names are rejected instead of being replaced with another filename.
NUL-delimited listings must be complete and contain no empty records before
copying starts. Existing evidence-output exclusions and symlink/containment checks
remain in effect.

An enumerated path that is not a regular file, such as an untracked nested
repository directory, is rejected rather than silently omitted. Copy failures
are clean-room errors and the disposable worktree is cleaned up. Ignored files
remain outside the existing untracked-copy contract. Git submodules are not
recursively initialized by this change.

This is a clean-room boundary fix, not a claim of complete end-to-end support for
every Git pathname. The separate collector changes in PR #65 address other literal
pathname cases; POSIX backslash and non-UTF-8 collection remain separate limits.
Checks still execute repository code with the caller's privileges. The additional
index checks are best-effort detection, not an atomic filesystem snapshot or
protection against every concurrent source/target replacement. Use an isolated
runner or OS sandbox for untrusted repositories and do not mutate a checkout
during capture.

## Git hooks in check subprocesses (unreleased)

Disabling hooks only on `git worktree add` does not disable them in Git commands
subsequently launched by a check. A real installed-wheel reproduction invoked
`git checkout --detach HEAD` from a check: the capture returned PASS and reported
`git_hooks_disabled: true`, but a local `post-checkout` hook ran.

Clean-room check processes now inherit a command-scoped `core.hooksPath` pointing
to a fresh empty directory outside the candidate. Each check has its own directory,
kept for the bounded process lifetime and removed afterward, including on failure
or timeout. Live checks retain their original hook behavior. The source repository
configuration, tracked index entries, hooks and parent environment are not changed.
Git itself can refresh index stat-cache bytes during ordinary collection.

The implementation appends a safely single-quoted entry to
`GIT_CONFIG_PARAMETERS`, Git's own inherited `-c` parameter representation. This
retains unrelated inherited parameters and `GIT_CONFIG_COUNT` pairs while placing
the hook setting after them. Tests exercise real Git dispatch, inherited overrides,
parallel checks and directory names containing quotes, spaces and Unicode. This
representation follows Git's implementation; cross-platform CI runs the same
regressions. It is not a new public PatchWitness API.

**This is default hook suppression, not a sandbox.** A check can explicitly pass
`git -c core.hooksPath=...`, replace its environment or run any executable directly.
Such intentional overrides are outside this boundary and are regression-tested
as a limitation, not claimed to be blocked. The existing evidence field records
requested clean-room configuration; it is not authenticated proof of descendant
behavior or a claim that checks ran. No Evidence v1 fields or digest rules change.
Re-run affected checks using the fixed source; a historical valid digest does not
establish that its hooks were suppressed. This source change is not in v0.3.0.

## Reproduction and references

Run `python -m pytest -q tests/test_cleanroom_fidelity.py` for real-Git flag,
textconv, CLI and pathname regressions plus contained error-path fixtures.

- [Git index flags](https://git-scm.com/docs/git-update-index)
- [Git NUL-delimited listings and status tags](https://git-scm.com/docs/git-ls-files)
- [Git diff textconv semantics](https://git-scm.com/docs/git-diff)

- [Git hook lookup](https://git-scm.com/docs/githooks)
- [Git command configuration and precedence](https://git-scm.com/docs/git-config)
- [Git inherited parameter encoder/parser (2.47.3)](https://github.com/git/git/blob/v2.47.3/config.c)

Run `python -m pytest -q tests/test_check_git_hooks.py` for check-process regressions.
