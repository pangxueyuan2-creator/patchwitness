# Target Projects and Communities

**Research refreshed:** 2026-08-13 UTC
**Purpose:** Identify technically relevant places where a maintainer may *eventually* evaluate PatchWitness. This is a relevance map, not a contact list, and no row implies permission to open an Issue, PR, direct message or promotional discussion.

## Method and scoring

The 35 repositories below were rechecked through the GitHub repository API for public metadata, activity, archived status, topic fit and available Discussions. The raw snapshot is retained outside this repository for audit. Scores are deliberately about **potential**, not adoption: `Relevance` measures alignment with post-agent change verification; `Likelihood` measures whether a small optional example appears plausible *after current contribution rules are checked*; `Adoption value` measures the quality of a real maintained integration if the project independently accepts it. A score of 5 is not an entitlement to contact.

| Score | Meaning |
|---:|---|
| 5 | Direct technical fit with a documented agent/CI extension point or an unusually clear post-change verification boundary. |
| 4 | Strong adjacent fit; needs a local proof-of-concept and rules check. |
| 3 | Relevant ecosystem or research fit; usually a documentation/example target before any conversation. |
| 1–2 | Context only; not an active outreach priority. |

> **Contact gate:** Before any contact, build or reproduce the specific integration; read the project’s current CONTRIBUTING and channel rules; identify a current technical discussion or documented showcase route; disclose PatchWitness maintainer affiliation; ask for technical criticism rather than a Star or adoption; make no second follow-up after silence. Never open an Issue or PR whose only purpose is promotion.

## Priority A — build evidence first

| Project | R | L | V | Why it fits | First artifact before any conversation | Contact gate |
|---|---:|---:|---:|---|---|---|
| [Claude Code](https://github.com/anthropics/claude-code) | 5 | 4 | 5 | Official hooks can execute deterministic shell commands at lifecycle events, including after tools or when an agent completes.[1] | A sanitized post-task hook that invokes `patchwitness scan --no-checks` by default and documents the explicit opt-in to checks. | Only a relevant integration, hooks or security discussion; do not create a feature request. |
| [GitHub Copilot CLI](https://github.com/github/copilot-cli) | 5 | 4 | 5 | Repository-level hooks support session and tool lifecycle commands on Windows, macOS and Linux.[2] | Cross-platform hook example with a safe default, exit-code explanation and Change Passport path. | Use a discussion or showcase route if it exists; no marketing Issue. |
| [OpenAI Codex](https://github.com/openai/codex) | 5 | 3 | 5 | Terminal agent workflows have a direct post-task evidence boundary; hook behavior needs current-version verification before any recipe claim. | Provider-neutral shell recipe and a reproducible Codex-generated patch fixture. | Participate only in an existing hook/verification discussion or documented extension route. |
| [Cline](https://github.com/cline/cline) | 5 | 3 | 5 | SDK, IDE and headless agent modes make an agent-neutral post-task evidence artifact relevant. | Local Cline hook or command integration, tested against a public synthetic patch. | Confirm current SDK/extension contribution process and share only working evidence. |
| [Goose](https://github.com/aaif-goose/goose) | 5 | 3 | 4 | An extensible agent that executes, edits and tests can surface a deterministic final verification step. | A local extension or wrapper that preserves Goose’s existing approval model. | Only use a maintained extension/community channel after local validation. |
| [GitHub Agentic Workflows](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/) | 5 | 3 | 5 | GitHub’s technical-preview workflows run coding agents in Actions with explicit sandboxing, permissions, control and review boundaries.[3] | A standalone Action recipe demonstrating PatchWitness as a separate evidence stage after agent work. | Treat preview status and project rules carefully; no implied GitHub endorsement. |
| [OpenHands](https://github.com/OpenHands/OpenHands) | 5 | 2 | 5 | Autonomous issue-to-patch workflows have a natural post-task verification boundary. | Reproduce a public synthetic OpenHands patch and record a Change Passport. | Share only in a relevant existing Discussion or evaluation context. |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) | 5 | 2 | 4 | Issue-to-patch automation fits a benchmarkable scope/check-evidence handoff. | A forked, public evaluation fixture with documented limitations. | Do not approach maintainers before measured local results. |
| [PR-Agent](https://github.com/Qodo-AI/pr-agent) | 4 | 2 | 4 | AI PR review can consume deterministic facts without claiming PatchWitness replaces semantic review. | JSON/markdown summary prototype linking a Change Passport to a PR. | Use a documented integration channel only after showing non-overlap. |
| [Harden-Runner](https://github.com/step-security/harden-runner) | 5 | 3 | 4 | Runtime runner observability complements pre-execution protected-control-plane evidence. | Combined GitHub Actions example with separate signals and no false claim of integrated security coverage. | Only a relevant security/integrations discussion after workflow succeeds. |

## Priority B — strong ecosystem fit, research and examples first

| Project | R | L | V | Evidence-based technical angle | Appropriate first move |
|---|---:|---:|---|---|---|
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | 4 | 3 | 4 | Terminal coding agent; portable post-task recipe. | Build provider-neutral recipe; wait for a relevant extension/security discussion. |
| [Aider](https://github.com/Aider-AI/aider) | 4 | 3 | 4 | Git-centric agent flow matches Git-derived change evidence. | Document `aider → patchwitness gate` locally; request feedback only in a designated community route. |
| [Continue](https://github.com/continuedev/continue) | 4 | 2 | 4 | Open-source coding agent across IDE/CLI. | Build a minimal post-task example; inspect current contribution rules. |
| [OpenCode](https://github.com/anomalyco/opencode) | 4 | 3 | 4 | Active open coding-agent ecosystem with CLI workflow. | Validate a shell handoff rather than assume a hook API. |
| [GitHub MCP Server](https://github.com/github/github-mcp-server) | 4 | 2 | 4 | Agent hosts that change repositories can benefit from a bounded, separate verification tool. | Build a local composition example, not an issue. |
| [OpenAI Agents Python](https://github.com/openai/openai-agents-python) | 3 | 2 | 3 | Multi-agent workflows can consume a deterministic JSON result at a repository-changing tool boundary. | Build a small sample repository first. |
| [AutoGen](https://github.com/microsoft/autogen) | 3 | 2 | 3 | Orchestration workflows can branch on a deterministic gate result. | Publish a tiny local conditional-edge example. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 3 | 2 | 3 | Stateful graphs can retain a verification artifact before approval. | Build an example outside the project and label it independent. |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 3 | 2 | 3 | Final verification can be a non-agent mechanical step. | Create a public sample without disparaging CrewAI’s review design. |
| [DeepAgents](https://github.com/langchain-ai/deepagents) | 3 | 2 | 3 | Agent harness context; integration viability must be tested. | Research its current extension model before drafting anything. |
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | 3 | 2 | 3 | Agent orchestration with Python/.NET surfaces. | Produce a small external sample, not a product pitch. |
| [Semantic Kernel](https://github.com/microsoft/semantic-kernel) | 3 | 2 | 3 | Multi-agent/tool orchestration context. | Test a typed tool wrapper locally. |
| [Strands Agents](https://github.com/aws/strands-agents) | 3 | 2 | 3 | Agent framework with potential evidence handoff. | Confirm current tool lifecycle semantics first. |
| [Vercel AI SDK](https://github.com/vercel/ai) | 2 | 1 | 2 | Broad AI toolkit; repository patching is not its primary public boundary. | Research only; no active outreach. |
| [AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) | 2 | 2 | 2 | Educational resource, useful only if a curriculum contribution fits documented standards. | Do not propose inclusion without a lesson-quality contribution. |

## Priority C — security and supply-chain compositions

| Project | R | L | V | Boundary and first artifact |
|---|---:|---:|---|
| [Dagger](https://github.com/dagger/dagger) | 4 | 3 | 4 | A reusable pipeline can retain Change Passport JSON/SARIF. Create a local Dagger composition first. |
| [E2B](https://github.com/e2b-dev/E2B) | 4 | 2 | 4 | Sandbox answers where code ran; PatchWitness records what changed and what checks were evidenced. Build an independent recipe, not a co-marketing claim. |
| [Daytona](https://github.com/daytonaio/daytona) | 4 | 2 | 4 | Workspace isolation is complementary to repository evidence. Prototype in a public test workspace. |
| [Semgrep](https://github.com/semgrep/semgrep) | 4 | 2 | 4 | Semgrep can remain a required check whose execution evidence is retained. Build a composable CI recipe. |
| [Trivy](https://github.com/aquasecurity/trivy) | 4 | 2 | 4 | Trivy results can be an explicit required check. Create a public Docker/CI recipe. |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | 3 | 1 | 4 | Repository posture and per-change evidence are distinct. Write a precise design comparison before any community discussion. |
| [in-toto](https://github.com/in-toto/in-toto) | 3 | 1 | 4 | Potential future attestation envelope; no compatibility claim without implementation. |
| [SLSA](https://github.com/slsa-framework/slsa) | 3 | 1 | 4 | Build provenance differs from pre-merge change evidence. Keep discussion architectural and evidence-driven. |
| [Cosign](https://github.com/sigstore/cosign) | 3 | 1 | 4 | PatchWitness hashes are integrity markers, not authenticated signatures. Prototype end-to-end signing before describing integration. |
| [Syft](https://github.com/anchore/syft) | 3 | 2 | 3 | An SBOM command can be a required recorded check. Build an example and do not imply a product partnership. |
| [MCP reference servers](https://github.com/modelcontextprotocol/servers) | 3 | 1 | 3 | Reference point for narrow tool boundaries; share architecture only when invited. |

## Community opportunity rules

| Community | Valid technical question | Required conditions | Explicit non-goals |
|---|---|---|---|
| Hacker News / Show HN | Where should independent evidence sit after an AI coding agent changes a repository? | Runnable no-registration Demo, maker available for technical discussion and approval immediately before posting. | Votes, generic announcement, copy/paste responses. |
| r/devops | How do teams detect a correct patch that also weakens CI control-plane controls? | Same-day rule review, suitable thread or allowed project post, maintainer affiliation disclosed. | Cross-posting, direct traffic request, claims of adoption. |
| r/opensource | What belongs in a transparent agent-change evidence artifact? | Same-day flair/rule review, contribution-oriented framing, public source. | Drive-by promotion or Star request. |
| r/AI_Agents and r/devsecops | Which deterministic inputs/outputs matter to an agent-harness verification loop? | A current technical thread that invites answers and no rule conflict. | Inserting a link into unrelated trust discussions. |
| DEV / Hashnode | Why tests passing can be insufficient for agent-authored patches. | An independently useful article with real commands, limitations and source citations. | Thin product announcement or hidden affiliation. |

## Deferred and disallowed actions

No external repository will be contacted from this research alone. Do not send a private message, create an Issue/PR, or post a comment merely because it is scored highly. The highest-value next action is to produce and test a narrow, optional hook or Action example for one documented hook surface, then wait for a maintainer-invited venue or a genuine related conversation.

## References

[1]: https://code.claude.com/docs/en/hooks-guide "Claude Code hooks guide"
[2]: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks "GitHub Copilot CLI hooks"
[3]: https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/ "GitHub Agentic Workflows technical preview"
