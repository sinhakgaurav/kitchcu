# Kitchcu — CPO Product Blueprint

**Kitchcu cloud kitchen platform**

| Field | Value |
|-------|-------|
| Version | 3.0 — CPO Product Edition |
| Audience | CPO, CEO, Product, Engineering, Investors |
| Companion | [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) · [`CKAC-IMPLEMENTATION-GUIDE.md`](./CKAC-IMPLEMENTATION-GUIDE.md) · [`CKAC-COMPLETE-PLANNING-BENCHMARK.md`](./CKAC-COMPLETE-PLANNING-BENCHMARK.md) · [`CKAC-PITCH-DECK.pdf`](./CKAC-PITCH-DECK.pdf) |
| Last updated | July 2026 |

---

## 1. Product North Star

**Mission:** Give every cloud kitchen owner the operating system to run, grow, and trust their business — while giving customers honest visibility into what they eat.

| Stakeholder | One-line promise |
|-------------|------------------|
| Owner | WhatsApp order → revenue report same day |
| Customer | Live photos, home-taste ratings, fair delivery |
| Platform | Subscription SaaS — zero food commission |

---

## 2. Current Market Pain Points → Kitchcu Solutions

### 2.1 Owner Pain Points

| # | Pain Point | Impact | Kitchcu Module | Solution |
|---|------------|--------|-------------|----------|
| P1 | 70%+ orders on WhatsApp — no structure | Lost orders, no analytics | Order + Notification | Unified inbox, parser, manual fallback |
| P2 | Aggregator 18–30% commission | Margin erosion | Billing (subscription) | Flat monthly fee; kitchen keeps food revenue |
| P3 | No daily profit visibility | Cash flow guesswork | Analytics | Revenue, dish, pattern reports (Phase 1–2) |
| P4 | Stock photos mislead customers | Refunds, bad reviews | Catalog + Media | Live-capture hero images enforced |
| P5 | Batch-to-batch taste inconsistency | Repeat loss | Catalog + Ingredient (P3) | Per-dish standards, ingredient mapper |
| P6 | Customer data owned by aggregators | No CRM, no coupons | Marketing | Owner CRM, coupons, tiffin plans |
| P7 | Promotions are guesswork | Wasted discounts | Growth Engine | Seasonal, win-back, combo suggestions |
| P8 | Multi-channel chaos (call, walk-in, chat) | Double-booking | Order Service | Single lifecycle for all sources |

### 2.2 Customer Pain Points

| # | Pain Point | Kitchcu Solution |
|---|------------|---------------|
| C1 | Cannot trust menu photos | Live-capture dish media with timestamp |
| C2 | Opaque delivery fees | PostGIS distance + owner rules shown at checkout |
| C3 | No real order tracking | Lifecycle + WhatsApp + push on every transition |
| C4 | Star ratings feel generic | Home-taste benchmark (1–5) + optional A/V review |
| C5 | One kitchen per cart on aggregators | Multi-kitchen cart + single payment (Phase 2) |
| C6 | Cannot subscribe to home tiffin | Kitchen-defined meal plans (Phase 2) |

---

## 3. Platform Modules (Bounded Contexts)

### 3.1 Module Map

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
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Marketing  │  │   Rating    │  │  Delivery   │
│  Phase 2    │  │  Phase 2    │  │  Phase 2    │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 3.2 Module Detail

| Module | Responsibility | Key Features | DB Schema | Status |
|--------|----------------|--------------|-----------|--------|
| **Gateway** | Auth routing, rate limit | Path-based proxy to services | — | ✅ v0.3 |
| **Identity** | Owners, kitchens, OTP, JWT | F26 onboarding, kitchen codes | `ckac_identity` | ✅ Sprint 1 |
| **Catalog** | Menu, categories, media | F13–F15, live-capture rule | `ckac_catalog` | ✅ Sprint 2 |
| **Order** | Intake, lifecycle, history | F03–F05, F30 | `ckac_orders` | ✅ Sprint 3 |
| **Notification** | WhatsApp, push, SMS | F01–F02, F45 | — | ⏳ Sprint 4 |
| **Billing** | Subscriptions, payments | F26, F42–F44 | `ckac_billing` | ⏳ Sprint 6 |
| **Analytics** | Reports, patterns | F07–F12 | materialized views | ⏳ Sprint 6+ |
| **Marketing** | CRM, coupons, tiffin | F34–F40 | `ckac_marketing` | Phase 2 |
| **Rating** | Home taste, A/V | F16–F18 | `ckac_ratings` | Phase 2 |
| **Delivery** | Radius, fees, tracking | F27–F31 | geo rules | Phase 2 |
| **Growth** | AI-ready suggestions | F11 | `ckac_growth` | Phase 2–3 |
| **Learning** | Recipes, trials | F21–F23 | `ckac_learning` | Phase 3 |
| **Streaming** | Live prep | F46–F48 | session metadata | Phase 3 |

---

## 4. Application Flows

### 4.1 Owner — Day 1 Onboarding

```
Register (phone) → OTP verify → JWT
    → Create kitchen (name, geo, code CKPNQ001)
    → Add dishes (live photo required for hero)
    → Connect WhatsApp (Sprint 4)
    → First order in inbox (< 5 min target)
```

### 4.2 Order Intake Flow (All Sources)

```
Source: WhatsApp | Manual | Customer PWA
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

### 4.3 Order Lifecycle (F04)

```
received → accepted → preparing → ready → out_for_delivery → delivered
   │          │           │          │            │
   └──────────┴───────────┴──────────┴────────────┴──→ cancelled (reason required)

Each transition:
  • Persisted in order_status_events
  • Publishes order.status.changed
  • Triggers WhatsApp + push (Sprint 4+)
```

### 4.4 Customer Order Flow (Phase 2)

```
Discover (map) → Kitchen profile → Add to cart
    → Multi-kitchen checkout → Delivery fee quote
    → Pay UPI/COD → Track lifecycle → Rate home taste
    → Repeat order (2 taps)
```

### 4.5 Multi-Kitchen Checkout (F06 — Phase 2)

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

---

## 5. Data Flow Architecture

### 5.1 Request Path

```
PWA / WhatsApp → API Gateway (:18000)
    → Identity | Catalog | Order service
    → PostgreSQL (schema-per-domain)
    → Redis (cache + event streams)
    → MinIO (media)
```

### 5.2 Event-Driven Data Flow (EDD)

| Event | Producer | Stream | Consumers (future) |
|-------|----------|--------|---------------------|
| `kitchen.created` | identity | `ckac:identity:kitchen` | analytics |
| `dish.created` | catalog | `ckac:catalog:dish` | search, cache invalidation |
| `dish.updated` | catalog | `ckac:catalog:dish` | menu cache |
| `order.placed` | order | `ckac:orders:order` | notification, analytics, billing |
| `order.status.changed` | order | `ckac:orders:order` | notification, customer tracking |
| `payment.captured` | billing | `ckac:billing:payment` | settlement, reports |

**Contract:** DB commit first → publish `EventEnvelope` → outbox for reliability (Sprint 4+).

### 5.3 Database Schema Roadmap

| Schema | Tables | Phase |
|--------|--------|-------|
| `ckac_identity` | owners, kitchens | 1 ✅ |
| `ckac_catalog` | categories, dishes, dish_media | 1 ✅ |
| `ckac_orders` | orders, order_items, order_status_events | 1 ✅ |
| `ckac_events` | outbox, processed_events | 1 ✅ |
| `ckac_billing` | payments, subscriptions | 1 |
| `ckac_marketing` | customers, coupons, plans | 2 |
| `ckac_ratings` | dish_ratings, suggestions | 2 |
| `ckac_growth` | suggestions, patterns | 2–3 |

---

## 6. Feature Catalog (48 Features)

### Phase 1 — Owner Can Run Kitchen (Months 1–3)

| ID | Feature | Module | Sprint |
|----|---------|--------|--------|
| F01 | WhatsApp order capture | notification + order | S4 |
| F02 | Normal message parser | notification | S4 |
| F03 | Manual order input | order | S3 ✅ |
| F04 | Order lifecycle | order | S3 ✅ |
| F05 | Order history | order | S3 ✅ |
| F07 | Revenue report | analytics | S6 |
| F13 | Dish + live photo | catalog | S2 ✅ |
| F14 | Price, ingredients, quality | catalog | S2 ✅ |
| F15 | Categories | catalog | S2 ✅ |
| F26 | Owner subscription | billing | S6 |
| F30 | Per-dish prep time | order + catalog | S3 ✅ |
| F42 | Online pay + COD | billing | S6 |
| F43 | UPI scanner | billing | S6 |
| F45 | App + WhatsApp notify | notification | S4 |

### Phase 2 — Growth (Months 4–6)

F06, F08–F11, F16–F18, F25, F27–F33, F34–F40, F41, F44

### Phase 3 — Differentiation (Months 7–10)

F12, F19–F24, F46–F48

---

## 7. Current Build Status (July 2026)

| Sprint | Deliverable | Tests |
|--------|-------------|-------|
| S1 ✅ | Identity, gateway, Docker, JWT | 25 |
| S2 ✅ | Catalog, live-capture, EDD | 10 |
| S3 ✅ | Order manual, lifecycle, history | 16 |
| S4 ✅ | WhatsApp webhook + parser + AI support chat | +8 notification |
| S5 🟡 | PWAs (portal, customer, kitchen, admin) + owner analytics + ticketing | Frontend + order analytics |
| S6 ⏳ | Billing + revenue reports | — |

**Total automated tests:** 90+ passing

---

## 8. Success Metrics (CPO KPIs)

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

## 9. Product Principles (Non-Negotiable)

1. **Truth in media** — hero dish photos must be live-capture
2. **Quality over speed** — owner-set prep times, no fake ETAs
3. **Owner sovereignty** — CRM and customer data belong to kitchen
4. **Progressive complexity** — hide advanced features until 50+ orders
5. **WhatsApp-native** — meet owners where they already work

---

## 10. Regenerate PDF

```bash
python scripts/generate_pitch_pdf.py
```

Output: `docs/CKAC-PITCH-DECK.pdf`
