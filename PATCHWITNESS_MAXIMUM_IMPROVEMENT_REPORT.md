# PatchWitness Maximum Improvement — Final Execution Report

**Evidence snapshot:** 2026-08-13, UTC.
**Repository:** [`pangxueyuan2-creator/patchwitness`](https://github.com/pangxueyuan2-creator/patchwitness)
**Snapshot revision:** [`4c62b50af201ff09583e319439066912560d96c7`](https://github.com/pangxueyuan2-creator/patchwitness/commit/4c62b50af201ff09583e319439066912560d96c7)
**Decision:** Critical and High engineering work is closed for this program cycle. Further non-essential feature work is stopped; the remaining priority is an independently chosen external trial or integration.

> This report distinguishes tested repository work from external adoption. Maintainer commits, release downloads, marketplace publication, documentation, benchmarks, public Issue creation and an attempted community post are **not** counted as external use.

## Outcome at a glance

| Goal | Actual result | Evidence status |
| --- | --- | --- |
| Make evidence capture safer | Fixed out-of-repository symlink reads during hashing and secret scanning. | Merged and regression-tested. |
| Make releases more trustworthy | Added a tag-only verified build/release pipeline, artifact digests, clean-wheel smoke test, provenance attestation, and optional PyPI OIDC publishing boundary. | Merged; local release preflight passed. |
| Make agent integrations easier to use | Added fixture-verified OpenAI Codex Stop-hook path and a documented CI handoff; clarified all agent integration levels. | Merged; fixture-tested and PR-validated. |
| Make Action adoption safer | Added minimal, recommended and strict GitHub Action templates with full-SHA pins, least privilege and explicit fork-PR guidance. | Merged; Marketplace listing reachable. |
| Make contribution practical | Rewrote the five-minute contributor path and opened one bounded Windows validation task. | Merged; Issue #9 is open. |
| Obtain external adoption | No verified non-maintainer trial, integration, contributor, human PR or recommendation yet. | **0** across all counted classes. |

## Actual merged commits and changed files

| Change | Actual commit / PR | Key files | Result |
| --- | --- | --- | --- |
| Symlink trust-boundary fix | [`66893d27874d8b283e8b17583b46c36f4a4b8ca4`](https://github.com/pangxueyuan2-creator/patchwitness/commit/66893d27874d8b283e8b17583b46c36f4a4b8ca4), PR #6 | `src/patchwitness/git.py`, `src/patchwitness/security.py`, `tests/test_evidence.py` | Change Passport hashing and secret scanning refuse untracked symlinks that resolve outside the repository. |
| Trusted release pipeline | [`fa5e2ede4aded18c6c2647e21ad53bc92c4cfb6e`](https://github.com/pangxueyuan2-creator/patchwitness/commit/fa5e2ede4aded18c6c2647e21ad53bc92c4cfb6e), PR [#7](https://github.com/pangxueyuan2-creator/patchwitness/pull/7) | `.github/workflows/release.yml`, `Makefile`, `pyproject.toml`, `PYPI_RELEASE_CHECKLIST.md` | Tag verifies version, tests, Ruff, mypy, Demo, benchmark, build, manifest, Twine, clean install, SHA-256 and provenance before GitHub Release assets; PyPI OIDC is separately gated by `PYPI_TRUSTED_PUBLISHING=true`. |
| Codex hook and Action profiles | [`46502a841bb600c28d720d70c15064b78baa78f7`](https://github.com/pangxueyuan2-creator/patchwitness/commit/46502a841bb600c28d720d70c15064b78baa78f7), PR [#8](https://github.com/pangxueyuan2-creator/patchwitness/pull/8) | `examples/codex-hooks/Stop.py`, `tests/test_codex_hook.py`, `docs/integrations/codex.md`, `docs/integrations/github-actions.md`, `docs/integrations/coding-agents.md`, `examples/README.md` | Codex Stop-hook fixture validates trusted-base structural evidence and input minimization; Action documentation now has three security-scoped profiles. |
| Contributor onboarding | [`1a0c6ed8e2831502d7a6fff5a39476ebb164a0e9`](https://github.com/pangxueyuan2-creator/patchwitness/commit/1a0c6ed8e2831502d7a6fff5a39476ebb164a0e9) | `CONTRIBUTING.md` | Clone, dev install, tests, Ruff, mypy, Demo, benchmark, fixture, documentation/security boundaries and PR expectations are explicit. |
| Candidate review | [`4c62b50af201ff09583e319439066912560d96c7`](https://github.com/pangxueyuan2-creator/patchwitness/commit/4c62b50af201ff09583e319439066912560d96c7) | `docs/adoption/contribution-candidates.md` | Completed Codex task was removed; Medium/Low benchmark candidate was skipped; only the real Windows gap became Issue #9. |

## Validation record

| Scope | Actual result |
| --- | --- |
| Critical symlink regression | A pre-fix reproduction found `PW030` for an outside symlink; post-fix capture produces no such finding and the regression test passes. |
| Local full release preflight | `make release-check` passed after the Codex/Action implementation: **56 tests**, coverage gate, Ruff, mypy, real Demo, all five change-risk scenarios, build, Twine and clean-wheel install. |
| Build and artifact validation | `patchwitness-0.2.0.tar.gz` and `patchwitness-0.2.0-py3-none-any.whl` built successfully; `twine check dist/*` passed; clean virtual-environment installation reported `patchwitness 0.2.0`. |
| PR #7 | CI matrix, CodeQL and dependency review passed. The self-gate intentionally emitted `PW003` for a workflow change and `PW005` for a development dependency change; this protected-control-plane signal was manually reviewed before the approved merge. |
| PR #8 | All **10** checks passed: Linux Python 3.11/3.14, Windows Python 3.13, macOS Python 3.13, Docker, package build, PatchWitness gate, dependency review and CodeQL. |
| Current main | CI run [31684834028](https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834028) and CodeQL run [31684834026](https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834026) passed for snapshot commit `4c62b50`. |

## Integration status

| Surface | Status | Verified boundary |
| --- | --- | --- |
| GitHub Action | **VERIFIED** | Public [Marketplace listing](https://github.com/marketplace/actions/patchwitness-gate); minimal/recommended/strict templates load policy from immutable PR base SHA with read-only permissions. |
| OpenAI Codex | **VERIFIED (fixture boundary)** | `tests/test_codex_hook.py` invokes the published Stop adapter against a temporary Git fixture, verifies `PW003`, checks offline integrity and asserts prompt/transcript-like values are excluded. No paid Codex session, provider endorsement or Windows configuration is claimed. |
| Cline | **VERIFIED (fixture boundary)** | The existing TaskComplete adapter fixture invokes the public event shape, validates a protected-file failure and verifies evidence offline. |
| Claude Code | **VERIFIED (repository-local example boundary)** | Published safe-hook reproduction path; advisory by design. |
| GitHub Copilot CLI | **DOCUMENTED** | Bash safe path is documented; Windows PowerShell lifecycle validation is intentionally outstanding in [Issue #9](https://github.com/pangxueyuan2-creator/patchwitness/issues/9). |
| Aider | **DOCUMENTED** | Provider-neutral local evidence plus independent CI handoff; no native lifecycle-hook contract claimed. |

Local agent evidence is not a merge trust root. In every supported configuration, the independent `pull_request` CI gate remains the merge boundary.

## PyPI and distribution status

| Item | Actual status |
| --- | --- |
| PyPI publication | **Not published.** The PyPI JSON API and simple index for `patchwitness` returned HTTP 404 on 2026-08-13. The project-page HTTP response alone is not used as publication evidence. |
| Package name reservation | None. A 404 is an observation, not a reservation or guarantee. |
| First PyPI release | Not attempted. It remains an irreversible action requiring separate maintainer confirmation after Trusted Publisher and protected environment setup. |
| GitHub distribution | `v0.2.0` remains the published GitHub Release and is the documented wheel-install source. |
| Trusted release readiness | Ready but disabled by default: `PYPI_TRUSTED_PUBLISHING` must be deliberately set only after exact OIDC Trusted Publisher/environment configuration. |

## Contribution and external-adoption facts

The repository has one open maintainer-created contribution task: [Issue #9](https://github.com/pangxueyuan2-creator/patchwitness/issues/9), labeled `good first issue`, `help wanted` and `documentation`. It is a real, bounded request to validate the untested Windows PowerShell Copilot CLI hook path using only a public/synthetic repository and sanitized evidence.

| Counted external class | Verified count | Treatment |
| --- | ---:| --- |
| Non-maintainer trial reports | 0 | No claimed trial without a permissioned, attributable report. |
| External repository integrations | 0 | Marketplace availability and agent examples are not integrations. |
| External human PRs / contributors | 0 | The only human contributor is the maintainer; Dependabot is excluded. |
| External recommendations | 0 | A public technical comment is feedback, not a recommendation. |
| External adoption | **0** | Maintainer commits, release downloads, raw traffic and discovery indexes are excluded. |

The maintainer authorized one Show HN submission on 2026-08-13. The browser reached the final submit action, but Hacker News redirected the account to its temporary Show HN restriction page and created **no story**. No retry and no substitute public posting was made. The attempt is recorded in `maximum-improvement-audit/show-hn-submission-attempt-2026-08-13.md` outside the repository; it is not adoption evidence.

## Highest unresolved risks and next action

| Priority | Unresolved condition | Correct next action |
| --- | --- | --- |
| Highest | No real external trial or integration exists. | Stop adding non-essential engineering features. Obtain one independently chosen, permissioned trial through an allowed channel; record only evidence the user permits. |
| High | Windows PowerShell Copilot CLI hook path is not validated. | Let Issue #9 attract a real Windows contributor; do not invent compatibility. |
| High | PyPI distribution is unavailable. | Do not publish until a separate immediate confirmation, exact Trusted Publisher setup and release-candidate checks are complete. |
| Medium | HN currently restricts the maintainer account from posting Show HNs. | Do not retry automatically; reassess only after account/community eligibility changes and a fresh explicit confirmation. |

## Final assessment

PatchWitness is now materially safer at its repository trust boundary, more reproducible as a release artifact, clearer to install and integrate, and easier for a stranger to contribute to. The program deliberately stopped before cosmetic work or fictitious outreach. **Its remaining weakness is not an engineering checklist item: it is the absence of independently chosen external use.**
