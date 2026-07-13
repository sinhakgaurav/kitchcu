# F29 + F45 Notification Design Pack (S14)

## Features

| ID | Feature | Owner |
|----|---------|-------|
| F29 | Tracking link + interval notifications | Notification |
| F45 | App + WhatsApp order notifications | Notification |

## Bounded context

Extend `services/notification/` — schema `ckac_notifications`.

Cross-schema reads:
- `ckac_orders.orders` — status, tracking_token, customer_phone
- `ckac_identity.kitchens` — name, tracking_notify_interval_min

## Tables

### `notification_log`
- Audit of outbound messages (whatsapp/push)
- Dev mode: logged without Meta API call

### `tracking_reminders` (F29)
- Active while order status is `preparing` or `out_for_delivery`
- `next_reminder_at` advanced by kitchen `tracking_notify_interval_min` (default 5)

## Internal API (X-Internal-Key)

| Method | Path | Trigger |
|--------|------|---------|
| POST | `/internal/notifications/order-placed` | Order service after create |
| POST | `/internal/notifications/order-status-changed` | Order service after status update |
| POST | `/internal/notifications/tracking-interval/tick` | Cron / manual |
| POST | `/internal/notifications/daily-menu-blast` | Growth daily menu push |

## Events (EDD)

| Event | Stream |
|-------|--------|
| `notification.sent` | `ckac:notify:dispatch` |
| `notification.tracking_interval` | `ckac:notify:tracking` |

## Templates (dev text)

- `order_confirmed` — order code + tracking link
- `order_status_update` — new status + tracking link
- `delivery_progress` — interval reminder + tracking link
- `daily_menu_blast` — owner menu message

Tracking URL: `{customer_app_url}/t/{tracking_token}`
