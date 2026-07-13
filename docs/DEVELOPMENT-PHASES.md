# Kitchcu — Phased Development Plan

**Strictly follows `AGENTS.md` — TDD, EDD, microservices, scalable PostgreSQL schema-per-domain.**

**Implementation status:** see [`CKAC-IMPLEMENTATION-GUIDE.md`](./CKAC-IMPLEMENTATION-GUIDE.md) for code mapped to features and benchmarks.

| Version | 1.0 |
|---------|-----|
| Method | Test-Driven Development (Red → Green → Refactor) |
| Events | Event-Driven Design via Redis Streams → Kafka (Phase 4) |
| Data | Single PostgreSQL cluster, schema-per-bounded-context |

---

## Development Contract (Every Sprint)

```
1. Read feature ID + acceptance criteria (docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md)
2. Define DB migration (Alembic) — schema in ckac_<domain>
3. RED:   Write failing tests (API + domain + event assertions)
4. GREEN: Implement minimal code to pass
5. REFACTOR: Clean up; ensure event publish + cache invalidation
6. Run scripts/run-tests.ps1 + update AGENTS.md status
```

### TDD Layers (per service)

| Layer | Location | What to test |
|-------|----------|--------------|
| Unit | `tests/test_schemas.py` | Validators, domain logic, code generators |
| API | `tests/test_*.py` | httpx AsyncClient, status codes, response shape |
| Events | `tests/test_events.py` | Publisher called with correct `EventEnvelope` |
| Integration | `tests/test_*_integration.py` | Cross-schema reads, Redis stream append |

### EDD Rules

| Rule | Implementation |
|------|----------------|
| Every write publishes an event | `EventPublisher.publish()` after DB commit |
| Standard envelope | `ckac_common.events.EventEnvelope` |
| Stream naming | `ckac:<domain>:<aggregate>` e.g. `ckac:catalog:dish` |
| Outbox (reliability) | `ckac_events.outbox` table + worker (Sprint 3+) |
| Consumers | Separate worker process per subscribing service |
| No sync cross-service writes | Service A never INSERTs into Service B's tables |

---

## Architecture Overview

```
                    ┌─────────────┐
                    │   Gateway   │ :8000 / :18000
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Identity  │  │  Catalog   │  │   Order    │  ...
    │   :8001    │  │   :8002    │  │   :8003    │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
              ┌───────────────────────┐
              │  PostgreSQL 16        │
              │  ckac_identity        │
              │  ckac_catalog         │
              │  ckac_orders          │
              │  ckac_billing         │
              │  ckac_events (outbox) │
              └───────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
         Redis Streams            MinIO/S3
         (event bus)              (media)
```

---

## PostgreSQL Schema Roadmap

### Phase 1 — Owner Can Run Kitchen

| Schema | Sprint | Tables |
|--------|--------|--------|
| `ckac_identity` | S1 ✅ | `owners`, `kitchens` |
| `ckac_catalog` | S2 ✅ | `categories`, `dishes`, `dish_media` |
| `ckac_orders` | S3 ✅ | `orders`, `order_items`, `order_status_events` |
| `ckac_events` | S2 ✅ | `outbox`, `processed_events` |

### Phase 2 — Customer Discovery & CRM

| Schema | Sprint | Tables |
|--------|--------|--------|
| `ckac_orders` | S8 | `master_orders` (multi-kitchen) |
| `ckac_billing` | S9 | `payments`, `settlements` |
| `ckac_marketing` | S10 | `kitchen_customers`, `coupons`, `subscription_plans` |
| `ckac_ratings` | S11 | `dish_ratings`, `dish_suggestions` |

### Phase 3 — Quality & Community

| Schema | Sprint | Tables |
|--------|--------|--------|
| `ckac_catalog` | S14 | `ingredients`, `dish_ingredients` |
| `ckac_learning` | S15 | `recipes`, `trials` |
| `ckac_growth` | S12 | `suggestions`, `seasonal_patterns` |

### Scaling Path (DBA)

| Scale | Action |
|-------|--------|
| 0–500 kitchens | Single PG instance, schema isolation |
| 500–5K | Read replica for analytics; PgBouncer |
| 5K+ | Partition `order_status_events` by month; Redis cluster |
| National | Regional read replicas; evaluate Citus |

---

## Phase 1 — Foundation (Months 1–3)

**Goal:** 10 pilot kitchens processing real orders daily.

### Sprint 1 ✅ — Platform Bootstrap (DONE)

| Deliverable | Status |
|-------------|--------|
| Docker stack (PG, Redis, MinIO) | ✅ |
| `ckac-common` (config, DB, events) | ✅ |
| Identity service (owners, kitchens, OTP, JWT) | ✅ |
| Gateway proxy | ✅ |
| 32 tests | ✅ |
| `AGENTS.md` + Cursor rules | ✅ |

**Events published:** (S2 adds) `kitchen.created`

---

### Sprint 2 — Catalog Service ✅ (DONE)

**Features:** F13–F15 (dishes, categories, live photo metadata)

#### DB Migration `ckac_catalog`

```sql
categories (id, kitchen_id, name, slug, sort_order)
dishes (id, kitchen_id, category_id, name, price, prep_time_min, ...)
dish_media (id, dish_id, url, is_hero, is_live_capture, captured_at)
```

#### Microservice: `services/catalog/` (:8002)

| Method | Endpoint | Event |
|--------|----------|-------|
| GET | `/api/v1/kitchens/{id}/categories` | — |
| POST | `/api/v1/kitchens/{id}/categories` | `category.created` |
| GET | `/api/v1/kitchens/{id}/menu` | — (cacheable) |
| POST | `/api/v1/kitchens/{id}/dishes` | `dish.created` |
| PATCH | `/api/v1/dishes/{id}` | `dish.updated` |
| POST | `/api/v1/dishes/{id}/media` | `dish.media.uploaded` |

#### TDD Test List (write first)

- [ ] `test_list_categories_empty`
- [ ] `test_seed_default_categories_on_kitchen_first_access`
- [ ] `test_create_dish_requires_auth`
- [ ] `test_create_dish_requires_live_capture_for_hero`
- [ ] `test_get_menu_returns_active_dishes`
- [ ] `test_dish_created_publishes_event`
- [ ] `test_menu_cache_invalidated_on_dish_updated`

#### EDD

```
POST /dishes → DB commit → XADD ckac:catalog:dish → invalidate menu:{kitchen_id}
Consumers (future): analytics, notification, search indexer
```

---

### Sprint 3 — Order Service ✅ (DONE)

**Features:** F03, F04, F05, F30

#### DB `ckac_orders`

```sql
orders, order_items, order_status_events (partitioned monthly)
```

#### Events

`order.placed`, `order.status.changed`

#### TDD focus

- Manual order creation
- Lifecycle state machine (valid transitions only)
- Order code format `CKPNQ001-BILL-YYYYMMDD-SEQ`

---

### Sprint 4 — WhatsApp Intake ✅ (DONE)

**Features:** F01, F02

#### Microservice extension: `notification-service` or order parser worker

#### Events

`whatsapp.message.received`, `order.draft.created`

---

### Sprint 5 — PWAs, Analytics & Support (partial ✅)

**Features:** Marketing portal, customer/kitchen/admin PWAs, owner growth analytics, AI support chat, admin ticketing

#### Stack

React + Vite + TS (multi-app build: portal, customer, kitchen, admin)

#### Delivered

- `apps/website/` — parallax marketing portal, AI chat, ticket escalation
- Owner **Reports** page — analytics API via order service
- Admin **Tickets** tab — support ticket CRUD + reply

#### Remaining S5

Workbox offline, SPA deep-link reload, customer checkout

---

### Sprint 6 — Billing & Payments

**Features:** F07, F42, F43, F26

#### DB `ckac_billing`

`payments`, `owner_subscriptions`

---

## Phase 2 — Growth (Months 4–6)

| Sprint | Service | Features |
|--------|---------|----------|
| S7 | Customer PWA | F32 discovery |
| S8 | Order + Gateway | F06 multi-kitchen cart |
| S9 | Billing | F44 split payment (Razorpay Route) |
| S10 | Marketing | F36, F37, F38 CRM/coupons |
| S11 | Rating | F16–F18 |
| S12 | Analytics + Growth | F07–F11, F39 |
| S13 | Delivery | F27–F31, F29 |
| S14 | Notification | F45 WhatsApp + push |

---

## Phase 3 — Differentiation (Months 7–10)

| Sprint | Focus |
|--------|-------|
| S15 | Ingredient mapper F19 |
| S16 | Learning portal F21–F22 |
| S17 | Community F23–F24 |
| S18 | Live streaming F46–F48 |

---

## Phase 4 — Scale (Months 11–12+)

- Kafka migration from Redis Streams
- Kubernetes + HPA
- Read replicas + connection pooling
- ML growth engine
- White-label / franchise

---

## Service Port Map

| Service | Internal | Host (dev) |
|---------|----------|------------|
| gateway | 8000 | 18000 |
| identity | 8001 | 18001 |
| catalog | 8002 | 18002 |
| order | 8003 | 18003 |
| billing | 8004 | 18004 |
| notification | 8005 | 18005 |
| analytics | 8006 | 18006 |

---

## Event Catalog (Growing)

| Event | Producer | Consumers |
|-------|----------|-----------|
| `kitchen.created` | identity | catalog (seed categories), analytics |
| `dish.created` | catalog | cache, analytics |
| `dish.updated` | catalog | cache, search |
| `order.placed` | order | notification, analytics, billing |
| `order.status.changed` | order | notification, customer WS |
| `payment.captured` | billing | order, settlement |
| `payment.split.completed` | billing | identity (owner notify) |

---

## CI/CD Gates (Every PR)

1. `ruff check`
2. `pytest` all services
3. Alembic migration applies cleanly
4. No secrets in diff
5. `AGENTS.md` updated if new service/convention

---

## Reference

- Agent spec: `AGENTS.md`
- Feature details: `docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md`
- Architecture: `docs/CKAC-SYSTEM-BENCHMARK.md`
