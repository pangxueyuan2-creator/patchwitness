# Policy rule reference

PatchWitness rules are deterministic and stable within a major schema version.

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

## PW031

A changed text file is larger than the 2 MB scan limit, so its secret scan was skipped. This is an
informational finding: the gate still passes, but the evidence pack records which files were not
scanned. Lower the limit only after weighing scan cost against the risk of missing a secret.
