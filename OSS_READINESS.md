# OSS readiness for Codex for Open Source

**Decision: NOT READY TO APPLY**

Snapshot refreshed: **2026-08-13 09:30 UTC** at [`4c62b50`](https://github.com/pangxueyuan2-creator/patchwitness/commit/4c62b50af201ff09583e319439066912560d96c7). This file records public, source-verifiable evidence. Unknown values are not estimated; maintainer activity, raw downloads, marketplace publication, automation and bot activity are not counted as external adoption. See the [Real Adoption Report](docs/adoption/REAL_ADOPTION_REPORT.md) for the complete classification record.

The [official OpenAI application](https://openai.com/form/codex-for-oss/) describes eligible projects as active open-source projects with meaningful usage, broad adoption or clear ecosystem importance. This repository has not yet met the meaningful-usage or broad-adoption thresholds with independently attributable evidence.[1]

## Current gap

| Area | Score | Evidence-based assessment |
| --- | ---:| --- |
| Meaningful usage | 0/10 | No verified external download, user report, trial, dependent or integration. |
| Broad adoption | 0/10 | One raw star/subscriber belongs to the maintainer; zero forks and zero external human contributors. |
| Ecosystem importance | 2/10 | The project addresses agent-patch verification and provides CI, JSON, SARIF, SDK, MCP and provider integration surfaces, but no external project depends on them. |
| Active maintenance | 6/10 | Recent security, release, integration, CI/CodeQL and contributor-path work is verifiable; sustained maintenance over time is still absent. |
| Maintainer evidence | 6/10 | The owner manages releases and security controls, merged reviewed PRs and maintains clear contribution boundaries; external human triage/review history is absent. |
| Technical quality | 8/10 | Cross-platform CI, CodeQL, trusted-base policy, clean-room support, real Demo, benchmark, fixture tests and release validation are present. This does not imply adoption. |
| External validation | 1/10 | One unaffiliated technical comment is genuine feedback, but not a trial, recommendation or endorsement. [2] |

## Current evidence

| Signal | Current value | Source and treatment |
| --- | ---:| --- |
| Main revision | `4c62b50` | [Commit](https://github.com/pangxueyuan2-creator/patchwitness/commit/4c62b50af201ff09583e319439066912560d96c7) passed [CI](https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834028) and [CodeQL](https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31684834026). |
| Releases | 3 (`v0.1.0`, `v0.1.1`, `v0.2.0`) | [GitHub Releases](https://github.com/pangxueyuan2-creator/patchwitness/releases); distribution, not adoption. |
| Raw release downloads | 14 | Downloader identity is unavailable, so excluded. |
| Stars / forks / subscribers | 1 / 0 / 1 | [Repository API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness); the star/subscriber are maintainer-owned and excluded. |
| Contributors | 1 human maintainer + Dependabot; 0 external humans | [Contributors API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/contributors). |
| Public contribution task | 1 maintainer-created Issue | [Issue #9](https://github.com/pangxueyuan2-creator/patchwitness/issues/9) is a Windows Copilot hook validation request; it is not a user contribution. |
| Verified external Action / CLI use | 0 | External code-search matches are not verified integrations. |
| PyPI | Not published | `https://pypi.org/pypi/patchwitness/json` and `/simple/patchwitness/` returned 404 at snapshot time. |
| Show HN | No story created | HN redirected the authorized submission to its temporary Show HN restriction page; no retry. |

## What is ready

The repository can support a meaningful trial without additional feature construction. It has a reproducible no-registration Demo, safe first-run `doctor`/`scan --no-checks` path, trusted-base GitHub Action, provider-neutral handoff guidance, fixture-verified Codex/Cline adapters, a public Marketplace Action, and an explicit five-minute contributor setup. The full release preflight passed with 56 tests, coverage, Ruff, mypy, Demo, five change-risk scenarios, build, Twine and clean-wheel installation.

## What is still missing

1. **Real usage:** a non-maintainer runs the tool on a real or public-synthetic repository and provides a permissioned report.
2. **External adoption:** a public repository independently integrates the CLI or Action and retains evidence.
3. **Sustained community maintenance:** human issues/PRs plus visible triage, review, releases and security stewardship over time.

## Rules for future updates

Refresh only from traceable sources. Do not count bots, maintainer-controlled accounts, self-downloads, duplicate mirrors, raw traffic, crawler indexes, public Issue creation or promotional posts as users. Do not apply until independently attributable usage, ecosystem importance and sustained maintenance are evidenced. The next highest-value action is one external trial—not more non-essential engineering.

## References

[1]: https://openai.com/form/codex-for-oss/ "OpenAI Codex for Open Source application"
[2]: https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j "External technical feedback"
