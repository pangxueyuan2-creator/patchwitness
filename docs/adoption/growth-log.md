# Growth Log

This is a chronological evidence ledger, not a dashboard of claimed users. Append a new record every 48 hours or when a genuine external event occurs. Do not backfill estimates. Values that cannot be attributed to an external actor remain `UNKNOWN`.

## 2026-08-13T07:34:30Z — Baseline

| Field | Value | Classification / note |
|---|---:|---|
| Views / unique visitors, trailing 14 days | 51 / 10 | `UNKNOWN` aggregate GitHub Traffic |
| Clones / unique cloners, trailing 14 days | 362 / 69 | `UNKNOWN` aggregate GitHub Traffic |
| Release asset downloads | 14 | `UNKNOWN`; GitHub does not identify downloaders |
| Stars / external verified Stars | 1 / 0 | Sole star is owner account |
| Forks | 0 | No forks |
| External Trial Reports | 0 | No non-maintainer reports |
| External Issues / PRs | 0 / 0 | Dependabot PRs excluded |
| External repository integrations | 0 | No public workflow or maintainer confirmation |
| Independent recommendations | 0 | No verified third-party recommendation |
| Recorded activity since prior entry | Baseline created; clean-room Demo fix and trial-path documentation are maintainer work | `OWNER_GENERATED`; not adoption |

## Entry template

```markdown
## YYYY-MM-DDTHH:MM:SSZ — short event label

| Field | Value | Classification / note |
|---|---:|---|
| Views / unique visitors, trailing 14 days |  | `UNKNOWN` aggregate GitHub Traffic |
| Clones / unique cloners, trailing 14 days |  | `UNKNOWN` aggregate GitHub Traffic |
| Release asset downloads |  | `UNKNOWN` unless the actor publicly confirms a run |
| Stars / external verified Stars |  | Do not identify private users; identify the owner separately if applicable |
| Forks |  | Link an external fork only when relevant |
| External Trial Reports |  | Link only permissioned reports |
| External Issues / PRs |  | Exclude bots and maintainer-authored activity |
| External repository integrations |  | Link workflow, PR or public maintainer statement |
| Independent recommendations |  | Link direct third-party source |
| Recorded activity since prior entry |  | Mark `OWNER_GENERATED`, `BOT_GENERATED`, `EXTERNAL_VERIFIED` or `UNKNOWN` |
```

## Interpretation rules

A referral, view, clone or release download can inform discovery experiments but does not establish use. An external repository becomes an adopter only at the evidence level documented in [`baseline.md`](baseline.md), and only if the public source or explicit permission supports that statement. If there is no new evidence, record `0`, `UNKNOWN` or `no change`; do not manufacture activity.
