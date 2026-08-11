# Project status

**Current release:** v0.1.1 public alpha
**Evidence schema:** v1  
**Maintainer status:** new project, single primary maintainer  
**Production claim:** no broad production adoption claimed

## Ready now

- Local and CI policy gates over Git changes.
- Base-authoritative contracts.
- Real check execution, clean-room worktrees, and evidence verification.
- Python/JS/TS file dependency impact.
- SDK, MCP, analyzer plugins, JSON, SARIF, Markdown, and GitHub annotations.
- Automated tests on Python 3.11-3.14 and the three major desktop OS families.
- Dockerfile with build/run smoke validation in GitHub CI (not locally validated on the initial
  maintainer machine because Docker is not installed there).

## Known limitations

- Clean-room mode is filesystem isolation, not an OS security sandbox.
- The dependency graph uses conservative import resolution rather than full compiler semantics.
- SHA-256 integrity is not identity authentication or non-repudiation.
- Required checks prove command execution and exit status, not semantic completeness.
- Plugins run in-process and must be treated as trusted code.
- No PyPI publication, hosted service, telemetry, or remote evidence store exists at launch.

## Release bar

Every release must pass tests, Ruff, strict mypy, package build, CLI smoke tests, and PatchWitness's
own trusted-base clean-room gate. Release artifacts receive GitHub build-provenance attestations,
and the release workflow rejects tags that do not match the packaged version. Performance claims
must come from committed raw benchmark output.

## Adoption status

At initial publication there are no legitimate claims of stars, forks, external contributors,
downloads, dependents, testimonials, or production users. Those metrics will only be added when
GitHub/package/community sources show real activity. See the dated, source-linked
[OSS readiness scorecard](OSS_READINESS.md).
