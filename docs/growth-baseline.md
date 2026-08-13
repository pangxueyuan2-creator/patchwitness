# Growth Baseline

**Snapshot date:** 2026-08-13 UTC
**Purpose:** Record a truthful starting point for product discovery and early-adopter learning. This document is not a forecast and does not treat traffic as proof of adoption.

## GitHub snapshot

| Metric | Value | Collection window / source |
|---|---:|---|
| Stars | 1 | GitHub repository API snapshot |
| Forks | 0 | GitHub repository API snapshot |
| Watchers | 1 | GitHub repository API snapshot |
| Open issues | 0 | GitHub repository API snapshot |
| Contributors | 2 | GitHub contributors endpoint |
| Releases | 3 | GitHub releases endpoint |
| Latest release | `v0.2.0` | Published 2026-08-11 |
| Release asset downloads | 14 | Sum from the releases endpoint at collection time |
| Views | 51 | GitHub Traffic, preceding 14 days |
| Unique visitors | 10 | GitHub Traffic, preceding 14 days |
| Clones | 362 | GitHub Traffic, preceding 14 days |
| Unique cloners | 69 | GitHub Traffic, preceding 14 days |

> **Interpretation boundary:** GitHub Traffic is an aggregate, short retention window. Clones may include automation, repeated CLI or Action fetches, mirrors, and testing. A clone is not an installation, successful scan, CI adoption, testimonial, or endorsement.

## Product and discovery evidence

The public README offers a no-install reproduction: `python demo/run_demo.py`. On the snapshot date, this demo was rerun from the released repository code and showed two passing unit tests, a failed PatchWitness gate for the intentionally modified CI workflow, and a successfully verified evidence file. The maintained assets include a committed terminal transcript, a generated Change Passport, a banner, a social preview, GitHub Action Marketplace listing, and integration documentation.

The first real learning goal is not a Star target. It is to collect permissioned trial reports that explain whether a team could run a structural scan, understand the evidence, and decide whether the policy gate fits its workflow. Submitters should never include private source, credentials, proprietary logs, or sensitive passports.

## Repeatable measurement plan

| Checkpoint | Recollect | Decision use |
|---|---|---|
| Day 7 | Repository metadata, 14-day Traffic, release downloads, issues, trial reports | Identify whether discovery has produced qualified feedback rather than raw visits only. |
| Day 14 | Same fields plus public integrations or mentions that users have explicitly shared | Compare sources and decide whether to continue the same message or test a different technical story. |
| Day 30 | Same fields plus resolved issues, external contributors, documented adoption with consent | Decide between a focused integration, documentation change, or new release based on evidence. |

Use GitHub repository, releases, contributors, and Traffic endpoints as the primary source. Public mentions should only be recorded with a direct URL and clear relevance. No automated engagement, fake accounts, paid follower acquisition, or unapproved bulk outreach is part of this plan.
