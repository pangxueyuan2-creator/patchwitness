# GitHub Copilot CLI: Safe Session-end Scan

This example runs a **local advisory PatchWitness scan** when a GitHub Copilot CLI session ends. It writes a Change Passport without executing detected tests or repository scripts. It is not a merge gate and it does not alter Copilot’s permissions.

## Install in a repository you trust

Install PatchWitness in the environment where Copilot CLI runs. Copy the three files into the target repository’s `.github/hooks/` directory, preserving their names.

```bash
mkdir -p .github/hooks
cp /path/to/patchwitness/examples/copilot-cli-hooks/.github/hooks/patchwitness-safe-scan.* .github/hooks/
chmod +x .github/hooks/patchwitness-safe-scan.sh
```

Restart Copilot CLI after adding or changing hook configuration. The JSON file uses `sessionEnd` and provides both Bash and PowerShell commands; the current [official Copilot CLI hooks guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks) describes repository-level hook location, lifecycle events and platform-specific commands.

## What runs

The scripts run only this command against the current Git repository:

```bash
patchwitness scan --no-checks --output .patchwitness/evidence/copilot-safe-scan-TIMESTAMP.json
```

They then verify the generated Passport locally. A finding is reported to the terminal, but the scripts exit `0` so a local advisory scan does not unexpectedly block an agent session. This is deliberate: a local session remains agent-controlled.

## Use a protected CI gate for enforcement

For a merge boundary, use the independent GitHub Actions job from [the PatchWitness GitHub Actions guide](../../docs/integrations/github-actions.md). Configure it to load policy from the trusted pull-request base SHA, use read-only permissions and produce the CI-owned Change Passport. Review all detected test commands before choosing to let any repository code execute.

## Limitations

This example was tested by executing the Bash script directly in the public PatchWitness repository. The PowerShell script is exercised directly by the Windows CI runner with a strict caller, a synthetic uncommitted change, and local Passport verification. This does **not** exercise Copilot CLI event dispatch, and it does not claim that every Copilot CLI release, Windows installation, shell policy or repository layout behaves identically. Validate the hook configuration in a non-sensitive repository before relying on it, and retain standard code review, branch protection and CI controls.
