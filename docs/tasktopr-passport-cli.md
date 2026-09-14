# TaskToPR Safe Delivery passport CLI

PatchWitness can consume a sanitized TaskToPR exact-head execution handoff without letting the producer define PatchWitness's candidate manifest or reviewer policy.

The installed composition command is:

```console
patchwitness-safe-delivery tasktopr \
  --handoff ./tasktopr-execution.json \
  --tasktopr-revision <reviewed-40-char-tasktopr-commit> \
  --base <reviewed-base-commit> \
  --policy-ref <reviewed-policy-commit> \
  --output ./safe-delivery.json
```

`--base`, `--policy-ref`, and `--tasktopr-revision` must be exact lowercase 40-character Git commit identities. `--head` defaults to the repository's current `HEAD`; PatchWitness refuses to compose a passport if that resolved candidate is not the current exact `HEAD` or if the repository is dirty. The policy is read from `.patchwitness.toml` at the exact `--policy-ref` commit unless `--policy-path` selects another repository-relative path.

## What PatchWitness derives independently

PatchWitness computes the Safe Delivery `ChangeSubject` itself. The repository identity uses the canonical local-root digest expected by the current TaskToPR handoff protocol. The base and head commits are resolved from Git, ancestry is checked, and the manifest identity is a domain-separated SHA-256 over Git's exact-commit raw diff records. The reviewer policy identity is SHA-256 over the policy bytes loaded from the exact policy commit.

TaskToPR's `change_scope_sha256` and execution-policy digest remain producer provenance. They never replace the PatchWitness manifest or reviewer-owned policy identity.

After subject derivation, PatchWitness validates the handoff envelope, its canonical receipt digest, schema, producer revision, repository/base/head identity, exact-head test result, protected-path decision, and resource budgets. The producer revision must exactly match `--tasktopr-revision`.

## Decision semantics

The TaskToPR command intentionally creates a **PR-stage** Safe Delivery report with only the `execution` component populated. A valid TaskToPR handoff can make that one component `PASS`; it cannot invent API, dependency, privacy, artifact, policy, CI, or review evidence. Missing independent components therefore remain `UNKNOWN` or `REVIEW_REQUIRED`, and the overall passport normally remains `UNKNOWN` until separate producers supply those facts.

That behavior is deliberate: an execution receipt is not merge authorization, a signature, producer authentication, or proof that the whole change is safe.

## Independent offline verification

A saved Safe Delivery passport can be verified without the source repository, producer, network, or working tree:

```console
patchwitness-safe-delivery verify ./safe-delivery.json
patchwitness-safe-delivery --json verify ./safe-delivery.json
```

Verification uses a bounded regular-file reader, rejects symlinks, duplicate JSON keys, invalid UTF-8/JSON, read races, unsupported schema/fields, inconsistent decision semantics, and receipt-digest tampering. A zero exit status means the envelope, Safe Delivery semantics, and content-addressed receipt are internally valid. It does **not** mean `payload.decision` is `PASS` and it does not authenticate a producer. The JSON result therefore reports the verified overall/component decisions separately from `ok: true`.

The external-consumer regression builds a wheel, installs it into a clean virtual environment outside the source checkout, creates synthetic pinned Safe Delivery evidence using only that installed package, and invokes the installed `patchwitness-safe-delivery verify` command. It covers clean `PASS`, blocking `FAIL`, incomplete `REVIEW_REQUIRED`, and a tampered receipt that must fail closed. This is intended to exercise the same package/user boundary as a real downstream consumer rather than relying on source-tree imports.

## Output and publication safety

Composition output is re-verified before writing. PatchWitness writes through a temporary file, flushes it with `fsync`, and atomically replaces the destination. Existing output is refused unless `--force` is explicit, and symlink output targets are rejected. Candidate cleanliness and exact `HEAD` are checked again after composition so a concurrent candidate change fails closed rather than producing apparently fresh evidence for stale bytes.

The Safe Delivery passport is designed to carry bounded identifiers, digests, decisions, rule IDs, and numeric metrics. It must not be treated as a safe container for raw prompts, command output, credentials, secrets, or private producer payloads. Repository identity may still be environment-specific metadata, so publication policy should review whether even hashed/local identities are appropriate for the intended audience.

Use `--json` before the `tasktopr` subcommand for machine-readable status:

```console
patchwitness-safe-delivery --json tasktopr ...
```

A successful composition command exit means the passport was composed and verified structurally. It does **not** mean the overall Safe Delivery decision is `PASS`; consumers must inspect `payload.decision` and the individual component decisions.
