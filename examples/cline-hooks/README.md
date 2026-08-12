# Cline TaskComplete hook

This example uses Cline's `TaskComplete.py` file-hook convention to create a structural Change
Passport after a successful agent turn. Copy the hook into a repository that Cline edits:

```bash
mkdir -p .cline/hooks
cp examples/cline-hooks/TaskComplete.py .cline/hooks/TaskComplete.py
chmod +x .cline/hooks/TaskComplete.py
```

On Windows, create `.cline\hooks` and copy the same Python file; Cline's current hook runner invokes
`.py` hooks through `py -3`, with a `python` fallback.

Install PatchWitness, then use Cline normally in the repository. The hook writes each result under
`.patchwitness/evidence/` and prints one short status line to Cline's hook log. It does not retain the
prompt, model response, user ID, or full hook payload.

Cline disables file hooks in `--yolo` mode. Use Cline's Act or Plan mode when you want this trigger.

The hook deliberately runs `patchwitness scan --no-checks`: an automatic post-task hook should not
execute code from a repository merely because an agent edited it. Use a reviewed
`.patchwitness.toml` and the [GitHub Action](../../docs/integrations/github-actions.md) for required
checks and merge enforcement.

Full setup, contract evidence, limitations, and a manual reproduction are in the
[Cline integration guide](../../docs/integrations/cline.md).
