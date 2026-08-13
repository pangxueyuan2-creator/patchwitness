# Show HN Final Draft

**Status:** Prepared, not published.
**Account disclosure:** The poster is the PatchWitness maintainer.

## Title

```text
Show HN: PatchWitness – Independent evidence for AI-generated code changes
```

## Post body

I built PatchWitness because a coding agent’s completion message is useful context, but it is not independent evidence.

The failure mode I wanted to make concrete is small: an agent makes a correct product change and the test command passes, but the same patch also weakens a GitHub Actions workflow. “Tests passed” can be true while “the verifier was preserved” is false.

PatchWitness reads the actual Git change, loads a reviewed policy from a trusted base revision, records checks that really ran, and writes a canonical JSON Change Passport. The policy can reject out-of-scope paths, protected CI or policy changes, dependency changes, missing required checks and other explicit contract violations. The core is deterministic: it does not ask one model to grade another, upload source, fetch remote policy or execute a command merely because a repository mentioned it.

The public demo reproduces the control-plane case: two unit tests pass, then PatchWitness blocks the protected workflow change with `PW002` and `PW003`, and verifies the resulting Passport offline.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

I also added a small change-risk benchmark. It uses five fresh temporary repositories with policy loaded from `HEAD`: a permitted product-only change passes; product-plus-CI, out-of-scope and policy-self-modifying changes fail even while the known-safe check passes; and `--no-checks` is reported incomplete when policy requires a check. The raw scenarios and results are in `benchmarks/change-risk/`.

For an untrusted repository, the safest first path is structural inspection without executing repository code:

```bash
patchwitness doctor
patchwitness scan --no-checks
```

PatchWitness does not claim to be a kernel sandbox, semantic code reviewer, signer identity system, branch-protection replacement or deployment guarantee. A local agent hook is advisory; a protected CI job using policy from the pull-request base SHA is the intended merge boundary.

I would value technical criticism from maintainers and CI/AppSec engineers on two questions:

1. What evidence is missing from a portable, reviewable Change Passport?
2. Which agent or CI integration would be genuinely useful enough to test in a public repository?

Repository: https://github.com/pangxueyuan2-creator/patchwitness

## Publishing checklist

- Re-read [Show HN guidelines](https://news.ycombinator.com/showhn.html) on the posting day.
- Confirm the demo and `benchmarks/change-risk/run.py` pass from the linked revision.
- Post only once, without requesting votes, Stars or comments.
- Stay available for technical questions during the initial discussion.
- Answer limitations directly and never turn a question, index listing or traffic signal into a user-adoption claim.
