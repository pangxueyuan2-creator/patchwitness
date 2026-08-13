# Codex integration

## Status: VERIFIED — project-local Stop-hook fixture and CI handoff

PatchWitness supports a **two-stage** Codex workflow. A repository-local Codex `Stop` hook captures a structural, advisory Change Passport after a turn stops; the ordinary pull-request CI gate independently decides whether a change may merge. Codex documents `Stop` as a lifecycle event and supports project-local `hooks.json` / `.codex/config.toml` configuration, with review-and-trust required for non-managed command hooks.[1]

| Layer | Verified behavior | Trust boundary |
| --- | --- | --- |
| Local Codex task | `examples/codex-hooks/Stop.py` receives a documented Stop payload, derives the Git root from `cwd`, and runs `patchwitness gate --base HEAD --policy-ref HEAD --no-checks`. | Advisory only; the agent controls the workspace and can modify it. |
| Passport review | The hook writes a safe, repository-relative Passport and users run `patchwitness verify` offline. | Integrity verification proves the captured payload was not later altered; it does not authenticate the producer. |
| Pull-request CI | PatchWitness Gate loads policy from the immutable PR base SHA and runs outside the Codex task environment. | This is the only layer that should be required for merging. |

The **VERIFIED** label is deliberately narrow. The repository test suite exercises the public Stop-hook event shape in a synthetic Git fixture, validates a `PW003` protected-workflow finding, verifies the artifact offline, and asserts that prompt/transcript-like values do not enter output or evidence. It does not assert that a paid Codex session ran in CI, that every Codex release preserves the event schema, or that Windows-specific configuration works.

## Local post-task setup

The complete macOS/Linux configuration is in [the Codex Stop-hook example](../../examples/codex-hooks/README.md). It is intentionally a project-local setup rather than a global machine policy:

```text
Codex turn stops
  → Codex runs the reviewed project Stop hook
  → hook resolves the Git root and invokes PatchWitness outside that root
  → PatchWitness evaluates working-tree changes against the committed HEAD contract
  → hook emits a structural Passport under .patchwitness/evidence/
  → developer verifies and reviews the Passport
```

The hook locks in `--no-checks`. This prevents an agent completion event from executing repository-owned test commands merely because a project is opened. If a local repository is trusted and you intentionally want test execution, run `patchwitness doctor` first, inspect detected commands, and invoke PatchWitness yourself; do not silently remove the hook's safe default.

## CI handoff after Codex changes

Codex may work locally, in a cloud task, or through a GitHub-connected workflow. In every case, have it open a normal branch or pull request and let the repository's `pull_request` workflow enforce policy. The GitHub Action template below uses an immutable base SHA and read-only permissions:

```yaml
name: PatchWitness
on:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Install project test dependencies
        run: python -m pip install -e ".[test]"
      - uses: pangxueyuan2-creator/patchwitness@fa5e2ede4aded18c6c2647e21ad53bc92c4cfb6e # v0.2.0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          policy-ref: ${{ github.event.pull_request.base.sha }}
          clean-room: "true"
```

The action must run only after every command declared in the committed PatchWitness contract is available. Make this job required in branch protection; keep ownership controls around `.patchwitness.toml` and workflow files. A Codex completion summary, an agent-created Passport, or an action output is never a replacement for review and a protected CI result.

## GitHub Action and Codex safety boundary

OpenAI's official Codex Action can run feedback/review tasks in CI, but it requires an OpenAI credential and its own security design. If adopting it, place Codex in a read-only job with `contents: read`, restrict triggers to trusted actors, keep the API key only on the Codex Action step, and emit a patch/review artifact rather than giving the same job repository write permissions.[2] PatchWitness can then run as a separate, no-secret `pull_request` job.

Do **not** use `pull_request_target` to check out or execute a Codex-authored fork pull request with base-repository secrets or a write token. GitHub documents this as a privileged context; checking out and running untrusted PR code in it creates a pwn-request risk.[3]

## Revalidate on Codex updates

| Change | Required action |
| --- | --- |
| Codex changes Hook event/config documentation | Re-run `python -m pytest tests/test_codex_hook.py` and review the official schema before claiming compatibility. |
| Changing `Stop.py` | Run the targeted test, then the project quality gate before merging. |
| Moving from local hook to CI Codex Action | Treat API-key scope, actor restrictions, prompt injection resistance and permission separation as a new security review. |
| Adding Windows support | Validate `commandWindows` with a real Windows Codex environment and add a platform-specific regression before advertising it. |

## References

[1]: https://developers.openai.com/codex/hooks "OpenAI Codex Hooks"
[2]: https://developers.openai.com/codex/github-action "OpenAI Codex GitHub Action"
[3]: https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target "GitHub: Securely using pull_request_target"
