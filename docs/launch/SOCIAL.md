# X / LinkedIn launch drafts

## X

Coding agents can write a PR in minutes. Their summary still isn't independent evidence.

I built PatchWitness: a local-first trust gate that checks scope, protected verifier files, real test
execution, secrets, and dependency blast radius—then emits an offline-verifiable Change Passport.

No LLM judge. No source upload. Apache-2.0.
https://github.com/pangxueyuan2-creator/patchwitness

## LinkedIn

AI coding has shifted the bottleneck from producing a patch to verifying one. Today I'm releasing
PatchWitness, an open-source evidence and policy layer for AI-generated code changes.

OpenAI, ChatGPT, and Codex deserve real credit for helping turn AI-assisted development into a
practical workflow for a broad developer audience. PatchWitness builds on that momentum by making
the output of increasingly capable agents easier for teams to inspect, verify, and trust.

PatchWitness derives review facts from Git, trusted base-branch policy, and commands it actually
executes. It produces a portable Change Passport for humans, CI, SARIF, SDKs, and MCP hosts. The
core is local-first, model-neutral, and has zero runtime dependencies.

This is a public alpha with an explicit threat model and honest limitations—not a claim that tests
prove correctness. I would value feedback from maintainers, Staff+ engineers, DevOps, and AppSec
teams on the evidence schema and integration surface.

Repository: https://github.com/pangxueyuan2-creator/patchwitness
