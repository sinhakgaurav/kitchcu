# Kitchcu — Product Depth Complete Guide

> **Superseded by [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md)** — the unified CEO + CPO + CTO guide. This file remains for reference.

**Comprehensive product reference — modules, features, flows, architecture, APIs, and delivery status**

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Audience | CPO, Product, Engineering, Investors, Partners |
| PDF | [`CKAC-PRODUCT-DEPTH-GUIDE.pdf`](./CKAC-PRODUCT-DEPTH-GUIDE.pdf) |
| Companion | [Implementation Guide](./CKAC-IMPLEMENTATION-GUIDE.md) · [CTO Architecture](./CKAC-ARCHITECTURE-CTO.md) · [CPO Blueprint](./CKAC-CPO-PRODUCT-BLUEPRINT.md) · [System Benchmark](./CKAC-SYSTEM-BENCHMARK.md) |
| Last updated | July 2026 |

---

## How to use this guide

| Need | Section |
|------|---------|
| Product vision and principles | [§1](#1-product-foundation) |
| Market pains and solutions | [§2](#2-market-problems--solutions) |
| Module deep dives | [§3](#3-platform-modules) |
| All 48 features with status | [§4](#4-48-feature-catalog) |
| End-to-end flows | [§5](#5-application--data-flows) |
| APIs, DB, stack | [§6](#6-technical-reference) |
| Business model, roadmap, KPIs | [§7](#7-business-delivery--metrics) |

**Pitch deck (33 slides):** [CKAC-PITCH-DECK.pdf](./CKAC-PITCH-DECK.pdf) — investor/CPO overview  
**This guide:** portrait reference manual with implementation depth

---

## 1. Product Foundation

### 1.1 Executive summary

**Kitchcu** (Kitchcu cloud kitchen platform) is a **B2B2C operating system for cloud kitchens** — not a food aggregator.

| Stakeholder | Promise |
|-------------|---------|
| Owner | WhatsApp order → revenue report same day |
| Customer | Live photos, home-taste ratings, fair delivery |
| Platform | Subscription SaaS — zero food commission |

### 1.2 Personas

| Persona | Goal | Surface today | Planned |
|---------|------|---------------|---------|
| Raj (Owner) | Run kitchen, see orders | kitchen.kitchcu.in PWA | Full offline PWA (S5+) |
| Priya (Customer) | Order trusted food | — | Customer PWA (Phase 2) |
| Platform admin | Moderate, bill | — | Admin console (Phase 4) |

### 1.3 Non-negotiable principles

1. **Truth in media** — hero dish photos must be live-capture (`DishMediaInput` validator)
2. **Quality over speed** — owner-set prep times; ETA from `prep_time_min`
3. **Owner sovereignty** — CRM and customer data belong to the kitchen
4. **Progressive complexity** — advanced features after kitchen traction
5. **WhatsApp-native** — primary order channel for Indian cloud kitchens

---

## 2. Market Problems & Solutions

### 2.1 Owner pains (P1–P8)

| ID | Pain | Module | Solution | Status |
|----|------|--------|----------|--------|
| P1 | WhatsApp chaos | Order + Notification | Parser, drafts, inbox | Partial |
| P2 | 18–30% aggregator commission | Billing | Flat subscription | Sprint 6 |
| P3 | No daily profit visibility | Analytics | Owner revenue reports live; profit margin S6+ | Partial |
| P4 | Stock photos mislead | Catalog | Live-capture enforced | **Done** |
| P5 | Taste inconsistency | Catalog | Quality fields, ingredient mapper (P3) | Partial |
| P6 | No CRM | Marketing | Owner CRM, coupons | Phase 2 |
| P7 | Promotion guesswork | Growth | Seasonal, win-back suggestions | Phase 2 |
| P8 | Multi-channel silos | Order | Single lifecycle + `source` | Partial |

### 2.2 Customer pains (C1–C6)

| ID | Pain | Answer | Status |
|----|------|--------|--------|
| C1 | Untrustworthy photos | Live-capture + timestamp | **Done** |
| C2 | Opaque delivery fees | PostGIS + owner rules | Fields only |
| C3 | No tracking | Lifecycle + WhatsApp/push | Partial |
| C4 | Generic ratings | Home-taste 1–5 | Phase 2 |
| C5 | One kitchen per cart | Multi-kitchen checkout | Phase 2 |
| C6 | No tiffin | Kitchen meal plans | Phase 2 |

---

## 3. Platform Modules

### 3.1 Architecture

```
Experience: Owner PWA | Customer PWA | WhatsApp
     ↓
Gateway :18000
     ↓
Identity :18001 | Catalog :18002 | Order :18003 | Notification :18005
     ↓
PostgreSQL 16 + PostGIS | Redis Streams + cache | MinIO
```

### 3.2 Module status

| Module | Schema | Sprint | Status | Key events |
|--------|--------|--------|--------|------------|
| Gateway | — | S1 | ✅ | — |
| Identity | `ckac_identity` | S1 | ✅ | `kitchen.created` |
| Catalog | `ckac_catalog` | S2 | ✅ | `dish.created`, `dish.updated` |
| Order | `ckac_orders` | S3 | ✅ | `order.placed`, `order.status.changed` |
| Notification | ckac_support | S4 | ✅ | `whatsapp.message.received`, `support.ticket.*` |
| Billing | `ckac_billing` | S6 | ⏳ | `payment.captured` |
| Analytics | mat. views | S6+ | ⏳ | consumes `order.*` |
| Marketing | `ckac_marketing` | P2 | ⏳ | CRM, coupons |
| Rating | `ckac_ratings` | P2 | ⏳ | home taste, A/V |
| Delivery | geo rules | P2 | ⏳ | fee quotes |
| Growth | `ckac_growth` | P2–3 | ⏳ | F11 suggestions |
| Learning / Stream | `ckac_learning` | P3 | ⏳ | F21–F24, F46–F48 |

### 3.3 Service responsibilities (summary)

- **Identity:** registration, OTP, JWT, kitchen onboarding, kitchen codes
- **Catalog:** categories, dishes, live-capture media, public menu + Redis cache
- **Order:** manual orders, parser, drafts, lifecycle, history, order codes
- **Notification:** WhatsApp webhook, kitchen lookup, forward to order internal API

See [CKAC-ARCHITECTURE-CTO.md](./CKAC-ARCHITECTURE-CTO.md) for engineering layer detail.

---

## 4. 48-Feature Catalog

**Legend:** ✅ Done · 🟡 Partial · ⏳ Not started

### Phase 1 — Owner can run kitchen

| ID | Feature | Status |
|----|---------|--------|
| F01 | WhatsApp order capture | 🟡 |
| F02 | Message parser | ✅ |
| F03 | Manual order input | ✅ |
| F04 | Order lifecycle | ✅ |
| F05 | Order history | ✅ |
| F07 | Revenue report | ⏳ S6 |
| F13 | Dish + live photo | ✅ |
| F14 | Price, ingredients, quality | ✅ |
| F15 | Categories | ✅ |
| F26 | Owner subscription | 🟡 |
| F30 | Per-dish prep time | ✅ |
| F42–F43 | Online pay + UPI | ⏳ S6 |
| F45 | App + WhatsApp notify | 🟡 |

**Counts:** 8 done · 4 partial · 4 Phase 1 remaining · 48 total spec

### Phase 2 — Growth (Months 4–6)

F06, F08–F12, F16–F18, F25, F27–F33, F34–F40, F41, F44

### Phase 3 — Differentiation (Months 7–10)

F12, F19–F24, F46–F48

Full acceptance criteria: [CKAC-COMPLETE-PLANNING-BENCHMARK.md](./CKAC-COMPLETE-PLANNING-BENCHMARK.md)

---

## 5. Application & Data Flows

### 5.1 WhatsApp order intake

```
Meta webhook → notification (kitchen lookup)
  → whatsapp.message.received (outbox + Redis)
  → order /internal/.../from-whatsapp
  → parse → draft → owner confirm → order.placed
```

### 5.2 Order lifecycle

```
received → accepted → preparing → ready → out_for_delivery → delivered
Any pre-delivered → cancelled (reason required)
Each step: order_status_events + order.status.changed
```

### 5.3 Event catalog

| Event | Producer | Stream |
|-------|----------|--------|
| `kitchen.created` | identity | `ckac:identity:kitchen` |
| `dish.created` / `dish.updated` | catalog | `ckac:catalog:dish` |
| `order.placed` | order | `ckac:orders:order` |
| `order.status.changed` | order | `ckac:orders:order` |
| `order.draft.created` | order | `ckac:orders:draft` |
| `whatsapp.message.received` | notification | `ckac:notify:whatsapp` |

---

## 6. Technical Reference

### 6.1 Database (live schemas)

| Schema | Tables |
|--------|--------|
| `ckac_identity` | owners, kitchens |
| `ckac_catalog` | categories, dishes, dish_media |
| `ckac_orders` | orders, order_items, order_status_events, order_drafts |
| `ckac_events` | outbox, processed_events |

### 6.2 API reference (gateway `:18000/api/v1`)

See [Implementation Guide §7](./CKAC-IMPLEMENTATION-GUIDE.md#7-api-reference) for full endpoint list.

### 6.3 Dev ports

| Service | Port |
|---------|------|
| Gateway | 18000 |
| Identity | 18001 |
| Catalog | 18002 |
| Order | 18003 |
| Notification | 18005 |
| PostgreSQL | 15432 |
| Redis | 16379 |

---

## 7. Business, Delivery & Metrics

### 7.1 Subscription tiers

| Tier | Price/mo | Includes |
|------|----------|----------|
| Starter | Rs 499 | WhatsApp, menu, basic reports |
| Pro | Rs 1,499 | CRM, marketing, tiffin, analytics |
| Enterprise | Rs 3,999 | Live stream, API, multi-branch |

Zero food commission. Razorpay Route for multi-kitchen split (Phase 2).

### 7.2 Build status (July 2026)

| Sprint | Deliverable | Status |
|--------|-------------|--------|
| S1–S4 | Identity, Catalog, Order, Notification + gateway | ✅ Complete |
| S5 | PWAs + portal + owner analytics + support/tickets | 🟡 Partial |
| S6 | Billing + revenue | ⏳ Planned |

**90+ automated tests passing** across all services.

### 7.3 CPO KPIs

| Metric | Phase 1 target |
|--------|------------------|
| Time to first order | < 5 min post-signup |
| WhatsApp parse rate | 95% |
| Hero live-capture rate | 100% |
| Owner retention M6 | 80% |
| Repeat customer rate | 40%+ |

---

## Regenerate PDF

```bash
python scripts/generate_product_depth_pdf.py
```

Output: `docs/CKAC-PRODUCT-DEPTH-GUIDE.pdf`

Also available: `python scripts/generate_pitch_pdf.py` → `docs/CKAC-PITCH-DECK.pdf` (33-slide CPO deck)
