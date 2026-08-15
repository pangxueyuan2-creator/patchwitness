# Project status

**Current release:** v0.2.x public alpha  
**Evidence schema:** v1  
**Maintainer:** single primary maintainer  
**Production use:** none claimed yet

## What works now

- Local and CI policy gates over Git changes
- Zero-config scan with local project detection
- Policy loaded from a trusted base commit
- Real test execution + clean-room worktrees
- Basic dependency impact (Python / JS / TS)
- JSON evidence, SARIF, SDK, MCP, GitHub Action

## Known limitations

- Clean-room is filesystem isolation, not a real sandbox
- Dependency graph is conservative, not full type-aware
- A green passport only proves the recorded checks ran and the scope rules held
- No PyPI package yet
- No external production users yet

## Release bar

Tests, Ruff, mypy, package build, and the tool's own gate must pass before a release.
