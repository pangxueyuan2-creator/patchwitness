# Cline integration

Use PatchWitness as a post-task evidence layer for Cline. When Cline completes a successful agent
turn, its `TaskComplete` file hook emits an `agent_end` event. The included Python hook reads only
the event type, task ID, timestamp, and `workspaceRoots`, then runs a structural PatchWitness scan in
each Git workspace.

## Install in a repository

Install PatchWitness first:

```bash
pipx install "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.1/patchwitness-0.2.1-py3-none-any.whl"
```

Copy the hook from a PatchWitness checkout:

```bash
mkdir -p .cline/hooks
cp examples/cline-hooks/TaskComplete.py .cline/hooks/TaskComplete.py
chmod +x .cline/hooks/TaskComplete.py
```

Cline disables file hooks in `--yolo` mode. Use Act or Plan mode for this integration.

Or download that single file:

```bash
mkdir -p .cline/hooks
curl -fsSL \
  https://raw.githubusercontent.com/pangxueyuan2-creator/patchwitness/main/examples/cline-hooks/TaskComplete.py \
  -o .cline/hooks/TaskComplete.py
chmod +x .cline/hooks/TaskComplete.py
```

After a Cline task completes, inspect and independently verify the resulting passport:

```bash
ls .patchwitness/evidence/cline-*.json
patchwitness verify .patchwitness/evidence/cline-<task>-<timestamp>.json
patchwitness inspect .patchwitness/evidence/cline-<task>-<timestamp>.json
```

The hook returns `{}` on stdout because Cline reserves stdout for a JSON control object. It captures
PatchWitness output rather than forwarding it, so repository command output cannot corrupt the hook
protocol. Only a short status and repository-relative evidence path go to stderr.

## Reproduce without spending model tokens

Cline documents manual hook testing as the supported way to validate a file hook. From any Git
repository with an uncommitted change, substitute its absolute path below:

```bash
printf '%s' '{"hookName":"agent_end","taskId":"manual-1","timestamp":"2026-08-12T00:00:00Z","workspaceRoots":["/absolute/path/to/repository"]}' \
  | python3 examples/cline-hooks/TaskComplete.py
```

Expected stdout is exactly `{}`. The real status is printed to stderr and the generated JSON appears
under `.patchwitness/evidence/`. Run `patchwitness verify` on that file rather than trusting the log
line.

The repository test suite runs this hook as a subprocess against a temporary Git repository,
introduces a protected workflow change, verifies that the hook reports `FAIL`, and verifies the
generated Change Passport offline. The fixture conforms to Cline's `AgentEndHookPayload` as of
[`cline/cline@a5611e8`](https://github.com/cline/cline/blob/a5611e8f6dfedf2a82fb37c04713649b46c9a41f/sdk/packages/shared/src/hooks/events.ts).
This proves compatibility with the published hook contract; it is not a claim that a paid,
model-backed Cline session ran during CI.

## Trust boundary

This hook is an evidence trigger, not a merge gate:

- Cline's `TaskComplete` maps to the post-run `agent_end` event. The task has already completed, so
  the hook cannot undo agent actions or block a merge.
- The hook always uses `--no-checks`. It reads Git structure and policy but does not execute changed
  repository code.
- The hook does not serialize the prompt, model output, user ID, agent ID, or complete Cline payload.
- `taskId` and `timestamp` are reduced to safe filename characters and capped before use.
- The hook refuses a PatchWitness executable or evidence directory that resolves inside or outside
  the wrong side of the workspace trust boundary: the executable must be installed outside the
  repository, while the evidence directory must remain inside it.
- PatchWitness evidence is integrity-verifiable, but SHA-256 alone does not authenticate the machine
  or person that produced it.

For enforcement, put PatchWitness's required [GitHub Action](github-actions.md) on pull requests and
load policy from the immutable base revision. That CI job is the boundary that can prevent merge.

## Current Cline contract used

The implementation follows Cline's current public source:

- [`TaskComplete` maps to `agent_end`](https://github.com/cline/cline/blob/a5611e8f6dfedf2a82fb37c04713649b46c9a41f/sdk/packages/core/src/hooks/hook-file-config.ts)
- [`AgentEndHookPayload` includes `workspaceRoots`](https://github.com/cline/cline/blob/a5611e8f6dfedf2a82fb37c04713649b46c9a41f/sdk/packages/shared/src/hooks/events.ts)
- [Python hook discovery and Windows fallback](https://github.com/cline/cline/blob/a5611e8f6dfedf2a82fb37c04713649b46c9a41f/sdk/packages/core/src/hooks/hook-file-hooks.ts)
- [Official file-hook examples and manual test guidance](https://github.com/cline/cline/blob/a5611e8f6dfedf2a82fb37c04713649b46c9a41f/sdk/examples/hooks/README.md)

Cline can change this contract. The pinned links make the validated boundary explicit, and the
integration test should be rerun when updating compatibility claims.
