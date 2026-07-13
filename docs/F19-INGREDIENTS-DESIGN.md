# F19 — Ingredient Balance Mapper (S15)

## Features

| ID | Feature | Owner |
|----|---------|-------|
| F19 | Recipe per dish, stock deduct on accept, low-stock warnings | Catalog |

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

## Internal API (X-Internal-Key)

| Method | Path | Trigger |
|--------|------|---------|
| POST | `/internal/kitchens/{id}/stock/low-stock-check` | Order service before accept |
| POST | `/internal/kitchens/{id}/stock/deduct-order` | Order service on accept |

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
4. Owner accepts (`received` → `accepted`) → order service calls deduct
5. Owner can manually adjust stock anytime

## Schema additions (S15b)

| Table / column | Purpose |
|----------------|---------|
| `ingredients.photo_url` | Pantry reference photo |
| `dish_ingredients.photo_url`, `sort_order` | Per-portion line photo + order |
| `dish_prep_steps` | Ordered steps: title, `body_html`, photo, duration |
