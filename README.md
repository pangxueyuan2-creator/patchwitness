<p align="center">
  <img src="docs/assets/banner.svg" alt="PatchWitness" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/pangxueyuan2-creator/patchwitness/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/pangxueyuan2-creator/patchwitness/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/pangxueyuan2-creator/patchwitness/releases"><img alt="Release" src="https://img.shields.io/github/v/release/pangxueyuan2-creator/patchwitness"></a>
  <a href="https://github.com/marketplace/actions/patchwitness-gate"><img alt="GitHub Marketplace" src="https://img.shields.io/badge/GitHub_Marketplace-PatchWitness_Gate-2f81f7?logo=github"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11--3.14-3776AB">
  <img alt="Runtime dependencies" src="https://img.shields.io/badge/runtime_dependencies-0-2ea44f">
</p>

AI coding agents can spit out a patch in a few minutes.  
The hard part is still figuring out whether they stayed in scope, whether they touched CI or their own checks, and whether the tests they claim passed actually ran.

PatchWitness tries to answer those questions with real Git data and real process output instead of model claims.

It produces a **Change Passport** — a small evidence pack you can inspect and verify offline. No model is asked to grade its own work.

This is a local tool, not another AI reviewer.

## 60-second demo

The demo shows a common failure: the agent adds a correct feature and a passing test, but also weakens a protected CI workflow. Tests pass. PatchWitness still fails the change.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

No package install needed. See the [demo README](demo/README.md) and the committed [terminal transcript](demo/artifacts/terminal-output.txt).

## Quick start

Structural scan only (no code execution):

```bash
uvx --from "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.2/patchwitness-0.2.2-py3-none-any.whl" patchwitness scan --no-checks
```

Or install once:

```bash
pipx install "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.2/patchwitness-0.2.2-py3-none-any.whl"
# or
uv tool install "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.2/patchwitness-0.2.2-py3-none-any.whl"
```

Then inside any Git repo:

```bash
patchwitness doctor          # what it detected
patchwitness scan            # full scan (runs tests)
patchwitness scan --no-checks # structural only
```

`scan` compares the working tree against `HEAD` (or the latest commit if clean). Use `--base origin/main` when you want an explicit boundary.

## What it actually checks

| Question | How it answers |
|---|---|
| Did the change stay in scope? | Path rules against the real Git diff |
| Did it touch CI / the verifier itself? | Protected rules loaded from a trusted base commit |
| Did the tests really run? | Real process exit code + duration + redacted output hash |
| What else might break? | Local reverse dependency graph |
| Can I trust this report later? | Canonical JSON + SHA-256 |

A green passport does **not** mean the code is correct. It only means the recorded scope, policy, checks, and integrity claims hold.

## Setting up a policy

```bash
patchwitness init
# look at the generated .patchwitness.toml
git add .patchwitness.toml .gitignore
git commit -m "chore: add PatchWitness policy"
```

Then enforce against that base:

```bash
patchwitness gate --base origin/main --policy-ref origin/main --clean-room
```

In CI you can use the [Marketplace Action](https://github.com/marketplace/actions/patchwitness-gate).

## Commands

```text
patchwitness scan              first look, zero config
patchwitness init              write a starter contract
patchwitness gate ...          enforce and fail closed
patchwitness verify <file>     offline integrity check
patchwitness impact --base HEAD
patchwitness doctor
patchwitness mcp --root .
```

Exit codes: `0` pass, `1` gate failure, `2` usage/runtime error.

## Related tools

These answer different questions and do not depend on each other:

- [GuardSpec](https://github.com/pangxueyuan2-creator/guardspec) — before work starts, check the repository’s explicit agent rules against a proposed path or command
- [TaskToPR](https://github.com/pangxueyuan2-creator/tasktopr) — turn one Issue into an isolated branch, run real tests, leave evidence, optionally open a PR

Use any combination, or none of them.

## Status

Public alpha (v0.2.x). Evidence schema v1 is stable.  
Single maintainer. No production claims.

Limitations are listed in [PROJECT_STATUS.md](PROJECT_STATUS.md) and the [threat model](docs/threat-model.md). The important ones:

- Clean-room is filesystem isolation, not a real security sandbox
- Dependency graph is conservative, not full compiler-level analysis
- A passing check only proves the command ran and exited 0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports go to [SECURITY.md](SECURITY.md).

Apache-2.0.
