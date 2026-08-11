# Real-user discovery targets

Validated on 2026-08-11 from the projects' current GitHub metadata and community discussions. This is
a relevance map, not a mailing list. Do not open an issue or pull request merely to advertise
PatchWitness.

## Demand signals

- Hacker News developers are explicitly discussing
  [verification debt](https://news.ycombinator.com/item?id=47289406),
  [how to review agent output](https://news.ycombinator.com/item?id=46557580), and
  [who verifies AI-written software](https://news.ycombinator.com/item?id=47234917).
- r/devops has active discussions about
  [security and quality for AI-generated code](https://www.reddit.com/r/devops/comments/1n4z0rl/)
  and the need to review and secure
  [agent-generated CI/CD](https://www.reddit.com/r/devops/comments/1s28xen/).
- r/AI_Agents users describe the trust break as verifying
  [task scope and evidence](https://www.reddit.com/r/AI_Agents/comments/1tk6j3r/), which closely matches
  the Change Passport model.
- r/devsecops is discussing verification loops, policy controls, and auditability as part of
  [agent harness engineering](https://www.reddit.com/r/devsecops/comments/1toxh4e/).

These discussions are evidence of the problem, not permission to reply with a project link. Join
only when a new or existing thread asks for a solution that PatchWitness can demonstrate directly.

## Priority A: strongest integration fit

| Project / community | Why PatchWitness may help | Appropriate contact | Feature to emphasize |
|---|---|---|---|
| [Cline](https://github.com/cline/cline) | Its SDK, CLI, IDE agent, and headless CI mode produce repository changes across multiple surfaces. | Build and document a local post-task hook first; then use a project Discussion or integration channel if maintainers invite integrations. | Agent-neutral gate, task contracts, JSON/SDK output. |
| [OpenHands](https://github.com/OpenHands/OpenHands) | Autonomous issue-to-patch workflows need evidence that survives outside the agent session. | Reproduce on one public OpenHands-generated patch; share results in an existing relevant Discussion, not a new promotional issue. | Change Passport, clean-room checks, base policy. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | It maps GitHub issues to autonomous fixes and has a natural benchmark/evaluation boundary. | Create an optional evaluation adapter in a fork; approach maintainers only with measured results and a narrow integration proposal. | Scope contract, check evidence, benchmark-friendly JSON. |
| [Goose](https://github.com/aaif-goose/goose) | Extensible agents execute, edit, and test with many models; a model-neutral after-action gate fits the extension model. | Follow its extension contribution path and propose an example only after it works locally. | MCP/CLI integration and identical evidence across models. |
| [E2B](https://github.com/e2b-dev/E2B) | Secure execution environments answer “where code ran”; PatchWitness answers “what changed and what policy/checks proved.” | Publish a standalone integration recipe; ask for listing only if their docs have a community-integration process. | Complementary sandbox + Change Passport story. |
| [Daytona](https://github.com/daytonaio/daytona) | It provides secure elastic infrastructure for AI-generated code, making repository evidence a complementary artifact. | Prototype inside a Daytona workspace, measure setup time, then use the official community channel for feedback. | Local evidence inside isolated execution; no source upload. |
| [Dagger](https://github.com/dagger/dagger) | Portable local/CI pipelines can execute PatchWitness consistently and retain the JSON/SARIF result. | Publish a Dagger pipeline example in PatchWitness first; contact only through a relevant integrations discussion. | Reproducible CI execution and machine-readable reports. |
| [StepSecurity Harden-Runner](https://github.com/step-security/harden-runner) | Harden-Runner observes runner behavior; PatchWitness protects workflow/control-plane changes before execution. | Develop a combined GitHub Actions example and present it as complementary defense-in-depth. | PW003 plus runtime runner observability. |

## Priority B: coding-agent and agent-framework ecosystem

| Project / community | Why PatchWitness may help | Appropriate contact | Feature to emphasize |
|---|---|---|---|
| [OpenAI Codex](https://github.com/openai/codex) | A terminal coding agent can hand a deterministic passport to reviewers and CI after each task. | Publish a generic post-task recipe; use an existing feature discussion only if it asks about verification or hooks. | Trusted-base policy and agent-independent evidence. |
| [Claude Code](https://github.com/anthropics/claude-code) | Hooks and repository workflows can run a separate gate that the agent does not grade itself. | Share a tested hook recipe in PatchWitness docs; do not file an issue unless the documented hook behavior is insufficient. | Post-task gate, protected paths, explicit task scope. |
| [GitHub Copilot CLI](https://github.com/github/copilot-cli) | Terminal agent changes flow naturally into pull requests and GitHub Actions. | Build a copy-paste GitHub Actions example; participate only in relevant official Discussions. | GitHub annotations, SARIF, composite Action. |
| [Aider](https://github.com/Aider-AI/aider) | Aider's Git-centric workflow makes before/after hashes and task-scoped contracts easy to apply. | Write a short `aider -> patchwitness gate` recipe and ask users for feedback in Aider's community channel. | Git-derived evidence and low-friction CLI. |
| [Continue](https://github.com/continuedev/continue) | An open-source agent across IDE/CLI contexts benefits from a portable verifier outside the model provider. | Create a recipe using its existing config/hooks; submit docs only if the maintainers' contribution guide welcomes integrations. | Vendor neutrality, JSON and CI continuity. |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Multi-agent workflows need durable evidence at the boundary where coding tools modify repositories. | Build an example tool wrapper in PatchWitness; discuss only after there is a runnable example and clear non-overlap. | Python SDK, MCP, explicit handoff artifact. |
| [Microsoft AutoGen](https://github.com/microsoft/autogen) | Orchestrated agents can treat the passport as a deterministic tool result and approval gate. | Publish a minimal external sample rather than opening a product issue. | Structured JSON, deterministic gate, human approval. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Stateful agent graphs can branch on a verified gate result instead of model self-assessment. | Produce a tiny conditional-edge example, then use a community showcase channel if available. | Stable exit codes and typed SDK result. |
| [CrewAI](https://github.com/crewAIInc/crewAI) | Role-based agent teams still need a non-agent source of truth for repository changes. | Demonstrate as a final verification task; avoid implying CrewAI's own review agents are insufficient for semantic review. | Independent mechanical evidence, not another reviewer role. |

## Priority C: security and software-supply-chain alignment

| Project / community | Why PatchWitness may help | Appropriate contact | Feature to emphasize |
|---|---|---|---|
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Scorecard measures project security posture; PatchWitness records per-change policy and execution evidence. | Seek architecture feedback through an existing OpenSSF working group only after mapping schemas precisely. | Per-change evidence versus repository-level posture. |
| [in-toto](https://github.com/in-toto/in-toto) | Change Passports could eventually be wrapped in established supply-chain attestations. | Start with a design note comparing models; do not claim compatibility before implementing signatures/envelopes. | Canonical payload and future signer identity roadmap. |
| [SLSA](https://github.com/slsa-framework/slsa) | SLSA focuses on build provenance; PatchWitness covers pre-merge change and verification facts. | Participate in specification discussions only with a concrete gap analysis, not a product pitch. | Complementary pre-merge evidence boundary. |
| [Semgrep](https://github.com/semgrep/semgrep) | Semgrep can remain the semantic/static analyzer while PatchWitness records that it ran and protects its configuration. | Publish a repository check example and ask Semgrep users for practical feedback. | Orchestration evidence, protected config, SARIF coexistence. |
| [Trivy](https://github.com/aquasecurity/trivy) | Trivy findings can be required repository checks and retained in the passport's execution evidence. | Create a Docker/CI recipe before approaching its community. | Composable checks, secrets/config scan complement. |
| [MCP reference servers](https://github.com/modelcontextprotocol/servers) | Agent hosts need narrow tools and explicit permission boundaries around repository operations. | Share PatchWitness's stdio MCP design for review only in security/tooling discussions that invite examples. | Read/capture/impact tools, execution disabled by default. |

## Communities

| Community | Why it is relevant | Appropriate contact | Feature to emphasize |
|---|---|---|---|
| [Hacker News / Show HN](https://news.ycombinator.com/show) | Current discussions identify verification as the scaling bottleneck for agent-generated code. | One Show HN post after approval; remain present for technical questions and never ask for votes. | Real demo, design tradeoffs, explicit limitations. |
| [r/devops](https://www.reddit.com/r/devops/) | CI generation, workflow security, and production guardrails are direct concerns. | A single case-study post after checking current self-promotion rules; ask about existing practices. | Tests pass while CI control plane changes. |
| [r/opensource](https://www.reddit.com/r/opensource/) | Maintainers can evaluate transparency, contributor experience, licensing, and schema governance. | Disclose maintainer status and ask for design/contribution feedback, not stars. | Apache-2.0, zero dependencies, extensibility. |
| [r/programming](https://www.reddit.com/r/programming/) | The deterministic-versus-probabilistic review boundary is a programming-tool design question. | Post only if project submissions are currently allowed; lead with architecture and source. | Base-authoritative policy and canonical evidence. |
| [r/AI_Agents](https://www.reddit.com/r/AI_Agents/) | Users explicitly discuss agent trust, scope drift, and evidence packets. | Ask where the verifier belongs in real harnesses; do not paste links into unrelated trust threads. | Task contracts, MCP, post-agent handoff. |
| [r/devsecops](https://www.reddit.com/r/devsecops/) | Agent harness security discussions include verification loops, auditability, and policy controls. | Share the minimal workflow-risk reproduction after checking promotion rules. | Protected control plane and defense in depth. |

## Contact discipline

1. Build or reproduce the integration before contacting a project.
2. Prefer a relevant existing Discussion, integration gallery, or community channel.
3. Never open an Issue or PR whose only purpose is promotion.
4. State maintainer affiliation immediately.
5. Offer evidence, code, or a measured result; do not ask for stars.
6. Stop after one unanswered contact. No follow-up sequence or bulk messaging.
7. Track opt-outs and community rules in the launch log.

Roo Code was evaluated but excluded from the active target list because the checked repository is
currently archived. Re-evaluate the maintained successor before proposing any integration.
