# Kitchcu — CTO Architecture & CPO Product Map

**Engineering structure aligned with System Benchmark and CPO Product Blueprint**

| Field | Value |
|-------|-------|
| Version | **2.0** |
| Date | 2026-07-19 |
| Audience | CTO, Engineering Managers, Tech Leads, CPO (product ↔ code traceability) |
| Status | **S1–S18 + P19–P32.1 shipped** (gateway + 13 domain services + 4 PWAs) |
| Companion | [Architecture Flows](./PLATFORM-ARCHITECTURE-FLOWS.md) · [Complete Guide](./CKAC-COMPLETE-GUIDE.md) · [Implementation Guide](./CKAC-IMPLEMENTATION-GUIDE.md) · [Advancement Tracker](./ADVANCEMENT-TRACKER.md) · [AGENTS.md](../AGENTS.md) |

---

## 1. Layered Architecture (CTO View)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXPERIENCE LAYER                                                       │
│  Portal · Customer PWA · Kitchen PWA · Admin PWA · WhatsApp webhook     │
│  apps/website/  (:13000–13003)                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / JWT
┌───────────────────────────────────▼─────────────────────────────────────┐
│  EDGE LAYER — API Gateway (services/gateway :18000)                     │
│  Path routing · CORS · X-Correlation-ID · OTP rate limits · OpenAPI     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│  APPLICATION LAYER — 13 bounded-context microservices                   │
│  identity · catalog · order · billing · marketing · ratings · growth    │
│  delivery · learning · community · streaming · notification             │
│  Pattern: routes (thin) → schemas (domain) → models (persistence)       │
└───────────────┬─────────────────────────────┬───────────────────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼──────────────────────────┐
│  DOMAIN DATA LAYER           │   │  INTEGRATION LAYER                  │
│  PostgreSQL 16 + PostGIS     │   │  Redis Streams (events)             │
│  Schema-per-service          │   │  Redis cache (menu TTL 300s)        │
│  ckac_identity … streaming   │   │  Internal HTTP (X-Internal-Key)     │
│  + ckac_events (outbox)      │   │  Outbox (ckac_events.outbox)        │
└──────────────────────────────┘   └─────────────────────────────────────┘
                │
┌───────────────▼──────────────┐
│  MEDIA LAYER — MinIO / S3    │
│  Live-capture dish URLs      │
└──────────────────────────────┘
```

Full narrative: Complete Guide §9–§11 · flow snapshot: [PLATFORM-ARCHITECTURE-FLOWS.md](./PLATFORM-ARCHITECTURE-FLOWS.md).

### 1.1 Engineering standards (enforced in code)

| Standard | Location | Rule |
|----------|----------|------|
| Service template | `services/<name>/app/` | `main.py`, `routes.py`, `schemas.py`, `models.py` |
| Shared library | `packages/ckac-common/` | Config, DB, auth, events, cache, health, admin_rbac, internal auth |
| Health probes | `ckac_common.health` | `GET /health/live`, `GET /health/ready` |
| EDD writes | `EventPublisher.publish(..., session=session)` | Outbox + Redis in same transaction |
| Cross-service auth | `ckac_common.internal_auth` | `X-Internal-Key` |
| Menu cache | `ckac_common.cache` | Tenant keys `menu:{kitchen_id}`; invalidate on dish events |
| No cross-schema writes | Each Alembic | Read-only SELECT across schemas for ownership/menu |

---

## 2. Service Registry & Ownership

| Service | Port | Schema | Writes | Cross-schema reads |
|---------|------|--------|--------|--------------------|
| **gateway** | 18000 | — | — | Proxies only |
| **identity** | 18001 | `ckac_identity` | owners, customers, kitchens, admin RBAC/audit, delivery-settings, branded_page | — |
| **catalog** | 18002 | `ckac_catalog` | categories, dishes, media, ingredients | kitchens (ownership) |
| **order** | 18003 | `ckac_orders` | orders, drafts, master orders, status events, analytics | identity + catalog |
| **billing** | 18004 | `ckac_billing` | payments, subscriptions, GST, refunds, packages, wallet | identity (kitchen) |
| **notification** | 18005 | `ckac_support` | tickets, WA handlers, dispatch | kitchens (whatsapp_phone_id) |
| **marketing** | 18006 | `ckac_marketing` | CRM, coupons, promos, templates | — |
| **ratings** | 18007 | `ckac_ratings` | ratings, aggregates | orders (verified purchase) |
| **growth** | 18008 | `ckac_growth` | suggestions, daily menu, golden day | order/catalog projections |
| **delivery** | 18009 | `ckac_delivery` | quotes, tracking views | kitchens (radius / subsidy) |
| **learning** | 18010 | `ckac_learning` | trials, invites | — |
| **community** | 18011 | `ckac_community` | recipes, rewards, rankings | — |
| **streaming** | 18012 | `ckac_streaming` | live sessions, showcase | — |

**Shared:** `ckac_events` (outbox/DLQ) · Redis · MinIO · `packages/ckac-common/`.

---

## 3. Event Catalog (EDD) — summary

Format: `ckac:{domain}:{aggregate}` via `stream_key()`.

| Domain streams | Examples |
|----------------|----------|
| identity | `kitchen.created` |
| catalog | `dish.*`, `ingredient.*` |
| orders | `order.placed`, `order.status.changed`, `order.delivery_mode.set`, drafts, master_order |
| billing | payment, settlement, subscription, wallet, gst, refund, package |
| marketing | coupon, promotion, crm, template |
| delivery | `delivery.fee_quoted`, tracking |
| notify | whatsapp, dispatch, tracking |
| streaming / growth / ratings / learning / community | session, suggestion, rating, trial, recipe… |

**Relay worker** (outbox → Kafka) remains Phase 4 — table + write path exist today.

Full stream list: [AGENTS.md](../AGENTS.md) · [PLATFORM-ARCHITECTURE-FLOWS.md](./PLATFORM-ARCHITECTURE-FLOWS.md) §2.

---

## 4. CPO Product → Code Map (current)

### 4.1 Owner pain → implementation

| CPO pain | Module | Feature IDs | Code / API | Status |
|----------|--------|-------------|------------|--------|
| P1 WhatsApp chaos | Order + Notification | F01–F02 | handlers, drafts, template blast | ✅ Partial→strong |
| P2 Aggregator commission | Billing | F42–F44 | subscriptions, packages, no food commission | ✅ |
| P3 No profit visibility | Order analytics + Growth | F07–F12 | analytics routes + suggestions | ✅ |
| P4 Stock photo deception | Catalog | F13 | live-capture validator | ✅ |
| P5 Taste inconsistency | Catalog + Ratings | F16–F18, F30 | quality fields + home_taste | ✅ |
| P6 No owner CRM | Marketing | F36–F38 | CRM / coupons / promos | ✅ |
| P7 Promotion guesswork | Growth | F09–F11, F39 | combos, patterns, daily menu | ✅ |
| P8 Multi-channel chaos | Order | F03–F05 | lifecycle + `source` | ✅ |

### 4.2 Customer pain → implementation

| CPO pain | Feature | Code | Status |
|----------|---------|------|--------|
| C1 Untrustworthy photos | F13 | Catalog media rules | ✅ |
| C2 Opaque delivery fees | F27–F31 + P32 | Quote modes + cost-share + Porter | ✅ |
| C3 No tracking | F04, F29 | Track token + notify intervals | ✅ |
| C4 Generic ratings | F16–F18 | Ratings service | ✅ |
| C5 Single-kitchen cart | F06, F33 | Master order + history/repeat | ✅ |
| C6 No tiffin / daily menu | F39 | Growth daily menu push | ✅ |

### 4.3 Module → repository path

| CPO module | Sprint | Path | Status |
|------------|--------|------|--------|
| Identity | S1 | `services/identity/` | ✅ |
| Catalog | S2 | `services/catalog/` | ✅ |
| Order | S3 | `services/order/` | ✅ |
| Notification | S4 | `services/notification/` | ✅ |
| Gateway | S1 | `services/gateway/` | ✅ |
| Billing | S6 | `services/billing/` | ✅ |
| Delivery | S13 + P32 | `services/delivery/` + order Porter | ✅ |
| Marketing / Ratings / Growth | S10–S12 | respective services | ✅ |
| Streaming | S18 + P30 | `services/streaming/` + LiveKit UI | ✅ |
| PWAs | S5+ | `apps/website/` (not `owner-pwa/`) | ✅ |

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

### 5.2 Menu read (cache)

```
GET /kitchens/{id}/menu
  → catalog: Redis cache hit? return
  → else DB active dishes → set cache (300s TTL)
  → dish create/update invalidates cache + dish.* event
```

### 5.3 Checkout + Porter cost-share (P32.1)

```
Customer checkout
  → POST /delivery/quote (subtotal, lat/lng)
      → distance vs max_delivery_radius_km
      → modes: self | platform (Porter/mock gross)
      → split_delivery_cost → customer_fee / owner_fee / payer
  → POST .../orders/customer { delivery_mode, delivery_fee, Idempotency-Key }
      → order re-validates fee + stores mode / payer / owner_delivery_cost
  → billing pay (COD | online | UPI)
  → owner PATCH status → accepted
      → stock deduct (catalog internal)
      → if delivery_mode=platform → porter_client.quote_and_book_porter
      → courier_job_id stored
  → track GET /delivery/track/{token} + WA notify
```

### 5.4 Kitchen onboarding (F26)

```
POST /owners/register → OTP → POST /kitchens
  → identity: PostGIS location, code CKPNQ001
  → kitchen.created event
  → PATCH delivery-settings (radius, min_order, subsidy %)
  → branded_page publish → /k/{code}
```

---

## 6. EM Checklist — Definition of Done (per service)

- [ ] `main.py` lifespan: Redis + `EventPublisher`
- [ ] Health uses `ckac_common.health`
- [ ] All mutating routes pass `session` to `publish()`
- [ ] Alembic owns exactly one `ckac_*` schema
- [ ] Tests: schemas + routes + events
- [ ] Gateway route registered
- [ ] Documented in Implementation Guide / Architecture Flows

**Current compliance:** All 13 domain services + gateway on Phase 1 template. Expand event-matrix tests for new money/Porter paths continuously.

---

## 7. What’s Next (CTO roadmap)

| Priority | Item | Why |
|----------|------|-----|
| Wave A | Live Razorpay + prod OTP | Money trust |
| Wave B | Kitchen staff RBAC | Multi-human kitchens |
| Wave B | Porter webhooks | Courier status honesty |
| Wave C | E1–E2 Quality Loop | Profit OS |
| Wave D | Cloud Run + OTel + SLOs | 100k sessions |
| Phase 4 | Outbox → Kafka relay | Bus scale |

See [DEVELOPMENT-PHASES.md](./DEVELOPMENT-PHASES.md) · [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md) · [PLATFORM-ARCHITECTURE-FLOWS.md](./PLATFORM-ARCHITECTURE-FLOWS.md).

---

## Document control

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-07 | Early Phase 1 registry (incomplete) |
| **2.0** | 2026-07-19 | Full 13-service registry; CPO map current; Porter checkout flow; PWA path `apps/website/` |
