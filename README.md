# PatchWitness

> Independent evidence and policy gates for AI-generated code changes.

PatchWitness turns a repository change into a deterministic, integrity-checked **Change Passport**.
It verifies scope, protected control-plane files, change budgets, dependency surfaces, and commands
that were actually executed. The core is local-first, model-agnostic, and has zero runtime
dependencies.

```console
$ patchwitness gate --base origin/main
PatchWitness PASS
  4 files · 126 lines · 2/2 checks
  Evidence: .patchwitness/evidence/20260811T080000Z.json
  SHA-256:  9e3b...1a7c
```

The full launch documentation is being completed as part of the first public release.

## Quick start

```bash
pip install patchwitness
patchwitness init
patchwitness gate --base HEAD
```

## Why

AI coding agents can summarize their own work, but self-reported claims are not independent
evidence. PatchWitness derives its result from Git, a repository-owned contract, and real process
exit codes, then seals the normalized facts into an offline-verifiable JSON evidence pack.

## License

Apache-2.0

