# Codex Stop-hook example

This example adds **advisory, local** Change Passport capture to a Codex CLI task. It uses Codex's documented `Stop` lifecycle event and runs a structural `patchwitness gate --no-checks` after a Codex turn stops. The hook reads the working directory and opaque session/turn identifiers only; it does not serialize prompts, transcript paths, model output, or arbitrary hook input.[1]

> The hook is not a merge gate. It runs in the same workspace as the agent, returns success to Codex after writing any Passport, and does not execute repository-owned commands. Keep the independent pull-request gate described in [the GitHub Actions integration](../../docs/integrations/github-actions.md) as the merge boundary.

## Install on macOS or Linux

Install PatchWitness outside the repository, then copy the committed hook into the project-local Codex configuration directory:

```bash
pipx install "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.0/patchwitness-0.2.0-py3-none-any.whl"
mkdir -p .codex/hooks
cp examples/codex-hooks/Stop.py .codex/hooks/patchwitness-stop.py
chmod +x .codex/hooks/patchwitness-stop.py
```

Create `.codex/hooks.json` with the following content. The command resolves from the Git root because Codex may start in a subdirectory.[1]

```json
{
  "description": "Capture a structural PatchWitness passport when a Codex turn stops.",
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/env python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/patchwitness-stop.py\"",
            "timeout": 120,
            "statusMessage": "Capturing PatchWitness evidence"
          }
        ]
      }
    ]
  }
}
```

Codex requires review and trust for a non-managed project hook before it runs. Open `/hooks`, inspect the exact command and trust its current definition. A changed hook requires review again; do **not** bypass trust review merely to make an automation run.[1]

## Verify the result

Make a small uncommitted change in a Git repository with a committed `.patchwitness.toml`, finish a Codex turn, then inspect the Passport:

```bash
ls .patchwitness/evidence/codex-stop-*.json
patchwitness verify .patchwitness/evidence/codex-stop-<session>-<turn>.json
patchwitness inspect .patchwitness/evidence/codex-stop-<session>-<turn>.json
```

The hook loads the contract from `HEAD` via `--policy-ref HEAD` and compares the current working tree to that same trusted baseline. It always passes `--no-checks`, so the local evidence is structural and safe for an untrusted project. A `PASS` or `FAIL` line is evidence metadata, not a claim that the task is semantically correct, reviewed, or safe to merge.

## CI handoff

After Codex opens or updates a pull request, run the repository's ordinary `pull_request` workflow. The recommended CI job uses PatchWitness Gate with the pull request base SHA for both `base` and `policy-ref`; it is independent of the agent-controlled workspace and can block merging. Do not use `pull_request_target` to execute Codex-generated fork code with secrets or a write token.[2]

## Verified fixture boundary

`tests/test_codex_hook.py` starts this hook as a subprocess against a temporary public-style Git fixture, changes a protected workflow after the committed base, and checks all of the following:

| Verified property | Result |
| --- | --- |
| Documented `Stop` event plus `cwd` resolves to a Git workspace | The hook generates one Passport. |
| Committed-base policy controls evaluation | The protected workflow edit produces `PW003` and `FAIL`. |
| Hook does not run repository checks | `--no-checks` is fixed in the invocation. |
| Prompt and transcript-like data are excluded | Fixture secrets do not appear in stderr or evidence. |
| Evidence integrity is real | The generated Passport passes offline `patchwitness verify`. |

This verifies the published hook contract against a deterministic fixture. It does **not** claim that a paid Codex session or a user-specific Codex configuration ran in the test suite. Windows-specific `commandWindows` configuration has not been exercised and is intentionally not claimed.

## References

[1]: https://developers.openai.com/codex/hooks "OpenAI Codex Hooks"
[2]: https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target "GitHub: Securely using pull_request_target"
