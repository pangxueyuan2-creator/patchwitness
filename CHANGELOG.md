# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). PatchWitness
uses semantic versioning once the v1 compatibility contract is reached.

## [Unreleased]

### Changed

- Added a measured acknowledgement of OpenAI, ChatGPT, and Codex to the project and launch
  documentation, while retaining an explicit no-affiliation disclaimer.

### Planned

- Community feedback from the first public release.

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

[Unreleased]: https://github.com/pangxueyuan2-creator/patchwitness/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.1.0
