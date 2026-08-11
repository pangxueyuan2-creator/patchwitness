# Architecture

PatchWitness separates the thing making a change from the infrastructure producing evidence about
that change.

## Data flow

1. **Git adapter** resolves a trusted base commit, enumerates tracked and untracked changes, and
   computes SHA-256 for before/after blobs. Base blobs use one batch Git process; current files hash
   concurrently.
2. **Contract loader** reads TOML from the working tree for local iteration or directly from a
   trusted Git revision in CI.
3. **Policy engine** applies deny, allow, protected-surface, dependency, binary, and budget rules in
   a deterministic order.
4. **Check runner** executes explicit repository commands concurrently with timeouts and redaction.
   Clean-room mode applies the change to a disposable base-derived worktree with Git hooks disabled.
5. **Impact engine** builds a file import graph for Python, JavaScript, and TypeScript, reverses the
   edges, and finds direct/transitive dependents and affected tests. The graph cache is keyed by file
   path, size, and modification time.
6. **Security scanner** searches changed text files for high-confidence secret shapes while
   retaining only type, path, and line.
7. **Plugin runner** loads explicitly installed `patchwitness.analyzers` entry points and places
   isolated results under the extension namespace.
8. **Evidence builder** canonicalizes all facts, computes a payload SHA-256, verifies it, and writes
   JSON atomically.
9. **Reporters/adapters** render the same verified payload to CLI text, Markdown, SARIF, GitHub
   annotations, SDK objects, or MCP results.

## Package boundaries

| Module | Responsibility |
|---|---|
| `git.py` | Repository discovery, revision resolution, change and blob facts |
| `config.py` | Contract parsing, validation, initialization, task contract authoring |
| `policy.py` | Stable deterministic rule evaluation |
| `checks.py` | Bounded concurrent command execution |
| `cleanroom.py` | Hook-disabled disposable verifier worktrees |
| `impact.py` | Import graph, cache, downstream impact and risk heuristic |
| `security.py` | Value-free high-confidence secret findings |
| `evidence.py` | Orchestration, canonical digest, atomic persistence, verification |
| `plugins.py` | Analyzer protocol and entry-point discovery |
| `reporters.py` | Markdown, SARIF, GitHub, and rule help |
| `mcp.py` | Repository-confined stdio JSON-RPC tools |
| `sdk.py` | Embeddable facade |

## Compatibility contracts

- Evidence schema v1 fields will only receive backward-compatible additions during 0.x.
- Rule IDs keep their meaning within a schema major version.
- CLI exit codes are stable.
- Plugin output is namespaced and cannot alter core findings.
- Analyzer exceptions become explicit failed extension results; they do not disappear.

## Why no database or web service

A Change Passport is designed to travel with CI artifacts, releases, and pull requests. Keeping the
core stateless and zero-dependency makes air-gapped use, local inspection, and integration simple.
Remote stores and UIs belong behind adapters rather than inside the trust root.

