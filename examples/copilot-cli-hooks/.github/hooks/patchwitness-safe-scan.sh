#!/usr/bin/env bash
set -euo pipefail

# This repository-level Copilot CLI hook is advisory. It writes local evidence
# without executing repository-owned checks and never changes the agent's
# permission model or merge requirements.
if ! command -v patchwitness >/dev/null 2>&1; then
  printf '%s\n' 'PatchWitness hook: patchwitness is not installed; skipping local scan.' >&2
  exit 0
fi

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  printf '%s\n' 'PatchWitness hook: current directory is not a Git repository; skipping local scan.' >&2
  exit 0
fi

cd "$repo_root"
mkdir -p .patchwitness/evidence
stamp=$(date -u +%Y%m%dT%H%M%SZ)
evidence=".patchwitness/evidence/copilot-safe-scan-${stamp}.json"

set +e
patchwitness scan --no-checks --output "$evidence"
scan_status=$?
set -e

if [ -f "$evidence" ]; then
  patchwitness verify "$evidence" || true
  printf 'PatchWitness hook: local advisory passport: %s (scan exit %s)\n' "$evidence" "$scan_status" >&2
else
  printf 'PatchWitness hook: no passport was written (scan exit %s).\n' "$scan_status" >&2
fi

exit 0
