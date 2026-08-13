# Adoption Baseline

**Collection timestamp:** 2026-08-13T07:34:30Z
**Repository revision:** `765eef745af9e8a8ac66c659f546a681dfc8e614`
**Scope:** This document records observable public and owner-authorized GitHub data at collection time. It is a starting point for comparison, not a claim of user adoption.

## Classification rules

Only evidence with a public URL or a maintained raw API response is recorded. The labels below are mutually important: **OWNER_GENERATED** means the maintainer or owner account created the signal; **BOT_GENERATED** means automation created it; **EXTERNAL_VERIFIED** requires a distinct public person or repository and a specific, supportable claim; **UNKNOWN** means GitHub exposes an aggregate count but not a reliable actor or purpose.

> **No inference rule:** A clone, release download, Star, fork, view, crawler index, mirror, CI download, or social listing does not by itself prove that a non-maintainer installed, ran, adopted, recommended, or endorsed PatchWitness.

## GitHub repository and traffic snapshot

| Signal | Raw value | Classification | Interpretation boundary | Primary source |
|---|---:|---|---|---|
| Stars | 1 | OWNER_GENERATED | The sole stargazer is `pangxueyuan2-creator`; external verified Stars: 0. | [Stargazers API][1] |
| Forks | 0 | — | No fork exists in the repository API snapshot. | [Repository API][2] |
| Subscribing watchers | 1 | OWNER_GENERATED | The sole subscriber is `pangxueyuan2-creator`; external verified watchers: 0. | [Subscribers API][3] |
| Views, trailing 14 days | 51 | UNKNOWN | 10 unique visitors. Traffic is an aggregate, and GitHub does not expose visitor identity. | Owner-authorized Traffic API snapshot |
| Clones, trailing 14 days | 362 | UNKNOWN | 69 unique cloners. This may include repeated CLI fetches, Actions, mirrors, bots or manual clones. | Owner-authorized Traffic API snapshot |
| Referrer, trailing 14 days | `github.com`: 5 views / 1 unique | UNKNOWN | Other referral sources were not returned at collection. | Owner-authorized Traffic API snapshot |
| Popular content | Repository overview: 19 views / 6 uniques; release-management pages appear in top paths | OWNER_GENERATED / UNKNOWN | Release creation/edit pages may be maintainer activity and are not counted as discovery. | Owner-authorized Traffic API snapshot |
| GitHub Marketplace | Public listing available | Distribution surface, not adoption | Installability does not expose or prove external workflow use. | [PatchWitness Gate][4] |

## Releases and downloads

| Release asset | Raw downloads | Classification | Interpretation boundary |
|---|---:|---|---|
| `patchwitness-0.2.0-py3-none-any.whl` | 4 | UNKNOWN | GitHub does not identify downloaders. |
| `patchwitness-0.2.0.tar.gz` | 1 | UNKNOWN | Same limitation. |
| `patchwitness-0.1.1-py3-none-any.whl` | 1 | UNKNOWN | Same limitation. |
| `patchwitness-0.1.1.tar.gz` | 1 | UNKNOWN | Same limitation. |
| `patchwitness-0.1.0-py3-none-any.whl` | 6 | UNKNOWN | Same limitation. |
| `patchwitness-0.1.0.tar.gz` | 1 | UNKNOWN | Same limitation. |
| **Total release-asset downloads** | **14** | **UNKNOWN** | Includes no verified external-user count; maintainer validation and CI download attribution cannot be reliably separated. |

The public release list currently contains three releases. The project is not published on PyPI, so package-registry download data is not applicable at this snapshot.[5]

## Community, maintenance and external-use snapshot

| Signal | Raw value | Classification | Evidence / interpretation |
|---|---:|---|---|
| Open human Issues | 0 | — | No open Issues in GitHub search at collection. |
| Closed human Issues | 0 | — | No closed Issues in GitHub search at collection. |
| Open PRs | 0 | — | No open PRs in GitHub search at collection. |
| Closed / merged PRs | 4 / 4 | BOT_GENERATED | The merged PRs are Dependabot maintenance PRs, not external human contributions. |
| Contributors | 2 listed | OWNER_GENERATED + BOT_GENERATED | `pangxueyuan2-creator` and `dependabot[bot]`; external human contributors: 0. |
| External public code references | 2 | Not adoption | `Klausc06/ai-trends` is a metadata index and `lethanhson9901/repo-dashboard` indexes a community-news item; neither contains a PatchWitness install, workflow, trial or recommendation. |
| Third-party discovery listing | 1 verified | External indexing only | [Trendshift][6] indexes the repository and re-displays a maintainer-owned X post. It is not an external trial, endorsement or use case. |
| Verified external Action / CLI use | 0 | — | Exact GitHub code search found no external workflow or CLI reference at collection. |
| Verified external repository integration | 0 | — | No public integration, dependent or maintainer confirmation has been identified. |
| Verified external Trial Reports | 0 | — | No non-maintainer structured trial has been received. |
| Verified third-party technical feedback | 1 | EXTERNAL_VERIFIED feedback only | A distinct public developer left a substantive threat-model comment; it is technical feedback, not evidence of running or adopting the tool.[7] |
| External mentions | 0 verified independent recommendations | — | Existing DEV, Reddit, X and GitHub Discussion items are maintainer-authored launch activity; maintain them separately from third-party mentions. |

## First-use and conversion path

The public README leads with the “tests pass, gate fails” risk, a 60-second demonstration and two low-friction paths. The no-install Demo command is `python demo/run_demo.py` after cloning the public repository. The safer structural-trial path is `patchwitness doctor` followed by `patchwitness scan --no-checks`, which does not execute repository checks. The 60-second Demo was re-run from a clean shallow clone on 2026-08-13 after the clean-room handling fix; it produced two passing unit tests, a blocked protected CI modification (`PW002` and `PW003`), and an offline-verified Change Passport.

The recorded baseline does not yet contain a non-maintainer first-use time. Future Trial Reports may record time-to-first-result with the submitter’s permission, but must not include private source, credentials, proprietary logs or sensitive Passport data.

## Evidence levels at baseline

| Adoption level | Verified count | Notes |
|---:|---:|---|
| 0 — Visitor | 0 individual users | Aggregate traffic exists but cannot identify persons. |
| 1 — Clone / release download | 0 external verified | Raw clone and download counts are UNKNOWN. |
| 2 — Non-maintainer Demo run | 0 | No public report. |
| 3 — Non-maintainer repository run | 0 | No public report. |
| 4 — External Trial Report / Issue | 0 | No report or Issue. |
| 5 — External optional workflow | 0 | No public integration. |
| 6 — External required/recommended CI | 0 | No public integration. |
| 7 — Accepted external contributor PR | 0 | Dependabot is excluded. |
| 8 — Independent technical recommendation | 0 | One feedback comment is not a recommendation. |
| 9 — Multiple sustained independent users | 0 | No evidence. |

## Recollection protocol

Recollect these fields every 48 hours and append a dated entry to [`growth-log.md`](growth-log.md). Preserve raw API responses outside the repository or link stable public sources where allowed. Each newly observed signal must be classified before it can affect `OSS_READINESS.md`. If attribution cannot be established, record **UNKNOWN** rather than guessing.

## References

[1]: https://api.github.com/repos/pangxueyuan2-creator/patchwitness/stargazers "GitHub stargazers API"
[2]: https://api.github.com/repos/pangxueyuan2-creator/patchwitness "GitHub repository API"
[3]: https://api.github.com/repos/pangxueyuan2-creator/patchwitness/subscribers "GitHub subscribers API"
[4]: https://github.com/marketplace/actions/patchwitness-gate "PatchWitness Gate on GitHub Marketplace"
[5]: https://github.com/pangxueyuan2-creator/patchwitness/releases "PatchWitness releases"
[6]: https://trendshift.io/repositories/128828 "Trendshift repository record"
[7]: https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j "External technical comment on DEV"
