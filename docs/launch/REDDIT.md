# Reddit launch drafts

## r/programming / r/opensource title

PatchWitness: a local-first trust gate for AI-generated code changes (no LLM reviewer, Apache-2.0)

## Body

AI coding agents are useful, but their completion summaries are not independent evidence. I built
PatchWitness to mechanically verify scope, protected files, change budgets, dependency surfaces,
and repository checks, then emit an offline-verifiable Change Passport.

The unusual part is `--policy-ref`: CI loads the policy from the base SHA, so a PR cannot weaken its
own gate and report green. `--clean-room` applies the patch to a disposable Git worktree with hooks
disabled. Output supports JSON, Markdown, SARIF, GitHub annotations, SDK, MCP, and plugins.

It is a public alpha, not production-proven. The threat model calls out that clean-room mode is not a
kernel sandbox and SHA-256 is not signer identity. Feedback and adversarial testing are welcome.

https://github.com/pangxueyuan2-creator/patchwitness

## Community etiquette

- Read each community's self-promotion rules before posting.
- Post once where relevant; do not cross-post in bulk.
- Disclose maintainer affiliation in the first paragraph.
- Answer technical questions and accept criticism; do not ask for stars.

