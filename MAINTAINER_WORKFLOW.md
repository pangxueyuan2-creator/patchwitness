# Maintainer workflow

This document defines how PatchWitness should be maintained. It is a commitment to future behavior,
not evidence that activity has already occurred. Actual work must remain visible in GitHub issues,
pull requests, releases, security advisories, and commit history.

## Issue triage

- Review new issues at least weekly while the project is active.
- Reproduce bugs before labeling them confirmed.
- Ask for the smallest safe reproduction; never request private source, credentials, or sensitive
  Change Passports.
- Close duplicates with a link to the canonical issue and a concise explanation.
- Do not create placeholder issues to simulate activity.

## Pull request review

- Require CI and CodeQL to pass or document why a failing security gate is the expected result.
- Review correctness, threat-model impact, compatibility, tests, and documentation.
- Prefer bounded adapters, analyzers, and examples over widening the trusted core without evidence.
- Record material review decisions in the pull request. Bot updates do not count as external
  contribution or community review.

## Release management

- Release only a tested, user-relevant change; never release merely to increase activity.
- Update the changelog, run the full quality gate, build and smoke-test artifacts, then publish notes
  that distinguish observed facts from limitations.
- Never move a published tag. Use a new patch release for artifact changes.
- Record asset download counts without downloading assets to alter the counter.

## Security response

- Follow [`SECURITY.md`](SECURITY.md) for private reporting.
- Acknowledge a credible report promptly, reproduce it privately, and avoid exposing exploit details
  before a fix or coordinated disclosure.
- Treat verifier bypasses, unsafe command execution, path escape, evidence tampering, and secret
  exposure as high-priority classes.

## Contributor onboarding

- Point contributors to [`CONTRIBUTING.md`](CONTRIBUTING.md), the threat model, and a bounded issue.
- Explain architectural constraints in review rather than relying on undocumented maintainer taste.
- Credit only real contributors and accepted work.

## Readiness review

- Refresh [`OSS_READINESS.md`](OSS_READINESS.md) from source links when a release, external issue,
  pull request, integration, mention, or verified user report changes the evidence.
- Keep unknown values as `UNKNOWN` and distinguish maintainer activity from external adoption.
- Apply to support programs only when the evidence, not repository polish alone, supports the claim.
