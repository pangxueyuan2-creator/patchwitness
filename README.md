<p align="center">
  <img src="docs/assets/banner.svg" alt="PatchWitness - proof before merge" width="100%" />
</p>

<p align="center">
  <strong>Independent evidence and policy gates for AI-generated code changes.</strong>
</p>

<p align="center">
  <a href="https://github.com/pangxueyuan2-creator/patchwitness/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/pangxueyuan2-creator/patchwitness/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/pangxueyuan2-creator/patchwitness/releases"><img alt="Release" src="https://img.shields.io/github/v/release/pangxueyuan2-creator/patchwitness"></a>
  <a href="https://github.com/marketplace/actions/patchwitness-gate"><img alt="GitHub Marketplace" src="https://img.shields.io/badge/GitHub_Marketplace-PatchWitness_Gate-2f81f7?logo=github"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11--3.14-3776AB">
  <img alt="Runtime dependencies" src="https://img.shields.io/badge/runtime_dependencies-0-2ea44f">
</p>

AI coding agents can write a patch in minutes. Reviewers still have to figure out whether the agent stayed in scope, whether it touched CI or its own verifier, and whether the claimed tests actually ran.

**PatchWitness turns a change into a verifiable Change Passport.**  
It reads Git facts, loads policy from a trusted base commit, runs the repository's own checks, looks at dependency impact, and produces an offline-verifiable evidence pack. No model is asked to judge its own work.

It is a local-first trust gate, not another AI code reviewer.

## 60-second demo

The demo shows a common failure mode: the agent adds a correct feature and a passing test, but also weakens a protected CI workflow. Tests pass. PatchWitness still blocks the change.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

No package installation required. See the [demo README](demo/README.md) and the committed [terminal transcript](demo/artifacts/terminal-output.txt).

## Quick start

Structural scan (no repository code execution):

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
patchwitness doctor          # see what it detected
patchwitness scan            # full scan (will run tests)
patchwitness scan --no-checks # structural only
```

`scan` looks at the working tree vs `HEAD` (or the latest commit if the tree is clean). Use `--base origin/main` when you want an explicit boundary.

## Core idea

| Question | How PatchWitness answers |
|---|---|
| Did the change stay in scope? | Path contract against the real Git diff |
| Did it touch CI / the verifier? | Protected rules loaded from the trusted base |
| Did the tests actually run? | Real process exit code + duration + redacted output hash |
| What else might break? | Local reverse dependency graph |
| Can I trust the report later? | Canonical JSON + SHA-256 |

A green Change Passport does **not** mean the code is correct. It only means the recorded scope, policy, checks, and integrity claims hold.

## Making a trusted policy

```bash
patchwitness init
# review the generated .patchwitness.toml
git add .patchwitness.toml .gitignore
git commit -m "chore: add PatchWitness policy"
```

Then enforce against that trusted base:

```bash
patchwitness gate --base origin/main --policy-ref origin/main --clean-room
```

In CI you can use the [Marketplace Action](https://github.com/marketplace/actions/patchwitness-gate).

## Commands

```text
patchwitness scan              Zero-config first look
patchwitness init              Create a starter contract
patchwitness gate ...          Enforce and fail closed
patchwitness verify <file>     Offline integrity check
patchwitness impact --base HEAD
patchwitness doctor
patchwitness mcp --root .
```

Exit codes: `0` pass, `1` gate failure, `2` usage/runtime error.

## Current status

Public alpha (v0.2.x). Evidence schema v1 is stable.  
Single maintainer. No production adoption claims yet.

Known limitations are documented in [PROJECT_STATUS.md](PROJECT_STATUS.md) and the [threat model](docs/threat-model.md). The important ones:

- Clean-room is filesystem isolation, not a security sandbox
- Dependency graph is conservative, not full compiler-level
- A passing check only proves the command ran and exited successfully

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports go to [SECURITY.md](SECURITY.md).

Licensed under [Apache-2.0](LICENSE).
