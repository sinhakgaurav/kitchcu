# Delivery payer + Porter courier (owner control)

## Product rules (CEO / CPO)

| Distance | Min order met? | Who pays logistics |
|----------|----------------|--------------------|
| **In range** (`≤ max_delivery_radius_km`) | n/a | **Kitchen 100%** — customer fee `0` |
| **Out of range** | No | **Customer 100%** |
| **Out of range** | Yes (`subtotal ≥ min_order_for_free_delivery`) | **Kitchen `delivery_subsidy_percent`%** · customer pays the rest (`shared`) |

Default subsidy: **50%**. Configurable per kitchen via `PATCH /kitchens/{id}/delivery-settings`.

Checkout shows **two modes** (self vs Porter/platform) with clear customer vs kitchen ₹ split.

## Porter integration (CTO)

`services/delivery/app/platform_courier.py`

| `DELIVERY_PARTNER` | Behaviour |
|--------------------|-----------|
| `mock` (default) | `base + per_km * distance` |
| `porter` | Porter Partner quote API (`PORTER_API_KEY`, `PORTER_BASE_URL`) when feature `courier_porter_dunzo` is on |
| `http` | Generic POST `DELIVERY_PARTNER_QUOTE_URL` |

Order booking: owner `POST .../delivery-mode` with `mode=platform` → `order.porter_client` books Porter and stores `courier_partner` / `courier_job_id`.

## Order fields

- `delivery_mode`: `self` | `platform`
- `delivery_payer`: `owner` | `customer` | `shared`
- `owner_delivery_cost`: kitchen share (INR)
- `courier_partner` / `courier_job_id`: Porter job (nullable)

## Env

```
DELIVERY_PARTNER=mock|porter|http
PORTER_API_KEY=
PORTER_BASE_URL=https://api.porter.in
PORTER_QUOTE_PATH=/v1/get_quote
PORTER_ORDER_PATH=/v1/orders
DELIVERY_PARTNER_BASE_FEE=25
DELIVERY_PARTNER_PER_KM=12
```
