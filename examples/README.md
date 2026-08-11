# Runnable examples

Start with the scenario that proves the trust boundary, then use the repository shape closest to
your own project.

| Example | Time | What it proves |
|---|---:|---|
| `patchwitness scan` in your repository | About 30 seconds | Detects the local stack, runs repository-owned checks, and writes first evidence without a config file. |
| [Flagship workflow-risk demo](../demo/README.md) | About 60 seconds | Tests pass, but a protected CI change is independently blocked and sealed into a Change Passport. |
| [Python service](python-service/README.md) | About 5 minutes | A task contract limits an agent to pricing code and records a real test command. |
| [GitHub Actions](../docs/integrations/github-actions.md) | About 5 minutes | A pull request is evaluated against policy loaded from its immutable base SHA. |
| [MCP integration](../docs/integrations/mcp.md) | About 5 minutes | An agent host can capture, verify, and inspect impact through bounded stdio tools. |

Every example uses the real PatchWitness engine. Committed transcripts and passports are generated
artifacts, not hand-authored success output.

Before running checks in source you do not trust, use `patchwitness doctor` to inspect the detected
commands or start with `patchwitness scan --no-checks`. Detection is read-only; test commands execute
the repository's code with your local user permissions.
