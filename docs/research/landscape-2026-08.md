# 2026 AI developer infrastructure opportunity research

**Snapshot date:** 2026-08-11  
**Method:** GitHub Trending and repository/issues search, Hacker News scan, Reddit developer threads,
official standards/security guidance, project documentation, and current product announcements.

This is a product strategy scorecard, not a scientific measurement. Each dimension is a comparative
1-10 judgment based on the cited snapshot. Scores intentionally include competition density and
implementation risk in the relevant dimensions.

## Signals that shaped the decision

- Agent use is rising while human review remains the default: Stack Overflow reported 59% agent use
  in its 2026 pulse survey, while 63% rarely or never allow fully autonomous system changes and
  accuracy/security remain top concerns.
- Trust is the bottleneck: the 2025 Stack Overflow survey found 84% using or planning AI tools but
  only 29% trusting AI output, and its 2026 material says agent usage rose while concern grew.
- GitHub's agentic workflows are read-only by default, sandboxed, and use preapproved safe outputs,
  validating that control/evidence belongs outside natural-language agent behavior.
- MCP's official security guidance documents token, session, prompt-injection, tool-change, and SSRF
  risks. OWASP's 2026 Agentic Top 10 highlights goal hijacking, tool misuse, identity abuse, supply
  chain risk, and unexpected code execution.
- OpenTelemetry standardizes agent/model/tool traces, reducing the opportunity for yet another
  proprietary observability schema while leaving change-specific trust evidence open.
- Community threads repeatedly ask whether an agent stayed in scope, really ran tests, or modified
  verification surfaces. Existing answers are fragmented among transcripts, scanners, PR bots, and
  general supply-chain attestations.

## 16 directions scored

Dimensions: **D** demand, **S** severity, **U** potential users, **B** technical barrier, **I**
innovation, **P** propagation, **G** GitHub-star potential, **E** ecosystem value, **X**
extensibility, **L** longevity, **C** commercial-team value, **F** implementation feasibility.

| # | Direction | D | S | U | B | I | P | G | E | X | L | C | F | Total /120 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Independent evidence/trust gate for AI code changes | 10 | 9 | 10 | 8 | 8 | 9 | 9 | 10 | 10 | 10 | 10 | 9 | **112** |
| 2 | MCP runtime authorization and policy proxy | 10 | 10 | 9 | 9 | 8 | 8 | 9 | 10 | 10 | 10 | 10 | 7 | 110 |
| 3 | Agent trace record/replay and behavioral diff | 9 | 8 | 9 | 8 | 7 | 8 | 8 | 9 | 9 | 9 | 9 | 8 | 101 |
| 4 | Self-hosted secure sandbox fabric | 10 | 10 | 9 | 10 | 7 | 8 | 9 | 10 | 9 | 10 | 10 | 5 | 107 |
| 5 | Repository context compiler/token-budget optimizer | 9 | 8 | 10 | 8 | 7 | 9 | 9 | 9 | 10 | 9 | 9 | 8 | 105 |
| 6 | Durable agent memory with poisoning defenses | 9 | 9 | 10 | 9 | 8 | 9 | 9 | 10 | 10 | 10 | 10 | 6 | 109 |
| 7 | Agent fault injection and resilience testing | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | 9 | 9 | 8 | 100 |
| 8 | Agent skill/plugin supply-chain scanner | 9 | 10 | 9 | 9 | 9 | 9 | 9 | 10 | 9 | 10 | 10 | 7 | 110 |
| 9 | Computer-use deterministic test harness | 8 | 8 | 8 | 9 | 8 | 9 | 9 | 9 | 9 | 9 | 9 | 6 | 101 |
| 10 | Multi-agent orchestration/coordination protocol | 8 | 7 | 9 | 8 | 6 | 9 | 8 | 9 | 10 | 8 | 8 | 7 | 97 |
| 11 | Agent identity, delegation, and revocable authority | 9 | 10 | 8 | 10 | 9 | 7 | 8 | 10 | 10 | 10 | 10 | 5 | 106 |
| 12 | Semantic repository blast-radius graph | 9 | 8 | 10 | 9 | 7 | 8 | 8 | 9 | 10 | 10 | 10 | 7 | 105 |
| 13 | Local inference router/cost-quality optimizer | 8 | 7 | 9 | 8 | 6 | 8 | 8 | 9 | 9 | 8 | 9 | 7 | 96 |
| 14 | Autonomous CI/incident diagnosis and remediation | 8 | 8 | 9 | 8 | 7 | 8 | 8 | 9 | 9 | 9 | 10 | 7 | 100 |
| 15 | AI-introduced dependency/provenance firewall | 9 | 10 | 10 | 9 | 8 | 9 | 9 | 10 | 10 | 10 | 10 | 6 | 110 |
| 16 | General agent observability dashboard | 9 | 8 | 9 | 7 | 5 | 8 | 7 | 9 | 8 | 8 | 9 | 8 | 95 |

## Decision

Direction 1 wins because it sits at the point where adoption, security, review capacity, and
software supply-chain concerns converge, while remaining useful without an LLM, cloud service, or
specific coding agent. It can also absorb focused capabilities from directions 12 and 15 through
impact and analyzer plugins.

The product wedge is deliberately narrow: **prove scope and execution facts for a patch**. The
platform opportunity is broad: a portable Change Passport protocol and extension ecosystem that CI,
agents, code hosts, policy engines, security tools, and release systems can consume.

## Competition and white space

| Category | Strong existing work | Remaining opening |
|---|---|---|
| Agent observability | OpenTelemetry GenAI conventions, Phoenix, Langfuse, AgentReplay | Repository-change contract, base policy, and PR evidence rather than runtime span UI |
| Replay/evals | promptfoo, Inspect AI, agent replay tools, MCP replay tools | Independent change proof tied to Git before/after state and real verifier commands |
| Supply-chain attestation | in-toto Witness, Sigstore, GitHub artifact attestations | Coding-task scope and agent-change semantics before artifact build |
| Code/security scanning | CodeQL, Semgrep, GitHub security scanning | Did the change stay authorized and avoid changing its verifier? |
| MCP/agent security | MCP gateways, OWASP guidance, sandbox projects | Agent-neutral Git change gate that complements the runtime control plane |
| Blast radius | Sourcegraph-style graphs and new graph tools | Lightweight zero-service impact evidence embedded in one portable passport |

## Sources

Primary/official sources were preferred for technical claims:

- [GitHub Trending, weekly snapshot](https://github.com/trending?since=weekly)
- [GitHub Agentic Workflows technical preview](https://github.blog/changelog/2026-02-13-github-agentic-workflows-are-now-in-technical-preview/)
- [GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
- [GitHub Copilot coding agent updates](https://github.blog/ai-and-ml/github-copilot/whats-new-with-github-copilot-coding-agent/)
- [Stack Overflow: closing the developer AI trust gap](https://stackoverflow.blog/2026/02/18/closing-the-developer-ai-trust-gap/)
- [Stack Overflow: agents on a leash](https://stackoverflow.blog/2026/05/27/agents-on-a-leash-agentic-ai-remains-mostly-monitored-at-work/)
- [MCP security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)
- [NSA MCP Security Design Considerations](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf)
- [OpenTelemetry GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/)
- [Early Adoption of Agentic Coding Tools by GitHub Projects](https://arxiv.org/abs/2607.14037)
- [Hacker News front page/community scan](https://news.ycombinator.com/)
- [Reddit discussion: trust evidence for agent PRs](https://www.reddit.com/r/ClaudeCode/comments/1tkbmkz/ai_coding_agents_what_evidence_would_make_you/)
- [Reddit discussion: AI agent review capacity](https://www.reddit.com/r/programming/comments/1qzsxy9/96_engineers_dont_fully_trust_ai_output_yet_only/)
- [in-toto Witness](https://github.com/in-toto/witness)
- [AgentReplay](https://github.com/agentreplay/agentreplay)
- [Kubernetes Agent Sandbox](https://agent-sandbox.sigs.k8s.io/)

