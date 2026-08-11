# One-minute risk demo

This demo creates a disposable Git repository and simulates a coding-agent patch with two parts:

1. a correct `discount()` feature with a passing unit test; and
2. a GitHub Actions edit that makes CI failures non-blocking.

The repository tests pass. PatchWitness still blocks the patch because the workflow is outside the
approved task scope and is a protected control-plane surface in the contract loaded from the trusted
base commit.

## Run it

Requirements: Git and Python 3.11 or newer. PatchWitness has no runtime dependencies.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

The command writes a fresh passport to `demo/output/change-passport.json`. Verify it independently:

```bash
PYTHONPATH=src python -m patchwitness verify demo/output/change-passport.json
```

PowerShell equivalent:

```powershell
$env:PYTHONPATH = "src"
python -m patchwitness verify demo/output/change-passport.json
```

## Expected result

- `2` repository tests pass.
- PatchWitness runs the contract's required test check: `1/1 checks`.
- `PW002` reports that `.github/workflows/ci.yml` is outside the approved task scope.
- `PW003` reports that the patch changed a protected verification/control-plane file.
- The generated Change Passport passes offline SHA-256 integrity verification.

The committed [terminal transcript](artifacts/terminal-output.txt) and
[Change Passport](artifacts/risk-change-passport.json) were produced by running this script with
`--record`. Only machine-specific filesystem paths are normalized in the transcript; status, counts,
findings, and evidence hash come from the real run.

## Why this case matters

An agent can truthfully say “the tests pass” while changing whether those tests are allowed to block
a merge. PatchWitness does not ask another model whether the patch looks safe. It derives the change
set from Git, loads policy from the trusted base revision, executes the repository-owned check, and
emits a portable evidence record for humans and automation.
