# Kitchcu — CPO Product Blueprint

**Growth Operating System for cloud kitchens & home food businesses**

| Field | Value |
|-------|-------|
| Version | **4.0** — Module encyclopedia edition |
| Audience | CPO, CEO, Product, Engineering, Investors |
| Master guide | [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) · [`CKAC-COMPLETE-GUIDE.pdf`](./CKAC-COMPLETE-GUIDE.pdf) |
| Quality loop design | [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| Last updated | July 2026 |

> This blueprint is the **CPO lens extract**. Full CEO/CTO depth, architecture diagrams, ER, and flow charts live in the Complete Executive Guide v2.0.

---

## 1. Product North Star

**Mission:** Give every cloud kitchen the operating system to run, grow, and standardize quality — while customers get honest visibility into food.

| Stakeholder | Promise |
|-------------|---------|
| Owner | WhatsApp order → revenue report same day |
| Customer | Live photos, home-taste ratings, fair delivery |
| Platform | Subscription SaaS — **zero food commission** |

**Principles:** Quality over speed · Truth in media · Owner owns CRM · Progressive complexity · Not a restaurant POS.

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

Detailed description + challenge narrative for each: **Complete Guide §6**.

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

---

## 5. Surfaces

| Domain | Audience | Job |
|--------|----------|-----|
| kitchcu.in (portal) | Market | Brand, education, signup |
| kitchen.kitchcu.in | Owner | Run & grow the kitchen |
| customer.kitchcu.in | Diner | Discover, order, track, rate |
| admin.kitchcu.in | Ops | Support, kitchens, attention |

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

## 7. CTO pointer

For architecture, event flows, and ER diagrams see:

- Complete Guide **Part III** (PDF + markdown)
- `CKAC-ARCHITECTURE-CTO.md`
- `CKAC-SYSTEM-BENCHMARK.md`

---

*CPO Product Blueprint v4.0 — aligned with Complete Guide v2.0 — July 2026*
