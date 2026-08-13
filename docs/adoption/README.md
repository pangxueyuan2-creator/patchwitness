# Adoption Evidence

This directory records **observable adoption evidence**, not marketing activity. It exists so maintainers, contributors and potential users can distinguish a runnable project from a project with verified non-maintainer use.

## Evidence standard

A signal is classified as one of the following:

| Classification | Meaning | Can support an external-adoption claim? |
|---|---|---|
| `OWNER_GENERATED` | Produced by the repository owner or an account they control. | No |
| `BOT_GENERATED` | Produced by Dependabot, CI or another automated account. | No |
| `EXTERNAL_VERIFIED` | A distinct public person or repository has a direct URL and a specific supportable claim. | Yes, but only at the stated evidence level. |
| `UNKNOWN` | An aggregate count or unverified observation whose actor or purpose cannot be determined. | No |

The adoption levels are documented in [`baseline.md`](baseline.md). A Star, clone, release download, crawler listing or social reaction is never automatically upgraded to a trial, integration or recommendation.

## Records

| File | Purpose | Update rule |
|---|---|---|
| [`baseline.md`](baseline.md) | The dated zero point for repository, release, traffic and external-use evidence. | Replace only with a new timestamped snapshot; retain the earlier record in Git history. |
| [`growth-log.md`](growth-log.md) | Chronological metric snapshots and recorded maintainer actions. | Append an entry every 48 hours or after a genuine external event. |
| [`external-adopters.md`](external-adopters.md) | Public, permissioned external trials and integrations. | Add only after a public URL or explicit permission establishes the reported level. |
| [`external-mentions.md`](external-mentions.md) | Independent public mentions and technical discussions. | Add only with a direct URL and exact relevance; maintainer-authored announcements are listed separately. |

## Trial reports and privacy

Use the [Trial Report form](https://github.com/pangxueyuan2-creator/patchwitness/issues/new?template=trial-report.yml) after a real run. The form accepts a public URL or a sanitized repository shape. Do **not** include private source, credentials, proprietary logs, or sensitive Change Passports.

Negative results, false positives, false negatives and “this does not fit my workflow” are valuable feedback. Submitting a report does not authorize a testimonial, endorsement or public adopter listing. Permission is recorded separately and honored at the specific scope granted.
