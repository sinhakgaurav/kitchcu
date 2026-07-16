# Seed multiple owners, kitchens, menus, orders, drafts, and platform extras.
# Optional environment variables:
#   CKAC_BULK_OWNERS, CKAC_BULK_KITCHENS, CKAC_BULK_KITCHENS_PER_OWNER
#   CKAC_BULK_ORDERS, CKAC_BULK_ORDERS_PER_OWNER
#   CKAC_BULK_DRAFTS, CKAC_BULK_DRAFTS_PER_OWNER
#   CKAC_SEED_EXTRAS=1  (customers, ratings, CRM, coupons, enterprise sub, recipes)
# For full stack: .\scripts\seed-all.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:CKAC_GATEWAY_URL) {
    $env:CKAC_GATEWAY_URL = "http://localhost:18000"
}

Write-Host "Seeding CKAC multi-owner bulk data via $env:CKAC_GATEWAY_URL ..."
python "$PSScriptRoot\seed-bulk-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
