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
- It does not turn a local advisory scan into a merge gate. CI still has to be the authoritative boundary.

## When to skip pieces

- No AGENTS.md / CLAUDE.md style rules → skip GuardSpec.
- You already have a branch and just need evidence → skip TaskToPR.
- You only need a preflight answer → skip PatchWitness.

Use the tools that match the question you actually have.
