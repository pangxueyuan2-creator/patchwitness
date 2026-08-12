# Early-adopter guide

PatchWitness is seeking 10 real, non-maintainer trial runs before choosing its next major
integration. This is an evidence-gathering program, not a request for stars, endorsements, or
positive reviews.

## Option 1: reproduce the known risk case

Prerequisites: Git and Python 3.11 or newer. No package installation is required.

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python demo/run_demo.py
```

The demo adds a correct feature and passing test while also making a GitHub Actions failure
non-blocking. A useful result contains passing repository tests, `PW002` and `PW003` findings, a
generated Change Passport, and a successful offline verification of that passport.

## Option 2: inspect a trusted repository without executing it

Install the public release:

```bash
pipx install "https://github.com/pangxueyuan2-creator/patchwitness/releases/download/v0.2.0/patchwitness-0.2.0-py3-none-any.whl"
```

Inside a Git repository:

```bash
patchwitness doctor
patchwitness scan --no-checks
```

`doctor` reads repository metadata and reports the detected project profile. `scan --no-checks`
collects structural change evidence without running repository code. Use a full `patchwitness scan`
only when you trust the repository and have reviewed the detected commands.

## Report what happened

Open a [Trial Report](https://github.com/pangxueyuan2-creator/patchwitness/issues/new?template=trial-report.yml)
and include:

- the PatchWitness version and trial path;
- the public repository URL, or only a sanitized language/build-system description;
- the coding-agent, human, CI, or orchestrator workflow;
- commands, exit codes, and sanitized findings;
- what was useful, noisy, confusing, or missing; and
- whether the trial may be counted anonymously or linked publicly.

Negative results are welcome. A report that PatchWitness adds no value to a workflow is more useful
than an unverified endorsement.

## Privacy and security

Do not paste private source, credentials, proprietary logs, secret values, or sensitive Change
Passports into a public issue. Report vulnerabilities through
[private security advisories](https://github.com/pangxueyuan2-creator/patchwitness/security/advisories/new).
PatchWitness does not add telemetry for this program; adoption is recorded only from public or
explicitly opted-in evidence.

## Local feedback and CI enforcement

The recommended rollout uses both:

1. Run `patchwitness scan` locally or from an agent post-task hook for fast, advisory feedback.
2. Review and commit `.patchwitness.toml` on the protected base branch.
3. Add [PatchWitness Gate](https://github.com/marketplace/actions/patchwitness-gate) to pull requests,
   load policy from the immutable base SHA, and make the job required in branch protection.

Local runs shorten the feedback loop, but the developer or agent still controls that environment.
The required CI job is the enforcement boundary. CODEOWNERS and branch protection remain responsible
for protecting the base branch and deciding who may approve policy changes.
