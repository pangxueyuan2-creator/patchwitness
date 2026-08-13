# OSS readiness for Codex for Open Source

**Decision: NOT READY TO APPLY**

Snapshot refreshed: **2026-08-13 07:51 UTC**. This file records public, source-verifiable evidence.
Unknown values are not estimated. Maintainer runs, maintainer downloads, and bot activity are not
counted as external adoption. The latest [Real Adoption Report](docs/adoption/REAL_ADOPTION_REPORT.md)
and [adoption baseline](docs/adoption/baseline.md) document the refreshed raw data, new maintainer-built
trial assets and the unchanged absence of verified external trials or integrations.

The [official OpenAI application](https://openai.com/form/codex-for-oss/) says eligible projects are
active open-source projects with meaningful usage, broad adoption, or clear ecosystem importance.
OpenAI reviews repository usage, ecosystem importance, active maintenance, and the ongoing work of
primary or core maintainers, including pull request review, issue triage, and release management.

## OSS application gap

| Area | Score | Evidence-based assessment |
|---|---:|---|
| Meaningful usage | 0/10 | No verified external download, user, feedback, dependent, or integration. |
| Broad adoption | 0/10 | The only star and subscribing watcher belong to the maintainer; there are 0 forks and 0 external contributors. |
| Ecosystem importance | 2/10 | The project targets a real AI-change verification gap and exposes reusable CI/SDK/JSON/SARIF/MCP surfaces, but no external project depends on them yet. |
| Active maintenance | 5/10 | Three maintained releases, 20 main-branch commits, working automation, security hardening, and four reviewed dependency updates exist, all within the repository's first day; sustained maintenance is not yet established. |
| Maintainer evidence | 5/10 | The owner authored the project, manages provenance-attested releases, merged four reviewed Dependabot pull requests, and completed both security-hardening and first-use adoption cycles. There is no external human PR review, issue triage, or security-response history yet. |
| Technical quality | 8/10 | Cross-platform CI, CodeQL, tests, strict typing, a threat model, release artifacts, a real demo, and reproducible evidence are present. This score does not imply adoption. |
| External validation | 1/10 | One unaffiliated developer posted substantive public feedback on the threat model and asked where the gate belongs. This is useful external technical validation, but not a testimonial, trial, adoption, or user report. |

## Current evidence

| Signal | Current value | Source |
|---|---:|---|
| Stars | 1 raw; 0 external verified | [GitHub stargazers API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/stargazers) identifies the owner as the only stargazer |
| Forks | 0 | [GitHub repository API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness) |
| Subscribing watchers | 1 raw; 0 external verified | [GitHub subscribers API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/subscribers) identifies the owner as the only subscriber |
| Releases | 3 (`v0.1.0`, `v0.1.1`, `v0.2.0`) | [GitHub releases](https://github.com/pangxueyuan2-creator/patchwitness/releases) |
| Release asset downloads | 12 raw; external attribution UNKNOWN | [GitHub release API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/releases); maintainer verification downloads occurred and GitHub does not expose downloader identity, so none is counted as a real-user milestone |
| Contributors reported by GitHub | 1 human maintainer + Dependabot | [GitHub contributors API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/contributors) |
| External human contributors | 0 | Contributors API, excluding the owner and bot accounts |
| Human issues | 0 | [GitHub issues](https://github.com/pangxueyuan2-creator/patchwitness/issues?q=is%3Aissue) |
| Pull requests | 4 merged Dependabot PRs; 0 external human PRs | [GitHub pull requests](https://github.com/pangxueyuan2-creator/patchwitness/pulls?q=is%3Apr) |
| Commits | 20 on `main` across the first day | [GitHub commits API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/commits) |
| Dependents | UNKNOWN | GitHub's public API does not expose a reliable dependent count for this unregistered package. |
| Internal GitHub Actions usage | 61 workflow runs: 55 successful, 6 failed, 0 other/in progress | [GitHub Actions](https://github.com/pangxueyuan2-creator/patchwitness/actions); these are maintenance automation, not external usage |
| Repository security posture | Secret scanning and push protection enabled; Dependabot security updates enabled with 0 open alerts; active default-branch history-protection ruleset | [GitHub Security](https://github.com/pangxueyuan2-creator/patchwitness/security) and [Rules](https://github.com/pangxueyuan2-creator/patchwitness/settings/rules) |
| Verified external GitHub Action usage | 0 found | [Exact GitHub code search](https://github.com/search?q=%22pangxueyuan2-creator%2Fpatchwitness%22&type=code) returned no external reference at capture time |
| GitHub Marketplace | Public listing; adoption UNKNOWN | [PatchWitness Gate](https://github.com/marketplace/actions/patchwitness-gate) is installable from the Marketplace, but publication is a distribution surface rather than evidence of external usage |
| GitHub traffic | 0 counted views; 0 counted clones in the available 14-day window | Repository traffic API checked by the maintainer; GitHub exposes this endpoint only to push-authorized users, so the value is recorded without claiming a public verification link |
| Package registry | Not published on PyPI | [`patchwitness` PyPI JSON endpoint](https://pypi.org/pypi/patchwitness/json) returned 404 at capture time |
| Package downloads | Registry: not applicable; external Release downloads: UNKNOWN | No package-registry publication; raw Release downloads cannot be attributed publicly |
| External mentions | 4 verified maintainer-authored launch publications; 0 verified third-party mentions; exhaustive count UNKNOWN | [r/devops comment](https://www.reddit.com/r/devops/comments/1vkd20a/comment/p303xwh/), [r/ChatGPTCoding comment](https://www.reddit.com/r/ChatGPTCoding/comments/1vkehmk/comment/p36g7xn/), [DEV Community article](https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88), and [X thread](https://x.com/jordyuout/status/2087162269738336713) publicly link the project or demo; none is counted as external adoption or validation |
| Discussions | 1 maintainer-authored launch announcement; 0 external discussions or replies | [GitHub Discussion #4](https://github.com/pangxueyuan2-creator/patchwitness/discussions/4) |
| Other repositories integrated | 0 verified | Exact GitHub code search found no external action or CLI reference |
| External technical feedback | 1 verified comment; 0 verified trials | [Anas Rhimi's DEV comment](https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3co2j) independently identifies the self-reporting trust problem and asks whether PatchWitness belongs in CI or pre-PR. The commenter has a separate [public GitHub account](https://github.com/Mealiclay01). This is feedback, not proof of use, adoption, or endorsement. |

## Maintainer evidence

- Primary maintainer and repository owner: [`pangxueyuan2-creator`](https://github.com/pangxueyuan2-creator).
- Release management: [`v0.1.0`](https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.1.0),
  the provenance-attested security release
  [`v0.1.1`](https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.1.1), and the
  zero-configuration adoption release
  [`v0.2.0`](https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.2.0).
- Dependency maintenance: [PR #1](https://github.com/pangxueyuan2-creator/patchwitness/pull/1),
  [PR #2](https://github.com/pangxueyuan2-creator/patchwitness/pull/2), and
  [PR #3](https://github.com/pangxueyuan2-creator/patchwitness/pull/3), and
  [PR #5](https://github.com/pangxueyuan2-creator/patchwitness/pull/5) were reviewed and merged by
  the owner.
- CI and security automation: active CI, CodeQL, PatchWitness, dependency-review, provenance release,
  and Dependabot workflows; immutable Action pins and a default-branch history-protection ruleset.
- Launch and feedback management: [GitHub Discussion #4](https://github.com/pangxueyuan2-creator/patchwitness/discussions/4)
  plus policy-compliant launch publications on [r/devops](https://www.reddit.com/r/devops/comments/1vkd20a/comment/p303xwh/),
  [r/ChatGPTCoding](https://www.reddit.com/r/ChatGPTCoding/comments/1vkehmk/comment/p36g7xn/),
  [DEV Community](https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88), including a
  [public technical reply](https://dev.to/pangxueyuan2creator/why-ai-generated-code-needs-independent-verification-1j88#comment-3cp2p),
  and [X](https://x.com/jordyuout/status/2087162269738336713).
- Sustained history: **not yet demonstrated**; the repository was created on 2026-08-11.

## Three missing evidence classes

1. **Real usage:** the first non-maintainer release download and a reproducible report from a real
   repository.
2. **External adoption:** at least one public repository integration or dependent that runs the gate
   and retains a Change Passport.
3. **Sustained community maintenance:** real human issues/PRs plus visible triage, review, releases,
   and security stewardship over time.

## Update rules

Refresh this snapshot only from public source links. For external feedback, record the author's own
public link and exact claim; do not turn private conversation into a testimonial without permission.
Do not count bots, maintainer-controlled accounts, self-downloads, duplicate mirrors, or promotional
posts as users. Technical quality can support an application, but it cannot substitute for adoption.
