#Requires -Version 5.1
<#
.SYNOPSIS
  Dry-run the GCP VM compose path locally (validate config, batch-build, up, health, optional seed smoke).
.NOTES
  Uses project name ckac-gcp-dry and remapped ports (23000+/28000) so the main local stack can stay up.
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $Root

$EnvFile = Join-Path $Root "infra/gcp-vm/.env.dryrun"
$Example = Join-Path $Root "infra/gcp-vm/.env.production.example"

Write-Host "=== GCP VM dry-run (local) ===" -ForegroundColor Cyan

# 1) Seed script syntax
Write-Host "`n[1/6] Parse seed scripts..."
python -c @"
import ast, pathlib
files = [
  'scripts/seed-bulk-data.py',
  'scripts/seed_platform_extras.py',
  'scripts/demo_data.py',
  'scripts/bulk_demo_data.py',
]
for f in files:
  p = pathlib.Path(f)
  ast.parse(p.read_text(encoding='utf-8'))
  print('OK', f)
"@

# 2) Write dry-run env — also copy to .env because services use env_file: [.env]
Write-Host "`n[2/6] Write infra/gcp-vm/.env (dry-run secrets, APP_ENV=development)..."
$jwt = -join ((1..48) | ForEach-Object { "{0:x}" -f (Get-Random -Max 16) })
$key = -join ((1..32) | ForEach-Object { "{0:x}" -f (Get-Random -Max 16) })
$envBody = @"
POSTGRES_USER=ckac
POSTGRES_PASSWORD=ckac_dryrun_pw
POSTGRES_DB=ckac
APP_ENV=development
CORS_ORIGINS=http://localhost:23000,http://localhost:23001,http://localhost:23002,http://localhost:23003
JWT_SECRET=$jwt
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=480
JWT_REFRESH_EXPIRE_DAYS=7
INTERNAL_API_KEY=$key
WHATSAPP_VERIFY_TOKEN=ckac-dryrun-verify
ADMIN_EMAIL=admin@kitchcu.dev
ADMIN_PASSWORD=admin123456
MEDIA_STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio:9000
MINIO_SECURE=false
MINIO_ACCESS_KEY=ckac
MINIO_SECRET_KEY=ckac_minio_dev
MINIO_BUCKET=ckac-media
MINIO_PUBLIC_URL=http://localhost:9000
CUSTOMER_OAUTH_REDIRECT_BASE=http://localhost:23001
"@
$EnvProd = Join-Path $Root "infra/gcp-vm/.env"
# utf8NoBOM can fail on older PS — use UTF8
[System.IO.File]::WriteAllText($EnvFile, $envBody)
[System.IO.File]::WriteAllText($EnvProd, $envBody)

# 3) Compose config validate
Write-Host "`n[3/6] docker compose config..."
$composeArgs = @(
  "-p", "ckac-gcp-dry",
  "-f", "infra/gcp-vm/docker-compose.prod.yml",
  "-f", "infra/gcp-vm/docker-compose.dryrun.yml",
  "--env-file", "infra/gcp-vm/.env"
)
$cfg = docker compose @composeArgs config | Out-String
if ($LASTEXITCODE -ne 0) { throw "compose config failed" }
if ($cfg -match 'published: "?16379"?|published: "?15432"?|published: "?18000"?') {
  throw "dryrun ports still collide with local stack - check !override in docker-compose.dryrun.yml"
}
if ($cfg -notmatch '28000') {
  throw "gateway dryrun port 28000 missing from compose config"
}
Write-Host "OK compose config (ports remapped)"

# 4) Batch build (same batches as reset-fresh / startup)
Write-Host "`n[4/6] Batch build images..."
$env:COMPOSE_PARALLEL_LIMIT = "2"
$env:DOCKER_BUILDKIT = "1"
docker compose @composeArgs build identity catalog order billing notification gateway
if ($LASTEXITCODE -ne 0) { throw "batch1 build failed" }
docker compose @composeArgs build marketing ratings growth delivery learning community streaming
if ($LASTEXITCODE -ne 0) { throw "batch2 build failed" }
docker compose @composeArgs build portal-web kitchen-web customer-web admin-web
if ($LASTEXITCODE -ne 0) { throw "batch3 web build failed" }

# 5) Up + health
Write-Host "`n[5/6] Up stack (no caddy) + wait for gateway status=ok..."
docker compose @composeArgs up -d
$deadline = (Get-Date).AddMinutes(15)
$ready = $false
do {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:28000/health/ready" -UseBasicParsing -TimeoutSec 5
    $body = $r.Content
    Write-Host "ready: $($r.StatusCode) $($body.Substring(0, [Math]::Min(160, $body.Length)))"
    if ($r.StatusCode -eq 200 -and $body -match '"status"\s*:\s*"ok"') { $ready = $true; break }
  } catch {
    Write-Host "waiting: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds 8
} while ((Get-Date) -lt $deadline)

if (-not $ready) {
  docker compose @composeArgs ps
  docker compose @composeArgs logs --tail 40 identity catalog order gateway
  throw "Gateway not ready on :28000 (need status=ok, not degraded)"
}

# Smoke frontends
foreach ($p in @(23000, 23001, 23002, 23003)) {
  $fr = Invoke-WebRequest -Uri "http://127.0.0.1:$p/" -UseBasicParsing -TimeoutSec 10
  Write-Host "web :$p -> $($fr.StatusCode)"
}

# 6) Light seed smoke (1 kitchen) unless -SkipSeed
Write-Host "`n[6/6] Seed smoke (CKAC_BULK_KITCHENS=1)..."
$env:CKAC_GATEWAY_URL = "http://127.0.0.1:28000"
$env:CKAC_BULK_KITCHENS = "1"
$env:CKAC_BULK_FULL = "0"
python scripts/seed-bulk-data.py
if ($LASTEXITCODE -ne 0) { throw "seed smoke failed" }

Write-Host "`n=== DRY-RUN PASS ===" -ForegroundColor Green
Write-Host "Portal http://localhost:23000  Kitchen http://localhost:23002  Gateway http://localhost:28000"
Write-Host "Tear down: docker compose -p ckac-gcp-dry -f infra/gcp-vm/docker-compose.prod.yml -f infra/gcp-vm/docker-compose.dryrun.yml --env-file infra/gcp-vm/.env down -v"
