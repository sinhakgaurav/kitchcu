# Kitchcu — Implementation Guide & Product Map

**Living document — maps built code to planning benchmarks**

| Field | Value |
|-------|-------|
| Version | **2.0** |
| Status | **S1–S18 shipped** + post-S18 **P19–P28** (packages, templates, employees RBAC, kitchen workspace); E1/E2 = design pack only |
| Last updated | July 2026 |
| Advancement | **[ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md)** — sprint board + release gate |
| Encyclopedia | **[CKAC-COMPLETE-GUIDE.md](./CKAC-COMPLETE-GUIDE.md) v3.2.2** — packages/employees/templates + super-admin kitchen workspace; UI Catalog; OpenAPI |
| Companion docs | [Planning Benchmark](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) · [System Benchmark](./CKAC-SYSTEM-BENCHMARK.md) · [CPO Blueprint v4.2](./CKAC-CPO-PRODUCT-BLUEPRINT.md) · [CTO Architecture](./CKAC-ARCHITECTURE-CTO.md) · [Development Phases](./DEVELOPMENT-PHASES.md) · [User Flows](./CKAC-USERFLOWS.md) · [API.md](./API.md) · [AGENTS.md](../AGENTS.md) · [UI shots](./assets/ui/) |

> For deep definitions, module logic, Mermaid flows, and annotated screenshots, prefer the Complete Guide. This file remains the **code ↔ feature map** (what's wired where).

---

## How to use this document

| If you need… | Read section |
|--------------|--------------|
| Full definitions / how & why / UI screens | [Complete Guide v3.2](./CKAC-COMPLETE-GUIDE.md) |
| Full step-by-step user journeys (every persona, every screen, every API call) | [CKAC-USERFLOWS.md](./CKAC-USERFLOWS.md) / [.pdf](./CKAC-USERFLOWS.pdf) |
| What Kitchcu is and who it serves | [§1 Product Overview](#1-product-overview) |
| What's built vs planned (48 features) | [§2 Feature Implementation Matrix](#2-feature-implementation-matrix) |
| Services, ports, routing | [§3 Architecture](#3-architecture) |
| Tables, schemas, indexes | [§4 Database Design](#4-database-design) |
| Events and data flows | [§5 Event-Driven Design](#5-event-driven-design) |
| End-to-end user flows | [§6 Application Flows](#6-application-flows) |
| Every API endpoint + aggregated OpenAPI / gateway `/docs` | [§7 API Reference](#7-api-reference) · [API.md](./API.md) |
| Map to System Benchmark sections | [§8 Benchmark Cross-Reference](#8-benchmark-cross-reference) |
| CTO layers + CPO product ↔ code | [CKAC-ARCHITECTURE-CTO.md](./CKAC-ARCHITECTURE-CTO.md) |
| Map to Planning Benchmark parts | [§9 Planning Benchmark Cross-Reference](#9-planning-benchmark-cross-reference) |
| Tests, Docker, conventions | [§10 Engineering Reference](#10-engineering-reference) |

---

## 1. Product Overview

### 1.1 What Kitchcu is

**Kitchcu** is a **B2B2C operating system for cloud kitchens** — not a food aggregator.

| Dimension | Description |
|-----------|-------------|
| **For owners** | Run orders (WhatsApp, manual, future PWA), manage menu with live photos, track lifecycle, view history — from one platform |
| **For customers** | (Phase 2+) Discover kitchens, trust live-capture menus, fair delivery, home-taste ratings |
| **Business model** | Owner **subscription SaaS** — zero per-order food commission |
| **Differentiation** | WhatsApp-native ops + live-capture integrity + owner-owned CRM + quality-first lifecycle |

**Maps to:** Planning Benchmark [§1 Executive Vision](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#1-executive-vision-ceo) · System Benchmark [§1 Executive Summary](./CKAC-SYSTEM-BENCHMARK.md#1-executive-summary-ceo-lens) · CPO Blueprint [§1–2](./CKAC-CPO-PRODUCT-BLUEPRINT.md)

### 1.2 Problem → Solution (implemented foundation)

| Pain | Kitchcu module (built/planned) | Status |
|------|----------------------------|--------|
| Orders lost in WhatsApp | Notification + Order drafts | **Partial** — webhook + parser + draft confirm |
| No structured menu | Catalog | **Done** — dishes, categories, live-capture rule |
| No order tracking | Order lifecycle | **Done** — state machine + audit events |
| Walk-in / phone orders | Order manual entry | **Done** |
| Aggregator commission | Billing subscription | **Planned S6** |
| Stock photo deception | Catalog media validator | **Done** — hero requires `is_live_capture` |

**Maps to:** CPO Blueprint [§2 Pain Points → Solutions](./CKAC-CPO-PRODUCT-BLUEPRINT.md)

### 1.3 Product principles (enforced in code)

1. **Truth in media** — `DishMediaInput` validator rejects hero without live capture (`services/catalog/app/schemas.py`)
2. **Quality over speed** — ETA from sum of `prep_time_min`, not fake delivery races
3. **Owner sovereignty** — kitchen-scoped data; CRM schema planned Phase 2
4. **Progressive complexity** — backend MVP first; Owner PWA Sprint 5
5. **WhatsApp-native** — notification service + draft flow Sprint 4

**Maps to:** Planning Benchmark [§2.1 Product Principles](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#2-product-strategy-cpo) · AGENTS.md §1

### 1.4 Personas & surfaces

| Persona | Goal | Surface today | Surface planned |
|---------|------|---------------|-----------------|
| **Raj (Owner)** | Run kitchen, see orders | **kitchen.kitchcu.in** PWA (orders, menu, reports) | Full offline PWA (S5+) |
| **Priya (Customer)** | Order trusted food | **customer.kitchcu.in** PWA (browse, nearby) | Checkout + accounts (Phase 2) |
| **Platform admin** | Moderate, support, refunds, packages, staff RBAC | **admin.kitchcu.in** (Overview, Packages, Employees, Control, kitchen workspace) | Super-admin plane ✅ P25–P28 |

**Maps to:** Planning Benchmark [§2.2 Personas](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#22-personas-detailed) · System Benchmark [§2.2 Personas](./CKAC-SYSTEM-BENCHMARK.md#22-personas)

### 1.5 Monetization (spec vs implementation)

| Revenue stream | Spec | Implementation |
|----------------|------|----------------|
| Owner subscription tiers | F26 | DB columns on `owners` (`subscription_tier`, `subscription_status`); billing service **S6** |
| Zero food commission | Core principle | Enforced by product design; no commission tables |
| Customer tiffin | F34 | Phase 2 — `ckac_marketing` schema reserved |
| Live prep premium | F48 | Phase 3 |

**Maps to:** Planning Benchmark [§1.4 Business Model](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#14-business-model) · System Benchmark [§12 Monetization](./CKAC-SYSTEM-BENCHMARK.md#12-monetization--unit-economics)

---

## 2. Feature Implementation Matrix

Legend: ✅ Done · 🟡 Partial · ⏳ Not started

### Phase 1 — Owner can run kitchen

| ID | Feature | Priority | Status | Code / notes |
|----|---------|----------|--------|--------------|
| **F01** | WhatsApp order capture | Must | 🟡 | `services/notification/` webhook; `order_drafts`; confirm → order. Missing: customer tracking link, parse metrics |
| **F02** | Normal message order capture | Must | ✅ | `POST .../orders/parse-message`, source `manual_message` |
| **F03** | Custom manual order input | Must | ✅ | `POST .../orders/manual`, source `manual` |
| **F04** | Order lifecycle management | Must | ✅ | State machine in `order/app/models.py`; `PATCH .../status`; `order_status_events` |
| **F05** | Order history tracker | Must | ✅ | `GET .../orders` with `status`, `source` filters; index `(kitchen_id, created_at DESC)` |
| **F07** | Revenue report | Must | 🟡 | `services/order/app/analytics.py` — summary, timeseries, top dishes, peak hours, customer segments; owner Reports UI |
| **F13** | Add dish with live photo | Must | ✅ | `POST .../dishes` + `DishMediaInput` validator |
| **F14** | Price, ingredients, quality | Must | ✅ | Dish model fields + create API |
| **F15** | Dish categories | Must | ✅ | Auto-seed 10 categories; `GET .../categories` |
| **F26** | Owner subscription | Must | 🟡 | Owner table columns; payment flow S6 |
| **F30** | Per-dish prep/delivery time | Must | ✅ | `prep_time_min` on dish; order ETA uses max prep |
| **F42** | Online pay + COD | Must | ⏳ | `payment_method` field on order; Razorpay S6 |
| **F43** | Owner UPI scanner | Must | ⏳ | Billing service S6 |
| **F45** | App + WhatsApp notifications | Must | 🟡 | Inbound webhook; AI support chat + ticketing on portal; outbound WhatsApp pending |

### Phase 2 — Growth (not started in code)

| ID | Feature | Status |
|----|---------|--------|
| F06 | Multi-kitchen checkout | ⏳ |
| F08–F12 | Analytics & growth | ⏳ |
| F16–F18 | Ratings | ⏳ |
| F25 | Social share | ⏳ |
| F27–F33 | Delivery & customer PWA | ⏳ |
| F34–F41 | CRM, coupons, tiffin | ⏳ |
| F44 | Split payment | ⏳ |

### Phase 3 — Differentiation

F19–F24, F46–F48 — **shipped** in S15–S18 (see [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md)). Per-dish go-live showcase = **P22**.

### Post-S18 platform ops (P19–P28)

| ID | Feature | Status | Code / notes |
|----|---------|--------|--------------|
| P25 | Package mapper | ✅ | `services/billing/app/packages.py` · Admin → Packages · `008_packages` |
| P26 | WA/email templates | ✅ | `services/marketing/app/templates.py` · Owner Templates · `002_message_templates` |
| P27 | Employees + RBAC | ✅ | `services/identity/app/rbac.py` · Admin → Employees · `013_admin_rbac_employees` |
| P28 | Super-admin kitchen workspace gate | ✅ | Admin kitchen tabs + `.cursor/rules/kitchcu-superadmin-integration.mdc` |

**Maps to:** Planning Benchmark [§11 Feature Index](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#11-feature-index-all-45-features) · [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md) · DEVELOPMENT-PHASES.md

---

## 3. Architecture

### 3.1 Style

**Event-driven microservices** on Python 3.12 + FastAPI. Single PostgreSQL cluster, **schema-per-bounded-context**. Redis Streams for events; transactional outbox on all writes. See [CKAC-ARCHITECTURE-CTO.md](./CKAC-ARCHITECTURE-CTO.md) for layered view and CPO mapping.

**Maps to:** System Benchmark [§3 Technical Architecture](./CKAC-SYSTEM-BENCHMARK.md#3-technical-architecture-cto-lens) · Planning Benchmark [§4 Technical Architecture](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#4-technical-architecture-cto)

### 3.2 Service topology

```
                         ┌─────────────────┐
                         │  API Gateway    │  :18000
                         └────────┬────────┘
                                  │
     ┌────────────┬───────────────┼───────────────┬────────────┐
     ▼            ▼               ▼               ▼            ▼
 Identity     Catalog           Order      Notification    (future)
 :18001       :18002            :18003         :18005       Billing :18004
     │            │               │               │
     └────────────┴───────────────┴───────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            PostgreSQL 16                 Redis 7
            + PostGIS                       Streams + cache
                    │
                    MinIO :9000 (media storage ready)
```

### 3.3 Service responsibilities

| Service | Path | Owns writes to | Key events published |
|---------|------|----------------|----------------------|
| **gateway** | `services/gateway/` | — | — |
| **identity** | `services/identity/` | `ckac_identity` | `kitchen.created` |
| **catalog** | `services/catalog/` | `ckac_catalog` | `dish.created`, `dish.updated` |
| **order** | `services/order/` | `ckac_orders` | `order.placed`, `order.status.changed`, `order.draft.created` |
| **notification** | `services/notification/` | `ckac_support` (tickets) | `whatsapp.message.received`, `support.ticket.*` |
| **ckac-common** | `packages/ckac-common/` | — | EventPublisher, auth, cache, health, internal_auth |

**Maps to:** System Benchmark [§3.2 Service Boundaries](./CKAC-SYSTEM-BENCHMARK.md#32-service-boundaries)

### 3.4 Gateway routing rules

| Request path | Target |
|--------------|--------|
| `/api/v1/auth/*`, `/api/v1/owners/*` | Identity |
| `/api/v1/kitchens` (no order/catalog sub-path) | Identity |
| `/api/v1/kitchens/{id}/categories`, `/menu`, `/dishes` | Catalog |
| `/api/v1/kitchens/{id}/orders/*` | Order |
| `/api/v1/orders/*` | Order |
| `/api/v1/webhooks/*`, `/api/v1/support/*` | Notification |
| `/api/v1/admin/tickets*` | Notification (admin JWT) |
| `/api/v1/kitchens/{id}/analytics/*` | Order |

Implementation: `services/gateway/app/main.py` → `resolve_service_url()`

**Maps to:** System Benchmark [§9 API & Integration Design](./CKAC-SYSTEM-BENCHMARK.md#9-api--integration-design)

### 3.5 Cross-service rules

| Rule | Implementation |
|------|----------------|
| No cross-schema writes | Each service Alembic owns one schema |
| Cross-schema reads OK | Catalog/Order `SELECT` from `ckac_identity.kitchens` for auth |
| Menu reads for orders | Order loads dishes from `ckac_catalog.dishes` at order/draft time |
| Internal API | Order `/internal/...` secured with `X-Internal-Key` via `ckac_common.internal_auth` |
| Menu cache | Catalog GET menu — Redis TTL 300s; invalidate on dish create/update |
| JWT | Owner tokens; `decode_owner_id()` in `ckac_common.auth` |

**Maps to:** AGENTS.md §2.1 · Planning Benchmark [§4](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#4-technical-architecture-cto)

---

## 4. Database Design

### 4.1 Schema roadmap vs implementation

| Schema | Planning spec | Implemented tables | Migration |
|--------|---------------|-------------------|-----------|
| `ckac_identity` | §5 DBA | `owners`, `kitchens` (+ `whatsapp_phone_id`) | identity `001`, `002` |
| `ckac_catalog` | §5 DBA | `categories`, `dishes`, `dish_media` | catalog `001` |
| `ckac_orders` | §5 DBA | `orders`, `order_items`, `order_status_events`, `order_drafts` | order `001`, `002` |
| `ckac_events` | §5 / outbox | `outbox`, `processed_events` | `infra/postgres/init/02-events.sql` |
| `ckac_billing` | §9 | — | Sprint 6 |
| `ckac_marketing` | Phase 2 | — | — |

Bootstrap: `infra/postgres/init/01-schemas.sql` (extensions: uuid-ossp, postgis, pg_trgm)

**Maps to:** System Benchmark [§4 Database Architecture](./CKAC-SYSTEM-BENCHMARK.md#4-database-architecture-dba-lens) · Planning Benchmark [§5 Database Architecture](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#5-database-architecture-dba) · DEVELOPMENT-PHASES.md PostgreSQL roadmap

### 4.2 Entity reference (implemented)

#### `ckac_identity.owners`

Registration, subscription metadata, phone-as-identity.

#### `ckac_identity.kitchens`

| Field | Product meaning |
|-------|-----------------|
| `code` | Public kitchen ID prefix in order codes (`CKPNQ001`) |
| `location` | PostGIS point — future discovery & delivery (F27, F31, F32) |
| `free_delivery_radius_km`, `max_delivery_radius_km` | Spec fields; logic Phase 2 |
| `whatsapp_phone_id` | Links Meta Business phone to kitchen (F01) |
| `settings` | JSONB extensibility |

#### `ckac_catalog`

- **categories** — 10 defaults: Veg, Non Veg, Vegan, Beverages, etc.
- **dishes** — menu item with price, prep time, quality fields (F13–F15, F30)
- **dish_media** — URL + live-capture flags (F13 trust layer)

#### `ckac_orders`

- **orders** — bill header; `source` distinguishes whatsapp / manual / manual_message
- **order_items** — snapshot pricing at order time
- **order_status_events** — F04 audit trail
- **order_drafts** — F01/F02 pre-confirmation parsed messages (JSONB parsed_items)

### 4.3 Indexing (implemented)

| Index | Purpose | Spec reference |
|-------|---------|----------------|
| `ix_orders_kitchen_created` | Order history by date (F05) | System Benchmark §4.5 |
| `ix_orders_kitchen_status` | Filter active orders | F05 |
| GIST on `kitchens.location` | Geo queries (future) | System Benchmark §4.5 |
| `uq_category_kitchen_slug` | Category uniqueness per kitchen | F15 |

### 4.4 Naming conventions

| Entity | Format | Example |
|--------|--------|---------|
| Kitchen code | `CK` + region + seq | `CKPNQ001` |
| Bill ID | `BILL-YYYYMMDD-SEQ` | `BILL-20260712-0001` |
| Order code | `{kitchen_code}-{bill_id}` | `CKPNQ001-BILL-20260712-0001` |

**Maps to:** System Benchmark [§16 Appendix Naming](./CKAC-SYSTEM-BENCHMARK.md#16-appendix-naming-codes--conventions)

---

## 5. Event-Driven Design

### 5.1 Envelope standard

```json
{
  "event_id": "uuid",
  "event_type": "order.placed",
  "schema_version": "1.0",
  "aggregate_type": "order",
  "aggregate_id": "uuid",
  "occurred_at": "ISO8601",
  "producer": "order-service",
  "payload": {}
}
```

Code: `packages/ckac-common/ckac_common/events.py`

**Maps to:** System Benchmark [§3.3 Event-Driven Patterns](./CKAC-SYSTEM-BENCHMARK.md#33-event-driven-patterns)

### 5.2 Live event catalog

| Event | Producer | Stream | Trigger | Spec |
|-------|----------|--------|---------|------|
| `kitchen.created` | identity | `ckac:identity:kitchen` | POST kitchen | F26 |
| `dish.created` | catalog | `ckac:catalog:dish` | POST dish | Planning §12 / catalog events |
| `dish.updated` | catalog | `ckac:catalog:dish` | PATCH dish | F13/F15 |
| `order.placed` | order | `ckac:orders:order` | Manual or draft confirm | F03, F01 |
| `order.status.changed` | order | `ckac:orders:order` | PATCH status | F04 |
| `order.draft.created` | order | `ckac:orders:draft` | Parse message / WhatsApp | F01, F02 |
| `whatsapp.message.received` | notification | `ckac:notify:whatsapp` | Webhook POST | F01, Planning §8 |

Publisher: `ckac_common.event_bus.EventPublisher` — outbox insert + Redis `XADD` when `session` is passed; commit via `get_db()`.

### 5.3 Outbox (write path active)

Tables `ckac_events.outbox` and `processed_events` exist. Every service write path passes `session=session` to `publish()` so events are recorded in the outbox in the same DB transaction as the domain write. Relay worker for retry/at-least-once delivery is **Phase 4** (Kafka migration).

**Maps to:** Planning Benchmark [§6–7](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) · DEVELOPMENT-PHASES.md EDD rules

### 5.4 Future consumers (spec, not built)

| Event | Planned consumer |
|-------|------------------|
| `order.placed` | Notification (owner alert), Analytics, Billing |
| `order.status.changed` | Notification (customer WhatsApp/push F45), tracking UI |
| `dish.updated` | Menu cache invalidation |

**Maps to:** System Benchmark [§8 Core Domain Flows](./CKAC-SYSTEM-BENCHMARK.md#8-core-domain-flows)

---

## 6. Application Flows

### 6.1 Owner onboarding (Sprint 1)

```
Register (phone, name)
  → OTP request (dev OTP: 123456)
  → OTP verify → JWT
  → Create kitchen (name, address, lat/lng)
  → Receive kitchen code
```

**APIs:** Identity `/owners/register`, `/auth/otp/*`, `/kitchens`  
**Maps to:** Planning Benchmark [§2.3 Owner Journey Day 0](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#23-user-journey-maps) · CPO Blueprint [§4.1](./CKAC-CPO-PRODUCT-BLUEPRINT.md)

### 6.2 Menu publish (Sprint 2)

```
GET categories (auto-seed if empty)
  → POST dish with live-capture hero media
  → dish.created event
  → Public GET menu (no auth)
```

**Maps to:** System Benchmark [§8.2 adjacent catalog flow](./CKAC-SYSTEM-BENCHMARK.md) · F13–F15

### 6.3 Manual order (Sprint 3)

```
POST manual order (items, delivery_type, payment_method)
  → Validate dishes active in catalog
  → Generate bill_id + order_code
  → status=received, compute ETA
  → order.placed event
  → PATCH status through lifecycle
  → order.status.changed each step
```

**Lifecycle:** `received → accepted → preparing → ready → out_for_delivery → delivered` (or `cancelled` with reason)

**Maps to:** Planning Benchmark F03–F05, F30 · System Benchmark [§8.2 Order Lifecycle](./CKAC-SYSTEM-BENCHMARK.md#82-order-lifecycle-quality-first)

### 6.4 Message → draft → order (Sprint 4)

**Path A — Owner paste (F02):**
```
POST parse-message
  → parser: qty + dish names + notes
  → match menu (fuzzy)
  → order_drafts row
  → order.draft.created
  → POST drafts/{id}/confirm
  → order.placed (source=manual_message)
```

**Path B — WhatsApp (F01):**
```
Meta POST webhook
  → notification extracts message
  → lookup kitchen by whatsapp_phone_id
  → whatsapp.message.received
  → HTTP POST order /internal/.../from-whatsapp
  → same draft flow (source=whatsapp)
  → owner confirms in future PWA
```

Parser: `services/order/app/parser.py` — rule-based (not ML).

**Maps to:** Planning Benchmark F01–F02 · System Benchmark [§8.1 Order Intake WhatsApp](./CKAC-SYSTEM-BENCHMARK.md#81-order-intake-whatsapp) · Planning [§8 Notification System](./CKAC-COMPLETE-PLANNING-BENCHMARK.md#8-notification-system-app--whatsapp)

### 6.5 Flows specified but not implemented

| Flow | Spec section | Target sprint |
|------|--------------|---------------|
| Multi-kitchen checkout | System Benchmark §8.3 | Phase 2 / S8 |
| Delivery fee decision | System Benchmark §8.4 | Phase 2 |
| Home taste rating | System Benchmark §8.5 | Phase 2 / S11 |
| Revenue dashboard | F07 | S6 |
| Outbound WhatsApp status | F45 | S4+ / notification extend |

---

## 7. API Reference

Base URL (dev): `http://localhost:18000/api/v1`

### Identity

| Method | Path | Auth | Feature |
|--------|------|------|---------|
| POST | `/auth/otp/request` | — | Onboarding |
| POST | `/auth/otp/verify` | — | JWT |
| POST | `/owners/register` | — | Onboarding |
| GET | `/owners/me` | Bearer | Profile |
| POST | `/kitchens` | Bearer | Kitchen create |
| GET | `/kitchens/me` | Bearer | List kitchens |

### Catalog

| Method | Path | Auth | Feature |
|--------|------|------|---------|
| GET | `/kitchens/{id}/categories` | Bearer | F15 |
| GET | `/kitchens/{id}/menu` | Public | F13 |
| POST | `/kitchens/{id}/dishes` | Bearer | F13–F14 |
| PATCH | `/kitchens/{id}/dishes/{dish_id}` | Bearer | F13/F15 update, cache invalidation |

### Order

| Method | Path | Auth | Feature |
|--------|------|------|---------|
| POST | `/kitchens/{id}/orders/manual` | Bearer | F03 |
| POST | `/kitchens/{id}/orders/parse-message` | Bearer | F02 |
| GET | `/kitchens/{id}/orders/drafts` | Bearer | F01/F02 inbox |
| POST | `/kitchens/{id}/orders/drafts/{id}/confirm` | Bearer | F01/F02 |
| GET | `/kitchens/{id}/orders` | Bearer | F05 |
| GET | `/orders/{id}` | Bearer | F05 |
| PATCH | `/orders/{id}/status` | Bearer | F04 |
| POST | `/internal/kitchens/{id}/orders/from-whatsapp` | X-Internal-Key | F01 |

### Notification

| Method | Path | Auth | Feature |
|--------|------|------|---------|
| GET | `/webhooks/whatsapp` | Verify token | Meta setup |
| POST | `/webhooks/whatsapp` | Meta | F01 intake |

OpenAPI (aggregated): `http://localhost:18000/docs` · portal `http://localhost:13000/openapi` · raw `http://localhost:18000/openapi.json` · human index [`API.md`](./API.md)

---

## 8. Benchmark Cross-Reference

Maps **System Benchmark (`CKAC-SYSTEM-BENCHMARK.md`)** sections to implementation.

| System Benchmark § | Title | Implementation status |
|--------------------|-------|----------------------|
| 1 | Executive Summary | Product vision documented; MVP in progress |
| 2 | Product Vision & CPO | Principles in AGENTS.md + validators |
| 3 | Technical Architecture | **Done** — 5 services + gateway + common |
| 4 | Database Architecture | **Partial** — identity, catalog, orders, events bootstrap |
| 5 | Caching Strategy | **Not started** — Redis used for events only |
| 6 | Docker & Infrastructure | **Done** — docker-compose 8 services |
| 7 | Feature Catalog | See [§2 Feature Matrix](#2-feature-implementation-matrix) |
| 8 | Core Domain Flows | **Partial** — §8.1–8.2; 8.3+ Phase 2 |
| 9 | API & Integration | **Done** — gateway routing + internal key |
| 10 | Security & Compliance | JWT auth; RLS planned; PCI via Razorpay later |
| 11 | Scalability & SLOs | Single PG; path documented in DEVELOPMENT-PHASES |
| 12–15 | Business, phases, KPIs | Spec only |
| 17 | Notification System | **Partial** — inbound webhook |
| 18 | Payment & Settlement | **Not started** |
| 19 | Growth Engine | **Not started** |
| 16 | Naming conventions | **Done** — order codes, kitchen codes |

---

## 9. Planning Benchmark Cross-Reference

Maps **Complete Planning Benchmark (`CKAC-COMPLETE-PLANNING-BENCHMARK.md`)** parts to code.

| Part | Section | Implementation |
|------|---------|----------------|
| **A — Strategy** | §1 CEO Vision | Documented; aligns with CPO PDF |
| | §2 CPO Strategy | Personas/journeys — PWA not built |
| | §3 PWA Blueprint | **Sprint 5** — React + Vite planned |
| | §4 CTO Architecture | **Implemented** — see §3 above |
| | §5 DBA | **Partial** — see §4 above |
| | §6 Caching | Redis streams only |
| | §7 Docker | **Implemented** |
| | §8 Notifications | Inbound WhatsApp only |
| | §9 Payments | Not started |
| | §10 Growth engine | Not started |
| **B — Features** | §12 F01–F06 Orders | F01–F05 partial/done; F06 Phase 2 |
| | §13 F07–F12 Analytics | Not started |
| | §14 F13–F20 Catalog | F13–F15 done; F16+ Phase 2/3 |
| | §15–19 F21–F48 | Not started |
| **C — Execution** | §20 Dependencies | See DEVELOPMENT-PHASES.md |
| | §21 Sprint backlog | S1–S4 ✅; S5–S6 next |
| | §22–23 KPIs, risks | Spec only |

---

## 10. Engineering Reference

### 10.1 Sprint delivery log

| Sprint | Deliverable | Tests (approx) |
|--------|-------------|----------------|
| S1 | Identity, gateway, Docker, JWT, TDD setup | 25 identity + 10 gateway |
| S2 | Catalog, live-capture, `dish.created` | 10 catalog |
| S3 | Order manual, lifecycle, history | 16 order |
| S4 | WhatsApp webhook, parser, drafts, support chat | +10 order, +8 notification |
| S5 | PWAs (portal, customer, kitchen, admin), owner analytics, ticketing | Frontend + order analytics |
| **Total** | | **90+** |

### 10.2 Repository map

```
CKAC/
├── AGENTS.md                         Agent rules + status
├── packages/ckac-common/             Shared library
├── services/
│   ├── gateway/app/main.py           Routing v0.4
│   ├── identity/                     S1 + whatsapp_phone_id (002)
│   ├── catalog/                      S2
│   ├── order/                        S3–4 (+ app/parser.py)
│   └── notification/                 S4
├── infra/postgres/init/              Schemas + outbox
├── docs/
│   ├── CKAC-IMPLEMENTATION-GUIDE.md    ← this document
│   ├── CKAC-COMPLETE-PLANNING-BENCHMARK.md
│   ├── CKAC-SYSTEM-BENCHMARK.md
│   ├── CKAC-CPO-PRODUCT-BLUEPRINT.md
│   └── DEVELOPMENT-PHASES.md
├── docker-compose.yml
└── scripts/run-tests.ps1
```

### 10.3 Dev ports

| Service | Host port |
|---------|-----------|
| Gateway | 18000 |
| Identity | 18001 |
| Catalog | 18002 |
| Order | 18003 |
| Notification | 18005 |
| Portal (marketing) | 13000 |
| Customer PWA | 13001 |
| Kitchen PWA | 13002 |
| Admin PWA | 13003 |
| PostgreSQL | 15432 |
| Redis | 16379 |
| MinIO | 9000 / 9001 |

### 10.4 TDD pattern

```
RED → failing test → GREEN → minimal code → REFACTOR
```

- `tests/conftest.py` — NullPool engine, psycopg2 truncate, JWT fixtures
- `tests/test_events.py` — Redis `XREAD` assertions
- `asgi-lifespan` — FastAPI lifespan in tests

### 10.5 Run locally

```powershell
docker compose up --build -d
.\scripts\run-tests.ps1
```

### 10.6 Next implementation (from DEVELOPMENT-PHASES.md)

| Sprint | Scope |
|--------|-------|
| **S5** | Owner PWA — inbox, order board, menu manager |
| **S6** | Billing service — F07, F26, F42, F43; `ckac_billing` |

---

## Document control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | July 2026 | Initial guide — Sprints 1–4 mapped to benchmarks |

**Maintainers:** Update this file when a sprint completes or a feature moves from partial → done. Cross-update `AGENTS.md` §2 status table and `DEVELOPMENT-PHASES.md` sprint headers.
