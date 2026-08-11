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

