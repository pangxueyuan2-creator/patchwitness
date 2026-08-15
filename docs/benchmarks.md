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

## Windows scale comparison (2026-08-15)

Same machine as the maintainer baseline (Windows 11 10.0.26200 AMD64, Python 3.14.5).
Raw files:

- [windows-20260815-small-25.json](../benchmarks/results/windows-20260815-small-25.json)
- [windows-20260815-medium-250.json](../benchmarks/results/windows-20260815-medium-250.json)
- [windows-20260815-large-1000.json](../benchmarks/results/windows-20260815-large-1000.json)

| Size | Files / changed / rounds | Collect median | Collect p95 | Cold median | Cold p95 | Warm median |
|---|---:|---:|---:|---:|---:|---:|
| small | 25 / 5 / 5 | 186.384 ms | 203.321 ms | 3.015 ms | 14.726 ms | 1.165 ms |
| medium | 250 / 50 / 5 | 263.315 ms | 276.766 ms | 28.378 ms | 151.056 ms | 4.655 ms |
| large | 1000 / 200 / 3 | 510.459 ms | 525.712 ms | 162.529 ms | 739.869 ms | 28.152 ms |

The large run previously hung on Windows: `git cat-file --batch` wrote every blob query
before reading any response and filled the 4 KiB anonymous pipe. After interleaved I/O
the same 1000-file / 3-round command completed and produced the file above. Medium collect
is slower than the 2026-08-11 baseline (263 ms vs 201 ms); that is the measured result on
this run, not a claim of regression or improvement.

