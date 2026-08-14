# This repository-level Copilot CLI hook is advisory. It writes local evidence
# without executing repository-owned checks and never changes merge requirements.
$patchWitness = Get-Command patchwitness -ErrorAction SilentlyContinue
if ($null -eq $patchWitness) {
    [Console]::Error.WriteLine("PatchWitness hook: patchwitness is not installed; skipping local scan.")
    exit 0
}

$repoRoot = git rev-parse --show-toplevel 2>$null
if ([string]::IsNullOrWhiteSpace($repoRoot)) {
    [Console]::Error.WriteLine("PatchWitness hook: current directory is not a Git repository; skipping local scan.")
    exit 0
}

Set-Location $repoRoot
$evidenceDirectory = Join-Path $repoRoot ".patchwitness/evidence"
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$evidence = Join-Path $evidenceDirectory "copilot-safe-scan-$stamp.json"

& patchwitness scan --no-checks --output $evidence
$scanStatus = $LASTEXITCODE

if (Test-Path $evidence) {
    & patchwitness verify $evidence
    [Console]::Error.WriteLine("PatchWitness hook: local advisory passport: $evidence (scan exit $scanStatus)")
} else {
    [Console]::Error.WriteLine("PatchWitness hook: no passport was written (scan exit $scanStatus).")
}

exit 0
