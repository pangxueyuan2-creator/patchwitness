# TaskToPR execution adapter

`patchwitness.tasktopr_adapter.adapt_tasktopr_execution_handoff()` converts a sanitized
TaskToPR Safe Delivery handoff into PatchWitness `ComponentEvidence` for the
`execution` component.

The caller must derive the PatchWitness `ChangeSubject` independently. In particular,
TaskToPR's `change_scope_sha256` is **not** treated as PatchWitness's changed-file
manifest identity, and TaskToPR's execution-policy digest is **not** treated as the
reviewer-owned Safe Delivery policy identity. Both TaskToPR values are validated and
bound into the adapter details digest without being promoted to PatchWitness authority.

The adapter validates the handoff envelope and receipt digest, exact producer revision,
repository/base/head identity, bounded counts, test/protected-path status, source receipt,
and v2 plan-approval structure. Unknown fields and a handoff that claims `PASS` are
rejected. A repository/base/head mismatch fails closed. Producer `FAIL`,
`REVIEW_REQUIRED`, and `UNKNOWN` decisions are preserved conservatively; incomplete or
unknown execution facts cannot be upgraded.

A typical composition flow is:

```python
from patchwitness.safe_delivery import ChangeSubject, compose_safe_delivery
from patchwitness.tasktopr_adapter import adapt_tasktopr_execution_handoff

subject = ChangeSubject(
    repository_sha256=reviewer_repository_identity,
    base_sha=base_sha,
    head_sha=head_sha,
    manifest_sha256=patchwitness_manifest_identity,
    policy_sha256=reviewer_policy_identity,
)
execution = adapt_tasktopr_execution_handoff(subject, tasktopr_handoff)
report = compose_safe_delivery(
    subject,
    [execution, *other_components],
    trusted_tools={
        "execution": ("tasktopr", reviewed_tasktopr_revision),
        **other_trusted_tools,
    },
    policy_sha256=reviewer_policy_identity,
    stage="pr",
)
```

The exact TaskToPR producer revision still has to match the reviewer-controlled
`trusted_tools` pin during composition. The adapter performs no network access, imports
no TaskToPR code, executes no target code, and does not authenticate the handoff's
producer by itself. SHA-256 values provide identity/integrity only.
