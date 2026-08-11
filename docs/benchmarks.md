# Benchmarks

PatchWitness does not publish estimated or invented benchmark numbers. The harness is part of the
CLI, and raw results are committed under `benchmarks/results/`.

## Reproduce

```bash
patchwitness benchmark --files 250 --rounds 7 --output benchmark.json
```

The harness creates a temporary Git repository, writes a linear 250-module Python import graph,
commits it, modifies 50 files, and measures:

- Git change enumeration plus before/after SHA-256;
- cold impact graph construction;
- warm cached impact analysis.

It deletes the temporary repository after the run. Network access and model inference are not used.

## Maintainer baseline

Raw file: [windows-python314.json](../benchmarks/results/windows-python314.json)

| Environment | Value |
|---|---|
| Measured | 2026-08-11T06:53:21Z |
| OS | Windows 11 10.0.26200 AMD64 |
| Python | 3.14.5 |
| Repository / changed files | 250 / 50 |
| Rounds | 7 |

| Operation | Median | p95 |
|---|---:|---:|
| Git change collection | 200.935 ms | 209.552 ms |
| Cold impact | 19.684 ms | 129.844 ms |
| Warm impact | 3.946 ms | 4.166 ms |

This is a local synthetic baseline. Do not compare results across hardware, antivirus settings,
filesystems, Git versions, or repository shapes without controlling those variables.

