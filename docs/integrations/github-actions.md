# GitHub Actions integration

[PatchWitness Gate is published on GitHub Marketplace](https://github.com/marketplace/actions/patchwitness-gate) under the `security` and `code-review` categories. The Action generates a Change Passport, appends a Markdown summary to the workflow run, and returns a non-zero exit code when the committed policy or required checks fail. Use it as the **independent CI half** of a two-stage workflow: local/agent capture gives fast feedback, while this job is the branch-protection merge boundary.

| Profile | Choose it when | What it enforces |
| --- | --- | --- |
| Minimal | You want the safest first rollout and your contract has no executable checks. | Trusted-base structural policy, protected-path and secret scanning. |
| Recommended | You have reviewed a contract and normal project tests. | Trusted-base policy plus declared checks in a disposable hook-disabled worktree. |
| Strict | You need a separately auditable evidence artifact and stronger failure visibility. | Recommended enforcement plus retained JSON evidence and explicit required-check guidance. |

Every profile uses `pull_request`, read-only `contents` permission, full history, `persist-credentials: false`, and the pull request's immutable **base SHA** for both the comparison base and authoritative policy source. Replace the Action reference with the reviewed commit SHA for each upgrade; the current published v0.2.0 reference is `f95f84dbb35ce0e7d153e83503294d742275f3c5`.

> A Change Passport is review evidence, not a semantic-correctness proof. It records the policy, real command outcomes, changed paths and integrity data that the job observed. Protect the branch, policy and workflow separately with review rules and CODEOWNERS.

## 1. Minimal: structural policy rollout

Use a committed `.patchwitness.toml` whose policy either has `require_tests = false` or declares no required checks. This is appropriate for a safe first trial or a repository where CI has a separate testing workflow.

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
      - uses: pangxueyuan2-creator/patchwitness@f95f84dbb35ce0e7d153e83503294d742275f3c5 # v0.2.0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          policy-ref: ${{ github.event.pull_request.base.sha }}
          contract: .patchwitness.toml
          clean-room: "true"
```

## 2. Recommended: required CI policy and checks

Install every dependency used by the **committed base contract** before calling PatchWitness. The Action does not guess or install a target repository's test dependencies, so use that repository's own documented setup command; do **not** treat `.[test]` as a universal extra. For PatchWitness itself, the real development dependency path is `python -m pip install --disable-pip-version-check -e ".[dev]"`. `clean-room: "true"` executes checks in a disposable base-derived Git worktree with repository hooks disabled during materialization.

```yaml
name: PatchWitness
on:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    name: PatchWitness / gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7
        with:
          python-version: "3.13"
      # Add the target repository's own documented dependency-install step here.
      # Example for PatchWitness itself: python -m pip install --disable-pip-version-check -e ".[dev]"
      - uses: pangxueyuan2-creator/patchwitness@f95f84dbb35ce0e7d153e83503294d742275f3c5 # v0.2.0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          policy-ref: ${{ github.event.pull_request.base.sha }}
          contract: .patchwitness.toml
          clean-room: "true"
```

Make the resulting job required in branch protection only after it succeeds for trusted internal and fork pull requests. Keep policy/workflow changes protected by owners with authority to approve control-plane changes; PatchWitness reports those changes but does not decide who may approve them.

## 3. Strict: retained evidence and explicit review workflow

Use this profile when reviewers or downstream tools need the raw JSON Passport after a failure. The upload step uses `if: always()` so the evidence remains available whether the gate passes or fails. Do not add write permissions or secrets to this pull-request job.

```yaml
name: PatchWitness
on:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    name: PatchWitness / gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7
        with:
          python-version: "3.13"
      # Add the target repository's own documented dependency-install step here.
      # Example for PatchWitness itself: python -m pip install --disable-pip-version-check -e ".[dev]"
      - name: Enforce trusted-base contract
        id: patchwitness
        uses: pangxueyuan2-creator/patchwitness@f95f84dbb35ce0e7d153e83503294d742275f3c5 # v0.2.0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          policy-ref: ${{ github.event.pull_request.base.sha }}
          contract: .patchwitness.toml
          clean-room: "true"
      - name: Retain Change Passport
        if: always()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7
        with:
          name: patchwitness-passport-${{ github.event.pull_request.number }}
          path: .patchwitness/evidence/github.json
          if-no-files-found: error
          retention-days: 14
```

Treat the artifact as review evidence, not a credential container. PatchWitness redacts command output and avoids recording secret values, but repositories should still configure artifact retention and reviewer access according to their own data policy.

## Fork PRs, permissions and privileged events

Use `pull_request` for this gate. On a fork pull request, GitHub restricts `GITHUB_TOKEN` to read-only access, withholds secrets, and may require maintainer approval before the workflow runs.[1] This is the desired boundary for a job that checks out and runs untrusted change code.

Do **not** switch this workflow to `pull_request_target` merely to access secrets, post comments, or make the gate required. That event runs in the base repository's privileged context. If it checks out and executes fork code—directly or through a dependency install, test command, Makefile, artifact or Git fetch—it creates a pwn-request route to repository secrets and write tokens.[2]

If you need privileged automation, split it from the untrusted-code job. Keep the gate on `pull_request` with no secrets and no write permissions. A separate trusted workflow may process only reviewed, non-executable data and should use a narrowly scoped token. GitHub recommends least-privilege `GITHUB_TOKEN` permissions and immutable full-SHA Action pins.[3]

## Contract and base-policy rules

`policy-ref` must resolve to the PR base SHA and the contract must already exist at that revision. A task contract introduced or weakened by the pull request cannot be authoritative until a human reviews and merges it first.

For SARIF upload, run the CLI directly and grant `security-events: write` only to that dedicated job. Do not combine SARIF upload, repository write access, secrets and untrusted PR code in one job. The minimal-safe starting point is the first template above; advance profiles only after validating the commands and review process that the repository really needs.

## References

[1]: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks "GitHub: Approving workflow runs from forks"
[2]: https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target "GitHub: Securely using pull_request_target"
[3]: https://docs.github.com/en/actions/reference/security/secure-use "GitHub: Secure use reference"
