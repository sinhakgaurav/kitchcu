# Seed demo owner, kitchen, menu, and orders (requires docker compose stack running)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $env:CKAC_GATEWAY_URL) {
    $env:CKAC_GATEWAY_URL = "http://localhost:18000"
}

Write-Host "Seeding CKAC demo data via $env:CKAC_GATEWAY_URL ..."
python "$PSScriptRoot\seed-dev-data.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
