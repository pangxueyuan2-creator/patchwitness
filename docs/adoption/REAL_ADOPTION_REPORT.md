# Real Adoption Report

**Report timestamp:** 2026-08-13T07:51:27Z
**Repository revision assessed:** `09c4b841104b0adb946a2cf4f8d8a993c40476c6`
**Decision:** **NOT READY TO APPLY** for OpenAI Codex for Open Source.

This report uses the evidence definitions in [the adoption baseline](baseline.md). It does not treat maintenance work, generated examples, raw downloads, aggregate traffic, directories, crawlers or maintainer-authored posts as external use.

## Executive conclusion

PatchWitness is now easier for a non-maintainer to inspect and try safely, and it has a versioned evidence system for recording future trials. The project has **not** yet obtained a verified non-maintainer Demo run, external Trial Report, external repository integration, external human contribution, external human PR or independent recommendation. The highest-value next outcome is therefore not more product construction: it is one real maintainer or developer running the public trial path and leaving an honest, permissioned report.

| Readiness dimension | Current score | Evidence-based assessment |
|---|---:|---|
| Meaningful usage | 0/10 | No verified external Demo, repository run, Trial Report, integration or dependent. |
| Broad adoption | 0/10 | The only raw Star and subscriber belong to the maintainer; no forks or external human contributors. |
| Ecosystem importance | 2/10 | The project addresses a concrete agent-patch verification boundary and now has provider-specific hook examples, but no external project depends on them. |
| Active maintenance | 5/10 | Versioned documentation, tests, CI, CodeQL, real Demo fixes and adoption evidence infrastructure exist; sustained time-based maintenance is not yet demonstrated. |
| Maintainer evidence | 5/10 | Owner has released, reviewed dependency maintenance and created security/maintenance assets; no external human triage or PR review cycle exists yet. |
| Technical quality | 8/10 | Cross-platform CI, CodeQL, strict checks, real Demo, trusted-base policy, clean-room support, reproducible risk scenarios and documented boundaries are present. This does not imply adoption. |
| External validation | 1/10 | One distinct public technical comment challenges the trust-model placement; it is feedback, not a trial or testimonial.[1] |

## Completed

| Work item | Verifiable result | Classification |
|---|---|---|
| Real baseline | Versioned [`baseline.md`](baseline.md) records UTC, API-backed repository/traffic/release data, attribution limits, external code-reference review and evidence levels. | `OWNER_GENERATED` measurement infrastructure |
| Safer first trial | README now exposes `patchwitness doctor` plus `patchwitness scan --no-checks` directly after the Demo. The pathway was timed against the public repository: Demo 500 ms, doctor 141 ms, structural scan 179 ms after command invocation. | `OWNER_GENERATED` product documentation; not external use |
| Honest feedback system | Trial Report form, privacy guidance, adoption index, growth log, external-adopter ledger and external-mention ledger are in version control. | `OWNER_GENERATED` maintenance infrastructure |
| Target research | [`target-projects.md`](target-projects.md) covers 35 active coding-agent, CI, MCP and supply-chain candidates with scores and strict contact gates. | `OWNER_GENERATED` research; not outreach or adoption |
| Reproducible agent integration assets | Executable advisory local hook examples for Claude Code and Copilot CLI default to `--no-checks`; Bash variants were run locally and generated verifiable Passports. | `OWNER_GENERATED` example assets |
| Change-risk benchmark | Five fresh trusted-base fixtures produce one permitted pass and four intentional failures for protected CI, out-of-scope change, missing required check and policy self-modification. Raw results are committed under [`benchmarks/change-risk`](../../benchmarks/change-risk/). | `OWNER_GENERATED` reproducible evidence |
| Quality validation | Local run: 53 tests passed; Ruff passed; risk benchmark passed. Latest main CI and CodeQL passed for the report revision.[2] [3] | `OWNER_GENERATED` quality evidence |
| Periodic audit | A 48-hour read-only adoption audit is active until 2026-09-13 UTC. It is instructed to classify signals and never publish or contact users. | `OWNER_GENERATED` operational control |

## Verified external evidence

| Evidence | Level | What it proves | What it does not prove |
|---|---:|---|---|
| [Public DEV technical comment][1] from a distinct public developer | External feedback only | An independent developer engaged with the self-reporting trust problem and asked where the gate belongs. | Demo run, installation, adoption, recommendation or endorsement. |
| [Trendshift repository index][4] | None | A third-party discovery service indexed PatchWitness and displayed a maintainer-authored X post. | Any independent use or validation. |
| [`ai-trends` metadata record][5] and [`repo-dashboard` data record][6] | None | Third-party datasets contain PatchWitness-related metadata/community data. | Runtime use, workflow integration or endorsement. |

**Verified external adoption count:** 0.
**Verified external Trial Reports:** 0.
**Verified external integrations:** 0.
**Verified external human PRs:** 0.
**Verified external recommendations:** 0.

## Current raw signals and classification

| Signal at 2026-08-13T07:34:30Z | Raw value | Classification | Treatment |
|---|---:|---|---|
| Stars | 1 | `OWNER_GENERATED` | Excluded from external adoption. |
| Forks | 0 | — | No adoption inference. |
| Subscriber watchers | 1 | `OWNER_GENERATED` | Excluded from external adoption. |
| Views / unique visitors, trailing 14 days | 51 / 10 | `UNKNOWN` | Aggregated discovery signal only. |
| Clones / unique cloners, trailing 14 days | 362 / 69 | `UNKNOWN` | Not attributable to actual users; may include automated or repeated traffic. |
| Release asset downloads | 14 | `UNKNOWN` | No downloader identity; not counted. |
| Human Issues / external human PRs | 0 / 0 | — | Dependabot activity excluded. |
| Public external code references | 2 | Third-party indexing | Reviewed and excluded from adoption. |

## Prepared but not published

| Asset | Status | Rationale |
|---|---|---|
| [Show HN final draft](show-hn-final.md) | Ready for review; not posted | It uses the real Demo and benchmark, declares limitations and asks for technical criticism rather than votes. |
| [Contribution candidate drafts](contribution-candidates.md) | Ready; no Issues created | Prevents activity-seeking Issues; each task has real scope and acceptance criteria. |
| Narrow Claude/Copilot hook examples | Published in repository; not submitted to third-party projects | They are verified local assets but do not yet justify approaching any project without a relevant invited route. |
| 35-project relevance map | Published in repository; no contacts sent | A target score is never contact permission. |

## Blocked by permission or external choice

| Item | Status | Required next condition |
|---|---|---|
| Show HN submission | Blocked pending explicit confirmation immediately before public posting | Maintainer confirms final text, account use and posting time. |
| Reddit / DEV / Hashnode publication | Blocked pending explicit confirmation and same-day community rule review | One tailored technical post per allowed venue; no cross-post automation. |
| Third-party repository outreach | Not started by design | A real tested integration artifact plus a maintainer-invited channel or an active relevant discussion. |
| External trials and integrations | Not controllable by maintainer | Independent users must choose to run the tool and provide permissioned evidence. |

## Failed or intentionally not claimed

No engineering quality gate failed in this sprint after the final corrections. The initial change-risk benchmark failed once because the benchmark’s TOML command string was incorrectly escaped; the error was fixed, then the full five-scenario benchmark, 53 project tests and Ruff all passed. This report does **not** count any of the following as success: prepared copy, owner uploads, maintainer downloads, crawler indexing, raw clones, raw release downloads, Dependabot PRs or repository examples.

## Next highest-value action

Request approval to submit the prepared **single Show HN post** only after a final same-day guidelines check. It is the most appropriate first public surface because the repository has a runnable, no-registration Demo, a reproducible change-risk scenario and a maintainer-ready technical question. If approval is not granted, do not substitute bulk outreach. Continue the 48-hour evidence audit, respond promptly to any real Trial Report or external feedback, and improve only the friction directly reported by those users.

## References

[1]: https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j "External technical feedback on DEV"
[2]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31679485561 "Latest PatchWitness CI"
[3]: https://github.com/pangxueyuan2-creator/patchwitness/actions/runs/31679485597 "Latest PatchWitness CodeQL"
[4]: https://trendshift.io/repositories/128828 "Trendshift PatchWitness record"
[5]: https://github.com/Klausc06/ai-trends/blob/cc716c337d635933a68cba2f44f6c3cf89fd5afb/data/repos/pangxueyuan2-creator-patchwitness.json "ai-trends metadata record"
[6]: https://github.com/lethanhson9901/repo-dashboard/blob/ff2d4eb884922c4d9d1563fceb0f7debb1013938/src/data/reddit/community_news/ChatGPTCoding.json "repo-dashboard community data"
