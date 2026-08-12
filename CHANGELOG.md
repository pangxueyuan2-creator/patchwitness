# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). PatchWitness
uses semantic versioning once the v1 compatibility contract is reached.

## [Unreleased]

### Added

- Added a Cline `TaskComplete.py` integration that captures a structural Change Passport after a
  successful agent turn without retaining prompt, model output, or user identity fields.
- Added a subprocess compatibility test pinned to Cline's current `AgentEndHookPayload` contract and
  a setup guide that separates post-task evidence capture from CI merge enforcement.

### Planned

- Community feedback from the first public releases.

## [0.2.0] - 2026-08-11

### Added

- Added `patchwitness scan`, a zero-configuration path that selects the working tree or latest commit,
  detects repository-owned checks, runs them, and writes a real Change Passport.
- Added deterministic local project detection for Python, Node.js, Go, Rust, .NET, Maven, Ruby,
  PHP, and Make-based projects without network requests or LLM inference.
- Added `init --check`, `init --no-detect`, and richer machine-readable detection output.

### Changed

- `patchwitness init` now generates checks from detected repository conventions instead of assuming
  every project uses pytest; when no safe check is found, it creates an honest structural-only policy.
- `patchwitness doctor` now reports ecosystems, detected commands, missing executables, contract state,
  and a recommended next command.
- Check execution prefers a repository-local `.venv`, making isolated `pipx` and `uv tool`
  installations work naturally with project test dependencies.
- Human-readable results now label dependency severity as `Impact` and explain that high impact raises
  review priority rather than automatically failing policy.

### Security

- Smart detection remains read-only and does not execute project code to select commands. Detected
  checks do execute repository code; the CLI and documentation direct users of untrusted repositories
  to inspect with `doctor` or run `scan --no-checks` first.

### Compatibility

- Evidence schema remains `patchwitness.dev/evidence/v1`.
- No runtime dependencies were added, and existing contracts, commands, SDK calls, MCP tools, and
  reports remain compatible.

## [0.1.1] - 2026-08-11

### Security

- Pinned every third-party GitHub Action to an immutable commit and disabled persisted checkout
  credentials in read-only jobs.
- Added release tag/version validation and GitHub build-provenance attestations for release assets.
- Added a pull-request dependency review gate and moved Action update checks to a weekly cadence.
- Enabled repository dependency alerts, automated security fixes, and default-branch protection
  against deletion and non-fast-forward pushes.
- Added preventive ignores for common local credentials and signing keys, plus repository security
  regression tests that enforce workflow permissions and immutable Action references.

### Changed

- Added a measured acknowledgement of OpenAI, ChatGPT, and Codex to the project and launch
  documentation, while retaining an explicit no-affiliation disclaimer.
- Reworked the README conversion path around a real one-minute risk demo, simpler try-first flow,
  visual terminal output, and a concise FAQ.
- Added a five-minute trusted-base adoption path, explicit project-dependency setup for the GitHub
  Action, and a runnable examples index.

### Added

- Reproducible coding-agent risk demo with a committed terminal transcript and Change Passport.
- 1280x640 social-preview artwork and an end-to-end demo integration test.
- Source-linked OSS readiness scorecard and an explicit maintainer workflow for honest long-term
  triage, review, releases, security response, and evidence updates.

## [0.1.0] - 2026-08-11

### Added

- Deterministic Git change collection with before/after SHA-256.
- TOML policy contracts for paths, budgets, binaries, dependencies, and required checks.
- Trusted-revision policy loading to prevent self-weakened PR gates.
- Concurrent checks and disposable clean-room Git worktrees with hooks disabled.
- Python/JavaScript/TypeScript dependency blast radius with persistent cache.
- High-confidence, value-free secret findings and command-output redaction.
- Canonical Change Passport JSON with offline integrity verification.
- Markdown, SARIF, GitHub annotation, and JSON reporters.
- Typed Python SDK, analyzer entry points, and stdio MCP tools.
- Cross-platform CLI, Docker image, composite GitHub Action, CI, tests, and real benchmark harness.

[Unreleased]: https://github.com/pangxueyuan2-creator/patchwitness/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pangxueyuan2-creator/patchwitness/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/pangxueyuan2-creator/patchwitness/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.1.0
