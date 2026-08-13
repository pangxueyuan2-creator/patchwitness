# Claude Code: Safe Post-task Scan

This example runs a **local advisory PatchWitness scan** when Claude Code finishes a task. It intentionally uses `--no-checks`, so it does not execute repository-owned tests or scripts. It is a starting point for a trusted repository, not a replacement for branch protection, code review, sandboxing or a protected CI gate.

## What it produces

The hook writes a timestamped Change Passport under `.patchwitness/evidence/` and prints its path. A `fail` result is visible to the developer, but the hook exits successfully so it does not silently turn an advisory local check into an unreviewed agent permission system.

## Install in a repository you trust

Install PatchWitness in the environment where Claude Code runs. Copy the checked-in hook script into the repository, then add the `Stop` hook below to the repository’s `.claude/settings.json`.

```bash
mkdir -p .claude/hooks
cp /path/to/patchwitness/examples/claude-code-hooks/.claude/hooks/patchwitness-safe-scan.sh .claude/hooks/
chmod +x .claude/hooks/patchwitness-safe-scan.sh
```

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/patchwitness-safe-scan.sh"
          }
        ]
      }
    ]
  }
}
```

If the repository already has `hooks`, add the `Stop` entry without replacing existing hook groups. Claude Code hook events run user-defined commands at lifecycle boundaries; review the current [official hook guide](https://code.claude.com/docs/en/hooks-guide) before deployment because event schemas and project settings may change.

## Escalate only after review

The script calls:

```bash
patchwitness scan --no-checks --output .patchwitness/evidence/claude-safe-scan-TIMESTAMP.json
```

It never runs a detected test command. After a maintainer reviews the repository, its policy, the detected command and the agent workflow, they may choose to run `patchwitness scan` with checks locally. For merge enforcement, configure the independent GitHub Actions job from [the main integration guide](../../docs/integrations/github-actions.md) with policy loaded from the pull request base SHA.

## Trust boundary

| Layer | What it can establish | What it cannot establish |
|---|---|---|
| Claude Code hook | A local structural snapshot and Change Passport after the agent task. | Independent verification, semantic correctness or safe command execution. |
| Local checked scan | The recorded checks ran in the local environment. | A trusted merge boundary, because the agent/session controls the working tree and invocation. |
| Protected CI gate | Evidence generated outside the agent-controlled session using trusted-base policy. | Authorization to merge or proof that code meets all product requirements. |
