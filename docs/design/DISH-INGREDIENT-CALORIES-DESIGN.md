# Dish + ingredient calories + healthy tag (P53)

**Feature:** P53 · **Service:** `services/catalog/` · **Date:** 2026-09-15

## 1. Business understanding

- **Problem:** Diners cannot tell how heavy a home plate is. Owners already map F19 recipes but have no kcal on pantry SKUs, so menus cannot show an honest serving estimate or a **Healthy** mark.
- **Vision:** Owner sets kcal on each pantry SKU and an optional calories note on the dish. Recipe quantities × those SKUs **sum to the plate**. A **Healthy** tag is automatic — never a self-declared badge.
- **Business objective:** Trust vs restaurant calorie theatre; zero food commission preserved.
- **Why now:** P50 already quantity-weights recipes for a health score. Calories reuse the same map.
- **KitchCu product gate:** Yes — home kitchens win when the plate is explained, not hyped.

## 2. Challenge & improvement

- **Assumptions challenged:** “Owner types 320 kcal on the dish and we trust it.” The number must come from ingredient amounts. Owner copy is a **description**, not the total.
- **Improvements:** Incomplete pantry kcal still shows a partial sum; **Healthy** requires a complete map + kcal cap + P50 score floor (blocks greenwashing).
- **Out of scope:** Lab nutrition facts, FSSAI labels, medical advice, allergen certification, owner-forced Healthy tag, per-order commission.

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|----------------|
| Owner | Honest plate kcal | Pantry → kcal per 100 g/ml (or per piece) → map recipe qty → see running total → optional calories note on the dish |
| Customer | Pick a lighter plate | Menu card shows kcal + Healthy when earned; dish details list per-ingredient kcal |
| Support | Troubleshoot missing tag | Admin → Kitchens → **Pantry** kcal column + recipe coverage |
| Super-admin | Kill public calories / retune Healthy | Control → Dish calories & Healthy (`dish_calories`, `dish_healthy_tag`, kcal cap) |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Owner sets `kcal_per_100` on pantry SKU (per 100 g/ml, or per piece when unit is pcs) | Must |
| FR-2 | Owner sets optional `calories_description` on the dish | Must |
| FR-3 | Dish kcal = sum(ingredient kcal × recipe quantity), converted by unit | Must |
| FR-4 | **Healthy** tag automatic: complete kcal map + kcal ≤ Control `healthy_max_kcal` (default 500) + health score ≥ Control `healthy_min_score` (default 65) | Must |
| FR-5 | Public menu / health snapshot / recipe GET expose kcal + tag (flag on) | Must |
| FR-6 | Admin pantry shows kcal | Must |

## 5. Non-functional

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Menu attach is one recipe query (same batch as P50) | no N+1 |
| NFR-2 | Tenant isolation | `kitchen_id` on ingredients/dishes |
| NFR-3 | Copy | Kitchen estimate — not a lab nutrition label |

## 6. Business rules

| Rule | Layer |
|------|--------|
| `kcal_per_100` 0–2000 | Pydantic |
| g/ml: kcal in 100 of that unit. pcs: kcal per 1 piece | domain |
| Recipe `pcs` → 50 g equivalent when pantry is g/ml (same as P50 weight) | domain |
| Missing SKU kcal → line omitted from sum; `calories_incomplete=true` | domain |
| Healthy only when every recipe line has kcal, `calories_kcal ≤ healthy_max_kcal`, P50 score ≥ `healthy_min_score` | domain |
| Flag `dish_health` off → public health snapshot omitted; pantry fields still stored | API |
| Flag `dish_calories` off → public kcal omitted (and Healthy); pantry still stored | API |
| Flag `dish_healthy_tag` off → public Healthy omitted; kcal may still show | API |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | Set pantry kcal + dish note; see computed total | Force Healthy |
| Customer | See kcal / note / tag on public menu | See stock or other kitchens |
| Admin `kitchens:read` | Pantry kcal | Download recipes of other tenants |

### 7.1 Super-admin gate

| # | Y/N | Delivery |
|---|-----|----------|
| 1 Kitchen-scoped | Yes | Admin → Kitchens → **Pantry** kcal |
| 2 Entitlement | No | Core trust, not a paid module |
| 3 Ops/support | Yes | Pantry column · `kitchens:read` |
| 4 Cross-tenant | Yes | Ingredient/dish queries kitchen-scoped |
| 5 Kill-switch | Yes | `dish_calories` + `dish_healthy_tag` (P50 snapshot still `dish_health`) |
| 6 Credentials | No | — |

## 8. Domain

```
Ingredient.kcal_per_100
Dish.calories_description
Computed (not stored): calories_kcal, calories_incomplete, healthy_tag, line_kcal
```

## 9. Events

| Event | Stream | Payload |
|-------|--------|---------|
| `ingredient.updated` | `ckac:catalog:ingredient` | name, kcal_per_100 |
| `ingredient.recipe.updated` | `ckac:catalog:ingredient` | dish_id, line_count, calories_kcal, healthy_tag |
| `dish.updated` | `ckac:catalog:dish` | changes including calories_description |

## 10. Database

| Change | Schema | Migration |
|--------|--------|-----------|
| `ingredients.kcal_per_100` | `ckac_catalog` | Alembic `011` |
| `dishes.calories_description` | `ckac_catalog` | Alembic `011` |

## 11. API

Existing owner ingredient/dish/recipe routes + public menu / `GET /dishes/health`. No new public prefix.

## 12. Flow

```
Owner → PATCH ingredient kcal_per_100
      → PUT dish recipe (qty × SKU kcal)
      → optional PATCH dish calories_description
Customer → GET menu → health.calories_kcal + healthy_tag + description
```

## 13. Security

- No stock in public kcal lines
- Sanitize calories_description as plain text (max 500)
- Parameterized SQL; tenant filters

## 14. Tests

| Test | File |
|------|------|
| Unit math + healthy rules | `tests/test_dish_calories.py` |
| Menu / recipe / pantry / events | `test_ingredient_health.py`, `test_ingredients.py`, `test_events.py` |
