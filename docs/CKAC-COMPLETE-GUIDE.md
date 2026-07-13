# Kitchcu — Complete Executive Guide

**Growth Operating System for cloud kitchens & home food businesses**

| Field | Value |
|-------|-------|
| Version | **2.0** |
| Status | Phase 1 complete through **S18** (backend + PWAs); GST live; E1/E2 design pack ready |
| Audience | **CEO, CPO, CTO**, Product, Engineering, Investors |
| Last updated | July 2026 |
| PDF | [`CKAC-COMPLETE-GUIDE.pdf`](./CKAC-COMPLETE-GUIDE.pdf) |
| Design packs | [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) · feature packs in `docs/` |
| Living code map | [`CKAC-IMPLEMENTATION-GUIDE.md`](./CKAC-IMPLEMENTATION-GUIDE.md) |

> **Purpose:** Single CPO-led product encyclopedia + CTO architecture bible. Every platform module is defined with the **challenge it solves**, **capabilities**, **surfaces**, and **build status**. Diagrams cover system architecture, core flows, and schema-level ER.

---

## Table of Contents

### Part I — CEO Lens
1. Executive Summary & Current State  
2. Market Positioning & Business Model  
3. Go-to-Market Phases & Risks  

### Part II — CPO Lens
4. Product Vision, Personas & Principles  
5. Challenges → Module Solutions  
6. **Module Catalog (full definitions)**  
7. Product Journeys & Capability Map  
8. Product KPIs  

### Part III — CTO Lens
9. System Architecture Diagram  
10. Event & Data Flow Diagrams  
11. ER / Schema Diagram  
12. Services, APIs, Security & Standards  
13. Build Status Matrix  

### Appendices
A. Feature Implementation Matrix (F01–F48)  
B. Document Index  

---

# Part I — CEO Lens

## 1. Executive Summary & Current State

**Kitchcu** is a **B2B2C cloud kitchen operating system** — not a food aggregator and not a restaurant POS. Owners run orders, menu, quality, CRM, payments, GST, and growth from one PWA. Customers get live-capture honesty, distance-aware delivery, home-taste ratings, and multi-kitchen checkout — **without** giving away customer ownership or paying per-order commission.

| Stakeholder | Challenge | Kitchcu answer |
|-------------|-----------|----------------|
| Owner / chef | WhatsApp chaos, aggregator tax, no quality OS | Unified hub · subscription SaaS · ratings + standards |
| Customer | Fake photos, opaque fees, one-kitchen carts | Live media · fee quotes · multi-kitchen master order |
| Platform | Need capital-efficient SaaS | PWA-first · event-driven microservices · zero food commission |

### CEO guiding principle

> Keep day-one simple: accept an order and see revenue in minutes. Growth, streaming, and community layers unlock after traction.

### Platform snapshot (July 2026)

| Metric | Value |
|--------|-------|
| Sprints shipped | **S1–S18** (identity → live streaming) |
| Microservices | Gateway + **13** domain services |
| Domains | Portal · customer.kitchcu.in · kitchen.kitchcu.in · admin.kitchcu.in |
| Billing / GST | Payments, subscriptions, **GST profiles, tax invoices, monthly audit, balance sheet** |
| Next design | **E1 + E2 Kitchen Quality Loop** (purchase inventory + chef standard lock) — design approved pending build |

---

## 2. Market Positioning & Business Model

```
Aggregators (marketplace)          Kitchcu (operating system)
─────────────────────────          ─────────────────────────
Per-order commission 18–30%        Flat subscription
Platform owns the customer         Owner owns CRM + data
Stock / studio photos              Live-capture dish media
Speed race delivery timers         Owner-set quality SLA
Single kitchen cart                Multi-kitchen master checkout
No GST / quality OS for owner      GST, ingredients, standards
```

**Revenue:** Owner Starter / Growth / Pro subscriptions; optional live-prep premium later.  
**Non-negotiable:** **Zero per-order food commission.**

| Tier (dev defaults) | Monthly | Role |
|---------------------|---------|------|
| Starter | ₹499 | Operations + basic reports |
| Growth | ₹999 | CRM, coupons, deeper insights |
| Pro | ₹1,999 | Multi-kitchen, priority support |

Targets: CAC &lt; ₹2,000 · LTV &gt; ₹18,000 · LTV:CAC &gt; 3:1 · gross margin &gt; 75%.

---

## 3. Go-to-Market Phases & Risks

| Phase | Goal | Status |
|-------|------|--------|
| **1 Foundation** | Owner can run kitchen end-to-end | ✅ S1–S18 core shipped |
| **2 Growth polish** | Offline PWA, deeper CRM automation | Continuous |
| **3 Quality loop** | Purchase inventory + locked chef standards (E1/E2) | Design pack ready |
| **4 Scale** | National rankings, forecasting, white-label | Future |

| Risk | Mitigation |
|------|------------|
| WhatsApp API change | Manual + PWA intake always available |
| Scope creep | MoSCoW + design pack gate before code |
| Rating fraud | Verified purchase only |
| Multi-kitchen refunds | Sub-orders + Route settlements |
| Onboarding friction | 5-minute kitchen create → first dish → first order |

---

# Part II — CPO Lens

## 4. Product Vision, Personas & Principles

**Vision:** Every cloud kitchen scales like a brand — with data, taste standards, and direct customers — while diners see honest, real-time food truth.

| Persona | Promise | Primary surface |
|---------|---------|-----------------|
| **Owner / Chef** | WhatsApp → revenue same day | kitchen.kitchcu.in |
| **Customer** | Trust + fair delivery + rate home taste | customer.kitchcu.in |
| **Platform admin** | Support, kitchens, attention queue | admin.kitchcu.in |
| **Guest / market** | Discover brand story | portal (kitchcu.in) |

**Principles:** Quality over speed · Truth in media · Owner owns CRM · Progressive complexity · Growth OS, not POS.

---

## 5. Challenges → Module Solutions

### Owner challenges

| ID | Challenge | Modules that solve it |
|----|-----------|------------------------|
| P1 | Orders trapped in WhatsApp / calls | Order · Notification |
| P2 | Aggregator commission destroys margin | Billing (subscription) |
| P3 | No daily revenue / segment visibility | Order analytics · Growth · Reports UI |
| P4 | Stock photos erode trust | Catalog live-capture |
| P5 | Taste drifts batch to batch | Catalog recipes · Ratings · Growth (E2 planned) |
| P6 | Customer data owned by platforms | Marketing CRM · Coupons |
| P7 | Promotions are guesswork | Growth suggestions · Daily menu push |
| P8 | Multi-channel lifecycle chaos | Order status machine |
| P9 | Stock unknown until mid-service | Ingredients (F19) · Purchases (E1 planned) |
| P10 | GST / monthly audit pain | Billing GST |
| P11 | Skills & trial dishes hard to manage | Learning · Community |
| P12 | Trust & engagement without ads | Streaming live opt-in |

### Customer challenges

| ID | Challenge | Modules |
|----|-----------|---------|
| C1 | Cannot trust menu photos | Catalog |
| C2 | Opaque delivery fees | Delivery |
| C3 | Weak tracking | Order · Notification · Delivery links |
| C4 | Generic star ratings | Ratings (home taste) |
| C5 | One kitchen per cart | Order master checkout · Billing Route |
| C6 | Hard to re-find local kitchens | Identity discovery (nearby) |

---

## 6. Module Catalog — Definitions, Descriptions, Challenges

Each module below is a **bounded product + engineering context**. Status reflects production readiness in the monorepo as of July 2026.

---

### M01 — API Gateway
| | |
|--|--|
| **Definition** | Public edge router for all `/api/v1/*` traffic. |
| **Description** | Path-based proxy to domain services; correlation IDs; health aggregation; no business logic. |
| **Challenges solved** | Clients never call internal services; CORS/auth surface unified; blast radius contained. |
| **Key surfaces** | `services/gateway/` · port 18000 |
| **Status** | ✅ Live |

---

### M02 — Identity & Kitchen Profile
| | |
|--|--|
| **Definition** | Auth and tenant roots for owners, customers, kitchens, admins. |
| **Description** | OTP + JWT for owners; social OAuth + WhatsApp OTP for customers; PostGIS kitchen location; codes like `CKPNQ001`. |
| **Challenges solved** | P1 bootstrap; C6 nearby discovery; multi-kitchen ownership. |
| **Schema** | `ckac_identity` |
| **Status** | ✅ S1 · nearby F32 ✅ |

---

### M03 — Catalog & Live Media
| | |
|--|--|
| **Definition** | Menu of truth — categories, dishes, prices, live-capture hero media. |
| **Description** | Enforces `is_live_capture` on hero images; public/owner menus; Redis menu cache with invalidate-on-write. |
| **Challenges solved** | P4 / C1 photo deception; menu consistency across PWAs. |
| **Schema** | `ckac_catalog` |
| **Status** | ✅ S2 |

---

### M04 — Ingredients & Recipes (F19)
| | |
|--|--|
| **Definition** | Pantry stock + per-dish recipe standards + prep steps. |
| **Description** | Ingredients with thresholds; recipe lines; deduct on **order accept**; low-stock warnings before accept. |
| **Challenges solved** | P9 mid-service stock outs; foundation for taste standards (P5). |
| **Schema** | `ckac_catalog` (`ingredients`, `dish_ingredients`, `dish_prep_steps`) |
| **Status** | ✅ S15 · **E1 purchases design next** |

---

### M05 — Order Operations
| | |
|--|--|
| **Definition** | Order intake, lifecycle, PDF bills, owner analytics. |
| **Description** | Manual / WhatsApp / customer PWA; status machine `received→…→delivered`; bill PDF; revenue / peak / segments. |
| **Challenges solved** | P1, P3, P8, C3; operational single source of truth. |
| **Schema** | `ckac_orders` |
| **Status** | ✅ S3 + analytics + PDF bills |

---

### M06 — Multi-Kitchen Checkout (F06)
| | |
|--|--|
| **Definition** | Cart spanning many kitchens with one customer payment. |
| **Description** | Master order + atomic sub-orders; master receipt PDF; settlement splits via billing. |
| **Challenges solved** | C5 aggregator-style cart limitation **without** taking commission. |
| **Status** | ✅ S8 |

---

### M07 — Billing, Payments & Split Settlement
| | |
|--|--|
| **Definition** | Money movement — order payments, UPI intents, subscriptions, Route settlements. |
| **Description** | Online/UPI capture; COD excluded from online capture; F44 master payment → per-kitchen settlements. |
| **Challenges solved** | P2 subscription model; multi-kitchen payout fairness. |
| **Schema** | `ckac_billing` |
| **Status** | ✅ S6 · S9 |

---

### M08 — GST Finance
| | |
|--|--|
| **Definition** | GST registration profile, tax invoices, monthly audit, balance sheet. |
| **Description** | Owners with GSTIN sync invoices from delivered orders (tax-inclusive food rate); close month with snapshot. |
| **Challenges solved** | P10 compliance / accountant handoff for home/cloud kitchens. |
| **Surfaces** | kitchen PWA **GST & finance** · billing APIs |
| **Status** | ✅ Live (billing `003_gst`) |

---

### M09 — Notification & Support
| | |
|--|--|
| **Definition** | WhatsApp ingress/egress, order updates, tracking reminders, AI support + tickets. |
| **Description** | Webhook intake; F45 status WhatsApp; F29 interval reminders; admin ticket queue. |
| **Challenges solved** | P1 intake; C3 tracking communication; ops support. |
| **Schema** | `ckac_support` (+ notify streams) |
| **Status** | ✅ S4 · S14 |

---

### M10 — Marketing, CRM & Coupons
| | |
|--|--|
| **Definition** | Owner-owned customer relationship layer. |
| **Description** | Kitchen customer spend/history; coupons; targeted promotions. |
| **Challenges solved** | P6 / P7 customer ownership & promo ROI. |
| **Schema** | `ckac_marketing` |
| **Status** | ✅ S10 |

---

### M11 — Ratings & Customer Tips
| | |
|--|--|
| **Definition** | Verified home-taste / quality ratings + optional A/V + dish suggestions. |
| **Description** | Delivered-order only; aggregate overall = 0.6 taste + 0.4 quality; F20 tips for owners. |
| **Challenges solved** | C4 trust; P5 quality signal for E2 chef briefs. |
| **Schema** | `ckac_ratings` |
| **Status** | ✅ S11 |

---

### M12 — Growth Intelligence
| | |
|--|--|
| **Definition** | Actionable suggestions from patterns — not vanity dashboards. |
| **Description** | Combos (F09), order patterns (F10), grow suggestions (F11), daily menu WhatsApp (F39). |
| **Challenges solved** | P3 / P7 guesswork marketing. |
| **Schema** | `ckac_growth` |
| **Status** | ✅ S12 · **E2 chef brief design next** |

---

### M13 — Delivery Radius, Fees & Tracking
| | |
|--|--|
| **Definition** | Distance-aware quotes and shareable tracking. |
| **Description** | PostGIS distance; free/max radius; fee quotes; tracking tokens/links. |
| **Challenges solved** | C2 fee opacity; C3 journey visibility. |
| **Schema** | `ckac_delivery` |
| **Status** | ✅ S13 |

---

### M14 — Learning Portal & Dish Trials
| | |
|--|--|
| **Definition** | Skill-building content and controlled dish experiments. |
| **Description** | Curated learning; trials with promote-to-menu path. |
| **Challenges solved** | P11 capability gap for home chefs scaling up. |
| **Schema** | `ckac_learning` |
| **Status** | ✅ S16 |

---

### M15 — Community & Chef Rankings
| | |
|--|--|
| **Definition** | Recipe sharing rewards and chef league tables. |
| **Description** | Publish recipes for rewards; rankings from quality/activity signals. |
| **Challenges solved** | Differentiation vs aggregators; motivation loop. |
| **Schema** | `ckac_community` |
| **Status** | ✅ S17 |

---

### M16 — Live Streaming
| | |
|--|--|
| **Definition** | Owner opt-in live kitchen sessions for customer trust. |
| **Description** | LiveKit sessions; go-live controls; customer live filter. |
| **Challenges solved** | P12 trust without ad spend; C1 authenticity multiplier. |
| **Schema** | `ckac_streaming` |
| **Status** | ✅ S18 |

---

### M17 — Website PWAs & Portal
| | |
|--|--|
| **Definition** | Installable React surfaces for all personas. |
| **Description** | Vitest PWAs; Workbox; OwnerPageShell command-center UX; rich text recipes; maps. |
| **Challenges solved** | Distribution without app stores; WhatsApp deep links. |
| **Status** | ✅ Continuous polish |

---

### M18 — Kitchen Quality Loop (E1 + E2) — Design
| | |
|--|--|
| **Definition** | Closed loop: **purchases restock → recipes consume → ratings signal → chef locks standard**. |
| **Description** | E1 purchase ledger + auto stock-in; E2 daily chef brief from volume × home-taste × tips → lock recipe version. Catalog writes; Growth orchestrates. |
| **Challenges solved** | Completes P5 + P9 half-built by F19 alone. |
| **Doc** | [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| **Status** | 📋 Design pack — implement after approval |

---

## 7. Product Journeys & Capability Map

### Owner day-1
```
Register → OTP → JWT → Create kitchen (geo + code)
  → Add dish (live hero) → Optional GST profile
  → First manual / WhatsApp order → Accept → Deduct stock
  → Report same day
```

### Customer trust → order → rate
```
Nearby map → Menu (live photos) → Fee quote → Checkout
  → Pay (single or multi-kitchen) → Track → Delivered
  → Home-taste rating (+ tip)
```

### Capability ladder (progressive complexity)
1. Menu + Orders + Reports  
2. CRM + Coupons + Delivery quotes  
3. Ingredients + GST + Growth suggestions  
4. Learning + Community + Live stream  
5. Quality loop lock (E1/E2)

---

## 8. Product KPIs

| KPI | Near-term | 12-month |
|-----|-----------|----------|
| Active kitchens | 10 pilots | 500 |
| Platform orders / day | 50 | 5,000 |
| Owner monthly retention | 80% | 90% |
| 30-day customer repeat | 25% | 40% |
| Locked recipe standards / kitchen | — | ≥ 3 (post-E2) |
| GST audits closed on time | — | ≥ 80% registered kitchens |

---

# Part III — CTO Lens

## 9. System Architecture Diagram

```
                    ┌──────────────────────────────────────────┐
                    │  PWAs / Portal                            │
                    │  portal · customer · kitchen · admin      │
                    └──────────────────┬───────────────────────┘
                                       │ HTTPS /api/v1
                                       ▼
                    ┌──────────────────────────────────────────┐
                    │  API GATEWAY                              │
                    │  route · CORS · X-Correlation-ID · health │
                    └───┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬────┘
                        │  │  │  │  │  │  │  │  │  │  │  │
           ┌────────────┘  │  │  │  │  │  │  │  │  │  │  └────────────┐
           ▼               ▼  │  ▼  │  ▼  │  ▼  │  ▼  │               ▼
      IDENTITY         CATALOG │ ORDER │ BILLING│ GROWTH│         STREAMING
      kitchens            │  │  │  │  │  │  │  │  │  │
      customers           │  ▼  │  ▼  │  ▼  │  ▼  │  ▼
                          │ MARKET│ RATING│DELIV│ LEARN│ COMMUNITY
                          │       │       │     │      │
                          └───────┴───────┴─────┴──────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             PostgreSQL+PostGIS     Redis 7            MinIO
             schema-per-domain    Streams+cache        media
             + ckac_events.outbox
```

**Rules:** One bounded context per container · cross-service **writes via events** · cross-schema **reads only for ownership / evidence** · gateway is sole public edge.

---

## 10. Event & Data Flow Diagrams

### 10.1 Order + stock + notify (happy path)

```
Owner/Customer
      │ place / accept
      ▼
   ORDER SERVICE
      │ insert order + status_events
      │ publish order.placed / order.status.changed
      │ on accept ──HTTP internal──▶ CATALOG deduct stock
      │                              │ publish ingredient.stock.deducted
      ▼
   Redis Stream ckac:orders:order
      │
      ├─▶ NOTIFICATION (F45 WhatsApp update, tracking nudge)
      └─▶ (consumers: analytics caches invalidate)
```

### 10.2 Multi-kitchen payment (F06 / F44)

```
Customer cart [K1, K2]
      ▼
   ORDER: master_order + sub-orders
      ▼
   BILLING: create master payment → capture
      ▼
   settlements[] (net_to_owner per kitchen)
      │ publish payment.captured / settlement.*
      ▼
   Customer master bill PDF
```

### 10.3 GST monthly loop

```
Owner registers GSTIN ──▶ kitchen_gst_profiles
Delivered orders ──sync──▶ gst_tax_invoices
Monthly report + balance sheet
Owner closes audit ──▶ gst_monthly_audits (snapshot)
```

### 10.4 Quality loop (E1/E2 planned)

```
Purchase post ──▶ stock_movements (+) ──▶ pantry
Recipe deduct on accept ──▶ stock_movements (−)
Ratings + volume + F20 tips ──▶ GROWTH chef_brief
Owner Lock ──▶ recipe_standard_versions + dish_ingredients
```

### 10.5 Core Redis streams (representative)

| Stream | Examples |
|--------|----------|
| `ckac:orders:order` | placed, status.changed |
| `ckac:catalog:dish` / `ingredient` | created, updated, stock.* |
| `ckac:billing:payment` / `gst` | captured, profile, invoice, audit |
| `ckac:ratings:rating` / `dish` | created, aggregate.updated |
| `ckac:growth:suggestion` | generated, chef_standard (planned) |
| `ckac:notify:*` | whatsapp, tracking |

Transactional **outbox** in `ckac_events.outbox` with every write publish.

---

## 11. ER / Schema Diagram (logical)

Schemas are **separate Postgres schemas** (not cross-FK). Lines below are *logical* relationships.

```
ckac_identity                ckac_catalog                 ckac_orders
─────────────                ────────────                 ───────────
owners 1──* kitchens         kitchens(logical)            kitchens(logical)
customers                    categories 1──* dishes       master_orders 1──* orders
                             dishes 1──* dish_media       orders 1──* order_items
                             dishes 1──* dish_ingredients orders 1──* order_status_events
                             ingredients *──* dishes
                             dish_prep_steps

ckac_billing                 ckac_ratings                 ckac_marketing
────────────                 ────────────                 ──────────────
owner_subscriptions          dish_ratings                 kitchen_customers
payments 1──* settlements    dish_rating_aggregates       coupons
kitchen_gst_profiles         dish_suggestions             promotions
gst_tax_invoices
gst_monthly_audits

ckac_growth     ckac_delivery      ckac_learning     ckac_community     ckac_streaming
───────────     ─────────────      ─────────────     ──────────────     ──────────────
suggestions     fee_quotes*        lessons/trials    recipes/rewards    live_sessions
seasonal_*      tracking_links*    (service owned)   rankings

ckac_events
───────────
outbox · processed_events
```

\* Delivery tables may live in delivery schema / order tokens depending on sprint artifacts — see service Alembic.

**Tenant rule:** Almost every business table carries `kitchen_id` (or joins via kitchen ownership).

---

## 12. Services, APIs, Security & Standards

| Service | Port | Prefix highlights |
|---------|------|-------------------|
| gateway | 18000 | `/api/v1/*` |
| identity | 18001 | `/auth`, `/owners`, `/customers`, `/kitchens` |
| catalog | 18002 | `/kitchens/*/menu|dishes|ingredients` |
| order | 18003 | `/orders`, `/analytics`, bill `.pdf` |
| billing | 18004 | `/billing/*`, `/kitchens/*/gst/*` |
| notification | 18005 | `/webhooks`, `/support` |
| marketing | 18006 | `/crm`, `/coupons`, `/promotions` |
| ratings | 18007 | `/ratings`, `/suggestions` |
| growth | 18008 | `/growth/*` |
| delivery | 18009 | `/delivery/*` |
| learning | 18010 | `/learning/*` |
| community | 18011 | `/community/*` |
| streaming | 18012 | `/stream/*` |

**Security:** JWT Bearer · tenant filters · Pydantic validation · secrets in env · mask PII in logs · internal `X-Internal-Key` for service-to-service · health `/live` + `/ready`.

**Engineering constitution:** TDD + EDD · design pack before new modules · Alembic only · no restaurant POS features.

---

## 13. Build Status Matrix

| Module | Sprint | Status |
|--------|--------|--------|
| Gateway / Identity / Catalog / Order / Notify | S1–S4 | ✅ |
| PWAs + checkout + analytics | S5 | ✅ |
| Billing + GST | S6 + GST | ✅ |
| Discovery / history | S7 | ✅ |
| Multi-kitchen cart | S8 | ✅ |
| Split payment Route | S9 | ✅ |
| CRM / coupons / promos | S10 | ✅ |
| Ratings | S11 | ✅ |
| Growth | S12 | ✅ |
| Delivery | S13 | ✅ |
| Tracking notify | S14 | ✅ |
| Ingredients | S15 | ✅ |
| Learning | S16 | ✅ |
| Community | S17 | ✅ |
| Streaming | S18 | ✅ |
| E1 Purchases + E2 Chef lock | S19 proposed | 📋 Design |

---

# Appendix A — Feature Implementation Matrix (summary)

| Band | Features | Status |
|------|----------|--------|
| Orders & lifecycle | F01–F05, F30, F45 | ✅ / partial WhatsApp AI |
| Multi-kitchen & pay | F06, F42–F44 | ✅ |
| Analytics & growth | F07–F12, F39 | ✅ |
| Catalog & trust media | F13–F15 | ✅ |
| Ratings | F16–F18, F20 | ✅ (owner F20 UI thin) |
| Ingredients | F19 | ✅ (E1 extends) |
| Delivery / discover | F27–F33 | ✅ |
| Marketing | F34–F38, F40–F41 | ✅ core |
| Learning / community | F21–F24 | ✅ |
| Live | F46–F48 | ✅ |
| GST | (finance extension) | ✅ |
| Quality loop | E1/E2 | Design |

Full acceptance criteria: [`CKAC-COMPLETE-PLANNING-BENCHMARK.md`](./CKAC-COMPLETE-PLANNING-BENCHMARK.md).

---

# Appendix B — Document Index

| Doc | Role |
|-----|------|
| This guide + PDF | CEO/CPO/CTO master |
| `E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md` | Next sprint design pack |
| `CKAC-IMPLEMENTATION-GUIDE.md` | What’s built ↔ code |
| `KITCHCU-ENGINEERING-STANDARDS.md` | Constitution |
| `templates/MODULE-DESIGN-PACK.md` | Pre-code gate |
| Feature design packs (`F*.md`) | Per-sprint designs |
| `AGENTS.md` | Agent / engineer quick spec |

---

*Kitchcu Complete Executive Guide v2.0 — Confidential — July 2026*
