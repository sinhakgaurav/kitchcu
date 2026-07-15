# Delivery payer + platform courier (owner control)

## Rules

| Distance | Modes | Who pays logistics |
|----------|--------|--------------------|
| **In range** (`distance ≤ max_delivery_radius_km`) | `self` or `platform` | **Owner** — customer fee `0` |
| **Out of range** (`distance > max`) | `self` or `platform` | **Customer** — owner may set/self fee; platform quote billed to customer |

## Platform courier

`services/delivery/app/platform_courier.py` — pluggable quote adapter.

- Dev/default: `base + per_km * distance` (env-tunable)
- Swap for real local courier later (`DELIVERY_PARTNER=mock|http`, webhook optional)

## Order fields (`ckac_orders.orders`)

- `delivery_mode`: `self` | `platform` | null
- `delivery_payer`: `owner` | `customer` | null
- `owner_delivery_cost`: INR owner owes for platform logistics
- `customer_latitude` / `customer_longitude`: for Google Maps tracking

## Tracking map

Public track + owner order detail: Google Maps directions embed (kitchen → customer) + open-in-Maps link. No partner GPS required for v1.
