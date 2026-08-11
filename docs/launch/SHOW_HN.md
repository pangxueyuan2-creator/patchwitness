# Show HN launch draft

## Recommended title

Show HN: PatchWitness – a trust gate for AI-generated code changes

## Post

I built PatchWitness because a coding agent's completion message is useful context, but it is not
independent evidence.

The failure mode I wanted to make concrete is simple: an agent adds a correct feature and a passing
test, but also changes GitHub Actions to make failures non-blocking. “Tests passed” is true; “this
patch preserved the verifier” is false.

The repo now contains a real one-minute reproduction of that case. Two unit tests pass, then
PatchWitness loads policy from the trusted base commit and blocks the patch with:

```text
PatchWitness FAIL
  3 files | 10 lines | 1/1 checks
  ERROR PW002 [.github/workflows/ci.yml]: path is outside the approved scope
  ERROR PW003 [.github/workflows/ci.yml]: protected verification or control-plane file changed
```

It emits a Change Passport: canonical JSON containing the Git-derived change set, before/after
hashes, check exit codes and output hashes, policy findings, dependency impact, environment, and an
integrity hash. Reports can also be rendered as Markdown, SARIF, or GitHub annotations.

The trust root contains no LLM. Policy can come from the base SHA, checks can run in a disposable
hook-disabled worktree, and the core uploads no source. It is agent-neutral: Codex, Claude Code,
Copilot, Cline, Aider, custom agents, and human patches are treated the same.

Try the full risk demo with Git and Python 3.11+:

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

PatchWitness is an Apache-2.0 public alpha. It does not claim that passing tests prove correctness,
that SHA-256 authenticates an author, or that a Git worktree is a kernel sandbox. The threat model
and raw benchmark are in the repo.

I would especially value feedback from maintainers and CI/AppSec engineers on two questions:

1. Which evidence belongs in a portable Change Passport?
2. Which build-system or CI adapter would make this useful in a real repository?

Repository: https://github.com/pangxueyuan2-creator/patchwitness

## Posting notes

- Use the title exactly once; do not repost if it receives little attention.
- Stay available for technical questions for the first two hours.
- Lead with limitations when asked about sandboxing, signatures, or semantic correctness.
- Do not ask for stars or upvotes.
