# Real Adoption Report

**Report timestamp:** 2026-08-13T09:30:00Z
**Repository revision assessed:** [`4c62b50af201ff09583e319439066912560d96c7`](https://github.com/pangxueyuan2-creator/patchwitness/commit/4c62b50af201ff09583e319439066912560d96c7)
**Decision:** **NOT READY TO APPLY** for OpenAI Codex for Open Source.

This report uses the evidence definitions in [the adoption baseline](baseline.md). It does not treat maintainer commits, generated examples, raw downloads, aggregate traffic, marketplace availability, directories, crawlers, maintainer-authored posts or a public Issue as external use.

## Executive conclusion

PatchWitness is safer, more release-ready, and more usable in agent/CI workflows than at the previous snapshot. It has a fixture-verified Codex adapter, a trusted-release pipeline, an explicit contribution path and one bounded public contribution request. It has **not** obtained a verified non-maintainer Demo run, external Trial Report, external repository integration, external human contribution, external human PR or independent recommendation.

The highest-value next outcome is not more product construction. It is one real maintainer or developer choosing to run the public trial path and leaving an honest, permissioned report.

| Readiness dimension | Current score | Evidence-based assessment |
| --- | ---:| --- |
| Meaningful usage | 0/10 | No verified external Demo, repository run, Trial Report, integration or dependent. |
| Broad adoption | 0/10 | One raw star and subscriber belong to the maintainer; zero forks and zero external human contributors. |
| Ecosystem importance | 2/10 | The project addresses a concrete agent-patch verification boundary and now has fixture-verified Codex plus Cline/Copilot/Claude integration assets, but no external project depends on them. |
| Active maintenance | 6/10 | Security fix, release hardening, integration fixture, CI/CodeQL and contribution maintenance are present; sustained time-based maintenance is not yet demonstrated. |
| Maintainer evidence | 6/10 | The owner merged reviewed changes, runs quality/release controls and opened one real contribution task; no external human triage or PR review cycle exists yet. |
| Technical quality | 8/10 | Cross-platform CI, CodeQL, strict checks, trusted-base policy, clean-room support, reproducible Demo, change-risk scenarios and release validation are present. This does not imply adoption. |
| External validation | 1/10 | One distinct public technical comment is feedback, not a trial, testimonial, endorsement or adoption. [1] |

## Completed repository work

| Work item | Verifiable result | Classification |
| --- | --- | --- |
| Symlink trust-boundary fix | Change Passport hashing and secret scanning reject untracked symlinks that resolve outside the repository; regression test added. | `OWNER_GENERATED` security improvement |
| Trusted release pipeline | Tag workflow runs tests, Ruff, mypy, Demo, benchmark, build, Twine, clean install, SHA-256, provenance and optional OIDC PyPI publication with separate least-privilege job. | `OWNER_GENERATED` release hardening |
| Codex integration | Public `Stop` hook adapter and `tests/test_codex_hook.py` verify a trusted-base structural Passport, `PW003`, input minimization and offline evidence integrity. | `OWNER_GENERATED` fixture-verified integration |
| GitHub Action productization | Minimal, recommended and strict templates document full-SHA pins, least privilege, artifact handling and fork-PR / `pull_request_target` boundary. | `OWNER_GENERATED` integration UX |
| Contribution path | [CONTRIBUTING.md](../../CONTRIBUTING.md) provides clone, dev install, tests, Ruff, mypy, Demo, benchmark, fixture, documentation, security and PR steps. | `OWNER_GENERATED` onboarding |
| Real contribution task | [Issue #9](https://github.com/pangxueyuan2-creator/patchwitness/issues/9) validates the untested Windows Copilot CLI PowerShell path with sanitized evidence. | `OWNER_GENERATED` contribution opportunity; not a contribution |
| Quality validation | `make release-check` passed: 56 tests, coverage, Ruff, mypy, Demo, five-scenario benchmark, build, Twine and clean-wheel installation. Latest main CI and CodeQL passed. [2] [3] | `OWNER_GENERATED` quality evidence |

## Verified external evidence

| Evidence | Level | What it proves | What it does not prove |
| --- | ---:| --- | --- |
| [Public DEV technical comment][1] from a distinct public developer | External feedback only | An independent developer engaged with the self-reporting trust problem and asked where the gate belongs. | Demo run, installation, adoption, recommendation or endorsement. |
| Third-party discovery/index entries | None | The repository is discoverable. | Runtime use, workflow integration or validation. |

**Verified external adoption count:** 0.
**Verified external Trial Reports:** 0.
**Verified external integrations:** 0.
**Verified external human PRs:** 0.
**Verified external recommendations:** 0.

## Current raw signals and classification

| Signal at 2026-08-13 | Raw value | Classification | Treatment |
| --- | ---:| --- | --- |
| Stars / forks / subscribers | 1 / 0 / 1 | Maintainer-owned or absent | Excluded from external adoption. |
| Published GitHub Releases | 3 (`v0.1.0`, `v0.1.1`, `v0.2.0`) | Distribution surface | Not a user count. |
| Release asset downloads | 14 total raw downloads | `UNKNOWN` | GitHub does not disclose downloader identity; excluded. |
| Human contributors | 1 maintainer; 0 external | `OWNER_GENERATED` | Dependabot excluded. |
| Public Issues | 1, Issue #9 | Maintainer-created opportunity | Not a user signal. |
| External code search | 2 raw matches | Discovery/indexing signal | No verified external Action or CLI integration. |
| PyPI project | JSON and simple endpoints return 404 | Not published | No registry downloads can be counted. |
| Show HN submission | 0 stories created | Platform restriction | The account was redirected to HN's temporary Show HN limitation page; no retry was made. |

## External-action boundary

The maintainer explicitly authorized one Show HN submission. The approved title and text were entered and the submit control was used, but Hacker News redirected to its temporary Show HN restriction page. No public story exists, no alternate community post was substituted, and no retry occurred. This is an account/platform eligibility outcome, not a product failure and not external adoption evidence.

No third-party repository outreach was attempted. The project will not manufacture traction through unsolicited marketing, self-authored claims or low-value issues.

## Next highest-value action

Do not add non-essential engineering features. Wait for a real, independently chosen trial or for a contributor to act on Issue #9; respond with prompt, evidence-based triage when that occurs. If a later public action becomes appropriate, recheck that venue's rules and request a fresh immediate confirmation for the exact content and account action.

## References

[1]: https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j "External technical feedback on DEV"
[2]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834028 "Latest PatchWitness CI"
[3]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834026 "Latest PatchWitness CodeQL"
