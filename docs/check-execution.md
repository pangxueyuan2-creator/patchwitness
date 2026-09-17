# Check execution and capture limits

A required check must finish within its deadline **and** produce completely captured
output within the limits. A child exit code of zero alone is not enough.

## Execution contract

`scan`, `capture`, `gate` and SDK capture use the same runner. Commands remain
trusted repository/contract code; clean-room executable resolution and compound
command restrictions still apply. Checks are non-interactive (`stdin` is closed).
No credentials, workflow permissions or environment-isolation policy are changed.

The runner reads stdout and stderr separately and fairly in chunks of at most
8 KiB. Each stream accepts exactly 1,048,576 bytes; one additional byte fails the
check. This bounds **retained captured bytes**, not process RSS, Python allocation
and decoding overhead, operating-system pipe buffers or child memory usage. For
larger legitimate logs, configure the trusted check to emit a concise summary and
write its full log to a separately reviewed file; do not treat a truncated capture
as complete evidence.

The existing `timeout_seconds` deadline covers child execution and draining both
pipes, including a descendant holding a pipe after the shell exits. OS process
creation and individual platform system calls cannot be preempted by this loop.
A startup/pipe failure, output overflow or timeout never returns a passing result.

## Source scope after checks (unreleased fix)

PW032 now also rejects newly changed tracked or index paths, not just content
movement in paths recorded before checks. For example, a passing test that rewrites
an initially unchanged workflow, deletes or renames a tracked file, or stages a new
file cannot lend its result to a stale PASS. The gate exits 1, names the drifted
path, and keeps the original snapshot and real check result in the failing Passport.
A failure or timeout reading the final index is a runtime error (exit 2), not
permission to treat unknown paths as harmless untracked files.

New, unstaged build/test outputs remain outside the recorded scope for compatibility;
they are **not certified by that Passport**, including their contents or policy status.
Stage intended generated changes before rerunning the gate. Checks that intentionally
rewrite tracked generated files should finish generation before capture, or use a
clean-room verifier when those writes should not change the source checkout.

This observes the source checkout and index after checks, including source movement
during clean-room execution. Writes confined to the disposable verifier retain their
existing behavior. Observations are not an atomic snapshot: transient changes restored
before observation, subsequent edits, and detached processes remain outside this
check's guarantee. Evidence-v1 fields and digest rules are unchanged.

## Evidence v1 compatibility

The CheckResult field set and evidence schema are unchanged. Successful and
ordinary nonzero child results retain stdout-then-stderr ordering, UTF-8 replacement
decoding, universal newline conversion, redaction, excerpting and SHA-256 behavior.

| Condition | Check `exit_code` | `timed_out` | Output evidence |
| --- | --- | --- | --- |
| Complete capture within limits | Actual child exit code | false | Redacted complete output hash and excerpt |
| Deadline exceeded | null | true | Fixed deadline diagnostic |
| Output overflow, invalid limits, startup or pipe failure | 125 | false | Fixed boundary diagnostic |
| Existing clean-room command refusal | 126 | false | Existing refusal diagnostic |

125 is a **runner-generated failure**, not an observed child exit. Boundary failures
discard all partial child output before redaction or hashing; a prefix must not be
misrepresented as complete output. This deliberately changes timeout diagnostics
from partial logs to a fixed message. Required failures still produce PW021 and
make `gate` exit 1; a failing Passport can still pass offline integrity verification.
Integrity verification is not policy approval or an authenticity signature.

## Cleanup and limits

On POSIX, checks start a new session. Failure cleanup kills the process group, even
when the shell has exited, then waits up to two seconds for the direct process. An exited shell is reaped
before group signalling; a group-signal failure permits only one retry after direct
child cleanup. Persistent group errors remain explicit cleanup failures.
On Windows, cleanup attempts the system `taskkill /T /F` with a two-second deadline,
then kills/waits for the direct process with a separate two-second deadline.
Windows pipe polling supports Python 3.11 without blocking reader threads.

All parent pipe descriptors are closed on success or failure. No background reader
threads survive capture. This is **not** a process-tree security boundary: detached
POSIX sessions and Windows descendants after shell exit may escape cleanup. A
process that closes its output and continues in the background is also outside the
capture guarantee. Use an external container, VM, Windows Job Object or runner
isolation for untrusted tests; memory, filesystem and network restrictions are not
provided here.

## Regression checks

```bash
python -m pytest tests/test_check_process.py tests/test_checks.py tests/test_scope_drift.py -q
python demo/run_bounded_checks.py
```

The demo uses only synthetic source in a temporary Git repository and exercises the
real CLI, trusted committed contracts, gate exit codes and offline verification.
It does not invoke a model, reach the network or upload evidence.
