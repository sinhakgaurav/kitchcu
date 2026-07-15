# Kitchcu — CTO Architecture & CPO Product Map

**Engineering structure aligned with System Benchmark and CPO Product Blueprint**

| Field | Value |
|-------|-------|
| Version | **1.1** |
| Audience | CTO, Engineering Managers, Tech Leads, CPO (product ↔ code traceability) |
| Status | S1–S18 shipped; deep how/why + ER + flows in Complete Guide v3.2 |
| Companion | [Complete Guide v3.2](./CKAC-COMPLETE-GUIDE.md) · [Implementation Guide](./CKAC-IMPLEMENTATION-GUIDE.md) · [System Benchmark](./CKAC-SYSTEM-BENCHMARK.md) · [CPO Blueprint v4.2](./CKAC-CPO-PRODUCT-BLUEPRINT.md) · [User Flows](./CKAC-USERFLOWS.md) · [API.md](./API.md) · [AGENTS.md](../AGENTS.md) · [UI Catalog](./assets/ui/) |

---

## 1. Layered Architecture (CTO View)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXPERIENCE LAYER (S5–S18)                                              │
│  Portal · Owner PWA · Customer PWA · Admin PWA · WhatsApp webhook       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / JWT
┌───────────────────────────────────▼─────────────────────────────────────┐
│  EDGE LAYER — API Gateway (services/gateway)                            │
│  Path routing · CORS · correlation ID · future rate limits              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│  APPLICATION LAYER — Bounded-context microservices (13 domains)         │
│  identity · catalog · order · billing · marketing · ratings · growth    │
│  delivery · learning · community · streaming · notification             │
│  Pattern: routes (thin) → schemas (domain) → models (persistence)       │
└───────────────┬─────────────────────────────┬───────────────────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼──────────────────────────┐
│  DOMAIN DATA LAYER           │   │  INTEGRATION LAYER                  │
│  PostgreSQL 16 + PostGIS     │   │  Redis Streams (events)             │
│  Schema-per-service          │   │  Redis cache (menu TTL 300s)        │
│  ckac_identity, catalog,     │   │  Internal HTTP (X-Internal-Key)     │
│  orders, billing, …events    │   │  Outbox (ckac_events.outbox)        │
└──────────────────────────────┘   └─────────────────────────────────────┘
                │
┌───────────────▼──────────────┐
│  MEDIA LAYER — MinIO / S3    │
│  Live-capture dish URLs      │
└──────────────────────────────┘
```

> For the full "why microservices / gateway / outbox / tenant scoping / 100k sessions" narrative, see Complete Guide **§9–§11**.

### 1.1 Engineering standards (enforced in code)

| Standard | Location | Rule |
|----------|----------|------|
| Service template | `services/<name>/app/` | `main.py`, `routes.py`, `schemas.py`, `models.py` |
| Shared library | `packages/ckac-common/` | Config, DB, auth, events, cache, health, internal auth |
| Health probes | `ckac_common.health` | `GET /health/live`, `GET /health/ready` with `service` field |
| EDD writes | `EventPublisher.publish(..., session=session)` | Outbox row + Redis XADD in same transaction |
| Cross-service auth | `ckac_common.internal_auth` | `X-Internal-Key` for service-to-service |
| Menu cache | `ckac_common.cache` | Read-through on GET menu; invalidate on dish create/update |
| No cross-schema writes | Each Alembic | Read-only SELECT across schemas for ownership/menu |

---

## 2. Service Registry & Ownership

| Service | Port | Schema / state | Writes | Reads (cross-schema) |
|---------|------|----------------|--------|----------------------|
| **gateway** | 18000 | — | — | Proxies only |
| **identity** | 18001 | `ckac_identity` | owners, kitchens | — |
| **catalog** | 18002 | `ckac_catalog` | categories, dishes, media | `ckac_identity.kitchens` (ownership) |
| **order** | 18003 | `ckac_orders` | orders, drafts, status events | identity + catalog dishes |
| **notification** | 18005 | — | — | `ckac_identity.kitchens` (whatsapp_phone_id) |

**Shared:** `ckac_events` (outbox), Redis (streams + cache), MinIO (media URLs).

---

## 3. Event Catalog (EDD)

All write paths pass `session` to `EventPublisher.publish()` so `ckac_events.outbox` records the event before Redis publish.

| Event | Producer | Stream | CPO capability |
|-------|----------|--------|----------------|
| `kitchen.created` | identity | `ckac:identity:kitchen` | F26 onboarding |
| `dish.created` | catalog | `ckac:catalog:dish` | F13 menu trust |
| `dish.updated` | catalog | `ckac:catalog:dish` | F13/F15 menu ops |
| `order.placed` | order | `ckac:orders:order` | F03 intake |
| `order.status.changed` | order | `ckac:orders:order` | F04 lifecycle |
| `order.draft.created` | order | `ckac:orders:draft` | F01/F02 WhatsApp parser |
| `whatsapp.message.received` | notification | `ckac:notify:whatsapp` | F01 unified inbox |

**Relay worker** (outbox → Kafka at scale) is Phase 4 — table and write path exist today.

---

## 4. CPO Product → Code Map

Maps [CPO Blueprint §2–3](./CKAC-CPO-PRODUCT-BLUEPRINT.md) pain points and modules to implemented code.

### 4.1 Owner pain → implementation

| CPO pain | Module | Feature IDs | Code / API | Status |
|----------|--------|-------------|------------|--------|
| P1 WhatsApp chaos | Order + Notification | F01, F02 | `notification/handlers.py`, `order/parser.py`, drafts API | Partial |
| P2 Aggregator commission | Billing | F42–F44 | — | Sprint 6 |
| P3 No profit visibility | Analytics | F07–F12 | — | Sprint 6+ |
| P4 Stock photo deception | Catalog | F13 | `DishMediaInput` live-capture validator | Done |
| P5 Taste inconsistency | Catalog | F30 | `quality_measures`, `ingredients_description` fields | Partial |
| P6 No owner CRM | Marketing | F34–F40 | — | Phase 2 |
| P7 Promotion guesswork | Growth | F11 | — | Phase 2 |
| P8 Multi-channel chaos | Order | F03–F05 | Single lifecycle + `source` field | Partial |

### 4.2 Customer pain → implementation

| CPO pain | Feature | Code | Status |
|----------|---------|------|--------|
| C1 Untrustworthy photos | F13 | Catalog media rules | Done |
| C2 Opaque delivery fees | F27–F31 | Kitchen radius fields on identity | Fields only |
| C3 No tracking | F04 | Order status events + future notify | Partial |
| C4 Generic ratings | F16–F18 | — | Phase 2 |
| C5 Single-kitchen cart | F33 | — | Phase 2 |
| C6 No tiffin | F39 | — | Phase 2 |

### 4.3 Module → repository path

| CPO module | Sprint | Path | Product promise |
|------------|--------|------|-----------------|
| Identity | S1 ✅ | `services/identity/` | Owner registers, kitchen goes live |
| Catalog | S2 ✅ | `services/catalog/` | Honest menu with live photos |
| Order | S3 ✅ | `services/order/` | Every order has a bill code and lifecycle |
| Notification | S4 ✅ | `services/notification/` | WhatsApp in → draft out |
| Gateway | S1 ✅ | `services/gateway/` | One API for all clients |
| Billing | S6 ⏳ | `services/billing/` (planned) | Subscription, not commission |
| Owner PWA | S5 ⏳ | `apps/owner-pwa/` (planned) | Single pane of glass |

---

## 5. Request Flow Examples

### 5.1 WhatsApp order (P1)

```
Meta webhook → gateway /webhooks/whatsapp
  → notification: lookup kitchen by whatsapp_phone_id
  → publish whatsapp.message.received (outbox + Redis)
  → POST order /internal/.../from-whatsapp (X-Internal-Key)
  → order: parse message → draft → order.draft.created
  → owner confirms draft → order.placed
```

### 5.2 Menu read (P4 + performance)

```
GET /kitchens/{id}/menu
  → catalog: Redis cache hit? return
  → else DB active dishes → set cache (300s TTL)
  → dish create/update invalidates cache + dish.* event
```

### 5.3 Kitchen onboarding (F26)

```
POST /owners/register → OTP → POST /kitchens
  → identity: PostGIS location, code CKPNQ001
  → kitchen.created event
  → catalog seeds default categories on first access
```

---

## 6. EM Checklist — Definition of Done (per service)

- [ ] `main.py` lifespan: Redis + `EventPublisher`
- [ ] Health uses `ckac_common.health`
- [ ] All mutating routes pass `session` to `publish()`
- [ ] Alembic owns exactly one `ckac_*` schema
- [ ] Tests: schemas + routes + events (`test_events.py`)
- [ ] Gateway route registered in `services/gateway/app/main.py`
- [ ] Documented in `CKAC-IMPLEMENTATION-GUIDE.md` §7 API Reference

**Current compliance:** identity, catalog, order, notification meet checklist after architecture alignment pass (July 2026).

---

## 7. What’s Next (CTO roadmap)

| Priority | Item | Why |
|----------|------|-----|
| S5 | Owner PWA | Closes P1/P8 for daily ops UX |
| S6 | Billing service | Closes P2/P3 subscription story |
| Phase 2 | Delivery fee engine | C2 — use PostGIS fields already on kitchens |
| Phase 4 | Outbox relay worker | At-least-once without Redis-only coupling |

See [DEVELOPMENT-PHASES.md](./DEVELOPMENT-PHASES.md) for sprint detail.
