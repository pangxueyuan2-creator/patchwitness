# Roadmap

The roadmap prioritizes trustworthy evidence over feature count. Dates are intentionally not
promised before maintainer capacity and community demand are known.

## v0.2 - Interoperability

- Evidence schema conformance fixtures and a standalone verifier specification.
- Native adapters for major coding-agent transcript/hook formats.
- In-toto/SLSA statement envelope and optional Sigstore signing guidance.
- Language analyzers for Go, Rust, and Java behind plugins.
- Contract inheritance with explicit, reviewable merge semantics.

## v0.3 - Review intelligence

- Diff-to-contract coverage signals without an LLM dependency.
- Changed-symbol impact adapters using tree-sitter plugins.
- Test selection providers with confidence and fallback behavior.
- Evidence diffing across agent reruns and model/provider changes.

## v0.4 - Organization scale

- Organization policy bundles pinned by digest.
- Remote evidence stores through an adapter interface.
- OPA/CEL bridge plugins without coupling the core to one policy language.
- Signed plugin metadata and compatibility checks.

## v1.0 - Stable trust contract

- Stable CLI and SDK compatibility guarantees.
- Evidence schema v1 conformance suite across Windows, Linux, and macOS.
- Independent security review of clean-room materialization and parsing surfaces.
- Documented migration and deprecation policy.
- Proven adoption in real repositories and a maintainer group larger than one person.

## Explicit non-goals

- Replacing human review with an LLM score.
- Running a hosted source-code collection service in the core project.
- Claiming process isolation without a real OS/container/VM sandbox.
- Detecting whether code was written by AI.

