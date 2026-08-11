# Security policy

## Supported versions

| Version | Security fixes |
|---|---|
| 0.1.x | Yes |
| Older / unreleased snapshots | No |

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not include tokens,
credentials, private source code, or exploit details in a public issue.

Include:

- affected version and operating system;
- minimal reproduction;
- impact and trust boundary crossed;
- whether a malicious repository, contract, plugin, or evidence pack is required;
- suggested mitigation if known.

Maintainers will acknowledge a complete report within 5 business days, investigate privately, and
coordinate disclosure after a fix is available. This is a response target, not a bounty promise.

## Repository and release hardening

- Workflows declare explicit minimum permissions, never use `pull_request_target`, and do not pass
  repository secrets to code from pull requests.
- Third-party Actions are pinned to immutable commit SHAs. Checkout credentials are discarded in
  every job that only reads the repository.
- Release tags must match the package version, and release assets receive GitHub build-provenance
  attestations before upload.
- Pull requests that introduce dependencies with known moderate-or-higher vulnerabilities are
  rejected by GitHub's dependency review gate.
- The active default-branch ruleset blocks branch deletion and non-fast-forward pushes without
  forcing a pull-request-only workflow on the single maintainer.
- GitHub secret scanning and push protection complement value-free secret detection in the CLI.
- Common local credential and signing-key files are ignored, but `.gitignore` is not a secret
  manager. Store credentials in the operating-system keychain or CI secret store and rotate any
  value that was ever committed.

Repository regression tests enforce these invariants. Review every Dependabot Action update before
merging because the human-readable version comment does not change the pinned commit's trust model.

## Security boundaries

PatchWitness executes commands explicitly defined by a repository contract. Treat contracts and
plugins as code. `--policy-ref` protects policy integrity only when the referenced Git commit is
trusted.

Clean-room mode disables Git hooks while creating a disposable worktree, but it is **not** a kernel,
container, VM, or network sandbox. A malicious test command still has the permissions of the user or
CI runner. Use an isolated runner/container for untrusted repositories.

Evidence SHA-256 detects mutation; it does not authenticate who produced the evidence. Use your CI
identity, GitHub artifact attestations, Sigstore, or another external signer when provenance identity
is required.

Read the complete [threat model](docs/threat-model.md).
