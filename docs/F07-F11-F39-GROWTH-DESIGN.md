# F07–F11, F39 Growth Intelligence Design Pack (S12)

## Features

| ID | Feature | Owner | Notes |
|----|---------|-------|-------|
| F07 | Revenue report | Order service | Already in `analytics.py` |
| F08 | Best performing dishes | Order service | Already in `analytics.py` |
| F09 | Best dish combinations | Growth | Association rules on `order_items` |
| F10 | Customer order patterns | Growth | Day-of-week + peak hour insights |
| F11 | Owner growth suggestions | Growth | Rules engine → `suggestions` table |
| F39 | Daily menu WhatsApp push | Growth | Owner selects dishes → blast event |

## Bounded context

New microservice `services/growth/` — schema `ckac_growth`.

Cross-schema reads only:
- `ckac_orders.orders` + `order_items` — combos, patterns, win-back
- `ckac_identity.kitchens` — owner validation
- `ckac_catalog.dishes` — daily menu dish validation
- `ckac_ratings.dish_rating_aggregates` — dish promo suggestions
- `ckac_marketing.kitchen_customers` — F39 recipient count

## Tables

### `suggestions` (F11)
- `suggestion_type`: `seasonal` | `dish_promo` | `customer_winback` | `combo_opportunity` | `peak_staffing`
- `action_payload` JSONB — coupon code hint, dish IDs, combo bundle, etc.
- `dismissed` boolean — owner can dismiss

### `seasonal_patterns` (F11 seasonal rules)
- Platform seed data: region, season_event, dish_category, demand_multiplier, sample_dishes

## API (prefix `/api/v1`)

| Method | Path | Auth |
|--------|------|------|
| GET | `/kitchens/{id}/growth/combos?days=` | Owner |
| GET | `/kitchens/{id}/growth/patterns?days=` | Owner |
| GET | `/kitchens/{id}/growth/suggestions` | Owner |
| POST | `/kitchens/{id}/growth/suggestions/generate` | Owner |
| PATCH | `/kitchens/{id}/growth/suggestions/{sid}` | Owner |
| GET | `/growth/seasonal-patterns?region=` | Owner |
| POST | `/kitchens/{id}/growth/daily-menu/push` | Owner |

## Events (EDD)

| Event | Stream |
|-------|--------|
| `suggestion.generated` | `ckac:growth:suggestion` |
| `daily_menu.blast_requested` | `ckac:growth:daily_menu` |

## Gateway routing

`/kitchens/*/growth/*`, `/growth/*` → growth service

## Tests

- Combo mining from multi-item orders
- Pattern insights (day-of-week)
- Suggestion generate (win-back, combo, peak staffing)
- Dismiss suggestion
- Daily menu push validates dishes + publishes event
- Event outbox on generate + daily menu push
