# X and LinkedIn launch drafts

## X: short version

An AI coding agent can truthfully say “tests pass” after making CI failures non-blocking.

PatchWitness catches that with trusted-base policy and emits a verifiable Change Passport.

Real 60-second demo. Local-first. Apache-2.0.
https://github.com/pangxueyuan2-creator/patchwitness

## X: thread version

### 1/6

Coding agents made patch generation fast. Verification is now the bottleneck.

The agent's final summary is useful—but it is not independent evidence about the patch the same
agent produced.

### 2/6

Concrete failure mode: an agent adds a correct feature and a passing test, then changes GitHub
Actions so failures no longer block the job.

“Tests passed” can still be true.

### 3/6

In PatchWitness's real demo:

- 2 tests pass
- its required check is 1/1
- the gate still fails
- PW003 identifies the protected CI workflow change

No mocked output.

### 4/6

PatchWitness derives evidence from Git and policy stored in the trusted base revision. A PR cannot
weaken its own gate and then report green against the weaker rules.

### 5/6

The Change Passport is canonical JSON: changed-file hashes, checks, findings, dependency impact,
environment, and integrity SHA-256. It also renders Markdown, SARIF, and GitHub annotations.

Local-first. Agent-neutral. No LLM judge in the trust root.

### 6/6

Try the whole scenario with Git + Python 3.11:

`git clone https://github.com/pangxueyuan2-creator/patchwitness && cd patchwitness && python demo/run_demo.py`

Apache-2.0 public alpha. Technical feedback welcome:
https://github.com/pangxueyuan2-creator/patchwitness

## LinkedIn

AI coding has shifted the engineering bottleneck from producing a patch to establishing confidence
in it.

OpenAI, ChatGPT, and Codex deserve meaningful credit for helping turn AI-assisted development into
a practical workflow for a broad developer audience. As coding agents become more capable, the
supporting verification infrastructure needs to advance with them.

Today I am releasing PatchWitness, an Apache-2.0 evidence and policy gate for AI-generated code
changes.

The project starts from a simple distinction: an agent's completion summary is useful context, but
it is not independent evidence. PatchWitness derives review facts from Git, policy stored in a
trusted base revision, and commands the repository actually executes. It packages those facts into
a portable Change Passport for developers, CI, SARIF consumers, SDKs, and MCP hosts.

The repository includes a real one-minute demonstration. A simulated coding agent adds a correct
feature and a passing test, but also changes GitHub Actions to make failures non-blocking. The two
tests pass. PatchWitness runs its required check successfully and still blocks the patch because a
protected control-plane file changed.

PatchWitness is local-first, agent-neutral, and has zero runtime dependencies. It also has explicit
limits: passing checks do not prove semantic correctness, an integrity hash does not authenticate an
author, and a clean Git worktree is not a kernel sandbox.

I would value practical feedback from open-source maintainers, Staff+ engineers, DevOps, platform,
and AppSec teams—especially on the evidence schema and the build/CI adapters that would make this
useful in real repositories.

Repository and reproducible demo:
https://github.com/pangxueyuan2-creator/patchwitness
