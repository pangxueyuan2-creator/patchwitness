# Reddit launch drafts

Every version below discloses maintainer affiliation. Check current subreddit rules before posting,
choose one relevant community first, and participate in replies. Do not cross-post all versions at
once.

## r/opensource

> Status on 2026-08-12: do not repost. The existing submission was automatically removed because
> the Reddit account is under the community's one-year age requirement. Do not evade the rule with
> another account or moderator solicitation.

### Title

I built an Apache-2.0 trust gate for AI-generated patches; looking for evidence-schema feedback

### Body

Maintainer here. I have released PatchWitness, a local-first Python project that turns a Git change
into a portable “Change Passport.”

The motivation is not that coding agents are bad. They are increasingly useful. The problem is that
their final summary is produced by the same system that produced the patch. I wanted a small,
inspectable trust layer that derives facts from Git, a contract stored in the trusted base commit,
and checks the repository actually executes.

The repo includes a real risk demo: the simulated agent adds a correct function and a passing test,
but also changes GitHub Actions to make failures non-blocking. The tests pass; PatchWitness still
reports the workflow as outside scope and protected (`PW002`/`PW003`). The generated JSON passport
is committed and verifies offline.

The core has zero runtime dependencies and supports CLI, Python SDK, JSON, Markdown, SARIF, GitHub
annotations, MCP, analyzer entry points, Docker, and a GitHub Action. It is a public alpha with an
explicit threat model—not a claim that hashes or tests prove correctness.

Three-command demo:

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

I would value open-source maintainer feedback on schema stability, contribution boundaries, and the
first language/build adapters worth supporting. I am not looking for reciprocal stars.

https://github.com/pangxueyuan2-creator/patchwitness

## r/devops

### Title

The tests passed, but the coding agent made CI failures non-blocking

### Body

I maintain PatchWitness and built a small reproducible case around a CI failure mode I worry about.

A simulated coding-agent patch adds a correct pricing function and a unit test. It also adds
`continue-on-error: true` to the GitHub Actions job. Running the repository tests produces `OK`.
Running PatchWitness produces `1/1 checks` and still fails the gate because the workflow is outside
the task scope and is a protected control-plane file.

The distinction is important: test execution answers whether the current test command passed.
It does not answer whether the patch weakened the mechanism that makes failures block a merge.

PatchWitness loads its contract from the base SHA, computes the change set from Git, optionally runs
checks in a disposable hook-disabled worktree, and emits canonical JSON plus SARIF/GitHub output.
The tool is local-first and agent-neutral; no model sits in the trust root.

Reproduce it in about a minute:

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

I am interested in how DevOps teams currently protect workflow files, generated IaC, and policy
configuration from agent-authored changes. Would a portable evidence artifact help, or is this best
kept entirely in existing branch protection and CODEOWNERS?

Repo and threat model: https://github.com/pangxueyuan2-creator/patchwitness

## r/programming

### Title

PatchWitness: deterministic Change Passports for AI-generated code changes

### Body

I am the maintainer of PatchWitness, an experiment in separating a code-producing system from the
evidence used to review its output.

Instead of asking another LLM whether a patch looks safe, PatchWitness records narrower mechanical
claims: the Git-derived files and hashes, whether paths fit a task contract, whether protected
verification files changed, which commands ran and their exit codes, and which source files/tests
sit downstream in a local dependency graph. The result is canonical JSON with an integrity hash and
renderers for Markdown, SARIF, and GitHub annotations.

The key design choice is base-authoritative policy. CI can load `.patchwitness.toml` from the base
commit, so a pull request cannot weaken the gate and then evaluate itself against the weaker rules.

The repository includes an end-to-end demo where all tests pass but a change to
`.github/workflows/ci.yml` is blocked. It runs with Git and Python 3.11+:

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

This is Apache-2.0 and still a public alpha. Known limits are explicit: tests are incomplete
specifications, SHA-256 is not signer identity, the clean worktree is not a kernel sandbox, and the
dependency graph is conservative.

I would welcome technical criticism of the trust model and evidence schema.

https://github.com/pangxueyuan2-creator/patchwitness

## r/AI_Agents or a relevant coding-agent community

### Title

Where should the trust boundary live when a coding agent edits its own verifier?

### Body

I maintain PatchWitness and am looking for feedback from people running coding agents on real
repositories.

Agent summaries are valuable, but scope compliance and test execution are currently often reported
by the same agent that made the patch. That becomes awkward when the agent can also edit CI,
repository policy, hooks, or the test command itself.

PatchWitness puts a deterministic boundary after the agent. It reads the actual Git change, loads a
task contract from a trusted base revision, runs repository checks, computes dependency impact, and
emits a verifiable Change Passport. It does not care which model or agent produced the patch.

The one-minute demo intentionally gives the agent a mixed patch: a correct feature and passing test,
plus a workflow edit that makes CI non-blocking. Tests pass; the gate rejects the control-plane
change.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

I am curious where this belongs in real agent harnesses: a post-task hook, a CI requirement, an MCP
tool the orchestrator calls, or a separate service the agent cannot modify? Concrete workflow
experience would be more useful than stars.

https://github.com/pangxueyuan2-creator/patchwitness

## r/ChatGPTCoding weekly self-promotion thread

### Comment

I maintain PatchWitness, an Apache-2.0 independent verifier for patches produced by coding agents.

Tools such as OpenAI Codex and ChatGPT have made agent-generated code dramatically more capable. The
remaining trust problem is that an agent may change both the implementation and the controls that
claim the implementation is safe.

The reproducible demo contains a correct feature and a passing test, but also adds
`continue-on-error: true` to GitHub Actions. The tests pass. PatchWitness still blocks the patch
because the protected workflow changed outside the declared scope.

PatchWitness derives the change set from Git, loads policy from the trusted base revision, executes
real repository checks, and emits an offline-verifiable Change Passport. No LLM judges its own work.
It is agent-neutral and provides a local CLI, GitHub Action, JSON/SARIF output, SDK, and MCP interface.

Repository and 60-second demo:
https://github.com/pangxueyuan2-creator/patchwitness

GitHub Marketplace:
https://github.com/marketplace/actions/patchwitness-gate

I would value critical feedback from people using Codex, ChatGPT, Cline, Claude Code, Cursor, or
autonomous coding workflows: would you use a separate verification layer before merging
agent-authored changes, and what evidence would it need to produce?

If you try it and genuinely find it useful, a star helps other developers discover it.

## Community etiquette

- Read each community's current self-promotion and account-age rules before posting.
- Post only where the technical topic is already relevant; never paste these into unrelated threads.
- Do not post the same day to all communities.
- Answer questions, publish corrections, and accept critical feedback.
- Do not ask for upvotes, stars, testimonials, or reciprocal promotion.
