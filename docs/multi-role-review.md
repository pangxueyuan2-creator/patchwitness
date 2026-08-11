# V5 multi-role release review

This review asks whether each role has a concrete reason to install, keep, recommend, integrate, and
contribute—not whether the feature list sounds impressive.

| Role | Install / keep using | Star / recommend | Integrate | Likely contribution | Remaining gap |
|---|---|---|---|---|---|
| Developer | One command catches scope creep and proves tests ran | Saves forensic PR review time without sending code to a cloud | Pre-push/CI gate | Better language import resolution | Task contracts need team conventions |
| Senior Engineer | Protected surfaces and budgets make reviews predictable | Gives stable evidence instead of agent prose | Required PR check + SARIF | Framework-specific test/impact adapter | Semantic correctness still needs review |
| Staff Engineer | Base-authoritative policy and portable schema create an org-wide control point | Agent/vendor neutrality avoids lock-in | Internal developer platform SDK/plugin | Policy bundle/OPA bridge | Organization distribution is roadmap |
| AI Engineer | Same evidence across models and agent harnesses enables fair rerun comparison | Deterministic layer complements evals/traces | MCP + analyzer plugin | Transcript adapters/evidence diff | No LLM-call trace ingestion in v0.1 |
| DevOps Engineer | Real exit codes, clean worktrees, JSON/SARIF, predictable exit codes | Easy to add without a service/database | Composite Action, Docker, CI artifact | CI provider adapters | Clean room is not container isolation |
| Security Engineer | Base policy, protected control plane, secret-safe output, explicit threat model | Honest residual-risk language and no auto-installed plugins | Branch protection + isolated runner + signing | Sigstore/in-toto and SAST analyzers | Independent security review not complete |
| Startup CTO | Raises agent throughput without accepting blind autonomy or a hosted source-code vendor | Low operational burden and commercial-friendly Apache-2.0 | Default template across repositories | Monorepo and policy inheritance | Adoption/maintenance bus factor is new |
| Open-source maintainer | Reduces low-context AI PR review and provides contributor-facing proof | Good fit for transparent, auditable project policy | PR template/Action/Change Passport | Language plugins, docs, issue triage | Community trust and contributors must be earned |

## Release decision

The project is ready for a public alpha because the core workflow is end-to-end, tested, honest
about its trust boundary, and useful without future roadmap items. It is not labeled production
proven or v1.0 because community adoption, independent security review, additional language
semantics, and maintainer diversity do not exist yet.

