# This repository-level Copilot CLI hook is advisory. It writes local evidence
# without executing repository-owned checks and never changes merge requirements.
# Stay advisory even when the caller set Stop / native-command error preference
# (pwsh 7 treats a non-zero patchwitness scan as a terminating error otherwise).
$ErrorActionPreference = 'Continue'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$patchWitness = Get-Command patchwitness -ErrorAction SilentlyContinue
if ($null -eq $patchWitness) {
    [Console]::Error.WriteLine("PatchWitness hook: patchwitness is not installed; skipping local scan.")
    exit 0
}

# Git stdout on Chinese Windows can be a different code page than pwsh 7 UTF-8,
# which corrupts Unicode user/temp paths (e.g. pytest-of-庞学渊). Prefer a path
# PowerShell already resolved; only trust git's toplevel if it exists on disk.
$inside = git rev-parse --is-inside-work-tree 2>$null
if ($inside -ne 'true') {
    [Console]::Error.WriteLine("PatchWitness hook: current directory is not a Git repository; skipping local scan.")
    exit 0
}
$gitTop = (git rev-parse --show-toplevel 2>$null)
if ($gitTop -and (Test-Path -LiteralPath $gitTop)) {
    $repoRoot = (Resolve-Path -LiteralPath $gitTop).ProviderPath
    Set-Location -LiteralPath $repoRoot
} else {
    $repoRoot = (Get-Location).ProviderPath
}
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
