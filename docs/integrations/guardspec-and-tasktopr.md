# Using GuardSpec, TaskToPR, and PatchWitness together

These three tools answer different questions. None of them requires the others.

| Tool | When | Question |
| --- | --- | --- |
| [GuardSpec](https://github.com/pangxueyuan2-creator/guardspec) | Before the work starts | Do the repository’s explicit agent rules allow this path / command / network / MCP action? |
| [TaskToPR](https://github.com/pangxueyuan2-creator/tasktopr) | During the work | Can one Issue be turned into an isolated branch, real tests, and an optional PR with evidence? |
| PatchWitness | After a change exists | What does the real Git diff + executed checks say about scope, protected paths, and integrity? |

They share a conservative attitude toward agent output, but they do not share a code dependency or a single policy format.

## Minimal local sequence

1. **Preflight with GuardSpec** (optional)

```bash
guardspec scan --root .
guardspec check --root . --path src/auth/session.ts --command "pnpm test"
```

If it denies or reports a conflict, stop and clarify the rules. Do not edit the policy inside the same unreviewed task just to make the check pass.

2. **Make the change with TaskToPR or any other agent**

```bash
tasktopr plan 123 --demo          # or a real Issue number
tasktopr fix 123 --no-pr          # local branch + tests, no PR
```

Or do the edit yourself / with another coding agent. TaskToPR is only one possible way to produce a change.

TaskToPR can also export its sanitized `tasktopr.dev/safe-delivery/execution/v1` handoff. PatchWitness now has a strict adapter for that handoff. The adapter accepts execution evidence only when the producer is pinned to an exact reviewed Git revision and its repository/base/head identities match the PatchWitness `ChangeSubject` exactly.

The boundary is deliberately asymmetric: TaskToPR's `change_scope_sha256` and execution-policy digest remain producer provenance. They do **not** become PatchWitness's Git-derived manifest identity or reviewer-owned policy identity. A TaskToPR handoff therefore cannot relabel the candidate, choose PatchWitness policy, or authorize merge by itself.

Python integrations can adapt a loaded handoff before Safe Delivery composition:

```python
from patchwitness.tasktopr import adapt_tasktopr_execution, load_tasktopr_handoff

handoff = load_tasktopr_handoff(path)
execution = adapt_tasktopr_execution(
    handoff,
    subject=reviewer_derived_subject,
    trusted_revision="<exact reviewed TaskToPR commit>",
)
```

The returned record is a `PASS` for the **execution component facts** only: TaskToPR demonstrated a bounded, protected-path-allowed, tested exact HEAD. Overall Safe Delivery still depends on PatchWitness's independently derived subject plus every other required component, including authoritative CI and review evidence.

3. **Record the observed change with PatchWitness**

```bash
patchwitness scan --base HEAD~1 --no-checks
# or, once a policy exists and you trust the repo:
patchwitness gate --base origin/main --policy-ref origin/main --clean-room
patchwitness verify .patchwitness/evidence/*.json
```

Keep the Change Passport. Treat a green result as evidence about scope and check execution, not as proof that the code is correct.

## What this sequence does not do

- It does not replace human review or branch protection.
- It does not give any model unrestricted shell or force-push rights.
- It does not claim that GuardSpec rules are automatically enforced by PatchWitness or TaskToPR.
- It does not treat TaskToPR's private execution policy or change-scope digest as PatchWitness policy or Git-manifest identity.
- It does not authenticate a producer merely because a payload contains hashes; the TaskToPR revision must come from reviewer-controlled trust configuration.
- It does not turn a local advisory scan into a merge gate. CI still has to be the authoritative boundary.

## When to skip pieces

- No AGENTS.md / CLAUDE.md style rules → skip GuardSpec.
- You already have a branch and just need evidence → skip TaskToPR.
- You only need a preflight answer → skip PatchWitness.

Use the tools that match the question you actually have.
