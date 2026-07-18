# Kitchcu Platform Gaps Tracker

Last updated: 2026-07-12. Focus: cloud kitchen & home-based food services.

> **Superseded for open gaps:** Many Phase 2/3 rows below are stale (checkout, billing, ratings, etc. later shipped).  
> Use **[`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) §5** and [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md) as the living gap board.

## Closed in this sprint

| Gap | Status | Notes |
|-----|--------|-------|
| Cuisine hierarchy (cuisine → veg/non-veg → dish) | Done | Catalog model, API `grouped` menu, customer + owner UI |
| Admin panel | Done | `admin.kitchcu.in` port 13003, login, stats, owners/kitchens/orders |
| Portal app chooser | Done | Port 13000 with customer / kitchen / admin tiles |
| Customer & kitchen Docker frontends | Done | Nginx + API proxy to gateway; `depends_on: gateway` |
| Seed scripts for cuisine | Done | `dish_create_payload()` with cuisine + diet IDs |
| Bulk demo data | Done | `seed-bulk-data.py` updated for required fields |
| **Owner growth analytics** | **Done** | Order service `analytics.py`: revenue summary, 30d trend, top dishes, IST peak hours, repeat rate, customer segments, churn/win-back. Gateway `/analytics` route, Redis-cached summary, owner **Reports** page, `test_analytics.py` (7 tests) |
| Owner app build broken (`fetchCuisines` missing) | Done | `shared/api.ts` `fetchCuisines()` + `createDish` cuisine/category ids added; all 4 PWAs build |
| Demo data had zero repeat customers | Done | `seed-bulk-data.py` weighted customer pool → realistic repeat/VIP/churn (86% repeat rate) |
| **Marketing portal (kitchcu.in)** | **Done** | Port 13000 one-page site: Features, Pricing, Support, Contact, parallax gallery, AI chat |
| **AI support chat** | **Done** | `POST /api/v1/support/chat` — owner & customer modes, knowledge base + optional OpenAI |
| **Support ticketing** | **Done** | `ckac_support` schema, public create + admin manage/reply, AI chat escalation, admin **Tickets** tab |
| **Product rebrand** | **Done** | Application name **Kitchcu** — `customer.kitchcu.in`, `kitchen.kitchcu.in`, `admin.kitchcu.in` |

## Open — Phase 2 (enterprise)

| Gap | Priority | Notes |
|-----|----------|-------|
| Customer online checkout | High | Menu browse only; no cart/payment from customer app |
| Billing & subscriptions | High | Owner tiers exist in DB; no Stripe/Razorpay integration |
| Production OTP (SMS) | High | Dev OTP `123456` only |
| **Profit reporting (ingredient cost)** | High | Analytics covers revenue; profit needs recipe/ingredient-cost model (Ingredient Balance Mapper). Prereq for margin & pricing AI |
| Analytics: admin-wide trends | Medium | Per-kitchen owner analytics done; platform-wide revenue trends for admin still counts-only |
| SPA deep-link reload | Low | Full-page reload of `/dashboard/*` bounces to `/`; in-app nav works. Add nginx `try_files` history fallback + router basename |
| Media upload (MinIO) | Medium | URLs only; no owner upload flow |
| PWA / offline | Medium | No service worker |
| Rate limiting & WAF | Medium | Gateway has no rate limits |
| Observability | Medium | No OpenTelemetry / centralized logs |
| Multi-city ops | Low | Single-region demo (Pune) |
| Delivery partner integration | Low | Manual delivery status only |

## Open — Phase 3

| Gap | Priority | Notes |
|-----|----------|-------|
| Customer accounts & order history | Medium | Session-based browse only |
| Reviews & ratings | Low | Not modeled |
| Kitchen staff roles | Low | Single owner per kitchen |
| Inventory & prep batches | Low | Not in scope for MVP |
| Compliance (FSSAI display) | Low | Field not enforced |

## How to verify closed items

```powershell
docker compose up -d --build
python scripts/seed-dev-data.py
python scripts/seed-bulk-data.py
```

| App | URL |
|-----|-----|
| Portal | http://localhost:13000 |
| Customer | http://localhost:13001 |
| Kitchen | http://localhost:13002 |
| Admin | http://localhost:13003 |
| API | http://localhost:18000 |

**Demo:** Owner `9876543210` / OTP `123456` · Admin local `admin@kitchcu.dev` / `admin123456` · Prod `admin@kitchcu.com` + `ADMIN_PASSWORD` (see [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md))

## Test coverage

- Backend: `scripts/run-tests.ps1` (identity, catalog, order, notification, gateway)
- Load: `python scripts/load-test.py` (gateway health + menu endpoints)
- E2E smoke: `python scripts/smoke-test.py` (23 checks: frontends, auth, cuisine menu, nearby, **owner analytics**, admin) — all passing

## Owner analytics API (Sprint 5)

Kitchen-scoped, owner JWT required, served by order service via gateway:

| Endpoint | Answers |
|----------|---------|
| `GET /kitchens/{id}/analytics/summary?days=` | Revenue, orders, AOV, cancellation & repeat rate |
| `GET /kitchens/{id}/analytics/revenue-timeseries?days=` | Daily revenue trend (fills gaps) |
| `GET /kitchens/{id}/analytics/top-dishes?days=&limit=` | Best sellers by revenue/qty — "which dish sells" |
| `GET /kitchens/{id}/analytics/peak-hours?days=` | Busiest hours (IST) — staffing/prep planning |
| `GET /kitchens/{id}/analytics/customers?days=&limit=` | New/repeat/VIP segments, top spenders, churn win-back list |

Time bucketing uses `Asia/Kolkata`. Summary is Redis-cached (120s TTL). Profit/margin intentionally excluded until ingredient-cost model exists (no fabricated numbers).
