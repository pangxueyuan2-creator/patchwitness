# Real Adoption Report

**Report timestamp:** 2026-08-13T11:55:00Z
**Release surface assessed:** [`v0.2.1`](https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.2.1), published 2026-08-13T10:57:36Z
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
| Published GitHub Releases | 4 (`v0.1.0`, `v0.1.1`, `v0.2.0`, `v0.2.1`) | Distribution surface | Not a user count. |
| Latest public wheel | `patchwitness-0.2.1-py3-none-any.whl`, public HTTP 200; its three raw downloads are not attributable | Distribution surface | Does not show who installed or ran PatchWitness. |
| Release asset downloads | 29 total raw downloads across all release assets | `UNKNOWN` | GitHub does not disclose downloader identity, version usage or command execution; excluded. |
| Human contributors | 1 maintainer; 0 external | `OWNER_GENERATED` | Dependabot excluded. |
| Public Issues | 1, Issue #9 | Maintainer-created opportunity | Not a user signal. |
| External code search | 2 raw matches | Discovery/indexing signal | No verified external Action or CLI integration. |
| PyPI project | JSON and simple endpoints return 404 | Not published | No registry downloads can be counted. |
| Show HN submission | 0 stories created | Platform restriction | The account was redirected to HN's temporary Show HN limitation page; no retry was made. |
| r/ClaudeAI technical reply | [Comment `p3ewuta`][4] is publicly reachable, authored by the maintainer account and timestamped 2026-08-13 | `OWNER-GENERATED / MAINTAINER PUBLIC ACTIVITY` | The public record is not an External Trial, Integration, Recommendation or Adoption. Reddit’s dynamic rendering exposed a blank automated body at capture time, so body equality is `UNKNOWN`; no non-maintainer reply was visible. |
| r/ClaudeAI v0.2.1 trial reply | [Comment `p3fd4f4`][5] is publicly visible in a six-day-old autonomous-workflow discussion, authored by the maintainer account with its full disclosure, scope boundary and v0.2.1 release link rendered publicly | `OWNER-GENERATED / MAINTAINER PUBLIC ACTIVITY` | A real installation, `doctor`/`scan --no-checks` run, result, feedback, independent actor or trial permission. Its displayed view count is raw telemetry and excluded. |

## External-action boundary

The maintainer explicitly authorized one Show HN submission. The approved title and text were entered and the submit control was used, but Hacker News redirected to its temporary Show HN restriction page. No public story exists, no alternate community post was substituted, and no retry occurred. This is an account/platform eligibility outcome, not a product failure and not external adoption evidence.

No third-party repository outreach was attempted. On 2026-08-13, the maintainer published two disclosed, context-specific r/ClaudeAI replies after thread/rule checks: one about independently verifying unattended coding-agent runs,[4] and one about fixed stopping conditions for autonomous workflows with a public v0.2.1 trial path.[5] Both are classified only as `OWNER-GENERATED / MAINTAINER PUBLIC ACTIVITY`. The first reply's body was unavailable to automated rendering; the second reply's full body was publicly rendered. No non-maintainer response, actual run or trial permission was visible at the initial checks. No repeat comment, upvote request, cross-post or follow-up outreach is planned.

The project will not manufacture traction through unsolicited marketing, self-authored claims or low-value issues.

## Next highest-value action

Do not add non-essential engineering features or expand outreach. Monitor only for a real, independently chosen v0.2.1 trial, integration, Trial Report, external Issue/PR/contribution, or a non-maintainer reply to the published r/ClaudeAI comments. If a distinct non-maintainer explicitly offers a trial, immediately provide the shortest no-credential path and collect only actor/profile, date, version, installation method, actual commands/result, first-use feedback and explicit permissions. A public reply may be used only if directly relevant, rule-checked and within the task's five-thread limit; direct messages, email and third-party GitHub Issue/PR actions require a fresh maintainer confirmation.

## References

[1]: https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j "External technical feedback on DEV"
[2]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834028 "Latest PatchWitness CI"
[3]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834026 "Latest PatchWitness CodeQL"
[4]: https://www.reddit.com/r/ClaudeAI/comments/1udrmrb/comment/p3ewuta/ "Maintainer-disclosed r/ClaudeAI technical reply"
[5]: https://www.reddit.com/r/ClaudeAI/comments/1vhy33b/comment/p3fd4f4/ "Maintainer-disclosed v0.2.1 trial-path reply"
