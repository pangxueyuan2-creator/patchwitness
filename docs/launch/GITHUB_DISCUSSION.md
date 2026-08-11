# GitHub Welcome / Launch Discussion draft

## Title

Welcome to PatchWitness — what should a trustworthy Change Passport prove next?

## Body

PatchWitness v0.1.0 is now public. It provides a deterministic, local-first evidence layer for
AI-generated and human-authored repository changes.

The core answers five narrow questions:

1. Did the patch stay inside its approved task scope?
2. Did it change CI, policy, or another protected verification surface?
3. Which repository-owned checks actually ran, and what were their exit codes?
4. What source files and tests are downstream of the change?
5. Can another tool verify and ingest the resulting evidence later?

The best place to start is the real one-minute risk demo:

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

In that scenario, the coding-agent patch adds a correct feature and a passing test while also making
CI failures non-blocking. Tests pass; PatchWitness still blocks the protected workflow change and
generates an offline-verifiable Change Passport.

If you try PatchWitness, please reply with:

```text
Repository language/build system:
Coding agent or human workflow:
Where you ran PatchWitness (local hook, CI, orchestrator, MCP, other):
Useful finding:
Noisy or missing evidence:
Preferred integration (core rule, plugin, provider, CI adapter):
```

Questions about the trust model, evidence schema, and roadmap are welcome. Adversarial examples are
especially valuable when they are minimal and reproducible.

Please do not paste private source, credentials, proprietary logs, or sensitive Change Passports
into a public discussion. Follow `SECURITY.md` for vulnerability reports.

PatchWitness is a public alpha. A passing passport does not prove semantic correctness; SHA-256 does
not establish signer identity; and clean-room mode is not an OS-level sandbox.
