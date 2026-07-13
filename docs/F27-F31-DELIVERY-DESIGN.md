# F27–F31, F29 Delivery Design Pack (S13)

## Features

| ID | Feature | Owner | Notes |
|----|---------|-------|-------|
| F27 | Service range & delivery radius | Identity + Delivery | Fee rules on kitchen; quote enforces radius |
| F28 | Delivery fee accept/deny | Delivery + Order + PWA | Quote → accept before place order |
| F29 | Tracking link + interval notifications | Order + Delivery | `tracking_token`; public `/t/{token}` |
| F30 | Per-dish prep/delivery time | Catalog + Order | `delivery_time_min`; ETA = max(prep)+delivery |
| F31 | Lat/long distance mapping | Delivery | PostGIS `ST_Distance` / 1000 → km |

## Bounded context

New microservice `services/delivery/` — schema `ckac_delivery` (quotes log + tracking intervals).

Cross-schema:
- `ckac_identity.kitchens` — location + fee rules (read); fee columns extended via identity migration
- `ckac_orders.orders` — distance/fee/token fields (order owns writes)
- `ckac_catalog.dishes` — `delivery_time_min` (catalog migration)

## Identity kitchen columns (F27)

Add to `ckac_identity.kitchens`:
- `delivery_fee_per_km` DECIMAL(8,2) DEFAULT 10
- `delivery_fee_flat_beyond` DECIMAL(8,2) DEFAULT 0
- `min_order_for_free_delivery` DECIMAL(10,2) NULL
- `tracking_notify_interval_min` INT DEFAULT 5

Owner: `PATCH /kitchens/{id}/delivery-settings`

## Delivery quote rules (F27/F28/F31)

1. Distance = `ST_Distance(kitchen.location, customer_point) / 1000`
2. If distance > `max_delivery_radius_km` → reject (`out_of_range`)
3. If distance ≤ `free_delivery_radius_km` → fee = 0
4. Else fee = `delivery_fee_flat_beyond` + `ceil(distance - free) * delivery_fee_per_km`
5. If `subtotal >= min_order_for_free_delivery` → fee = 0 (optional override)

## Order columns (F28/F29/F31)

- `distance_km`, `delivery_fee_accepted`, `tracking_token` UNIQUE
- On delivery place: persist distance + accepted fee; generate token
- ETA: `now + max(prep_time_min) + max(delivery_time_min)` when delivery

## Catalog (F30)

- `delivery_time_min` INT NULL on dishes

## API (`services/delivery/` prefix `/api/v1`)

| Method | Path | Auth |
|--------|------|------|
| POST | `/delivery/quote` | Public / Customer |
| GET | `/delivery/track/{token}` | Public |
| GET | `/kitchens/{id}/delivery/settings` | Owner |
| PATCH | `/kitchens/{id}/delivery/settings` | Owner (proxied writes to identity via same service reading/updating kitchen cols) |

Settings PATCH updates `ckac_identity.kitchens` fee columns (cross-schema write avoided: identity owns PATCH; delivery reads for quotes).

**Revised ownership:**
- Identity owns kitchen fee columns + `PATCH /kitchens/{id}` delivery settings
- Delivery owns quote + public tracking read model
- Order owns token generation on create + expose token in responses

## Events (EDD)

| Event | Stream |
|-------|--------|
| `delivery.fee_quoted` | `ckac:delivery:quote` |
| `delivery.tracking_created` | `ckac:delivery:tracking` |

## Gateway

`/delivery/*` → delivery service  
`/kitchens/*/delivery` → delivery service

## Tests

- Quote free within radius
- Quote per-km beyond free radius
- Out of max radius rejected
- Min order free override
- Tracking token public lookup
- Order create stores distance + token
- Event outbox on quote
