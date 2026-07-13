# Run all kitchCU tests (requires Docker postgres + redis)
$ErrorActionPreference = "Stop"

$env:DATABASE_URL = "postgresql+asyncpg://ckac:ckac_dev@localhost:15432/ckac"
$env:DATABASE_SYNC_URL = "postgresql://ckac:ckac_dev@localhost:15432/ckac"
$env:REDIS_URL = "redis://localhost:16379/0"
$env:JWT_SECRET = "test-secret-key-for-pytest"
$env:INTERNAL_API_KEY = "test-internal-key-for-pytest"
$env:WHATSAPP_VERIFY_TOKEN = "ckac-dev-verify"
$env:ORDER_SERVICE_URL = "http://localhost:18003"

Write-Host "Running identity migrations..."
Push-Location "$PSScriptRoot\..\services\identity"
python -m alembic upgrade head
Pop-Location

Write-Host "Running catalog migrations..."
Push-Location "$PSScriptRoot\..\services\catalog"
python -m alembic upgrade head
Pop-Location

Write-Host "Running order migrations..."
Push-Location "$PSScriptRoot\..\services\order"
python -m alembic upgrade head
Pop-Location

Write-Host "Running billing migrations..."
Push-Location "$PSScriptRoot\..\services\billing"
python -m alembic upgrade head
Pop-Location

Write-Host "Running marketing migrations..."
Push-Location "$PSScriptRoot\..\services\marketing"
python -m alembic upgrade head
Pop-Location

Write-Host "Running ratings migrations..."
Push-Location "$PSScriptRoot\..\services\ratings"
python -m alembic upgrade head
Pop-Location

Write-Host "Running growth migrations..."
Push-Location "$PSScriptRoot\..\services\growth"
python -m alembic upgrade head
Pop-Location

Write-Host "Running delivery migrations..."
Push-Location "$PSScriptRoot\..\services\delivery"
python -m alembic upgrade head
Pop-Location

Write-Host "Running learning migrations..."
Push-Location "$PSScriptRoot\..\services\learning"
python -m alembic upgrade head
Pop-Location

Write-Host "Running community migrations..."
Push-Location "$PSScriptRoot\..\services\community"
python -m alembic upgrade head
Pop-Location

Write-Host "Bootstrapping events outbox..."
python -c @"
import psycopg2
from pathlib import Path
root = Path(r'$PSScriptRoot\..')
url = 'postgresql://ckac:ckac_dev@localhost:15432/ckac'
conn = psycopg2.connect(url)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute('CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"')
    cur.execute('CREATE SCHEMA IF NOT EXISTS ckac_events')
    for name in ('02-events.sql', '03-events-fix.sql'):
        cur.execute((root / 'infra' / 'postgres' / 'init' / name).read_text(encoding='utf-8'))
conn.close()
"@

Write-Host "Running identity service tests..."
Push-Location "$PSScriptRoot\..\services\identity"
python -m pytest -q
Pop-Location

Write-Host "Running catalog service tests..."
Push-Location "$PSScriptRoot\..\services\catalog"
python -m pytest -q
Pop-Location

Write-Host "Running order service tests..."
Push-Location "$PSScriptRoot\..\services\order"
python -m pytest -q
Pop-Location

Write-Host "Running billing service tests..."
Push-Location "$PSScriptRoot\..\services\billing"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running marketing service tests..."
Push-Location "$PSScriptRoot\..\services\marketing"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running ratings service tests..."
Push-Location "$PSScriptRoot\..\services\ratings"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running growth service tests..."
Push-Location "$PSScriptRoot\..\services\growth"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running delivery service tests..."
Push-Location "$PSScriptRoot\..\services\delivery"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running learning service tests..."
Push-Location "$PSScriptRoot\..\services\learning"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running community service tests..."
Push-Location "$PSScriptRoot\..\services\community"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running notification migrations..."
Push-Location "$PSScriptRoot\..\services\notification"
python -m alembic upgrade head
Pop-Location

Write-Host "Running notification service tests..."
Push-Location "$PSScriptRoot\..\services\notification"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "Running gateway tests..."
Push-Location "$PSScriptRoot\..\services\gateway"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "All tests complete."
