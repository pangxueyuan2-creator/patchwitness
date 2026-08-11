# Analyzer plugin development

Analyzer plugins add evidence without modifying the deterministic core.

```python
from patchwitness.plugins import AnalyzerContext


class OwnershipAnalyzer:
    name = "ownership"

    def analyze(self, context: AnalyzerContext) -> dict[str, object]:
        changed = [item.path for item in context.changes]
        return {"changed_paths": changed, "needs_owner_review": bool(changed)}
```

Register it in `pyproject.toml`:

```toml
[project.entry-points."patchwitness.analyzers"]
ownership = "your_package:OwnershipAnalyzer"
```

Plugins are discovered in deterministic name order. Results are stored under
`extensions.analyzers.<name>`. Exceptions become explicit failure objects. Plugins cannot remove or
rewrite core findings.

## Design rules

- Return JSON-serializable data.
- Make analysis deterministic for the same context.
- Do not perform network calls unless your plugin's documentation makes that behavior explicit.
- Never return secret values or unredacted source content.
- Set finite time/resource limits for external processes.
- Use a unique, stable plugin name.
- Test against the oldest supported Python version.

Plugins run in-process and are trusted code. PatchWitness never downloads or installs them
automatically.

