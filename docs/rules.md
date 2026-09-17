# Policy rule reference

PatchWitness rules are deterministic and stable within a major schema version.

## Path pattern semantics

The allow, deny and protected lists share one repository-relative, case-sensitive
segment matcher. `*`, `?` and character classes match inside one path segment;
`**` spans zero or more complete segments. Directory forms ending in `/` or `/**`
include the matched directory itself and its descendants, including when the
prefix contains wildcards.

For example, `packages/*/generated/**` matches `packages/api/generated` and
`packages/api/generated/deep/out.txt`, but not `packages/a/b/generated/out.txt`
or `packages/api/generated-old/out.txt`. `**/.github/workflows/**` matches both
root and nested workflow directories. Patterns such as `src/` and plain `src`
keep their existing literal-directory behavior. The standalone patterns `*`,
`**` and `**/*` retain their legacy match-all behavior. Leading `./` is ignored.
Empty patterns match nothing and are rejected in contract files.

Both sides of a rename are checked. Deny wins over allow, and a protected match
is still PW003 even when it is also allowed. These rules are not a `.gitignore`
or CODEOWNERS parser; do not assume their negation or ownership semantics.

Before versions containing the directory-glob fix, wildcard prefixes ending in
`/` or `/**` were compared literally. Such deny/protected patterns could miss a
matching path, while allow patterns could reject it. Re-run prior checks that
relied on these patterns with the fixed revision. On v0.3.0, use explicit literal
directory entries (for example `packages/api/generated/**`) until upgrading.
The fix changes matching behavior, not rule IDs or evidence-v1 integrity bytes.

## PW001

The changed path matches `denied_paths`. Deny rules always win.

## PW002

The changed path is outside every `allowed_paths` pattern.

## PW003

The change modifies a protected control-plane surface such as CI or PatchWitness policy. In CI,
load the policy from the base branch with `--policy-ref` so the patch cannot weaken its own gate.

## PW004

A binary file changed while `allow_binary = false`.

## PW005

A dependency manifest or lockfile changed while `allow_dependency_changes = false`.

## PW010

The change exceeds `max_files`.

## PW011

Added plus deleted lines exceed `max_lines`.

## PW020

A required check was not executed.

## PW021

A required check failed or timed out.

## PW022

The contract requires tests but does not define a check.

## PW030

A high-confidence secret shape was found in a changed text file. PatchWitness records only the
secret type, path, and line; the value is never copied into evidence.

## PW032

A path that was part of the captured change moved after it was hashed but before verification
finished, or repository HEAD/branch moved during capture. This includes content, status, deletion,
or rename-provenance changes to recorded paths. The source repository is checked in both live
and clean-room execution modes. Evidence retains the initially observed HEAD and branch.
PatchWitness refuses to issue stale evidence: PW032 is an error and the gate fails. New untracked
build/test artifacts created by checks are not themselves PW032 because they were never part of
the recorded change; the final repository `dirty` flag still reflects them. Clean rooms isolate
ordinary relative writes, but they are not a process sandbox or an atomic source snapshot.

## PW033

A path changed in the index relative to the base has different working-tree content, a staged
deletion has a remaining working-tree replacement, or index flags prevent a reliable comparison.
Evidence records the index version while live checks and clean-room materialization read the
working tree. PatchWitness rejects this ambiguous state before running checks, and checks for
new ambiguity again after execution. Stage the intended content or unstage the path before
retrying. Normal Git line-ending conversions do not by themselves cause this rule to fail.

The rule also applies to `--no-checks`. Skipped required checks retain PW020; an absent test result
cannot be interpreted as a successful result. This comparison does not provide process isolation
or an atomic filesystem snapshot.
