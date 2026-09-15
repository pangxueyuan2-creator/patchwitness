# TaskToPR compatibility pins

`patchwitness-safe-delivery tasktopr` always requires a reviewer-controlled exact
TaskToPR Git revision. Reviewers can additionally pin the producer version and the
handoff schema when they need an explicit release-compatibility boundary.

```bash
patchwitness-safe-delivery --json tasktopr \
  --handoff execution-handoff.json \
  --tasktopr-revision <40-character-git-sha> \
  --tasktopr-version 0.1.0 \
  --tasktopr-schema tasktopr.dev/safe-delivery/execution/v2 \
  --base <base-sha> \
  --policy-ref <policy-sha> \
  --policy-path .patchwitness.toml \
  --require-plan-approval \
  --output safe-delivery.json
```

## What the pins mean

`--tasktopr-version` requires the version declared inside the validated TaskToPR
handoff to exactly match the reviewer's expected release label.

`--tasktopr-schema` requires one exact supported handoff schema. PatchWitness
currently accepts `tasktopr.dev/safe-delivery/execution/v1` and
`tasktopr.dev/safe-delivery/execution/v2`; an unknown schema is rejected rather
than guessed or silently downgraded.

When either pin is supplied, a mismatch fails before a Safe Delivery passport is
written. When the optional pins are omitted, the existing revision-pinned v1/v2
behavior remains backward compatible.

Use the v2 schema together with `--require-plan-approval` when the consumer policy
also requires TaskToPR prompt-mode approve/edit provenance. A schema/version match
does not by itself authorize merge or release.

## Trust boundary

These compatibility pins supplement the mandatory exact Git revision; they do not
replace it. The producer version is a label carried by integrity-checked handoff
evidence, while the Git revision remains the reviewer's exact source pin.

Neither a version match, a schema match, nor a content digest authenticates who
built a binary or wheel. Artifact signing/attestation and distribution-channel
provenance remain separate trust decisions for release consumers.
