# Coding agent integration

PatchWitness is agent-neutral. Use the same workflow with Codex, ChatGPT, Cline, Claude Code,
Cursor, Copilot, Aider, or a custom coding agent.

For working local post-task examples that default to structural inspection and do **not** execute repository code, see [Claude Code safe hooks](../../examples/claude-code-hooks/README.md) and [GitHub Copilot CLI safe hooks](../../examples/copilot-cli-hooks/README.md). Both examples remain advisory; the protected CI job described below is the merge boundary.

The integration has two layers:

1. The agent runs a local scan for fast, advisory feedback.
2. A protected CI job independently repeats enforcement with policy from the immutable base SHA.

An agent running PatchWitness on its own output is useful, but it is not an independent trust root:
the agent still controls the working tree, command invocation, and local environment. Treat the
required CI job—not the agent's completion summary—as the merge boundary.

## Copy into your agent instructions

Adapt the base branch and evidence path to your repository:

```text
After modifying the repository:

1. Do not describe your own completion summary as independent evidence.
2. Do not modify CI, test harnesses, hooks, or `.patchwitness.toml` unless the task explicitly
   requires it. If one changes, call it out before discussing product code.
3. Run `patchwitness doctor` and inspect every detected command before executing repository code.
4. For a trusted repository, run:
   `patchwitness scan --base origin/main --output .patchwitness/evidence/agent-local.json`
   For an untrusted repository, use `--no-checks` instead.
5. Run `patchwitness verify .patchwitness/evidence/agent-local.json`.
6. Report the evidence path, PatchWitness status, stable finding IDs, and checks that actually ran.
   Do not claim that a passing passport proves semantic correctness or deployment safety.
7. Never weaken policy or verification controls to make the gate pass. Stop and explain the
   conflict instead.
```

This instruction is deliberately provider-neutral. Put it in the repository instruction surface
your agent actually reads, or include it in the task contract supplied by your orchestrator.

## Persist reviewed policy

The first local scan can use an in-memory preview policy. Before enforcing a merge gate, generate
and review a repository policy:

```bash
patchwitness init
# Review detected commands, allowed paths, and protected paths.
git add .patchwitness.toml .gitignore
git commit -m "chore: add PatchWitness policy"
```

For a narrow task, create a separate task contract rather than expanding the default policy:

```bash
patchwitness contract new GH-123 \
  --goal "Fix token refresh without changing the public API" \
  --allow "src/auth/**" \
  --allow "tests/auth/**" \
  --protect ".github/workflows/**" \
  --check "tests=python -m pytest tests/auth"
```

## Make CI authoritative

Install [PatchWitness Gate](https://github.com/marketplace/actions/patchwitness-gate) on pull
requests, load `.patchwitness.toml` from `${{ github.event.pull_request.base.sha }}`, and make the
job required in branch protection. The complete copy-paste workflow is in the
[GitHub Actions integration](github-actions.md).

The required job should have read-only repository permissions, full Git history, no untrusted
secrets, and every dependency needed by the commands in `.patchwitness.toml`. Keep CODEOWNERS and
branch protection around policy and workflow changes. PatchWitness records and evaluates those
changes; it does not decide who may approve them.

## What to retain

Keep the CI-produced Change Passport as the review artifact. The local passport is useful for
debugging and comparison, but the CI passport is the one produced outside the agent-controlled
working environment. If the two disagree, investigate the environment, resolved base SHA, policy
source, and executed checks instead of accepting either summary blindly.
