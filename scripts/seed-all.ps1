# Full platform seed — dev baseline + bulk data + all personas
# Optional env:
# Optional env:
#   CKAC_BULK_KITCHENS=30 CKAC_BULK_FULL=1 CKAC_BULK_ORDERS_PER_KITCHEN=40 CKAC_SEED_EXTRAS=1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:CKAC_GATEWAY_URL) {
    $env:CKAC_GATEWAY_URL = "http://localhost:18000"
}
if (-not $env:CKAC_SEED_EXTRAS) {
    $env:CKAC_SEED_EXTRAS = "1"
}

Write-Host "=== CKAC full platform seed ===" -ForegroundColor Cyan
Write-Host "Gateway: $env:CKAC_GATEWAY_URL"

Write-Host "`n[1/2] Dev baseline (owner, kitchen, menu, sample orders)..."
python "$PSScriptRoot\seed-dev-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/2] Bulk data + platform extras (reports, CRM, ratings, recipes, referrals)..."
python "$PSScriptRoot\seed-bulk-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nFull platform seed complete." -ForegroundColor Green
