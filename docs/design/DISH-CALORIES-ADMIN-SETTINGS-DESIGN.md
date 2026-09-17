# Super-admin dish calories + Healthy settings (P54)

**Feature:** P54 (extends P53) · **Services:** `services/identity/`, `services/catalog/` · **Date:** 2026-09-16

## 1. Business understanding

- **Problem:** P53 shipped calories and an automatic **Healthy** tag with a hardcoded 500 kcal cap and a shared `dish_health` kill-switch. Ops cannot turn calories or the badge off independently, or change what “light enough” means, without a deploy.
- **Vision:** Super Admin Control owns public calories, the Healthy badge, and the kcal cap used to award it.
- **Business objective:** Trust settings stay platform-owned; zero food commission preserved.
- **Why now:** P53 is live; ops asked to enable/disable and to configure Healthy from calories.
- **KitchCu product gate:** Yes — honest plate math is a kitchen growth trust feature, gated by Control.

## 2. Challenge & improvement

- **Assumptions challenged:** “500 kcal is the Healthy rule forever” and “one flag covers health score + kcal.”
- **Improvements:** Separate public kill-switches; Healthy kcal cap is a Control integer (default 500). Score floor stays (default 65) so greenwashing still needs a complete map + light plate + decent P50 score.
- **Out of scope:** Lab/FSSAI labels, medical claims, owner-forced Healthy, per-kitchen kcal caps, package entitlements.

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|----------------|
| Super-admin | Kill or retune Healthy | Control → Dish calories & Healthy → ON/OFF + max kcal → Save |
| Customer | See honest public plates | Menu shows kcal / Healthy only when those flags are on; tag uses the live cap |
| Owner | Keep mapping pantry | Pantry kcal still stored; recipe running total uses the same cap as public Healthy |
| Support | Explain a missing badge | Control cap + complete map + score floor; Admin Kitchens → Pantry |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Flag `dish_calories` (default on) hides public kcal / line kcal / calories note | Must |
| FR-2 | Flag `dish_healthy_tag` (default on) hides public Healthy; kcal may still show | Must |
| FR-3 | Calories off also hides public Healthy (badge is calories-based) | Must |
| FR-4 | `healthy_max_kcal` 50–5000, default 500, used by catalog Healthy rule | Must |
| FR-5 | `healthy_min_score` 0–100, default 65 (same panel, not the primary knob) | Must |
| FR-6 | Owner recipe GET still returns computed kcal/tag + the live cap (prep, not a public surface) | Must |
| FR-7 | Pantry writes still stored when flags are off | Must |

## 5. Non-functional

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Load flags + cap once per `snapshots_for_dishes` | no N+1 |
| NFR-2 | Tenant isolation | unchanged kitchen-scoped recipes |
| NFR-3 | Copy | Kitchen estimate — not a lab/medical claim |

## 6. Business rules

| Rule | Layer |
|------|--------|
| Healthy = complete map AND kcal ≤ `healthy_max_kcal` AND score ≥ `healthy_min_score` | domain |
| Missing settings row → 500 / 65 | `ckac_common.platform_config` |
| `dish_health` off still omits the whole public snapshot (P50) | existing |
| Owners cannot pin Healthy | unchanged |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Super-admin `flags:read` | GET Control calories/Healthy | — |
| Super-admin `flags:write` | PATCH flags + kcal cap; audited | — |
| Owner | Pantry kcal + recipe math | Change platform cap or force Healthy |
| Customer | See public kcal/tag when flags on | See other kitchens’ recipes |

### 7.1 Super-admin gate

| # | Y/N | Delivery |
|---|-----|----------|
| 1 Kitchen-scoped | Yes | Existing Admin → Kitchens → **Pantry**; this increment is **Control** (platform) |
| 2 Entitlement | No | Core trust, not a paid module |
| 3 Ops/support | Yes | `GET/PATCH /admin/healthy-food` + Control panel; `flags:read` / `flags:write` |
| 4 Cross-tenant | Yes | Singleton platform row; catalog queries stay `kitchen_id` scoped |
| 5 Kill-switch | Yes | `dish_calories`, `dish_healthy_tag` (P50 remains `dish_health`) |
| 6 Credentials | No | — |

## 8. Domain

```
ckac_identity.feature_flags.dish_calories
ckac_identity.feature_flags.dish_healthy_tag
ckac_identity.healthy_food_settings (id=1) healthy_max_kcal, healthy_min_score
Computed Healthy uses those integers — not stored on the dish
```

## 9. Events / audit

| Write | Stream / audit |
|-------|----------------|
| PATCH healthy-food | Admin audit `healthy_food.updated` (flags + numbers) |
| Recipe still publishes `ingredient.recipe.updated` with computed tag | existing catalog EDD |

No new Redis stream — Control matches feature-flag / rate-limit audit, not a kitchen aggregate.

## 10. Database

| Change | Schema | Migration |
|--------|--------|-----------|
| Flags + singleton settings | `ckac_identity` | Alembic `029` |

## 11. API

- `GET/PATCH /api/v1/admin/healthy-food` (identity, gateway `/admin` prefix)
- Existing catalog menu / health / recipe routes honor flags + cap

## 12. Flow

```
Super-admin → PATCH healthy_max_kcal / flags
Catalog menu → snapshots_for_dishes loads flags+cap once → public kcal/tag
Owner recipe → same cap for automatic Healthy preview
```

## 13. Security

- Admin JWT + `flags:read`/`flags:write`
- No PII; numbers only
- Parameterized SQL; no cross-tenant lists

## 14. Tests

| Test | File |
|------|------|
| Identity GET/PATCH + validation + flags | `services/identity/tests/test_healthy_food_settings.py` |
| Unit Healthy respects `max_kcal` | `services/catalog/tests/test_dish_calories.py` |
| Menu kill-switch + live cap | `services/catalog/tests/test_ingredient_health.py` |
| Gateway prefix | `services/gateway/tests/test_gateway.py` |
