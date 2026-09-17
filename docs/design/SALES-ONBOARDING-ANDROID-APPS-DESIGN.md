# Sales onboarding + Customer / Kitchen / Admin apps (P55)

**Feature:** P55 · **Services:** `services/identity/`, `apps/website/`, `apps/android/`, `apps/ios/` · **Date:** 2026-09-17

## 1. Business understanding

- **Problem:** Field sales cannot create a kitchen on a phone and walk the owner through week-one. Diners and owners expect Play/App Store icons. Three Kotlin + three Swift clones would fork every API and miss the PWA source of truth.
- **Vision:** **One product, three skins.** Customer / Kitchen / Super Admin PWAs are the apps. Android Trusted Web Activities + iOS WKWebView shells put them on stores. A **sales** employee logs into Super Admin (web or Admin app), onboards owner+kitchen, fills address/pin, and ticks a training playbook with the owner. In-dashboard tutorials make each persona’s first five minutes obvious.
- **Business objective:** Faster kitchen acquisition, zero food commission, sales capacity without handing field staff Control or API Keys.
- **Why now:** PWAs are the live product; growth needs a field motion and installable apps.
- **KitchCu product gate:** Yes — more kitchens live on KitchCu, not aggregators.

## 2. Challenge & improvement

- **Assumptions challenged:** “Write native Android and iOS apps.” Rewriting checkout/orders/menu in Compose/SwiftUI splits truth and violates PWA-first (`AGENTS.md`). Sales is a **role**, not a fourth product.
- **Improvements:** Sales kitchen book is scoped (`onboarded_by_admin_id`). Training is a fixed 8-step playbook (not a CMS). Store apps are thin shells over `customer.` / `kitchen.` / `admin.` hosts. Tutorials are skippable, replayable, and the same on web and in the shells.
- **Out of scope:** Full native clones, Play/App Store listing upload, FCM/APNs (PWA later), kitchen-staff roles, commission, sales editing platform Meta/Razorpay SaaS secrets.

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|----------------|
| Sales | Onboard on-site | Admin login → **Sales** → owner phone/name → kitchen address + map pin → create → **Train** checklist with owner → hand kitchen code + OTP |
| Super-admin | Hire sales + oversee | Employees → role `sales` · Sales tab sees all books · Kitchen → **Train** |
| Kitchen owner | Go live | Kitchen app OTP · in-app tips: Orders → live dish photo → recipe |
| Diner | Order from home | Customer app · tips: nearby → plate → pay |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Role `sales` with `sales:write` + `kitchens:read` (no API keys, flags, refunds, employees) | Must |
| FR-2 | `POST /admin/sales/onboard` creates or reuses owner by phone + kitchen; sets `onboarded_by_admin_id` | Must |
| FR-3 | Sales `GET /admin/kitchens` scoped to kitchens they onboarded | Must |
| FR-4 | Training GET/PATCH; sales only on assigned kitchens | Must |
| FR-5 | Admin PWA **Sales** tab + kitchen **Train** tab | Must |
| FR-6 | In-dashboard tutorials (customer, kitchen, admin/sales) skip + replay | Must |
| FR-7 | Three Android TWAs + three iOS WKWebView shells | Must |
| FR-8 | Kill-switch `sales_onboarding` | Must |

## 5. Non-functional

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Onboard is one transaction (owner + kitchen + events) | no orphan kitchen |
| NFR-2 | Tenant isolation | sales cannot open another rep’s kitchen |
| NFR-3 | 100k sessions | index `onboarded_by_admin_id`; no unscoped sales lists |
| NFR-4 | Store shells are configuration, not business logic | hosts only |

## 6. Business rules

| Rule | Layer |
|------|--------|
| Existing owner phone → attach new kitchen (do not 409) | domain |
| New owner → trial, login via WhatsApp OTP (no owner password) | domain |
| Training does not block going live | product |
| Superadmin `*` sees every onboard | RBAC |
| Sales UI: Sales + Kitchens only (no overview KPIs / secrets) | RBAC tabs |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| `sales` | Onboard, edit assigned profile, train | Flags, API keys, refunds, employees, other reps’ kitchens, suspend |
| Superadmin | Hire sales, all kitchens, Train | — |
| Owner | Kitchen app after OTP | See sales employee list |

### 7.1 Super-admin gate

| # | Y/N | Delivery |
|---|-----|----------|
| 1 Kitchen-scoped | Yes | Kitchens → **Train**; Sales tab; `onboarded_by_admin_id` |
| 2 Entitlement | No | Field ops, not a paid kitchen module |
| 3 Ops/support | Yes | Employees role `sales`; `sales:write`; audit on onboard |
| 4 Cross-tenant | Yes | Sales lists filtered by onboarder |
| 5 Kill-switch | Yes | `sales_onboarding` |
| 6 Credentials | No | No platform secrets on sales form |

## 8. Domain

```
PlatformAdmin.role = sales
Kitchen.onboarded_by_admin_id
kitchen_training_progress (kitchen_id, step_key)
```

## 9. Events

| Event | Stream | Payload |
|-------|--------|---------|
| `kitchen.created` | `ckac:identity:kitchen` | code, owner_id, onboarded_by |
| `owner.created` | `ckac:identity:owner` | when new owner |
| `kitchen.training.updated` | `ckac:identity:kitchen` | step_key, completed |

## 10. Database

Identity Alembic `030`: column + training table + flag + `sales:write` + role grants.

## 11. API

- `POST /api/v1/admin/sales/onboard` (201)
- `GET /api/v1/admin/kitchens/{id}/training`
- `PATCH /api/v1/admin/kitchens/{id}/training`

## 12. Store apps

| Store name | Host (prod) | Android id / flavor | iOS bundle |
|------------|-------------|---------------------|------------|
| kitchCU - customers | `customer.kitchcu.com` | `in.kitchcu.customer` | `in.kitchcu.customer` |
| kitchCU - kitchen owner | `kitchen.kitchcu.com` | `in.kitchcu.kitchen` | `in.kitchcu.kitchen` |
| kitchCU - admin | `admin.kitchcu.com` | `in.kitchcu.admin` | `in.kitchcu.admin` |

Debug: Vite ports 13001 / 13002 / 13003. Digital Asset Links + AASA templates under `apps/website/public/.well-known/`.

## 13. Tutorials

Local skip state `kitchcu_tour_{persona}_v1`. Same copy on web and inside the shells. Admin stays English.

## 14. Security

Admin JWT · scoped queries · audit `sales.kitchen.onboarded` · no PII in logs · sales never pastes Meta app secret.

## 15. Tests

`services/identity/tests/test_sales_onboarding.py` · RBAC unit · gateway prefix · employee roles include `sales`.
