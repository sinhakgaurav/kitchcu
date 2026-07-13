# F16–F18 Ratings Service Design Pack (S11)

## Features

| ID | Feature | Owner |
|----|---------|-------|
| F16 | Home taste + quality rating (1–5) | Ratings |
| F17 | Weighted overall aggregate on dish cards | Ratings |
| F18 | Anonymous A/V experience reviews | Ratings |

## Rules

- **Verified purchase only:** order status `delivered`, customer phone matches JWT
- **One rating per dish per order per customer**
- **F17 formula:** `overall = 0.6 × avg_home_taste + 0.4 × avg_quality`
- **F18:** Optional `media_url` + `media_type` (video/audio); public list never exposes PII

## Schema `ckac_ratings`

| Table | Purpose |
|-------|---------|
| `dish_ratings` | Individual verified ratings |
| `dish_rating_aggregates` | Per-dish F17 aggregates |
| `dish_suggestions` | Customer dish suggestions (owner workflow) |

## Cross-schema reads

- `ckac_orders.orders` + `order_items` — verify delivered + dish in order
- `ckac_identity.customers` — phone lookup
- `ckac_catalog.dishes` — dish name/kitchen validation

## API (`/api/v1`)

| Method | Path | Auth |
|--------|------|------|
| POST | `/customers/me/orders/{order_id}/ratings` | Customer |
| GET | `/kitchens/{id}/ratings/summaries` | Public |
| GET | `/kitchens/{id}/dishes/{dish_id}/ratings/summary` | Public |
| GET | `/kitchens/{id}/dishes/{dish_id}/ratings/reviews` | Public |
| POST | `/kitchens/{id}/dishes/{dish_id}/suggestions` | Customer |
| GET | `/kitchens/{id}/suggestions` | Owner |
| PATCH | `/kitchens/{id}/suggestions/{sid}` | Owner |

## Events

| Event | Stream |
|-------|--------|
| `rating.created` | `ckac:ratings:rating` |
| `rating.aggregate.updated` | `ckac:ratings:dish` |
