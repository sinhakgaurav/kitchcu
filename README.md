# kitchCU — Cloud Kitchen Platform

> **Agents & developers:** Read [`AGENTS.md`](AGENTS.md) before any code change or implementation.

Phase 1 Sprint 1 scaffold: Docker stack, API gateway, identity service, PostgreSQL + PostGIS.

## Quick Start

```powershell
# Copy environment file
copy .env.example .env

# Start infrastructure + services
docker compose up --build

# Seed demo owner, kitchen, menu (8 dishes with images), and sample orders
python scripts/seed-dev-data.py

# Customer app:  http://localhost:13001  (customer.kitchcu.in)
# Kitchen app:   http://localhost:13002  (kitchen.kitchcu.in)
# Admin app:     http://localhost:13003  (admin.kitchcu.in)
# Portal:        http://localhost:13000  (kitchcu.in)
# API Gateway:   http://localhost:18000/docs
```

## Demo credentials (after seed)

| Field | Value |
|-------|-------|
| Owner phone (kitchen.kitchcu.in) | `9876543210` |
| OTP (dev) | `123456` |
| Kitchen code (customer.kitchcu.in) | `CKPNQ001` |
| Admin (admin.kitchcu.in) | `admin@kitchcu.dev` / `admin123456` |

- **Portal:** http://localhost:13000
- **Kitchen owners:** http://localhost:13002/login
- **Customers:** http://localhost:13001
- **Admin:** http://localhost:13003

Re-run `python scripts/seed-dev-data.py` anytime — it is idempotent.

## Services

| Service | Port | Description |
|---------|------|-------------|
| gateway | 18000 | API gateway (routes to all services) |
| identity | 18001 | Owner registration, kitchen onboarding, auth |
| catalog | 18002 | Dishes, categories, menu |
| order | 18003 | Manual orders, lifecycle, history |
| postgres | 15432 | PostgreSQL 16 + PostGIS |
| redis | 16379 | Cache & event bus (Phase 1) |
| minio | 9000/9001 | S3-compatible media storage |

## Owner Onboarding Flow (API)

```bash
# 1. Register owner
curl -X POST http://localhost:18000/api/v1/owners/register \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","name":"Raj Kitchen","email":"raj@example.com"}'

# 2. Request OTP (dev OTP: 123456)
curl -X POST http://localhost:18000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919876543210"}'

# 3. Verify OTP → get JWT
curl -X POST http://localhost:18000/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919876543210","otp":"123456"}'

# 4. Create kitchen (use token from step 3)
curl -X POST http://localhost:18000/api/v1/kitchens \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Raj Home Kitchen",
    "address_line":"Koregaon Park",
    "city":"Pune",
    "state":"Maharashtra",
    "latitude":18.5362,
    "longitude":73.8958
  }'
```

## Project Structure

```
CKAC/
├── apps/
│   └── website/          # Marketing landing page (parallax)
├── docs/                 # Benchmark & pitch deck
├── infra/postgres/init/  # DB extensions & schemas
├── packages/ckac-common/ # Shared config, DB, events
├── services/
│   ├── gateway/          # FastAPI API gateway
│   └── identity/         # Owner & kitchen service
├── docker-compose.yml
└── scripts/
```

## Run Tests

Requires Docker stack running (`docker compose up -d`).

```powershell
.\scripts\run-tests.ps1
```

Or manually:

```powershell
cd services/identity
$env:DATABASE_URL="postgresql+asyncpg://ckac:ckac_dev@localhost:15432/ckac"
$env:DATABASE_SYNC_URL="postgresql://ckac:ckac_dev@localhost:15432/ckac"
python -m pytest -v
```

**Coverage:** 25 identity tests (auth, owners, kitchens, schemas, health) + 7 gateway tests (proxy, health).

## Local Development (without Docker)

```powershell
cd packages/ckac-common && pip install -e .
cd services/identity && pip install -e ".[dev]"
# Start postgres + redis via docker compose up postgres redis -d
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

## Documentation

See [docs/README.md](docs/README.md) for full planning benchmark and pitch deck.

## Marketing Website

```powershell
cd apps/website
npm install
npm run dev
```

Open **http://localhost:13000** — Features, Services, Onboard, Contact with multi-layer parallax.

## Phase 1 Roadmap

- [x] Sprint 1: Docker, identity, kitchen onboarding
- [x] Sprint 2: Catalog service + live photo metadata
- [x] Sprint 3: Order service + manual orders
- [x] Sprint 4: WhatsApp webhook + message parser
- [ ] Sprint 5: Owner PWA
