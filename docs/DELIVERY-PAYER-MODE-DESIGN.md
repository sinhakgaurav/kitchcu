# Delivery payer + Porter courier (owner control)

## Product rules (CEO / CPO)

| Distance | Min order met? | Who pays logistics |
|----------|----------------|--------------------|
| **In range** (`≤ max_delivery_radius_km`) | n/a | **Kitchen 100%** — customer fee `0` |
| **Out of range** | No | **Customer 100%** |
| **Out of range** | Yes (`subtotal ≥ min_order_for_free_delivery`) | **Kitchen `delivery_subsidy_percent`%** · customer pays the rest (`shared`) |

Default subsidy: **50%**. Configurable per kitchen via `PATCH /kitchens/{id}/delivery-settings`.

Checkout shows **two modes** (self vs Porter/platform) with clear customer vs kitchen ₹ split.
Customer PWA sends `delivery_mode` on order create; fee is re-validated server-side.
Porter is **booked on kitchen accept** (not at cart place) so cancelled carts do not create jobs.

Owner configures radius + `min_order_for_free_delivery` + `delivery_subsidy_percent` on Kitchen settings.

## Delivery fee collection (P34)

| `delivery_payer` | Customer fee | Collection rule |
|------------------|--------------|-----------------|
| `owner` | ₹0 | No delivery-fee payment |
| `shared` | > 0 | **Must prepaid** (UPI/online). COD rejected. Porter book waits until payment `captured`. |
| `customer` | > 0 | Choose **`prepaid`** (pay first) or **`pay_on_delivery`**. Prepaid → online/UPI; POD → COD OK; Porter only gated when prepaid. |

Field: `orders.delivery_fee_payment` = `prepaid` | `pay_on_delivery` | null.

Agreement = quote shown + `delivery_fee_accepted` + (for shared) prepaid capture before Porter.

## Porter integration (CTO)

`services/delivery/app/platform_courier.py`

| `DELIVERY_PARTNER` | Behaviour |
|--------------------|-----------|
| `mock` (default) | `base + per_km * distance` |
| `porter` | Porter Partner quote API (`PORTER_API_KEY`, `PORTER_BASE_URL`) when feature `courier_porter_dunzo` is on |
| `http` | Generic POST `DELIVERY_PARTNER_QUOTE_URL` |

Order booking (P35): on accept with `delivery_mode=platform`:
- Kitchen `porter_auto_book_enabled` + module `courier_porter_auto_book` → schedule book at accept+delay (default 15m), retry ~2m until booked; pickup time ≈ `estimated_ready_at`.
- Otherwise → book immediately via `order.porter_client` (legacy).
- Stores `courier_partner` / `courier_job_id`. Customer ETA = max(prep) + max(delivery).

## Order fields

- `delivery_mode`: `self` | `platform`
- `delivery_payer`: `owner` | `customer` | `shared`
- `delivery_fee_payment`: `prepaid` | `pay_on_delivery` | null
- `owner_delivery_cost`: kitchen share (INR)
- `courier_partner` / `courier_job_id` / `courier_status`: Porter job (nullable)

## Env

```
DELIVERY_PARTNER=mock|porter|http
PORTER_API_KEY=
PORTER_BASE_URL=https://api.porter.in
PORTER_QUOTE_PATH=/v1/get_quote
PORTER_ORDER_PATH=/v1/orders
PORTER_WEBHOOK_SECRET=   # optional; header X-Porter-Secret
DELIVERY_PARTNER_BASE_FEE=25
DELIVERY_PARTNER_PER_KM=12
```

## Porter webhooks (P33)

`POST /api/v1/webhooks/porter` → gateway → **order** service.

- Matches `orders.courier_job_id`
- Updates `courier_status` only (food lifecycle stays owner-driven)
- Emits `order.courier_status.updated` on `ckac:orders:order`
- Owner Order detail shows courier status next to job id
