# Customer → Kitchen Monthly Subscription (Tiffin / Thali) — F34 / F35

**Service owner:** `services/marketing/` · **Sprint:** Phase-1 close / F34–F35 MVP · **Date:** 2026-07-19

## Super-admin gate

| # | Applies | Delivery |
|---|---------|----------|
| 1 Kitchen-scoped | Y | Admin → Kitchens → Tiffin tab (counts + module link) |
| 2 Entitlement | Y | `platform_features.tiffin_plans` → Growth/Pro; module `tiffin_plans` |
| 3 Ops override | Y | Admin Modules kill-switch; summary read |
| 4 Kill-switch | Y | Global `tiffin_plans` feature flag + kitchen module |
| 5 Credentials | N | Recurring Razorpay later on kitchen Route (out of MVP) |

## Product law

1. Owner defines **monthly plans** (thali/tiffin/combo/single_dish) with price, weekdays, dish config.
2. Customer **requests** subscribe → status `pending`.
3. Owner **accept** → `active`; **deny** → `denied`; **deactivate** → `paused`; **activate** → `active` again.
4. **No food commission** — monthly fee is kitchen revenue (subscription SaaS for platform stays separate).
5. MVP billing: enrollment + status machine; Razorpay recurring charge = follow-up (field `billing_status=manual`).

### Dish selection rules (F35 — server-enforced 2026-07-20)

| `plan_type` | `dishes_config.dish_ids` |
|-------------|--------------------------|
| `combo` | ≥ 2 |
| `single_dish` | exactly 1 |
| `thali` / `tiffin` | ≥ 1 |

Enforced in `validate_plan_dish_selection` on create/update. See also `docs/design/DISH-BULK-IMPORT-AND-PLAN-MEDIA-DESIGN.md`.

## Schema (`ckac_marketing`)

- `subscription_plans` — kitchen-scoped plan catalog
- `customer_subscriptions` — enrollment + lifecycle

## APIs

| Actor | Endpoints |
|-------|-----------|
| Owner | plan CRUD, list subscriptions, accept/deny/activate/deactivate, summary |
| Customer | list public plans, request subscribe, list mine, cancel |
| Admin | kitchen tiffin summary |

## Events (`ckac:marketing:subscription`)

`subscription.plan.created|updated` · `subscription.requested` · `subscription.accepted|denied|activated|deactivated|cancelled`

## UI

- Owner: `/dashboard/tiffin` (+ Reports KPI + Intelligence card)
- Customer: kitchen plans → request subscribe
- Admin: Kitchens → Tiffin tab + Packages/Modules

## Out of scope (explicit)

- Daily auto-order generation from plan (order generator job)
- Live Razorpay subscription objects
