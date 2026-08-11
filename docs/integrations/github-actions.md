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
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
      # Adapt this step so every command in .patchwitness.toml is available.
      - name: Install project test dependencies
        run: python -m pip install -e ".[test]"
      - uses: pangxueyuan2-creator/patchwitness@v0.1.0
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

For SARIF upload, run the CLI directly and give `security-events: write` only to that job. Do not use
`pull_request_target` to execute untrusted PR code with repository secrets.

## Base policy requirement

`--policy-ref` must point to an immutable trusted SHA and the contract must already exist in that
commit. A new task contract introduced by the PR cannot be authoritative until reviewed and merged.
