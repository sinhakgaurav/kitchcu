# F19b — Bulk prep batches + stock deduct on prepared

**Feature ID:** F19b · **Service:** `services/catalog/` (+ order trigger) · **Author:** Platform · **Date:** 2026-07-20

## 1. Business understanding

- **Problem:** Deducting stock on *accept* is wrong for cloud kitchens — acceptance is a promise, not consumption. Thali/tiffin kitchens cook in **bulk**; inventory should move when food is **prepared**, with explicit recipe quantities the owner can edit.
- **Vision:** Owner manages pantry truth: per-order “ready = prepared” for à la carte, or bulk prep batches (single dish / combo) with editable ingredient totals for thali scale.
- **Business objective:** Lower food waste, accurate COGS signal, trust in low-stock warnings before the next cook.
- **Why now:** F19 mapper exists; Wave 2 owners hit false stock after accept-before-cook.
- **KitchCu gate:** Yes — operational OS for home/cloud kitchens, not POS.

## 2. Challenge & improvement

- **Challenged:** “Deduct on accept” and “one recipe line = one order only.”
- **Improvements:** (1) Order consumption on first transition to `ready`. (2) Bulk prep batches with recipe expand → **explicit editable totals**. (3) Kitchen `deduct_mode` to avoid double-count when using bulk prep exclusively.
- **Out of scope:** Reversing stock on cancel after ready; purchase ledger / suppliers (E1); prepared-portion inventory (finished goods).

## 3. Personas & journey

| Persona | Goal | Steps |
|---------|------|--------|
| Owner (à la carte) | Stock drops when food is made | Accept → prepare → mark **Ready** → pantry deducts |
| Owner (thali bulk) | Morning cook for 40 thalis | Create combo prep batch → edit qty → Mark prepared → pantry deducts once |
| Owner | Avoid double deduct | Set stock mode to `prep_batch_only` when using batches |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Stop order stock deduct on `accepted` | Must |
| FR-2 | Deduct on first transition to `ready` when mode=`order_ready` | Must |
| FR-3 | Create prep batch from 1+ dishes + portions; expand recipes into editable lines | Must |
| FR-4 | Mark batch prepared → deduct once (idempotent) + EDD events | Must |
| FR-5 | Kitchen stock settings: `order_ready` \| `prep_batch_only` | Must |
| FR-6 | Owner UI: Bulk prep page | Must |

## 5. Non-functional

| ID | Target |
|----|--------|
| NFR-1 | Tenant filter `kitchen_id` on all prep queries |
| NFR-2 | Deduct best-effort from order (never block lifecycle) |
| NFR-3 | Indexes on `(kitchen_id, status)`, `(kitchen_id, created_at)` |

## 6. Business rules

| Rule | Layer |
|------|--------|
| Combo batch requires ≥2 dishes | Pydantic |
| Single-dish batch exactly 1 dish | Pydantic |
| Ingredient lines required before mark prepared | Domain |
| Prepared batch cannot re-deduct | Status machine |
| `prep_batch_only` → internal deduct-order no-ops | Catalog |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | CRUD drafts, mark prepared, toggle deduct mode | Cross-tenant |
| Customer | — | All |
| Admin | View (future) | Mutate in this sprint |

### Super-admin gate

| # | Y/N | Notes |
|---|-----|--------|
| Kitchen-scoped | Y | Owner kitchen ops only this ship |
| Entitlement | N | Core ops with F19 |
| Ops override | N | Defer |
| Kill-switch | N | Defer |
| Credentials | N | — |

## 8–10. Data / API / events

**Tables (`ckac_catalog`):** `kitchen_stock_settings`, `prep_batches`, `prep_batch_dishes`, `prep_batch_ingredients`.

**Owner API:**
- `GET/PATCH /kitchens/{id}/stock-settings`
- `GET/POST /kitchens/{id}/prep-batches`
- `GET/PATCH /kitchens/{id}/prep-batches/{batch_id}`
- `POST /kitchens/{id}/prep-batches/{batch_id}/mark-prepared`

**Internal:** `deduct-order` respects `deduct_mode`; docs say trigger = order `ready`.

**Events:** existing `ingredient.stock.deducted` / `low_stock`; payload may include `prep_batch_id` or `order_id`. New: `prep_batch.prepared` on `ckac:catalog:ingredient`.

## 11. Flow

```
Actor → API → Domain → DB → Outbox → Consumers → UI
Owner mark ready → order PATCH → catalog deduct-order (if order_ready)
Owner mark prep prepared → catalog deduct lines → pantry UI refresh
```

## 12. Test plan

- Catalog: expand combo, edit lines, mark prepared deducts, idempotent second mark
- Catalog: prep_batch_only skips deduct-order
- Order: mock client — deduct called on ready, not accept

## 13. Rollout

Migrate catalog `009`; rebuild catalog; owner PWA route `/dashboard/prep`. Update F19 design note.
