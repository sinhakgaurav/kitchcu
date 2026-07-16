# kitchCU — Agent Implementation Specification

**Read this document before any code change, feature implementation, or refactor.**

**Operating charter (strict):** `.cursor/rules/kitchcu-executive-operating-charter.mdc` — always on. Act as CEO · CPO · CTO · Senior Full-Stack · UX · DBA · QA Lead. Target **100k+ concurrent sessions**. TDD + EDD + microservices + tenant-safe DB + brand UX are mandatory.

**kitchCU** = Growth Operating System for cloud kitchens & home food businesses (internal repo/schemas use `ckac_*` identifiers).

**Engineering gate:** New modules/features require [`docs/templates/MODULE-DESIGN-PACK.md`](docs/templates/MODULE-DESIGN-PACK.md) before code. Full constitution: [`docs/KITCHCU-ENGINEERING-STANDARDS.md`](docs/KITCHCU-ENGINEERING-STANDARDS.md). Never ship TODO/dummy/placeholder logic or restaurant POS features.

| Doc | Purpose |
|-----|---------|
| **This file (`AGENTS.md`)** | Agent rules for every implementation |
| **`docs/KITCHCU-ENGINEERING-STANDARDS.md`** | **Engineering constitution — DDD, EDD, quality, security, phase targets** |
| **`docs/templates/MODULE-DESIGN-PACK.md`** | **Required pre-code design template (10-step gate)** |
| **`packages/ai-context/`** | **WhatsApp + support AI training/context pack** (options-first, FAQ answer_ids, order/menu extract, tickets) — branch `feature/whatsapp-ai-model-training` |
| `docs/CKAC-COMPLETE-GUIDE.md` | **Master guide v3.1** — CEO + CPO + CTO encyclopedia (definitions, how/why, flows, UI Catalog, aggregated OpenAPI reference + PDF) |
| `docs/CKAC-USERFLOWS.md` | **Full user journey pack** — every persona, every screen, every API call, step-by-step (+ PDF) |
| `docs/API.md` | **Public API reference** — auth, body/response examples; live aggregated OpenAPI at gateway `/openapi.json`/`/docs`/`/redoc` + portal `/openapi` |
| `docs/CKAC-ARCHITECTURE-CTO.md` | **CTO layers + CPO product ↔ code map** |
| `docs/CKAC-PRODUCT-DEPTH-GUIDE.md` | Product depth guide (superseded by Complete Guide) |
| `docs/CKAC-IMPLEMENTATION-GUIDE.md` | **What's built — mapped to planning & system benchmarks** |
| `docs/DEVELOPMENT-PHASES.md` | **Phased roadmap — TDD, EDD, DB schemas, sprints** |
| `docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md` | Full 48-feature spec + acceptance criteria |
| `docs/CKAC-SYSTEM-BENCHMARK.md` | Architecture, DB, caching, SLOs |
| `docs/CKAC-PITCH-DECK.pdf` | CPO Product Blueprint PDF v4.2 (modules, flows, pain points, OpenAPI) |
| `docs/CKAC-CPO-PRODUCT-BLUEPRINT.md` | CPO blueprint source v4.2 (markdown) |

---

## 1. Product North Star

**For owners:** Run the entire kitchen from one PWA — WhatsApp orders → revenue report same day.  
**For customers:** Trust through live-capture photos, home-taste ratings, fair delivery fees.  
**Business model:** Owner subscription SaaS — **no per-order food commission**.

### Non-Negotiable Principles

1. **Quality over speed** — owner-set prep/delivery times; never fake "10 min delivery" races
2. **Truth in media** — dish hero images must be live-capture (no stock photo deception)
3. **Owner owns CRM** — customer spend, patterns, coupons belong to the kitchen
4. **Progressive complexity** — MVP features first; hide advanced features until kitchen has traction
5. **Minimal diff** — only change what the task requires; match existing conventions

---

## 2. Current Implementation Status (Baseline)

### Implemented (Phase 1) ✅

| Component | Location | Notes |
|-----------|----------|-------|
| API Gateway | `services/gateway/` | Multi-service router (identity + catalog + order) |
| Identity service | `services/identity/` | Owners, kitchens, OTP, JWT |
| **Catalog service** | `services/catalog/` | **Sprint 2** — categories, dishes, menu, EDD |
| **Order service** | `services/order/` | **Sprint 3** — manual orders, lifecycle, history |
| **Billing service** | `services/billing/` | **Sprint 6** — payments, UPI intents, owner subscriptions; **GST**; **refunds** — full (gateway or direct) / partial (direct UPI/bank + evidence) |
| **Marketing service** | `services/marketing/` | **Sprint 10** — CRM (F37), coupons (F36), promotions (F38) |
| **Ratings service** | `services/ratings/` | **Sprint 11** — home taste ratings (F16–F18) |
| **Growth service** | `services/growth/` | **Sprint 12** — combos (F09), patterns (F10), suggestions (F11), daily menu push (F39) |
| **Delivery service** | `services/delivery/` | **Sprint 13** — fee quotes (F27–F28), distance (F31), tracking (F29) |
| **Notification service** | `services/notification/` | **Sprint 4** — WhatsApp webhook, AI support chat, ticketing; **S14** — order notifications, tracking intervals (F29/F45) |
| **Customer auth** | `services/identity/` | Social OAuth (Google, Facebook, Instagram, Twitter/X) + WhatsApp OTP; JWT `type: customer` |
| **Website PWAs** | `apps/website/` | Portal :13000, customer.kitchcu.in :13001, kitchen.kitchcu.in :13002, admin.kitchcu.in :13003 |
| **Customer checkout** | `services/order/`, `apps/website/` | **S5** — cart, checkout, customer JWT orders, billing customer payments |
| **Discovery + history** | `services/identity/`, `apps/website/` | **S7** — F32 nearby map/filters (diet, live-capture); F33 order history + repeat |
| **Multi-kitchen checkout** | `services/order/`, `apps/website/` | **S8** — F06 grouped cart, master receipt, atomic sub-orders |
| **Split payment** | `services/billing/` | **S9** — F44 aggregated payment + Route split settlements |
| **Marketing / CRM** | `services/marketing/`, `apps/website/` | **S10** — F36 coupons, F37 CRM, F38 targeted promotions |
| **Ratings** | `services/ratings/`, `apps/website/` | **S11** — F16–F18 home taste ratings, aggregates, A/V reviews |
| **Growth intelligence** | `services/growth/`, `apps/website/` | **S12** — F09 combos, F10 patterns, F11 suggestions, F39 daily menu WhatsApp |
| **Delivery** | `services/delivery/`, `apps/website/` | **S13** — F27–F31 radius/fees/distance, F29 tracking links |
| **Order notifications** | `services/notification/`, `services/order/` | **S14** — F29 tracking interval reminders, F45 WhatsApp order updates |
| **Ingredient mapper** | `services/catalog/`, `apps/website/` | **S15** — F19 recipes, stock deduct on accept, low-stock warnings |
| **Learning service** | `services/learning/`, `apps/website/` | **S16** — F21 curated portal, F22 dish trials + promote |
| **Community service** | `services/community/`, `apps/website/` | **S17** — F23 recipe rewards, F24 chef rankings |
| **Streaming service** | `services/streaming/`, `apps/website/` | **S18** — F46 LiveKit sessions, F47 owner opt-in go-live, F48 customer live filter |
| **Owner analytics** | `services/order/app/analytics.py` | F07–F08 revenue, top dishes, peak hours, customer segments |
| Shared lib | `packages/ckac-common/` | Config, DB, auth, `EventPublisher`, cache, health, internal auth |
| Event bus | Redis Streams | `ckac:catalog:dish`, `ckac:catalog:ingredient`, `ckac:orders:order`, `ckac:orders:draft`, `ckac:orders:master_order`, `ckac:billing:payment`, `ckac:billing:settlement`, `ckac:billing:subscription`, `ckac:billing:wallet`, `ckac:billing:gst`, `ckac:billing:refund`, `ckac:identity:kitchen`, `ckac:marketing:coupon`, `ckac:marketing:promotion`, `ckac:marketing:crm`, `ckac:ratings:rating`, `ckac:ratings:dish`, `ckac:growth:suggestion`, `ckac:growth:daily_menu`, `ckac:delivery:quote`, `ckac:delivery:tracking`, `ckac:learning:trial`, `ckac:community:recipe`, `ckac:community:reward`, `ckac:community:ranking`, `ckac:streaming:session`, `ckac:notify:whatsapp`, `ckac:notify:dispatch`, `ckac:notify:tracking` |
| PostgreSQL + PostGIS | `infra/postgres/init/` | Schema-per-domain |
| Docker stack | `docker-compose.yml` | postgres, redis, minio, gateway, identity, catalog, order, billing, marketing, ratings, growth, delivery, learning, community, streaming, notification |
| Tests | `services/*/tests/` | TDD — run `scripts/run-tests.ps1` |

### Next ⏳ (follow `docs/DEVELOPMENT-PHASES.md`)

| Sprint | Deliverable |
|--------|-------------|
| S5 | PWA polish (offline, deep links), customer checkout ✅ |
| S6 | Billing, payments, platform subscriptions ✅ (billing service MVP) |
| S7 | F32 discovery, F33 order history + repeat ✅ |
| S8 | F06 multi-kitchen cart + master receipt ✅ |
| S9 | F44 split payment (Razorpay Route dev) ✅ |
| S10 | F36–F38 CRM, coupons, targeted promotions ✅ |
| S11 | F16–F18 home taste ratings + aggregates ✅ |
| S12 | F09–F11 growth intelligence + F39 daily menu push ✅ |
| S13 | F27–F31 delivery fees/distance + F29 tracking ✅ |
| S14 | F29 tracking interval reminders + F45 order notifications ✅ |
| S15 | F19 ingredient balance mapper ✅ |
| S16 | F21 learning portal + F22 dish trials ✅ |
| S17 | F23 recipe rewards + F24 chef rankings ✅ |
| S18 | F46–F48 live streaming (LiveKit opt-in) ✅ |

**Do not implement Phase 2+ features unless explicitly requested.**

---

## 2.1 TDD + EDD (Mandatory)

### TDD — every feature

```
RED → write failing test → GREEN → minimal impl → REFACTOR
```

- Unit tests: `tests/test_schemas.py` (validators, domain logic)
- API tests: `tests/test_*.py` (httpx + LifespanManager)
- Event tests: `tests/test_events.py` (Redis Stream assertions)

### EDD — every write operation

1. DB commit first
2. Publish `EventEnvelope` via `EventPublisher` to Redis Stream `ckac:<domain>:<aggregate>`
3. **Transactional outbox:** pass `session=session` to `publish()` — writes `ckac_events.outbox` in the same transaction

```python
event = EventPublisher.build(
    event_type="dish.created",
    aggregate_type="dish",
    aggregate_id=str(dish.id),
    producer="catalog-service",
    payload={...},
)
await publisher.publish(stream_key("catalog", "dish"), event, session=session)
```

**Never** INSERT into another service's schema from write paths (read-only cross-schema for ownership checks is OK).

---

## 3. Tech Stack (Locked — Do Not Substitute)

| Layer | Technology |
|-------|------------|
| Backend | **Python 3.12+**, **FastAPI**, Pydantic v2, async SQLAlchemy 2.0 |
| Frontend (Phase 1) | **React 18 + Vite + TypeScript**, React Router — `apps/website/` (portal, customer, kitchen, admin) |
| Database | **PostgreSQL 16 + PostGIS** — single cluster, schema-per-domain |
| Cache / events (Phase 1) | **Redis 7** (Streams for events later) |
| Media | MinIO (dev) / S3 (prod) |
| Payments (planned) | Razorpay + Route for multi-kitchen split |
| WhatsApp (planned) | Meta Cloud API |
| Containers | Docker Compose → Kubernetes at scale |

---

## 4. Repository Layout

```
CKAC/
├── AGENTS.md                    ← YOU ARE HERE
├── apps/
│   ├── owner-pwa/               # Owner-facing PWA
│   └── customer-pwa/            # Customer-facing PWA
├── docs/                        # Benchmarks & pitch (read-only unless asked)
├── infra/postgres/init/         # DB extensions & schema bootstrap
├── packages/ckac-common/        # Shared: config, database, events, cache, health
├── services/
│   ├── gateway/                 # API gateway (multi-service router)
│   ├── identity/                # Auth, owners, kitchens
│   ├── catalog/                 # Dishes, categories, menu
│   ├── order/                   # Orders, drafts, lifecycle
│   ├── billing/                 # Payments, subscriptions (Sprint 6)
│   └── notification/            # WhatsApp webhook, inbound routing
├── scripts/
└── docker-compose.yml
```

### New Service Checklist

When adding a service (e.g. `catalog`, `order`):

1. Create `services/<name>/` with same structure as `identity`
2. Add Dockerfile, `pyproject.toml` depending on `ckac-common`
3. Register in `docker-compose.yml`
4. Add proxy prefixes in `services/gateway/app/main.py` if public
5. Create Alembic migrations in service schema (e.g. `ckac_catalog`)
6. Add tests in `services/<name>/tests/`
7. Update CI in `.github/workflows/ci.yml`

---

## 5. Backend Conventions (Mandatory)

### 5.1 Service Template

```
services/<name>/
├── app/
│   ├── main.py          # FastAPI app, CORS, lifespan, health
│   ├── routes.py        # API routes (thin — delegate to schemas/domain)
│   ├── schemas.py       # Pydantic request/response + business logic
│   └── models.py        # SQLAlchemy models
├── alembic/
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── Dockerfile
└── pyproject.toml
```

### 5.2 API Standards

| Rule | Value |
|------|-------|
| Version prefix | `/api/v1/` |
| Error format | FastAPI HTTPException → JSON `{"detail": "..."}` |
| Auth | JWT Bearer (`Authorization: Bearer <token>`) |
| Idempotency | `Idempotency-Key` header on POST for orders/payments (when implemented) |
| Health | Every service: `GET /health/live`, `GET /health/ready` |

### 5.3 Database Rules (DBA)

- **Schema naming:** `ckac_<domain>.<table>` (e.g. `ckac_identity.owners`)
- **Tenant isolation:** `kitchen_id` on all tenant-scoped tables + RLS when enabled
- **Migrations:** Alembic only — never manual DDL in prod paths
- **Geo:** PostGIS `GEOGRAPHY(POINT, 4326)` via GeoAlchemy2 `WKTElement`
- **UUIDs:** Primary keys as UUID v4
- **JSON flexibility:** `JSONB` for settings, metadata, lifecycle

### 5.4 Event Envelope (when publishing events)

Use `ckac_common.events.EventEnvelope`:

```python
EventEnvelope(
    event_type="order.placed",
    aggregate_type="order",
    aggregate_id="CKPNQ001-BILL-20260712-0042",
    producer="order-service",
    payload={...},
)
```

Stream naming: `ckac.<domain>.<event>` (Redis Streams Phase 1 → Kafka Phase 3)

### 5.5 Naming & ID Formats

| Entity | Format | Example |
|--------|--------|---------|
| Kitchen code | `CK` + city(3) + seq(3) | `CKPNQ001` |
| Bill ID | `BILL-YYYYMMDD-SEQ` | `BILL-20260712-0042` |
| Order code | `{kitchen_code}-{bill_id}` | `CKPNQ001-BILL-20260712-0042` |
| Master order | `MORD-YYYYMMDD-XXXX` | `MORD-20260712-A7F3` |

### 5.6 Order Status Enum (when implementing orders)

```
received → accepted → preparing → ready → out_for_delivery → delivered | cancelled
```

### 5.7 Dish Categories (seed slugs)

`veg`, `non_veg`, `vegan`, `beverages`, `hot_drinks`, `cold_drinks`, `snacks`, `desserts`, `combos`, `seasonal_special`

---

## 6. Caching Rules

| Data | Cache? | TTL |
|------|--------|-----|
| Active menu | Yes (Redis) | 5 min |
| Order history (recent) | Yes | 2 min |
| Revenue/analytics aggregates | Yes | 1–6 h |
| Payments / settlements | **Never cache** | — |
| Ingredient stock | 30 sec max or none | — |

Invalidate on domain events (`DishUpdated`, `OrderPlaced`, etc.)

---

## 7. Frontend Conventions (when implementing PWAs)

| Rule | Value |
|------|-------|
| Framework | React 18 + Vite + TypeScript |
| Owner PWA | `apps/owner-pwa/` |
| Customer PWA | `apps/customer-pwa/` |
| Offline | Workbox — cache menu, order history |
| Live photo | `getUserMedia` — enforce `is_live_capture: true` on dish hero upload |
| i18n | Hindi + English at launch |
| API base | Gateway at `/api/v1/` |

---

## 8. Testing Requirements

**Every new endpoint or feature MUST include tests.**

### Identity/Gateway pattern (follow exactly)

```python
# conftest.py — set env BEFORE app imports; use NullPool for async tests
# tests/ — pytest-asyncio, httpx AsyncClient + LifespanManager
# DB cleanup — sync psycopg2 TRUNCATE between tests
```

### Run tests

```powershell
.\scripts\run-tests.ps1
# Requires: docker compose up -d (postgres on 15432, redis on 16379)
```

### CI env (GitHub Actions)

```
DATABASE_URL=postgresql+asyncpg://ckac:ckac_dev@localhost:5432/ckac
DATABASE_SYNC_URL=postgresql://ckac:ckac_dev@localhost:5432/ckac
```

---

## 9. Docker & Local Dev

| Service | Host port |
|---------|-----------|
| Gateway | 18000 |
| Identity | 18001 |
| Catalog | 18002 |
| Order | 18003 |
| Billing | 18004 |
| Notification | 18005 |
| Marketing | 18006 |
| Ratings | 18007 |
| Growth | 18008 |
| Delivery | 18009 |
| Learning | 18010 |
| Community | 18011 |
| Streaming | 18012 |
| PostgreSQL | 15432 |
| Redis | 16379 |
| MinIO | 9000 / 9001 |

Copy `.env.example` → `.env` before `docker compose up`.

---

## 10. Feature Implementation Workflow

When implementing a feature from the benchmark:

1. **Find feature ID** in `docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md` (F01–F48)
2. **Check phase** — do not skip ahead unless user explicitly asks
3. **Read acceptance criteria** in the benchmark doc
4. **Identify service boundary** — which microservice owns it
5. **Schema first** — Alembic migration if new tables/columns
6. **API** — routes + schemas + tests
7. **Events** — publish if other services need to react
8. **Gateway** — add proxy prefix if customer/owner facing
9. **Run tests** — `scripts/run-tests.ps1`
10. **No drive-by refactors** — minimal focused diff

---

## 11. Security Checklist

- [ ] JWT validation on protected routes
- [ ] Tenant scoping via `kitchen_id` (RLS where applicable)
- [ ] No secrets in code — use env vars / `.env.example` template
- [ ] PII masked in logs
- [ ] Media via signed URLs (when media service exists)
- [ ] Ratings only from verified purchases
- [ ] Rate limiting on gateway (when implemented)

---

## 12. What NOT To Do

- ❌ Do not add per-order commission logic — subscription model only
- ❌ Do not use MongoDB as primary store — PostgreSQL is source of truth
- ❌ Do not build native mobile apps before PWA is stable
- ❌ Do not implement aggregator-style speed-first delivery timers
- ❌ Do not allow gallery upload as dish hero without live-capture flag
- ❌ Do not commit `.env`, secrets, or `pgdata/` volumes
- ❌ Do not create commits unless user explicitly asks
- ❌ Do not add features without tests for critical paths (auth, orders, billing)

---

## 13. Key Domain Flows (Reference)

### Owner onboarding (implemented)

```
Register owner → Request OTP → Verify OTP (JWT) → Create kitchen → Kitchen code assigned
```

### Order intake (planned — F01–F04)

```
WhatsApp/manual/PWA → draft order → owner confirm → OrderPlaced event → lifecycle updates → notifications
```

### Multi-kitchen checkout (planned — F06, F44)

```
Cart (multi kitchen) → single payment → Razorpay Route split → per-kitchen sub-orders + settlements
```

### Rating (planned — F16–F18)

```
Delivered order only → home_taste (1–5) + quality (1–5) → optional anonymous A/V → aggregate on dish
```

---

## 14. Agent Decision Matrix

| Question | Answer |
|----------|--------|
| Which DB? | PostgreSQL + PostGIS, schema `ckac_<domain>` |
| Sync or async API between services? | Async events default; sync REST only when immediate consistency required |
| Monolith or microservice? | Modular monolith per service container; split when hot path demands |
| Where does business logic go? | `schemas.py` domain functions or `domain/` package — not in routes |
| How to handle phone numbers? | Normalize to E.164 (`+91...`) via Pydantic validator |
| Default OTP in dev? | `123456` (replace with Redis + WhatsApp in prod) |
| Demo owner / kitchen? | Run `python scripts/seed-dev-data.py` or `.\scripts\seed-all.ps1` (bulk + all personas) → phones `9876543210`–`9876543213`, OTP `123456`, primary kitchen `CKPNQ001` |
| Demo customers? | WhatsApp OTP `123456` — `9123456789`, `9123456780`, `9988776655` |
| Platform admin? | `admin@kitchcu.dev` / `admin123456` (dev default) |
| Primary user for Phase 1? | Owner — optimize owner flows before customer PWA |

---

## 15. File Change Quick Reference

| Task | Files to touch |
|------|------------------|
| New API endpoint | `routes.py`, `schemas.py`, `tests/test_*.py`, maybe `gateway/main.py` |
| New table | `models.py`, `alembic/versions/`, `infra/postgres/init/` if new schema |
| New service | `services/<name>/`, `docker-compose.yml`, `gateway/main.py`, CI workflow |
| Shared util | `packages/ckac-common/ckac_common/` |
| Env var | `.env.example` + document in README |
| Owner UI | `apps/owner-pwa/` |
| Customer UI | `apps/customer-pwa/` |

---

*Last updated: Phase 1 S1–S18 complete (gateway + 13 domain services + PWAs + GST). Docs: Complete Guide v3.0 + UI Catalog. Next design: E1–E2 Quality Loop.*
