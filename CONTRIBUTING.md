# Contributing to PatchWitness

Thanks for helping make AI-assisted software changes easier to verify. PatchWitness welcomes bug
reports, documentation improvements, new language analyzers, integrations, and core changes.

## Before opening work

- Search existing issues and discussions.
- For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of filing publicly.
- Open an issue before a large architectural change so maintainers and contributors can align.
- Keep claims measurable. Benchmarks must include the command, environment, raw result, and date.

## Development setup

```bash
git clone https://github.com/pangxueyuan2-creator/patchwitness.git
cd patchwitness
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
python -m pytest
ruff check src tests
mypy src
python -m build
```

## Change discipline

1. Add or update a test that captures the intended behavior.
2. Keep deterministic core behavior free of network calls and model inference.
3. Never include secret values in findings, logs, fixtures, or evidence packs.
4. Document new rules in `docs/rules.md` and preserve rule semantics within evidence schema v1.
5. Update `CHANGELOG.md` for user-visible changes.
6. Run PatchWitness against the patch before submitting:

```bash
patchwitness gate --base origin/main --policy-ref origin/main --clean-room
```

## Pull requests

PRs should explain the problem, the chosen behavior, tests run, compatibility impact, and security
considerations. Small, reviewable changes merge faster. By contributing, you agree that your work is
licensed under Apache-2.0. Review, triage, releases, and security response follow the documented
[maintainer workflow](MAINTAINER_WORKFLOW.md).

## Analyzer plugins

Most organization- or language-specific analysis should be an entry-point plugin instead of a core
dependency. See [Plugin development](docs/plugin-development.md).
