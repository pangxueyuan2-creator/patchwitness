# Threat model

## Assets

- integrity of repository policy and required checks;
- reviewer confidence in what changed and what executed;
- confidentiality of source, credentials, and command output;
- availability of CI and local developer environments;
- integrity and portability of the Change Passport.

## Adversaries

1. A coding agent that unintentionally expands scope or optimizes for a green result.
2. A malicious pull request that changes CI, tests, policy, dependencies, or generated binaries.
3. A malicious repository with Git hooks, commands, symlinks, or expensive files.
4. A tampered evidence artifact.
5. A malicious explicitly installed analyzer plugin.

## Controls

| Threat | Control |
|---|---|
| PR weakens its own policy | Load contract from trusted base with `--policy-ref` |
| PR edits verifier/CI | `protected_paths` and deny-wins policy |
| Agent claims tests ran | PatchWitness executes commands and records exit/timing/output hash |
| Git hook executes during verification setup | Clean-room materialization sets an empty hooks path |
| Untracked symlink redirects verifier | Clean-room rejects untracked symlinks |
| Secret copied into evidence | Value-free findings and output redaction |
| Evidence modified later | Canonical payload SHA-256 and offline verify |
| Plugin failure is hidden | Explicit namespaced `{ok:false,error}` extension result |
| Resource exhaustion | File size limits, command timeouts, bounded workers, finite graph depth |

## Residual risk

- Repository check commands execute with the caller's OS privileges. Use containers, VMs, or
  isolated CI runners for untrusted code.
- A trusted base contract can itself be unsafe or incomplete.
- An agent can write a logically wrong patch that obeys scope and passes tests.
- SHA-256 without an external signature does not prove producer identity.
- Import regexes do not model dynamic imports, reflection, build systems, or runtime data flows.
- In-process plugins can read or mutate the process; only install trusted plugins.
- Redaction is defense in depth, not a guarantee against every novel secret format.

## Recommended high-assurance deployment

1. Pin PatchWitness by release digest in an ephemeral CI runner.
2. Fetch the pull request and immutable base SHA.
3. Load `.patchwitness.toml` from that base SHA.
4. Protect CI, policy, test harness, release, and dependency surfaces.
5. Run `--clean-room` inside a network-restricted container/VM.
6. Upload evidence and SARIF as artifacts.
7. Bind evidence to CI identity using an artifact attestation.
8. Require a human reviewer for high/critical impact even when the gate passes.

