# F19 — Ingredient Balance Mapper (S15)

## Features

| ID | Feature | Owner |
|----|---------|-------|
| F19 | Recipe per dish, low-stock warnings | Catalog |
| F19b | Stock deduct on order **ready** / bulk prep **prepared**; kitchen deduct mode | Catalog + Order |

## Bounded context

Extend `services/catalog/` — schema `ckac_catalog`.

## Tables

### `ingredients`
- `kitchen_id`, `name`, `unit` (g/ml/pcs), `current_stock`, `low_stock_threshold`
- Unique `(kitchen_id, name)`

### `dish_ingredients`
- Recipe standard: `dish_id`, `ingredient_id`, `quantity`, `unit`

## Owner API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/kitchens/{id}/ingredients` | List stock + low flags |
| POST | `/kitchens/{id}/ingredients` | Create ingredient |
| PATCH | `/kitchens/{id}/ingredients/{id}` | Update name/threshold |
| POST | `/kitchens/{id}/ingredients/{id}/adjust-stock` | Manual override |
| GET | `/kitchens/{id}/dishes/{dish_id}/recipe` | Get recipe |
| PUT | `/kitchens/{id}/dishes/{dish_id}/recipe` | Set recipe lines |
| GET/PATCH | `/kitchens/{id}/stock-settings` | Deduct mode: `order_ready` \| `prep_batch_only` |
| GET/POST | `/kitchens/{id}/prep-batches` | List / create bulk prep batches |
| PATCH | `/kitchens/{id}/prep-batches/{batch_id}` | Edit name/notes/ingredient totals |
| POST | `/kitchens/{id}/prep-batches/{batch_id}/mark-prepared` | Deduct stock for batch |

## Internal API (X-Internal-Key)

| Method | Path | Trigger |
|--------|------|---------|
| POST | `/internal/kitchens/{id}/stock/low-stock-check` | Order service before accept |
| POST | `/internal/kitchens/{id}/stock/deduct-order` | Order service on first `ready` (skipped if `prep_batch_only`) |

## Events (EDD)

| Event | Stream |
|-------|--------|
| `ingredient.created` | `ckac:catalog:ingredient` |
| `ingredient.stock.adjusted` | `ckac:catalog:ingredient` |
| `ingredient.stock.deducted` | `ckac:catalog:ingredient` |
| `ingredient.low_stock` | `ckac:catalog:ingredient` |

## Flow

1. Owner defines ingredients + recipe per dish (qty, photo per line)
2. Owner adds ordered prep steps (rich text + optional step photo + duration)
3. Order in `received` → UI shows low-stock warnings (non-blocking)
4. Owner accepts — stock warnings only (non-blocking); no deduct
5. Owner marks order **Ready** → order service calls deduct (mode `order_ready`)
6. **Or** owner creates bulk prep batch → edits ingredient totals → Mark prepared → deduct once (mode often `prep_batch_only` for thali kitchens)
7. Owner can manually adjust stock anytime

See also: `docs/design/F19B-BULK-PREP-STOCK-ON-PREPARED-DESIGN.md`.

## Schema additions (S15b)

| Table / column | Purpose |
|----------------|---------|
| `ingredients.photo_url` | Pantry reference photo |
| `dish_ingredients.photo_url`, `sort_order` | Per-portion line photo + order |
| `dish_prep_steps` | Ordered steps: title, `body_html`, photo, duration |
| `kitchen_stock_settings` | Per-kitchen `deduct_mode` |
| `prep_batches`, `prep_batch_dishes`, `prep_batch_ingredients` | Bulk cook batches + totals |

## Owner UI (kitchen PWA)

- `/dashboard/ingredients` — pantry form (full-width grid), listing toolbar (search/sort/low-stock), recipe cards
- `/dashboard/prep` — deduct mode toggle, new batch form, batches table with search/sort/status chips
