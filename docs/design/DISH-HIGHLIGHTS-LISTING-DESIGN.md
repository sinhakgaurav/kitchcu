# Dish highlights + listing filter/sort

**Feature:** Dish merchandising flags · **Service:** `catalog` · **Date:** 2026-07-19

## Business

Owners mark dishes as **Featured**, **Chef's special**, or **Unique recipe** so customers can find signature items. Helps kitchens grow without aggregator “boost” paywalls.

## Data

`ckac_catalog.dishes`: `is_featured`, `is_chefs_special`, `is_unique_recipe` (bool, default false). Indexed for menu filter queries.

## API

- Create/Update/Response include the three flags.
- `GET .../menu?highlight=&diet=&sort=&q=` — filter/sort applied in-process after cache (cache remains full active menu).
- Response adds `highlight_sections` (featured / chefs_special / unique_recipe) from the filtered dish set.

`sort`: `name_asc` | `name_desc` | `price_asc` | `price_desc` | `prep_asc` | `newest`

## Super-admin gate

Kitchen-scoped merchandising only — no package/credential/kill-switch. Admin sees flags via existing kitchen ops if they view menus; no new admin tab required.

## UI

- Owner: toggles on Add dish + Menu card edit.
- Customer menu: highlight sections + filter chips + sort.
- Shared listing toolbar on owner menu, customer menu, nearby kitchens, new-order dish pick, learning lists.
