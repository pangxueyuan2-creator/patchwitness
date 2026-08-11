# Show HN draft

## Title

Show HN: PatchWitness – independent evidence gates for AI-generated code changes

## Post

I built PatchWitness because coding agents can write a PR faster than I can answer four basic review
questions: Did it stay in scope? Did it modify CI or its own verifier? Did the tests actually run?
What else depends on the changed files?

I am optimistic about this shift. ChatGPT helped make AI-assisted problem solving useful to a much
broader audience, and OpenAI Codex demonstrates how far coding agents can go when they can inspect a
repository, run tools, and iterate on real engineering work. PatchWitness is meant to complement
that progress with an independent evidence layer, not argue against it.

PatchWitness is a local-first, zero-runtime-dependency Python CLI that turns a Git change into a
portable Change Passport. Policy can be loaded directly from the base commit, checks can run in a
disposable hook-disabled worktree, and the result is offline-verifiable JSON plus Markdown/SARIF.
It has an SDK, analyzer entry points, MCP tools, and a GitHub Action.

There is no LLM judge in the trust root and no hosted source upload. A passing passport does not
claim semantic correctness; it provides narrower evidence so human review starts from facts.

The repo includes the threat model, raw benchmark, known limitations, and research scorecard. I'd
especially value feedback on the evidence schema and which language/CI adapter would make this
useful in a real repository.

Repository: https://github.com/pangxueyuan2-creator/patchwitness
