# OSS readiness for Codex for Open Source

**Decision: NOT READY TO APPLY**

Snapshot captured: **2026-08-11 08:39 UTC**. This file records public, source-verifiable evidence.
Unknown values are not estimated. Maintainer runs, maintainer downloads, and bot activity are not
counted as external adoption.

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
| Active maintenance | 3/10 | One release, 11 commits, working automation, and three merged dependency updates exist, all within the repository's first day; sustained maintenance is not yet established. |
| Maintainer evidence | 3/10 | The owner authored the project, manages the release, and merged three Dependabot pull requests. There is no external human PR review, issue triage, or security-response history yet. |
| Technical quality | 8/10 | Cross-platform CI, CodeQL, tests, strict typing, a threat model, release artifacts, a real demo, and reproducible evidence are present. This score does not imply adoption. |
| External validation | 0/10 | No verified external mention, testimonial, issue, pull request, discussion, integration, or user report. |

## Current evidence

| Signal | Current value | Source |
|---|---:|---|
| Stars | 1 raw; 0 external verified | [GitHub stargazers API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/stargazers) identifies the owner as the only stargazer |
| Forks | 0 | [GitHub repository API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness) |
| Subscribing watchers | 1 raw; 0 external verified | [GitHub subscribers API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/subscribers) identifies the owner as the only subscriber |
| Releases | 1 (`v0.1.0`) | [GitHub releases](https://github.com/pangxueyuan2-creator/patchwitness/releases) |
| Release asset downloads | 1 raw; external attribution UNKNOWN | [GitHub release API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/releases); GitHub does not expose downloader identity, so this is not counted as a real-user milestone |
| Contributors reported by GitHub | 1 human maintainer + Dependabot | [GitHub contributors API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/contributors) |
| External human contributors | 0 | Contributors API, excluding the owner and bot accounts |
| Human issues | 0 | [GitHub issues](https://github.com/pangxueyuan2-creator/patchwitness/issues?q=is%3Aissue) |
| Pull requests | 3 merged Dependabot PRs; 0 external human PRs | [GitHub pull requests](https://github.com/pangxueyuan2-creator/patchwitness/pulls?q=is%3Apr) |
| Commits | 12 total across the first day | [GitHub commits API](https://api.github.com/repos/pangxueyuan2-creator/patchwitness/commits) |
| Dependents | UNKNOWN | GitHub's public API does not expose a reliable dependent count for this unregistered package. |
| Internal GitHub Actions usage | 35 workflow runs: 30 successful, 5 failed | [GitHub Actions](https://github.com/pangxueyuan2-creator/patchwitness/actions); failures were repository PR gates, not external usage |
| Verified external GitHub Action usage | 0 found | [Exact GitHub code search](https://github.com/search?q=%22pangxueyuan2-creator%2Fpatchwitness%22&type=code) returned no external reference at capture time |
| Package registry | Not published on PyPI | [`patchwitness` PyPI JSON endpoint](https://pypi.org/pypi/patchwitness/json) returned 404 at capture time |
| Package downloads | Registry: not applicable; external Release download: UNKNOWN | No package-registry publication; the one raw Release download cannot be attributed publicly |
| External mentions | 0 verified; exhaustive count UNKNOWN | Exact repository URL/name searches found no attributable external mention at capture time |
| Discussions | 0 | [GitHub Discussions](https://github.com/pangxueyuan2-creator/patchwitness/discussions) |
| Other repositories integrated | 0 verified | Exact GitHub code search found no external action or CLI reference |
| Real user feedback | 0 verified | No issue, discussion, PR, or linked public report from a non-maintainer |

## Maintainer evidence

- Primary maintainer and repository owner: [`pangxueyuan2-creator`](https://github.com/pangxueyuan2-creator).
- Release management: [`v0.1.0`](https://github.com/pangxueyuan2-creator/patchwitness/releases/tag/v0.1.0).
- Dependency maintenance: [PR #1](https://github.com/pangxueyuan2-creator/patchwitness/pull/1),
  [PR #2](https://github.com/pangxueyuan2-creator/patchwitness/pull/2), and
  [PR #3](https://github.com/pangxueyuan2-creator/patchwitness/pull/3) were merged by the owner.
- CI and security automation: active CI, CodeQL, PatchWitness, release, and Dependabot workflows.
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
