# Dish ingredient health (customer)

**Feature:** P50 · **Service:** `services/catalog/` · **Date:** 2026-09-15

## 1. Business

Diners should see how a plate is built — a 0–100 **ingredient health score** plus each mapped SKU’s typical **benefits** and **disadvantages** — so home kitchens can prove freshness without aggregator calorie theatre.

Helps kitchens grow: trust vs restaurant menus; zero food commission preserved.

## 2. Out of scope

- Medical advice, lab nutrition facts, allergen certification, calorie counts
- Owner-authored medical copy (platform library match by name)
- UIDAI / any identity data

## 3. Flow

`Owner maps F19 recipe → catalog scores dish from pantry names × qty → public menu + GET /dishes/health → customer Health tab / dish details / order confirm`

## 4. Rules

| Rule | Layer |
|------|--------|
| Score = quantity-weighted mean of matched library scores (g/ml as-is; pcs ≈ 50 g) | domain |
| Unmapped recipe → `score=null`, ingredients empty | domain |
| Never return stock, pack cost, or other kitchens’ recipes | API |
| Copy is typical home-kitchen use, not a diagnosis | UX disclaimer |
| Kill-switch `dish_health` (default on) | `is_feature_enabled` |

## 5. Super-admin gate

| # | Applies | Delivery |
|---|---------|----------|
| 1 Kitchen-scoped | Yes | Admin → Kitchens → **Pantry** (health match on SKUs) |
| 2 Entitlement | No | Core trust, not a paid module |
| 3 Ops/support | Yes | Pantry benefits/disadvantages · `kitchens:read` |
| 4 Cross-tenant | Yes | Recipe query filtered by dish/kitchen ids |
| 5 Kill-switch | Yes | `dish_health` |
| 6 Credentials | No | — |

## 6. Events

Recipe writes already publish `ingredient.recipe.updated`. Menu cache invalidated on recipe PUT so health on `/menu` stays fresh. No extra PII streams.

## 7. UI

| Surface | What diners/ops see |
|---------|---------------------|
| Customer menu dish details | Score + benefits/disadvantages |
| Customer dashboard **Health** | Quantity-weighted plate score across ordered dishes |
| Order confirm / My orders | Plate or per-dish score |
| Owner pantry + recipe line | Read-only library match |
| Admin → Kitchens → **Pantry** | Same match for support |

Copy is typical home-kitchen use, not a diagnosis.
