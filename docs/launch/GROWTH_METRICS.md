# Real growth metrics

Baseline captured 2026-08-11 after the initial public release:

| Metric | Baseline |
|---|---:|
| Stars | 0 |
| Forks | 0 |
| Release downloads | 0 |
| External human issues | 0 |
| External human pull requests | 0 |
| Verified external integrations | 0 |
| External human contributors | 0 |

Dependabot activity and maintainer downloads/tests do not count as user adoption.

## Current verified snapshot

Refreshed 2026-08-12 03:40 UTC from GitHub repository, release, and traffic APIs:

| Metric | Current value | Interpretation |
|---|---:|---|
| Stars | 1 raw; 0 external verified | The only known star is the maintainer's. |
| Forks | 0 | No external fork is visible. |
| Release asset downloads | 12 raw | Downloader identity is unavailable; none is counted as a real user. |
| Counted repository views | 0 | The immediate bottleneck is qualified discovery, not demonstrated conversion. |
| Counted repository clones | 0 | No clone is treated as adoption. |
| GitHub Marketplace listing | 1 public listing | Distribution is ready; usage remains unknown. |
| Verified external integrations | 0 | No public repository reference has been verified. |

Marketplace publication and maintainer-authored promotion are reach mechanisms, not adoption
evidence. The next valid milestone remains one non-maintainer trial with reproducible feedback.

## Milestone definitions and actions

### First real user

Definition: a non-maintainer runs the demo or PatchWitness on a real repository and provides
verifiable feedback.

Actions:

1. Launch with the real risk demo rather than a feature list.
2. Ask one question: “Where should this gate live in your workflow?”
3. Provide a copy-paste feedback template in GitHub Discussions.
4. Offer to debug the first integration publicly when no private source is required.

### First release download

Definition: GitHub reports a download of the published wheel or source archive that was not generated
by the maintainer's own verification.

Actions:

1. Use the release-wheel URL as the primary install command.
2. Link the Release from README, Show HN, and the article.
3. Do not download the asset to move the counter.

### First external issue

Definition: an unaffiliated human opens a bug, integration request, or documented question.

Actions:

1. Keep issue templates short and welcoming.
2. Respond within one working day with reproduction-oriented questions.
3. Label honestly; do not create maintainer-authored placeholder issues to simulate activity.

### First external pull request

Definition: an unaffiliated human submits a code or documentation change that passes project checks.

Actions:

1. Point interested users to the plugin guide and bounded adapters.
2. Offer small, real contribution surfaces: a build-system adapter, docs reproduction, or test case.
3. Review promptly and explain requested changes.

### First external integration

Definition: a public project or verifiable user repository runs PatchWitness in local automation, CI,
an agent hook, or an orchestrator.

Actions:

1. Build one reference integration in a fork before contacting a target project.
2. Record exact setup time, command, result, and limitations.
3. Link only with the adopter's permission; no invented “used by” section.

### First 10 real users

Definition: ten distinct non-maintainer users provide a verifiable install, run, issue, discussion,
integration, or contribution signal.

Actions:

1. Maintain a private aggregate count with evidence URLs; do not store personal data unnecessarily.
2. Publish the top three friction points and what changed.
3. Choose the first adapter from repeated demand, not projected popularity.

### First 50 real stars

Stars are a lagging discovery signal, not the primary goal. At 50 genuine stars:

1. publish a transparent “what we learned” update;
2. compare stars with real runs, downloads, issues, and integrations;
3. avoid milestone spam or giveaways; and
4. reassess whether a v0.2 release is justified by user-facing changes.

## Weekly scorecard

Collect through public GitHub APIs and direct opt-in feedback:

```text
Week ending:
Stars / forks:
Release downloads by asset:
External issues opened / resolved:
External PRs opened / merged:
New external contributors:
Verified user runs:
Verified integrations:
Top onboarding failure:
Top requested evidence or adapter:
Actions taken:
```

Do not add invasive telemetry to PatchWitness for launch measurement. Repository-native, public, and
opt-in signals are sufficient at this stage.
