# TOML contract types and migration

PatchWitness loads a local contract or the exact trusted revision supplied with
`--policy-ref` before it executes checks. The file loader validates the original
TOML types before constructing the shared contract model. A type error is a
configuration error (CLI exit 2); it must not become a successful policy result.

## Accepted values

| Field | TOML type |
| --- | --- |
| Optional top-level `version` | Integer `1` |
| `id`, `goal` | Strings |
| `policy` | A table, normally written `[policy]` |
| `allowed_paths`, `denied_paths`, `protected_paths` | Arrays of strings |
| `allow_binary`, `allow_dependency_changes`, `require_tests` | Booleans |
| `max_files`, `max_lines` | Nonnegative integers |
| `checks` | An array of tables, normally written `[[checks]]` |
| Each check's `id`, `command` | Required nonempty strings |
| Each check's optional `required` | Boolean |
| Each check's optional `timeout_seconds` | Positive integer |

Use `false`, not `"false"`. Use `["src/**"]`, not `"src/**"`. Integers must not be
quoted, fractional, or booleans. Explicit unsupported contract versions are
rejected rather than silently treated as version 1.

```toml
version = 1
id = "typed-policy"
[policy]
allowed_paths = ["src/**", "tests/**"]
allow_binary = false
allow_dependency_changes = false
require_tests = true
max_files = 50
max_lines = 2000
[[checks]]
id = "tests"
command = "python -m pytest"
required = true
timeout_seconds = 900
```

Install your target project's test dependencies separately. These checks execute
repository code; this example is not a hostile-code sandbox or an instruction to
run an unfamiliar repository's commands without review.

## Compatibility

Omitted fields retain their existing defaults. Omitted `version` remains accepted
for legacy contracts. The historical flat policy form remains accepted when no
`[policy]` table is present. Empty path arrays retain existing semantics; in
particular, an empty allow list is not a deny-all policy. Existing checks for
empty patterns, negative budgets, duplicate check IDs and empty commands remain.

This change deliberately rejects files that previously relied on coercion. In
v0.3.0, a quoted `"false"` could be converted to true, and a scalar path string
could be iterated as individual characters. Correct such files with real TOML
types on v0.3.0, then re-run verification with the fixed revision when available.
Do not reuse prior approval based on a mistyped policy.

This is validation at the TOML file boundary, including trusted-revision loads.
It does not change direct Python `Contract.from_dict` compatibility, the evidence
schema, digest semantics, path matching, or handling of unknown metadata fields.
It adds no filesystem snapshot, input-size guarantee, or policy authorization
mechanism. A valid contract and a passing recorded check still do not prove that
a change is correct or independently approved.
