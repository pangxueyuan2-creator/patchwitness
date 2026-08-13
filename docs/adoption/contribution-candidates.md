# Contribution Candidate Drafts

These are **drafts**, not open GitHub Issues. They exist so a future public `good first issue` or `help wanted` label corresponds to a real, bounded need. Before publishing any draft, check for duplicates, verify the task still reflects current code, apply the correct labels, and obtain approval for the public Issue.

## Candidate 1: Validate the Copilot CLI hook example on Windows

**Suggested labels:** `documentation`, `integration`, `good first issue`
**Why it is real:** The repository now includes a Bash and PowerShell safe-scan example. The Bash script has been executed against the public repository; the Windows PowerShell path has not been verified in this environment.

**Scope:** Use a non-sensitive Git repository with GitHub Copilot CLI and PatchWitness installed. Validate the `.github/hooks/patchwitness-safe-scan.json` configuration and PowerShell script. Improve documentation only where observed behavior differs from the published steps.

**Acceptance criteria:**

1. A contributor records the Copilot CLI version, PowerShell version and operating-system version in a sanitized PR description.
2. `sessionEnd` invokes the PowerShell script in a test repository.
3. The script writes a timestamped `.patchwitness/evidence/copilot-safe-scan-*.json` Passport using `--no-checks`.
4. The Passport verifies with `patchwitness verify`.
5. Documentation changes explain only observed differences; no claims are made for untested Copilot versions.

**Out of scope:** Editing Copilot permissions, marking an advisory local scan as a required gate, private repository evidence, product rewrites or unrelated formatting.

## Candidate 2: Add a documented Codex post-task recipe backed by a public fixture

**Suggested labels:** `documentation`, `integration`, `help wanted`
**Why it is real:** Codex is a high-fit target, but PatchWitness must not claim a hook integration until a documented configuration is reproduced against a public fixture.

**Scope:** Create a narrowly scoped recipe under `examples/` or `docs/integrations/` that runs PatchWitness after a Codex-authored patch in a synthetic public repository. The recipe must use trusted-base policy and explain whether it is an advisory local step or independent CI step.

**Acceptance criteria:**

1. The exact Codex version and official configuration source are cited.
2. The example reproduces a passing scoped patch and a protected-control-plane failure.
3. The default path uses `--no-checks` unless the fixture’s command is explicitly reviewed and safe.
4. The guide states that the local agent session is not the independent merge boundary.
5. Tests or an executable fixture prove every claimed command and result.

**Out of scope:** Unverified Codex hook claims, API credentials, private repositories, LLM-based judging or policy bypasses.

## Candidate 3: Extend the change-risk benchmark with a documented false-positive review case

**Suggested labels:** `tests`, `benchmark`, `good first issue`
**Why it is real:** The current benchmark covers permitted changes and four intentional evidence failures. A carefully designed false-positive-review fixture can strengthen the documented boundary without adding a new detector.

**Scope:** Propose one small, public fixture where a legitimate path or generated artifact initially conflicts with an explicit policy. The contribution must demonstrate whether a policy refinement—rather than a detector relaxation—is the correct resolution.

**Acceptance criteria:**

1. The fixture has a concrete repository shape and does not rely on a hidden service or proprietary input.
2. Expected policy, finding IDs and result are asserted in the benchmark harness or tests.
3. The documentation explains why the fixture is a policy-review example rather than a claim of false-positive rate.
4. The change preserves the trusted-base and protected-policy boundary.
5. `pytest`, linting and the benchmark reproduction command pass.

**Out of scope:** Changing stable finding semantics solely to make the benchmark pass, synthetic performance claims or removing intentional failure cases.

## Maintainer response standard

If any draft becomes an Issue, maintainers should acknowledge it promptly, reproduce it with public/sanitized inputs, state the review boundary and either accept, narrow or close it with technical reasoning. A low-quality PR should not be merged merely to create activity evidence.
