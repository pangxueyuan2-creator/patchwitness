# Clean-room patch path identity

This fix is unreleased. It does not alter the existing v0.3.0 release assets.

## Who is affected

Maintainers using `gate --clean-room` (or another capture with `--clean-room`)
may configure Git's display-oriented diff prefixes locally or globally.
In v0.3.0, `diff.noprefix=true` can silently redirect a patch for
`src/value.txt` to the unrelated root-level `value.txt` when the original
contents match. The verifier then reads the unchanged `src/value.txt`, so a
required check can incorrectly pass. Without a matching destination, patch
application can fail instead. Multi-component `diff.srcPrefix` and
`diff.dstPrefix` values can also prevent a valid patch from applying.

The same mechanism affects unstaged, staged and committed changes relative
to the selected base. It is not specific to one programming language.

## Corrected behavior

PatchWitness requests `--src-prefix=a/ --dst-prefix=b/` when creating its
internal binary patch and explicitly applies it with `-p1`. These options
keep repository-relative filename identity independent of the user's diff
display preferences. They do not rewrite repository or global Git config.
Default and mnemonic prefixes continue to work. Binary contents, additions,
deletions, renames and the existing untracked-file copy behavior are retained.

The regression suite includes an actual trusted-base gate with a required
check that rejects the changed nested file. The gate must exit 1 with PW021,
record the real failing check, and leave both source files unchanged.
`patchwitness verify` still accepts that internally consistent FAIL receipt;
integrity verification is not policy approval.

## Upgrade and boundaries

Re-run clean-room verification after upgrading when prior receipts were made
with affected Git prefix settings. On v0.3.0, set `diff.noprefix=false` and
use ordinary one-component `a/` and `b/` source/destination prefixes in the
verification environment before re-running. Review your own config rather
than treating a past PASS as proof that the intended file was tested.

This narrowly fixes patch path reconstruction. It does not make clean-room
execution a hostile-code sandbox, create an atomic source snapshot, or
normalize every Git configuration or attribute. Evidence-v1 fields, policy
rules, command trust restrictions, dependencies and release versions are
unchanged.

## References and reproduction

- [Git diff prefix options](https://git-scm.com/docs/git-diff)
- [Git apply path stripping](https://git-scm.com/docs/git-apply)

```console
python -m pytest -q tests/test_cleanroom_prefixes.py tests/test_cleanroom.py
```

These are maintainer-run synthetic regressions, not independent adoption.
