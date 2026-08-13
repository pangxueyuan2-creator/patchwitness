# Contributing to PatchWitness

PatchWitness welcomes small, evidence-backed improvements to deterministic change verification. Useful contributions include reproducible bug fixes, focused tests, integration validation, documentation that reflects observed behavior, and analyzer plugins. This guide is designed to let a first-time contributor create a working development environment and run the core proof path in roughly five minutes on a public, non-sensitive checkout.

> Do not place credentials, private source, proprietary logs, real secret values, or sensitive Change Passports in Issues, tests, fixtures, commits, pull requests, or screenshots. For a suspected vulnerability, follow [SECURITY.md](SECURITY.md) instead of opening a public Issue.

## Five-minute development path

| Step | Command | Expected result |
| --- | --- | --- |
| Clone | `git clone https://github.com/pangxueyuan2-creator/patchwitness.git && cd patchwitness` | A clean checkout on `main`. |
| Create environment | `python -m venv .venv` | An isolated Python environment. |
| Activate | Linux/macOS: `source .venv/bin/activate`<br>Windows PowerShell: `.venv\Scripts\Activate.ps1` | `python` uses `.venv`. |
| Install dev tools | `python -m pip install --upgrade pip && python -m pip install -e ".[dev]"` | Editable CLI plus test, lint, type and build tools. |
| Run tests | `python -m pytest` | All tests pass, including integration fixtures. |
| Run static checks | `ruff check src tests && mypy src` | No lint or strict typing errors. |
| Run real Demo | `python demo/run_demo.py` | The intentionally risky workflow change is blocked and its Passport verifies offline. |
| Run change-risk benchmark | `python benchmarks/change-risk/run.py` | The allowed scenario passes and the four intentional control failures are observed. |

Use Python 3.11–3.14. The project has zero runtime dependencies; the `.[dev]` extra supplies only development and release-validation tools.

## Work with a small, reviewable change

Create a branch, make the smallest behavior change that solves the documented problem, and add a deterministic regression test or fixture before changing implementation. New code must remain local-first and deterministic: do not add network calls, model inference, hidden services, or private inputs to the core verification path.

Before opening a pull request, run the checks that match your change. Every code, policy, workflow, packaging, integration-hook or release-path change requires the relevant targeted test plus Ruff and mypy. Run the full local release preflight for a broad or higher-risk change:

```bash
make release-check
```

`release-check` runs coverage-enforced tests, Ruff, mypy, the real Demo, the five-scenario change-risk benchmark, build, Twine metadata validation and a clean-wheel installation. It is not required for a spelling-only correction, but it is required before proposing a release-path or packaging change.

## Exercise an integration fixture

Integration claims need executable evidence, not only prose. For example, the Codex Stop-hook adapter is tested without a model account or private repository:

```bash
python -m pytest tests/test_codex_hook.py
```

The fixture creates a temporary Git repository, modifies a protected workflow after the trusted base, asserts a `PW003` finding, checks that prompt-like values stay out of evidence, and verifies the Passport offline. When adding or changing a provider integration, add an equivalent public fixture and state exactly what it proves and what it does **not** prove.

For manual safe first-run behavior in a repository you trust, inspect detected commands before executing them:

```bash
patchwitness doctor
patchwitness scan --no-checks
```

Do not run repository-owned checks from an unknown or untrusted checkout merely to reproduce an Issue.

## Documentation and compatibility claims

Update the smallest documentation surface that a user will consult. Stable rule semantics belong in [docs/rules.md](docs/rules.md); evidence-format changes belong in [docs/evidence-schema.md](docs/evidence-schema.md); integration behavior belongs under [docs/integrations](docs/integrations/); and user-visible behavior changes belong in [CHANGELOG.md](CHANGELOG.md). Documentation must distinguish an observed fact, a fixture-verified adapter, an advisory local workflow, and an independent CI merge boundary.

Do not claim a provider endorsement, broad platform compatibility, a paid-agent execution, an adoption result, or a security guarantee unless the repository contains public, reproducible evidence for that exact claim. Keep version and platform limits explicit.

## Policy and security discipline

A committed `.patchwitness.toml` is a reviewable control plane. Preserve the trusted-base model: a pull request must not weaken its own policy and then use that working-tree policy to pass. New rules require documented semantics and tests; changing stable rule meaning requires careful compatibility review.

Never include secret values in findings, logs, fixtures or evidence packs. Keep hook and integration scripts conservative: minimize input fields, write evidence only within the Git workspace, locate executable tools outside the workspace, and default to `--no-checks` unless executing repository code is explicitly reviewed and intended.

## Pull request expectations

A pull request should be small enough to review without reconstructing a large refactor. Its description should explain the problem, the selected behavior, affected users or integrations, targeted validation performed, compatibility implications and security considerations. Include sanitized command output or a public fixture reference when it establishes a compatibility claim; never include private source or sensitive artifacts.

Run PatchWitness against the patch before submitting when the repository and commands are trusted:

```bash
git fetch origin main
patchwitness gate --base origin/main --policy-ref origin/main --clean-room
```

A failure caused by a protected policy or workflow change is an important review signal, not a reason to weaken controls. Explain the intentional control-plane change and let maintainers review it separately.

By contributing, you agree that your work is licensed under Apache-2.0. Review, triage, releases and security response follow the documented [maintainer workflow](MAINTAINER_WORKFLOW.md). Most organization- or language-specific analysis should be an entry-point plugin rather than a core dependency; see [Plugin development](docs/plugin-development.md).
