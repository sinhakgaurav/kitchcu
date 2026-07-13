# Kitchcu — Complete Executive Guide

**Kitchcu cloud kitchen platform**

| Field | Value |
|-------|-------|
| Version | 1.1 |
| Status | Phase 1 partial — S1–S4 backend complete; S5 PWAs + portal + analytics + support/tickets partial |
| Audience | **CEO, CPO, CTO**, Product, Engineering, Investors |
| Last updated | July 2026 |
| PDF | [`CKAC-COMPLETE-GUIDE.pdf`](./CKAC-COMPLETE-GUIDE.pdf) |
| Living code map | [`CKAC-IMPLEMENTATION-GUIDE.md`](./CKAC-IMPLEMENTATION-GUIDE.md) |

> **Purpose:** Single source of truth combining executive strategy (CEO), product depth (CPO), and technical architecture (CTO). Companion deep specs remain in [`CKAC-SYSTEM-BENCHMARK.md`](./CKAC-SYSTEM-BENCHMARK.md), [`CKAC-CPO-PRODUCT-BLUEPRINT.md`](./CKAC-CPO-PRODUCT-BLUEPRINT.md), and [`CKAC-ARCHITECTURE-CTO.md`](./CKAC-ARCHITECTURE-CTO.md).

---

## Table of Contents

### Part I — CEO Lens
1. [Executive Summary](#part-i--ceo-lens)
2. [Market & Strategic Positioning](#12-market--strategic-positioning)
3. [Business Model & Unit Economics](#13-business-model--unit-economics)
4. [Go-to-Market & Phases](#14-go-to-market--development-phases)
5. [North-Star Metrics & Investment Thesis](#15-north-star-metrics--investment-thesis)
6. [Risks & Mitigations](#16-risks--mitigations)

### Part II — CPO Lens
7. [Product Vision & Personas](#part-ii--cpo-lens)
8. [Pain Points → Solutions](#82-pain-points--solutions)
9. [Platform Modules & Feature Catalog](#83-platform-modules--feature-catalog)
10. [Application Flows](#84-application-flows)
11. [Product Principles & KPIs](#85-product-principles--kpis)

### Part III — CTO Lens
12. [Architecture Overview](#part-iii--cto-lens)
13. [Services, Events & Data Flow](#132-services-events--data-flow)
14. [Database & Caching](#133-database--caching)
15. [API Reference & Security](#134-api-reference--security)
16. [Build Status & Engineering Standards](#135-build-status--engineering-standards)

### Appendices
17. [Feature Implementation Matrix](#appendix-a-feature-implementation-matrix)
18. [Document Index](#appendix-b-document-index)

---

# Part I — CEO Lens

## 1.1 Executive Summary

**Kitchcu** is a **B2B2C cloud kitchen operating system** — not another food aggregator. It gives kitchen owners full control over orders, quality, ingredients, marketing, and customer relationships while giving customers **real-time transparency** into what they eat, how far it travels, and how it was prepared.

| Stakeholder | Pain Today | Kitchcu Answer |
|-------------|-----------|-------------|
| Cloud kitchen owner | Orders scattered on WhatsApp, no revenue insight, aggregator commissions 18–30% | Unified order hub, analytics, subscription model (no per-order commission) |
| Customer | Stock photos, unknown quality, opaque delivery | Live-capture dish photos, home-taste ratings, distance-aware delivery |
| Market | Fragmented local kitchens, no quality benchmark | Chef rankings, recipe rewards, social sharing (Phase 3) |

### CEO Guiding Principle

> **Keep the product simple for the owner on day one.** A kitchen owner should accept a WhatsApp order and see revenue in under 5 minutes of onboarding. Learning portal, chef rankings, and live stream are growth layers — not blockers.

### Current State (July 2026)

| Metric | Value |
|--------|-------|
| Sprints complete | S1–S4 backend ✅; S5 PWAs + portal + analytics + support partial |
| Automated tests | **90+ passing** |
| Services live | Gateway + 5 microservices (identity, catalog, order, notification) |
| Apps live | Portal :13000 · customer.kitchcu.in :13001 · kitchen.kitchcu.in :13002 · admin.kitchcu.in :13003 |
| Next milestone | S6 Billing + outbound WhatsApp |

---

## 1.2 Market & Strategic Positioning

```
┌─────────────────────────────────────────────────────────────────┐
│  Aggregators (Swiggy/Zomato)     │  Kitchcu                        │
│  ─────────────────────────────   │  ─────────────────────────   │
│  Per-order commission            │  Monthly/yearly subscription │
│  Platform owns customer          │  Owner owns customer CRM       │
│  Stock photos                    │  Live-capture dish media       │
│  Speed-first delivery race       │  Quality-first delivery SLA    │
│  Single kitchen per cart         │  Multi-kitchen cart (unique)   │
└─────────────────────────────────────────────────────────────────┘
```

**Competitive moat:** WhatsApp-native operations + live-capture integrity + owner-owned CRM + quality-first lifecycle — none of which aggregators offer without taking commission.

**vs POS systems:** Kitchcu adds customer discovery, trust layer (live photos, ratings), and marketing intelligence — POS handles in-store only.

---

## 1.3 Business Model & Unit Economics

### Revenue Streams

| Stream | Model | Phase |
|--------|-------|-------|
| Owner subscription | Monthly/yearly tiers (Starter → Pro → Enterprise) | Phase 1 |
| Customer tiffin | Kitchen-defined pricing; **0% Kitchcu commission** | Phase 2 |
| Live prep premium | Platform add-on for customers filtering live kitchens | Phase 3 |

### Subscription Tiers (Benchmark)

| Tier | Monthly | Yearly | Includes |
|------|---------|--------|----------|
| **Starter** | ₹499 | ₹4,999 | 1 kitchen, 50 dishes, basic reports, WhatsApp orders |
| **Pro** | ₹1,499 | ₹14,999 | CRM, coupons, tiffin, marketing, multi-staff |
| **Enterprise** | ₹3,999 | ₹39,999 | Live streaming, API access, branches, priority support |

### Unit Economics Target (Year 1)

| Metric | Goal |
|--------|------|
| CAC (owner) | < ₹2,000 |
| Owner LTV | > ₹18,000 (12+ month retention) |
| LTV:CAC | > 3:1 |
| Gross margin | > 75% (SaaS) |

**Core promise:** Zero per-order food commission. Kitchen keeps 100% of food revenue.

---

## 1.4 Go-to-Market & Development Phases

### Phase 1 — Foundation (Months 1–3): *Owner Can Run Kitchen*

**Goal:** 10 pilot kitchens processing real orders daily.

| Milestone | Deliverable | Status |
|-----------|-------------|--------|
| M1.1 | Docker stack, CI, identity, kitchen onboarding | ✅ |
| M1.2 | Catalog + live photo upload | ✅ |
| M1.3 | Order service + manual + WhatsApp intake | ✅ |
| M1.4 | Order lifecycle + notifications (inbound) | 🟡 |
| M1.5 | PWAs + portal + owner analytics + support/tickets | 🟡 S5 partial |
| M1.6 | Razorpay subscription + COD/UPI | ⏳ S6 |
| M1.7 | Pilot launch | ⏳ |

### Phase 2 — Growth (Months 4–6): *Customer Discovery & CRM*

Customer PWA, multi-kitchen cart, delivery radius/fees, ratings, CRM, coupons, tiffin, analytics, social share.

### Phase 3 — Differentiation (Months 7–10): *Quality & Community*

Ingredient mapper, learning portal, recipe rewards, chef rankings, live kitchen streaming.

### Phase 4 — Scale (Months 11–12+): *National Platform*

State/national rankings, multi-branch, ML forecasting, POS APIs, white-label franchises.

---

## 1.5 North-Star Metrics & Investment Thesis

### Platform North Stars

1. **Owner GMV managed on platform** (not Kitchcu revenue alone)
2. **Repeat order rate** (customer loyalty proxy)
3. **Dish rating consistency** (quality standardization)
4. **Owner NPS** (would they reduce aggregator dependency?)

### KPI Targets

| KPI | MVP Target | 12-Month Target |
|-----|------------|-----------------|
| Active kitchens | 10 | 500 |
| Orders/day (platform) | 50 | 5,000 |
| Owner retention (monthly) | 80% | 90% |
| Customer repeat rate (30-day) | 25% | 40% |
| WhatsApp order parse success | 60% | 85% |

### Investment Thesis (One Paragraph)

India's cloud kitchen segment is growing but owners are trapped between WhatsApp chaos and aggregator commissions. Kitchcu captures the **operating system layer** — subscription SaaS with zero food commission — while aggregators remain discovery-only competitors. Phase 1 proves daily order throughput; Phase 2 unlocks customer-side network effects; Phase 3 builds defensible community and quality benchmarks. Capital-efficient: modular monorepo, managed infra, PWA-first (no app store dependency).

---

## 1.6 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp API policy changes | Order intake breaks | Manual input always available; SMS fallback Phase 2 |
| Live stream complexity | Delays Phase 3 | Managed provider (LiveKit); owner opt-in only |
| Multi-kitchen checkout disputes | Payment/refund mess | Per-kitchen sub-order IDs; clear refund policy |
| Rating fraud | Trust erosion | Verified purchase only; anomaly detection |
| Scope creep | Never launch | Strict MoSCoW; Phase 1 is sacred |
| Owner onboarding friction | Low adoption | WhatsApp-first; 5-min setup target |

---

# Part II — CPO Lens

## 2.1 Product Vision & Personas

### Vision Statement

*Empower every cloud kitchen to scale like a brand — with data, quality standards, and direct customer relationships — while giving diners honest, real-time visibility into their food.*

| Stakeholder | One-line promise |
|-------------|------------------|
| Owner | WhatsApp order → revenue report same day |
| Customer | Live photos, home-taste ratings, fair delivery |
| Platform | Subscription SaaS — zero food commission |

### Personas

| Persona | Goals | Primary Surfaces |
|---------|-------|------------------|
| **Owner / Chef (Raj)** | Track orders, control quality, market dishes | **kitchen.kitchcu.in** PWA — orders, menu, reports |
| **Customer (Priya)** | Discover kitchens, order, track, rate | **customer.kitchcu.in** PWA — browse menu (checkout Phase 2) |
| **Ops / Staff** | Update lifecycle, inventory alerts | Staff PWA (owner subset) — planned |
| **Platform Admin** | Moderate, support tickets, subscriptions | **admin.kitchcu.in** — stats, kitchens, orders, tickets |

### PWA-First UI Strategy

| Factor | Rationale |
|--------|-----------|
| Cost | One codebase for Android, iOS, desktop |
| Distribution | WhatsApp links open directly — critical for order capture |
| Offline | Service workers cache menu, orders, drafts |
| Updates | No app store delay for menu/price changes |
| Camera | Live dish photo via `getUserMedia` |

**PWA targets:** Lighthouse ≥ 90, install prompt after 2nd visit, Web Push for order alerts.

---

## 2.2 Pain Points → Solutions

### Owner Pain Points (P1–P8)

| # | Pain | Kitchcu Module | Solution | Status |
|---|------|-------------|----------|--------|
| P1 | 70%+ orders on WhatsApp — no structure | Order + Notification | Unified inbox, parser, manual fallback | 🟡 Partial |
| P2 | Aggregator 18–30% commission | Billing | Flat monthly fee | ⏳ S6 |
| P3 | No daily profit visibility | Analytics | Owner revenue reports live; profit/margin needs ingredient cost (S6+) | 🟡 Partial |
| P4 | Stock photos mislead customers | Catalog + Media | Live-capture hero images enforced | ✅ Done |
| P5 | Batch-to-batch taste inconsistency | Catalog + Ingredient | Per-dish standards, ingredient mapper | 🟡 Fields only |
| P6 | Customer data owned by aggregators | Marketing | Owner CRM, coupons, tiffin | ⏳ Phase 2 |
| P7 | Promotions are guesswork | Growth Engine | Seasonal, win-back, combo suggestions | ⏳ Phase 2 |
| P8 | Multi-channel chaos | Order Service | Single lifecycle for all sources | 🟡 Partial |

### Customer Pain Points (C1–C6)

| # | Pain | Kitchcu Solution | Status |
|---|------|---------------|--------|
| C1 | Cannot trust menu photos | Live-capture dish media with timestamp | ✅ Done |
| C2 | Opaque delivery fees | PostGIS distance + owner rules at checkout | ⏳ Fields only |
| C3 | No real order tracking | Lifecycle + WhatsApp + push on transitions | 🟡 Partial |
| C4 | Generic star ratings | Home-taste benchmark (1–5) + optional A/V | ⏳ Phase 2 |
| C5 | One kitchen per cart | Multi-kitchen cart + single payment | ⏳ Phase 2 |
| C6 | Cannot subscribe to tiffin | Kitchen-defined meal plans | ⏳ Phase 2 |

---

## 2.3 Platform Modules & Feature Catalog

### Module Map

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Identity   │  │   Catalog   │  │    Order    │  │   Billing   │
│  S1 ✅      │  │   S2 ✅     │  │   S3 ✅     │  │   S6 ⏳     │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┼────────────────┼────────────────┘
                        ▼                ▼
                 ┌─────────────┐  ┌─────────────┐
                 │ Notification│  │  Analytics  │
                 │ S4 ✅ +     │  │  S5 🟡      │
                 │  support    │  │  (owner)    │
                 └─────────────┘  └─────────────┘
```

| Module | Responsibility | DB Schema | Status |
|--------|----------------|-----------|--------|
| **Gateway** | Auth routing, proxy | — | ✅ |
| **Identity** | Owners, kitchens, OTP, JWT | `ckac_identity` | ✅ S1 |
| **Catalog** | Menu, categories, live media | `ckac_catalog` | ✅ S2 |
| **Order** | Intake, lifecycle, history | `ckac_orders` | ✅ S3 |
| **Notification** | WhatsApp, AI support chat, tickets | `ckac_support` | ✅ S4 + support/tickets |
| **Billing** | Subscriptions, payments | `ckac_billing` | ⏳ S6 |
| **Analytics** | Owner revenue, segments, peak hours | order service + Redis cache | 🟡 S5 partial |
| **Marketing** | CRM, coupons, tiffin | `ckac_marketing` | Phase 2 |
| **Rating** | Home taste, A/V | `ckac_ratings` | Phase 2 |
| **Delivery** | Radius, fees, tracking | geo rules | Phase 2 |
| **Growth** | AI-ready suggestions | `ckac_growth` | Phase 2–3 |
| **Learning** | Recipes, trials | `ckac_learning` | Phase 3 |
| **Streaming** | Live prep | session metadata | Phase 3 |

### 48-Feature Catalog (Summary)

**Phase 1 — Must (Owner can run kitchen):** F01–F05, F07, F13–F15, F26, F30, F42–F43, F45

**Phase 2 — Growth:** F06, F08–F12, F16–F18, F25, F27–F33, F34–F41, F44

**Phase 3 — Differentiation:** F19–F24, F46–F48

See [Appendix A](#appendix-a-feature-implementation-matrix) for full matrix with implementation status.

---

## 2.4 Application Flows

### Owner Day-1 Onboarding

```
Register (phone) → OTP verify → JWT
  → Create kitchen (name, geo, code CKPNQ001)
  → Add dishes (live photo required for hero)
  → Connect WhatsApp (S4)
  → First order in inbox (< 5 min target)
```

### Order Intake (All Sources)

```
Source: WhatsApp | Manual | Customer PWA (future)
              │
              ▼
        Draft or Placed order
              │
              ▼
    order.placed → Redis Stream
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 Notify   Analytics  Billing (future)
```

### Order Lifecycle (F04)

```
received → accepted → preparing → ready → out_for_delivery → delivered
   │          │           │          │            │
   └──────────┴───────────┴──────────┴────────────┴──→ cancelled (reason required)
```

Each transition: persisted in `order_status_events`, publishes `order.status.changed`, triggers WhatsApp + push (outbound S4+).

### WhatsApp Order Flow (F01)

```
Meta webhook → gateway /webhooks/whatsapp
  → notification: lookup kitchen by whatsapp_phone_id
  → publish whatsapp.message.received
  → POST order /internal/.../from-whatsapp (X-Internal-Key)
  → parse message → draft → order.draft.created
  → owner confirms draft → order.placed
```

### Multi-Kitchen Checkout (F06 — Phase 2)

```
Cart: [Kitchen A items] + [Kitchen B items]
         │
         ▼
   master_orders (1 payment)
         │
    ┌────┴────┐
    ▼         ▼
 order A   order B  (separate lifecycle, separate bills)
         │
         ▼
Razorpay Route split settlement
```

### Delivery Fee Decision (Phase 2)

1. Compute distance (PostGIS) owner ↔ customer
2. If ≤ free_delivery_radius → fee = 0
3. If > radius → calculate fee (owner rules)
4. Present at checkout; owner can waive or customer switches to pickup

---

## 2.5 Product Principles & KPIs

### Non-Negotiable Principles

1. **WhatsApp-native order intake** — meet owners where they work
2. **Quality over speed** — owner-set prep/delivery windows, not fake "10 min" promises
3. **Trust through media** — live capture > uploaded stock photos
4. **Owner-owned CRM** — customer list, spend, patterns belong to the kitchen
5. **Progressive complexity** — MVP = orders + menu + reports; v2+ = learning, rankings, live stream

### CPO KPIs

| Metric | Phase 1 Target | Measurement |
|--------|----------------|-------------|
| Time to first order | < 5 min post-signup | Onboarding funnel |
| Owner daily active | 80% of paying kitchens | PWA analytics |
| Order capture rate | 95% WhatsApp parsed or manual | Parser accuracy |
| Lifecycle update latency | < 2s to customer notify | Event → push SLA |
| Menu trust score | 100% hero images live-capture | Catalog audit |
| Owner retention M6 | 80% | Subscription churn |
| Repeat customer rate | 40%+ | CRM aggregates |

---

# Part III — CTO Lens

## 3.1 Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXPERIENCE LAYER (S5 Owner PWA next)                                 │
│  Owner PWA · Customer PWA · WhatsApp (Meta webhook)                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / JWT
┌───────────────────────────────────▼─────────────────────────────────────┐
│  EDGE LAYER — API Gateway (:18000)                                    │
│  Path routing · CORS · future rate limits                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│  APPLICATION LAYER — Bounded-context microservices                      │
│  identity · catalog · order · notification (+ billing, analytics later) │
│  Pattern: routes → schemas → models                                     │
└───────────────┬─────────────────────────────┬───────────────────────────┘
                │                             │
┌───────────────▼──────────────┐   ┌──────────▼──────────────────────────┐
│  DOMAIN DATA LAYER           │   │  INTEGRATION LAYER                  │
│  PostgreSQL 16 + PostGIS     │   │  Redis Streams (events)             │
│  Schema-per-service          │   │  Redis cache (menu TTL 300s)        │
│  ckac_identity, catalog,     │   │  Internal HTTP (X-Internal-Key)     │
│  orders, events              │   │  Outbox (ckac_events.outbox)        │
└──────────────────────────────┘   └─────────────────────────────────────┘
                │
┌───────────────▼──────────────┐
│  MEDIA LAYER — MinIO / S3    │
│  Live-capture dish URLs      │
└──────────────────────────────┘
```

### Architecture Style

**Event-driven microservices** on Python 3.12 + FastAPI. Single PostgreSQL cluster with **schema-per-bounded-context**. Redis Streams for events; **transactional outbox** on all writes (post-commit flush).

### Tech Stack (Locked)

| Layer | Choice |
|-------|--------|
| API | Python 3.12, FastAPI, Pydantic v2 |
| Database | PostgreSQL 16 + PostGIS |
| Events / Cache | Redis 7 Streams + menu cache |
| Media | MinIO (dev) → S3 + CDN (prod) |
| Frontend | React + Vite + TypeScript PWA |
| Payments | Razorpay (UPI, subscriptions, Route split) |
| WhatsApp | Meta Business Cloud API |
| Observability | OpenTelemetry + Prometheus (Phase 2+) |
| CI/CD | GitHub Actions → Docker |

### Repository Structure

```
ckac/
├── apps/           # owner-pwa, customer-pwa (planned)
├── services/       # gateway, identity, catalog, order, notification
├── packages/       # ckac-common (shared lib)
├── infra/          # postgres init, docker
├── docs/           # this guide + benchmarks
└── docker-compose.yml
```

---

## 3.2 Services, Events & Data Flow

### Service Registry

| Service | Port | Schema | Key Events |
|---------|------|--------|------------|
| **gateway** | 18000 | — | — |
| **identity** | 18001 | `ckac_identity` | `kitchen.created` |
| **catalog** | 18002 | `ckac_catalog` | `dish.created`, `dish.updated` |
| **order** | 18003 | `ckac_orders` | `order.placed`, `order.status.changed`, `order.draft.created` |
| **notification** | 18005 | — | `whatsapp.message.received` |

### Gateway Routing

| Request path | Target |
|--------------|--------|
| `/api/v1/auth/*`, `/api/v1/owners/*` | Identity |
| `/api/v1/kitchens` (no order/catalog sub-path) | Identity |
| `/api/v1/kitchens/{id}/categories`, `/menu`, `/dishes` | Catalog |
| `/api/v1/kitchens/{id}/orders/*` | Order |
| `/api/v1/orders/*` | Order |
| `/api/v1/webhooks/*` | Notification |

### Event Catalog (EDD)

| Event | Producer | Stream | CPO Feature |
|-------|----------|--------|-------------|
| `kitchen.created` | identity | `ckac:identity:kitchen` | F26 |
| `dish.created` | catalog | `ckac:catalog:dish` | F13 |
| `dish.updated` | catalog | `ckac:catalog:dish` | F13/F15 |
| `order.placed` | order | `ckac:orders:order` | F03 |
| `order.status.changed` | order | `ckac:orders:order` | F04 |
| `order.draft.created` | order | `ckac:orders:draft` | F01/F02 |
| `whatsapp.message.received` | notification | `ckac:notify:whatsapp` | F01 |

### Event Envelope

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

### Outbox Pattern (Critical)

1. Domain write + outbox insert in **same DB transaction** via `EventPublisher.publish(..., session=session)`
2. `get_db()` calls `flush_pending()` **after commit** — prevents Redis-before-commit bug
3. Relay worker (retry, Kafka migration) — Phase 4

### Cross-Service Rules

| Rule | Implementation |
|------|----------------|
| No cross-schema writes | Each Alembic owns one schema |
| Cross-schema reads OK | Catalog/Order SELECT from `ckac_identity.kitchens` |
| Internal API | `X-Internal-Key` via `ckac_common.internal_auth` |
| Menu cache | Redis TTL 300s; invalidate on dish create/update |
| Advisory locks | `pg_advisory_xact_lock` for kitchen codes and bill IDs |

---

## 3.3 Database & Caching

### Schema Roadmap

| Schema | Tables (live) | Status |
|--------|---------------|--------|
| `ckac_identity` | owners, kitchens (+ whatsapp_phone_id) | ✅ LIVE |
| `ckac_catalog` | categories, dishes, dish_media | ✅ LIVE |
| `ckac_orders` | orders, order_items, order_status_events, order_drafts | ✅ LIVE |
| `ckac_events` | outbox, processed_events | ✅ LIVE |
| `ckac_support` | support_tickets, support_ticket_messages | ✅ LIVE |
| `ckac_billing` | payments, subscriptions | ⏳ S6 |
| `ckac_marketing` | customers, coupons, plans | Phase 2 |
| `ckac_ratings` | dish_ratings, suggestions | Phase 2 |

### Multi-Tenancy

Shared database, shared schema, tenant isolation via `kitchen_id`. Row Level Security planned for production.

### Key Indexes (Implemented)

| Index | Purpose |
|-------|---------|
| `ix_orders_kitchen_created` | Order history by date (F05) |
| `ix_orders_kitchen_status` | Filter active orders |
| GIST on `kitchens.location` | Geo queries (future) |
| `dish_media(dish_id)` | Media lookups |
| `processed_events (event_id, consumer)` | Idempotent consumers |

### Naming Conventions

| Entity | Format | Example |
|--------|--------|---------|
| Kitchen code | `CK` + region + seq | `CKPNQ001` |
| Bill ID | `BILL-YYYYMMDD-SEQ` | `BILL-20260712-0001` |
| Order code | `{kitchen_code}-{bill_id}` | `CKPNQ001-BILL-20260712-0001` |

### Caching Strategy

| Key Pattern | Data | TTL | Invalidation |
|-------------|------|-----|--------------|
| `menu:{kitchen_id}` | Full active menu JSON | 5 min | `dish.updated` event |
| `dish:{dish_id}` | Dish detail | 10 min | Rating/dish update |
| `kitchen:{id}:profile` | Kitchen info, delivery rules | 15 min | Settings change |

**Do not cache:** payment state, coupon redemption counts (atomic DB or Redis INCR).

### SLO Targets (Production)

| Metric | Target |
|--------|--------|
| API p95 latency (read) | < 200 ms |
| API p95 latency (write/order) | < 500 ms |
| Menu page load (PWA) | < 2 s on 4G |
| Order placement E2E | < 3 s |
| WhatsApp status notification | < 10 s from event |
| Uptime | 99.9% (Phase 2+) |

---

## 3.4 API Reference & Security

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
| PATCH | `/kitchens/{id}/dishes/{dish_id}` | Bearer | F13/F15 |

### Order

| Method | Path | Auth | Feature |
|--------|------|------|---------|
| POST | `/kitchens/{id}/orders/manual` | Bearer | F03 |
| POST | `/kitchens/{id}/orders/parse-message` | Bearer | F02 |
| GET | `/kitchens/{id}/orders/drafts` | Bearer | F01/F02 |
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

OpenAPI: `http://localhost:18000/docs`

### Security Benchmark

| Area | Implementation |
|------|----------------|
| Auth | JWT access + refresh; OTP for owners |
| Tenant isolation | PostgreSQL RLS (planned prod) |
| Media | Signed URLs; live-capture validator |
| PII | Mask phone in logs |
| Payments | PCI via Razorpay (S6) |
| Internal services | `X-Internal-Key` header |
| WhatsApp verify | Token required outside dev/test |
| Rate limiting | 100 req/min customer; 500 owner (planned) |

### Health Probes

Every service: `GET /health/live`, `GET /health/ready` (DB + Redis check).

---

## 3.5 Build Status & Engineering Standards

### Sprint Progress

| Sprint | Deliverable | Tests | Status |
|--------|-------------|-------|--------|
| S1 | Identity, gateway, Docker, JWT | 27 | ✅ |
| S2 | Catalog, live-capture, EDD | 13 | ✅ |
| S3 | Order manual, lifecycle, history | 28 | ✅ |
| S4 | WhatsApp webhook + parser + drafts | 15 | ✅ |
| S5 | Owner/customer/admin PWAs + portal + analytics + support | — | 🟡 Partial |
| S6 | Billing + payment integration | — | ⏳ |

**Total: 90+ automated tests** — run `.\scripts\run-tests.ps1` (identity, catalog, order, notification, gateway)

### Frontends (Docker)

| App | Host | URL |
|-----|------|-----|
| Marketing portal | `kitchcu` | http://localhost:13000 |
| Customer PWA | `customer.kitchcu.in` | http://localhost:13001 |
| Kitchen owner PWA | `kitchen.kitchcu.in` | http://localhost:13002 |
| Platform admin | `admin.kitchcu.in` | http://localhost:13003 |

### Feature Summary

| | Count |
|---|------|
| Features fully done | **9** (+F07 owner analytics partial) |
| Features partial | **6** |
| Phase 1 remaining | **3** (billing, payments, outbound notify) |
| Total spec | **48** |

### Engineering Standards

| Standard | Rule |
|----------|------|
| TDD | RED → GREEN → REFACTOR for every feature |
| EDD | DB commit first; outbox + Redis via session-bound publisher |
| Service template | `main.py`, `routes.py`, `schemas.py`, `models.py` |
| API versioning | `/api/v1/` prefix |
| Migrations | Alembic; backward-compatible only |
| Error format | RFC 7807 Problem Details (target) |
| Testing | Unit + API + event tests per service |

### Docker Stack (Local)

`postgres`, `redis`, `minio`, `gateway`, `identity`, `catalog`, `order`, `notification`

---

# Appendix A: Feature Implementation Matrix

Legend: ✅ Done · 🟡 Partial · ⏳ Not started

### Phase 1

| ID | Feature | Status | Notes |
|----|---------|--------|-------|
| F01 | WhatsApp order capture | 🟡 | Webhook + draft; outbound notify pending |
| F02 | Message parser | ✅ | `parse-message`, source `manual_message` |
| F03 | Manual order input | ✅ | `POST .../orders/manual` |
| F04 | Order lifecycle | ✅ | State machine + status events |
| F05 | Order history | ✅ | Filters by status, source |
| F07 | Revenue report | 🟡 | Owner analytics API + Reports UI (revenue, top dishes, peak hours, segments); platform billing S6 |
| F13 | Dish + live photo | ✅ | `DishMediaInput` validator |
| F14 | Price, ingredients, quality | ✅ | Dish model fields |
| F15 | Categories | ✅ | 10 default categories |
| F26 | Owner subscription | 🟡 | DB columns; payment S6 |
| F30 | Per-dish prep time | ✅ | `prep_time_min` on dish |
| F42 | Online pay + COD | ⏳ | `payment_method` field only |
| F43 | UPI scanner | ⏳ | Billing S6 |
| F45 | App + WhatsApp notify | 🟡 | Inbound webhook; AI support chat + ticketing on portal; outbound WhatsApp pending |

### Phase 2 (all ⏳)

F06, F08–F12, F16–F18, F25, F27–F33, F34–F41, F44

### Phase 3 (all ⏳)

F19–F24, F46–F48

---

# Appendix B: Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| **This guide** | CEO + CPO + CTO unified reference | All executives |
| [CKAC-IMPLEMENTATION-GUIDE.md](./CKAC-IMPLEMENTATION-GUIDE.md) | Living code ↔ spec map | Engineering |
| [CKAC-ARCHITECTURE-CTO.md](./CKAC-ARCHITECTURE-CTO.md) | Layers + product ↔ code traceability | CTO, EM |
| [CKAC-SYSTEM-BENCHMARK.md](./CKAC-SYSTEM-BENCHMARK.md) | Deep architecture, DB, SLOs | CTO, DBA |
| [CKAC-CPO-PRODUCT-BLUEPRINT.md](./CKAC-CPO-PRODUCT-BLUEPRINT.md) | Product modules & flows | CPO |
| [CKAC-COMPLETE-PLANNING-BENCHMARK.md](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) | 48 features + acceptance criteria | Product, Engineering |
| [DEVELOPMENT-PHASES.md](./DEVELOPMENT-PHASES.md) | Sprint roadmap | Engineering |
| [AGENTS.md](../AGENTS.md) | AI agent implementation rules | Developers |
| [CKAC-PITCH-DECK.pdf](./CKAC-PITCH-DECK.pdf) | Investor pitch (33 slides) | CEO, Investors |

### Regenerate PDF

```bash
python scripts/generate_complete_guide_pdf.py
```

Output: `docs/CKAC-COMPLETE-GUIDE.pdf`

---

## Document Control

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | July 2026 | Kitchcu rebrand; PWAs + portal; owner analytics; AI support chat & ticketing |
| 1.0 | July 2026 | Initial unified CEO/CPO/CTO complete guide |
