# Contribution Candidate Review

This file records only real, bounded contribution opportunities and their disposition. A public `good first issue` or `help wanted` label is not an activity target: it is used only when the task is public-safe, independently completable, small enough to review, and has explicit acceptance criteria.

## Published: validate the Copilot CLI PowerShell hook on Windows

[Issue #9](https://github.com/pangxueyuan2-creator/patchwitness/issues/9) is the one currently valid contribution task. The Bash safe-scan hook has been exercised, while the Windows PowerShell path has not been verified in this environment. The Issue requires a non-sensitive test repository, a timestamped structural Passport created with `--no-checks`, offline verification, sanitized version information and documentation changes limited to observed behavior.

The task is intentionally advisory. It does not authorize changing Copilot permissions, placing secrets into a workflow, executing unknown repository checks, or turning a local post-session scan into a required merge gate.

## Completed: documented Codex post-task recipe

The former Codex candidate is complete and therefore is **not** an open Issue. PR [#8](https://github.com/pangxueyuan2-creator/patchwitness/pull/8) added the documented project-local Stop hook, a public deterministic fixture, explicit `--no-checks` default, trusted-base policy loading, an offline Passport verification assertion, and CI handoff guidance. The integration status is defined in [docs/integrations/codex.md](../integrations/codex.md).

## Skipped: false-positive benchmark review case

The proposed extra benchmark case is currently **not published**. It is a Medium/Low candidate without a concrete user-reported ambiguity or safety/correctness gap, so it does not satisfy the program's value threshold. Creating it solely to reach an Issue count would be documentation churn and fabricated activity. Reconsider only when a public, reproducible policy-review case emerges from a real trial, bug report or contributor observation.

## Maintainer response standard

For any published candidate, maintainers should reproduce with public or sanitized inputs, state the review boundary and either accept, narrow or close the work with technical reasoning. A low-quality pull request must not be merged merely to create adoption or contribution evidence.
