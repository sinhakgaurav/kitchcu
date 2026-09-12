# Full platform seed — dev baseline + bulk data + all personas
# Optional env:
# Optional env:
#   CKAC_BULK_KITCHENS=30 CKAC_BULK_FULL=1 CKAC_FEATURE_VOLUME=1 CKAC_SEED_EXTRAS=1
#   CKAC_WEEKLY_MANIFEST=C:\temp\weekly-cohort.json
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
# Avoid Windows cp1252 crashes on seed log lines (arrows / en-dashes).
$env:PYTHONIOENCODING = "utf-8"

if (-not $env:CKAC_GATEWAY_URL) {
    $env:CKAC_GATEWAY_URL = "http://localhost:18000"
}
if (-not $env:CKAC_SEED_EXTRAS) {
    $env:CKAC_SEED_EXTRAS = "1"
}

Write-Host "=== CKAC full platform seed ===" -ForegroundColor Cyan
Write-Host "Gateway: $env:CKAC_GATEWAY_URL"

Write-Host "`n[1/3] Dev baseline (owners, kitchens, menu, sample orders)..."
python "$PSScriptRoot\seed-dev-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/3] Bulk + feature volume (every kitchen + diner, every module)..."
python "$PSScriptRoot\seed-bulk-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[3/3] Weekly QA cohort (current ISO week)..."
$weeklyArgs = @()
if ($env:CKAC_WEEKLY_MANIFEST) {
    $weeklyArgs = @("--manifest", $env:CKAC_WEEKLY_MANIFEST)
}
python "$PSScriptRoot\weekly_test_data.py" @weeklyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nFull platform seed complete." -ForegroundColor Green
