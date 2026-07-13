# F36–F38 Marketing Service Design Pack (S10)

## Features

| ID | Feature | Owner |
|----|---------|-------|
| F36 | Owner custom coupons | Marketing |
| F37 | Owner CRM (spend, patterns, tags) | Marketing |
| F38 | Targeted special pricing by segment | Marketing |

## Bounded context

New microservice `services/marketing/` — schema `ckac_marketing`.

Cross-schema reads only:
- `ckac_orders.orders` + `order_items` — CRM sync (read)
- `ckac_identity.kitchens` — owner validation (read)
- `ckac_identity.customers` — customer phone lookup (read)
- `ckac_catalog.dishes` — promotion dish validation (read)

## Tables

### `kitchen_customers` (F37)
- Tenant: `kitchen_id`
- Key: `(kitchen_id, customer_phone)` unique
- Aggregates: `total_spend`, `monthly_spend`, `order_count`, `favorite_dishes` (JSONB), `order_patterns` (JSONB)
- Owner-editable: `tags` (JSONB string array)
- Sync from orders on list when `?refresh=true`

### `coupons` (F36)
- `code` unique per kitchen (uppercase)
- `discount_type`: `percent` | `fixed`
- `discount_value`, optional `min_order_amount`, `max_uses`, `used_count`
- `valid_from` / `valid_until`, `is_active`

### `promotions` (F38)
- `dish_id`, `special_price`, `segment` (`all|top_spenders|repeat|vip|churn_risk`)
- `segment_limit` (e.g. top 20), `starts_at`, `ends_at`, `is_active`

## API (prefix `/api/v1`)

| Method | Path | Auth |
|--------|------|------|
| GET | `/kitchens/{id}/crm/customers?refresh=` | Owner |
| PATCH | `/kitchens/{id}/crm/customers/{cid}` | Owner |
| GET/POST | `/kitchens/{id}/coupons` | Owner |
| PATCH | `/kitchens/{id}/coupons/{cid}` | Owner |
| POST | `/marketing/coupons/validate` | Customer |
| GET/POST | `/kitchens/{id}/promotions` | Owner |
| GET | `/kitchens/{id}/promotions/active` | Public / Customer |

## Events (EDD)

| Event | Stream |
|-------|--------|
| `coupon.created` | `ckac:marketing:coupon` |
| `promotion.created` | `ckac:marketing:promotion` |
| `crm.synced` | `ckac:marketing:crm` |

## Gateway routing

`/kitchens/*/crm`, `/coupons`, `/promotions` → marketing service  
`/marketing/*` → marketing service

## Tests

- CRM sync from seeded orders
- Coupon create + validate (percent/fixed, expiry, min order)
- Promotion create + active list with segment filter
- Event outbox on coupon/promotion create
