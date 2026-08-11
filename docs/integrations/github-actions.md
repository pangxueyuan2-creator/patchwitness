# GitHub Actions integration

The repository is itself a composite action:

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
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7
        with:
          python-version: "3.13"
      # Adapt this step so every command in .patchwitness.toml is available.
      - name: Install project test dependencies
        run: python -m pip install -e ".[test]"
      - uses: pangxueyuan2-creator/patchwitness@v0.1.1
        with:
          base: ${{ github.event.pull_request.base.sha }}
          policy-ref: ${{ github.event.pull_request.base.sha }}
          contract: .patchwitness.toml
          clean-room: "true"
```

The action installs PatchWitness from its checked-out action path, runs the gate, writes evidence to
`.patchwitness/evidence/github.json`, and appends a Markdown Change Passport to the job summary.
It intentionally does not guess or install the target repository's dependencies: install every
tool referenced by `.patchwitness.toml` before the PatchWitness step.

The example pins transitive GitHub-maintained actions to immutable commits. For the strongest
supply-chain guarantee, replace the PatchWitness release tag with the full commit SHA you reviewed,
and keep the release tag as a comment for Dependabot readability.

For SARIF upload, run the CLI directly and give `security-events: write` only to that job. Do not use
`pull_request_target` to execute untrusted PR code with repository secrets.

## Base policy requirement

`--policy-ref` must point to an immutable trusted SHA and the contract must already exist in that
commit. A new task contract introduced by the PR cannot be authoritative until reviewed and merged.
