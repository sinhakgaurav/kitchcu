# Porter Auto-Book + Customer ETA (P35)

**Feature:** Porter delayed auto-booking + prep+delivery ETA · **Owner:** `order` + `identity` + `billing` · **Date:** 2026-07-19

## Super-admin gate

| # | Applies | Delivery |
|---|---------|----------|
| 1 Kitchen-scoped | Y | Admin → Kitchens → Delivery tab + Modules (`courier_porter_auto_book`) |
| 2 Entitlement | Y | `platform_features.courier_porter_auto_book` → packages Growth/Pro |
| 3 Ops override | Y | Admin Delivery tab can set kitchen toggle/delay |
| 4 Kill-switch | Y | Global flag + kitchen module flag |
| 5 Credentials | N | Existing Porter platform keys |

## Product law

1. **Customer ETA** = max(prep) + max(delivery) across cart lines. Show breakdown + total. `estimated_ready_at` = food ready; `estimated_delivery_at` = doorstep.
2. **Auto-book** (when entitled + kitchen toggle on): after kitchen moves order to `accepted`, wait `porter_auto_book_delay_min` (default 15), then book Porter for pickup at `estimated_ready_at`. Retry every ~2 min until booked or max attempts.
3. **Toggle off / module off**: keep legacy immediate book on accept (ops continuity).
4. Prepaid fee gate (P34) still blocks booking until capture.

## Schema

- `ckac_identity.kitchens`: `porter_auto_book_enabled` BOOL DEFAULT true, `porter_auto_book_delay_min` INT DEFAULT 15
- `ckac_orders.orders`: `estimated_delivery_min`, `estimated_delivery_at`, `porter_auto_book_at`, `porter_auto_book_attempts`, `porter_auto_book_last_attempt_at`

## API

- Owner/Admin: `PATCH .../delivery-settings` (+ admin mirror)
- Internal: `POST /api/v1/internal/orders/porter-auto-book/tick` (+ in-process loop every 60s)
- Track/Order responses expose prep/delivery ETA fields

## Events

`order.porter_auto_book.scheduled` · `order.porter_auto_book.succeeded` · `order.porter_auto_book.retry` · `order.porter_auto_book.failed`
