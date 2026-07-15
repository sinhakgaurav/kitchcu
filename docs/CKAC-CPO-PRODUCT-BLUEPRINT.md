# Kitchcu — CPO Product Blueprint

**Growth Operating System for cloud kitchens & home food businesses**

| Field | Value |
|-------|-------|
| Version | **4.2** — Module encyclopedia + UI surfaces + positioning + OpenAPI/userflows links |
| Audience | CPO, CEO, Product, Engineering, Investors |
| Master guide | [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) **v3.2** · [`CKAC-COMPLETE-GUIDE.pdf`](./CKAC-COMPLETE-GUIDE.pdf) |
| Pitch PDF | [`CKAC-PITCH-DECK.pdf`](./CKAC-PITCH-DECK.pdf) (v4.2 landscape slides) |
| Full user journeys | [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) · [`CKAC-USERFLOWS.pdf`](./CKAC-USERFLOWS.pdf) |
| Public API reference | [`API.md`](./API.md) · aggregated spec at gateway `/openapi.json` / `/docs` / `/redoc` · portal `/openapi` |
| UI reference shots | [`docs/assets/ui/`](./assets/ui/) |
| Quality loop design | [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| Last updated | July 2026 |

> This blueprint is the **CPO lens extract**. Full CEO/CTO depth — definitions, architecture *why*, 100k-session scale lens, TDD+EDD rationale, Mermaid flows, per-schema ER, and UI anatomy (incl. login highlights, super-admin Control, delivery payer) — lives in the **Complete Executive Guide v3.2**. For the exhaustive step-by-step journey pack (every persona, every screen, every API call), see [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md).

**Positioning claim (product copy):** *India's first — and the world's third — platform with this feature stack* (`APP_POSITIONING` in `apps/website/src/shared/brand.ts`).

---

## 1. Product North Star

**Mission:** Give every cloud kitchen the operating system to run, grow, and standardize quality — while customers get honest visibility into food.

| Stakeholder | Promise |
|-------------|---------|
| Owner | WhatsApp order → revenue report same day |
| Customer | Live photos, home-taste ratings, fair delivery |
| Platform | Subscription SaaS — **zero food commission** |

**Principles:** Quality over speed · Truth in media · Owner owns CRM · Progressive complexity · Not a restaurant POS.

**Gate for every feature:** *Does this help a cloud kitchen grow, without dependence on an aggregator?* If no → reject.

---

## 2. Challenges solved (CPO framing)

### Owner

| ID | Challenge | Module answer |
|----|-----------|---------------|
| P1 | WhatsApp / call order chaos | Order + Notification |
| P2 | Aggregator commissions | Billing subscription |
| P3 | No daily profit / segment clarity | Analytics + Growth + Reports |
| P4 | Stock photo distrust | Catalog live-capture |
| P5 | Taste inconsistency | Recipes + Ratings (+ E2 lock) |
| P6 | Lost customer ownership | Marketing CRM |
| P7 | Promo guesswork | Growth suggestions + daily menu |
| P8 | Multi-channel lifecycle chaos | Order status machine |
| P9 | Unknown pantry mid-service | Ingredients (+ E1 purchases) |
| P10 | GST / monthly audit | Billing GST |
| P11 | Skills & trial management | Learning + Community |
| P12 | Trust without ads | Live streaming |

### Customer

| ID | Challenge | Module answer |
|----|-----------|---------------|
| C1 | Untrustworthy photos | Catalog |
| C2 | Opaque fees | Delivery quotes |
| C3 | Weak tracking | Order + Notify + tracking links |
| C4 | Generic ratings | Home-taste ratings |
| C5 | One kitchen per cart | Master checkout + split settlement |
| C6 | Hard to rediscover locals | Nearby discovery |

---

## 3. Module encyclopedia (definitions)

Each module below is a **bounded product context**. For *Definition · Description · Logic/how · Challenge solved · Events · UI surface*, see Complete Guide **§6**.

| Module | Definition (one line) | Status |
|--------|----------------------|--------|
| **Gateway** | Public API edge; never embeds domain logic | ✅ |
| **Identity** | Owners, customers, kitchens, JWT/OTP, PostGIS | ✅ |
| **Catalog** | Menu + live-capture media of truth | ✅ |
| **Ingredients** | Pantry stock + recipes; deduct on accept | ✅ |
| **Order** | Intake, lifecycle, PDF bills, owner analytics | ✅ |
| **Multi-kitchen checkout** | One payment → many kitchen sub-orders | ✅ |
| **Billing** | Payments, UPI, subscriptions, Route splits | ✅ |
| **GST Finance** | GSTIN, tax invoices, monthly audit, balance sheet | ✅ |
| **Notification** | WhatsApp, tracking nudges, support tickets | ✅ |
| **Marketing** | Owner CRM, coupons, targeted promos | ✅ |
| **Ratings** | Verified home-taste + tips | ✅ |
| **Growth** | Combos, patterns, action suggestions | ✅ |
| **Delivery** | Distance fees + tracking | ✅ |
| **Learning** | Curated portal + dish trials | ✅ |
| **Community** | Recipe rewards + chef rankings | ✅ |
| **Streaming** | Owner opt-in LiveKit kitchen sessions | ✅ |
| **PWAs** | Portal / customer / kitchen / admin surfaces | ✅ |
| **Quality Loop E1+E2** | Purchases + lock winning ingredient standards | 📋 Design |

---

## 4. Core journeys

```
Owner day-1:
  Register → OTP → Kitchen → Live dish → Order → Accept → Report

Customer:
  Nearby → Live menu → Fee quote → Checkout → Track → Rate home taste

Progressive unlock:
  Ops → CRM → Ingredients/GST/Growth → Learning/Community/Live → Quality loop
```

Step-by-step with APIs, events, and Mermaid: Complete Guide **Part IV (§17)**. Every screen, edge case, and API call for each journey: [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) / [`.pdf`](./CKAC-USERFLOWS.pdf).

---

## 5. Surfaces & UI catalog

| Domain | Audience | Job | Theme |
|--------|----------|-----|-------|
| kitchcu.in (portal) | Market | Brand, education, signup | Light cream/teal/orange |
| customer.kitchcu.in | Diner | Discover, order, track, rate | Light (appetite/trust) |
| kitchen.kitchcu.in | Owner | Run & grow the kitchen | Dark ops |
| admin.kitchcu.in | Ops | Support, kitchens, attention | Dark ops (platform scope) |

**Reference screenshots** (anatomy + UX intent + brand cues):

| Shot | File |
|------|------|
| Portal home | [`assets/ui/01-portal-home.png`](./assets/ui/01-portal-home.png) |
| Customer home | [`assets/ui/02-customer-home.png`](./assets/ui/02-customer-home.png) |
| Kitchen login | [`assets/ui/03-kitchen-login.png`](./assets/ui/03-kitchen-login.png) |
| Owner dashboard | [`assets/ui/04-owner-dashboard.png`](./assets/ui/04-owner-dashboard.png) |
| Admin overview | [`assets/ui/05-admin-overview.png`](./assets/ui/05-admin-overview.png) |

Full write-up: Complete Guide **§18**. Why two themes: **§19**.

---

## 6. KPIs

| KPI | Near-term | 12-month |
|-----|-----------|----------|
| Active kitchens | 10 | 500 |
| Orders/day | 50 | 5,000 |
| Owner retention | 80% | 90% |
| 30d repeat | 25% | 40% |
| Locked standards/kitchen | — | ≥ 3 (post-E2) |

---

## 7. How & why (product logic pointers)

| Question | Where answered |
|----------|----------------|
| Why subscription not commission? | Complete Guide §2 (business model) |
| Why microservices + schema-per-domain? | Complete Guide §9 |
| Why outbox + Redis Streams? | Complete Guide §9 + §11 (EDD) |
| Why live-capture only? | Principles §4 + Catalog module §6 |
| Why dark ops vs light marketing? | Complete Guide §19 |
| Why one unified form-spacing system? | Complete Guide §19.5 |
| Why aggregate OpenAPI at the gateway? | Complete Guide §15.5 · [`API.md`](./API.md) |
| Why E1 purchases before E2 lock? | E1–E2 design pack |

---

## 8. CTO pointer

For architecture, event flows, and ER diagrams see:

- Complete Guide **Part III** (markdown + PDF v3.2)
- `CKAC-ARCHITECTURE-CTO.md`
- `CKAC-SYSTEM-BENCHMARK.md`
- Live API contract: gateway `/docs` (aggregated) · [`API.md`](./API.md)

---

*CPO Product Blueprint v4.2 — aligned with Complete Guide v3.2 — July 2026*
