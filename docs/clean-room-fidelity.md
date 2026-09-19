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

## Reproduction and references

Run `python -m pytest -q tests/test_cleanroom_fidelity.py` for real-Git flag,
textconv, CLI and pathname regressions plus contained error-path fixtures.

- [Git index flags](https://git-scm.com/docs/git-update-index)
- [Git NUL-delimited listings and status tags](https://git-scm.com/docs/git-ls-files)
- [Git diff textconv semantics](https://git-scm.com/docs/git-diff)
