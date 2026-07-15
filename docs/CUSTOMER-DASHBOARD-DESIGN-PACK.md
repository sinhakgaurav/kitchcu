# Module Design Pack — Customer full dashboard

**Feature:** Customer Growth OS dashboard · **Services:** identity, billing, notification, order · **Date:** 2026-07-15

## Product gate

Yes — retained customers who trust home kitchens (ratings, prep media, refunds, health honesty) grow owner kitchens without aggregators.

## Surface

| Section | Data | Notes |
|---------|------|-------|
| Orders | history + filters (cuisine, veg/non-veg, live media) | rate, issue, prep pics/videos, track, bill, repeat |
| Savings | vs estimated restaurant dish price | ~40% uplift model; override when dish has `restaurant_benchmark_price` in settings |
| Health | home-kitchen vs restaurant-style score | ingredients / oil / veg share from catalog joins |
| Tips | post-rating wellness | walk minutes + water ml by portion heuristics |
| Refunds | received | customer read-only |
| Complaints | ticket inbox | raise + history |
| Addresses | CRUD + lat/lng pin | OSM embed |
| Profile | name/email/phone | OTP secure change |
| Security | password optional + WhatsApp OTP | customers are OTP-first; password is optional unlock |

## Extras integrated beyond ask

- Active coupons / promotions entry points
- Live kitchens near you
- Payout details (refund rail)
- Master-order / bill PDF
- Tracking deep links
- Soft login → full JWT gate for dashboard

## Out of scope

Native password-reset email flows; platform admin complaint SLA UI; medical nutritionist claims (tips are wellness nudges only).
