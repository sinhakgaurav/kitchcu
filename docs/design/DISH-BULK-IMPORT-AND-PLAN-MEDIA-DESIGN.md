# Design pack — Dish bulk Excel import · Recipe cover · Tiffin dish rules

**Status:** Retroactive compliance pack (shipped `f56d369`; this document locks acceptance, NFRs, EDD, admin gate).  
**Feature IDs:** Catalog bulk (menu ops) · F23 cover · F34/F35 dish selection rules  
**Services:** `catalog` · `community` · `marketing`  
**Date:** 2026-07-20 · **Author:** founding eng staff

---

## 1. Business understanding

| | |
|--|--|
| **Problem** | Owners with 20–100 dishes cannot key each row + hero in the PWA; community recipes lack a cover; tiffin “combo vs single dish pack” was UI-only. |
| **Vision** | Excel-first menu onboarding with mapped photos; shareable recipe covers; server-enforced plan composition. |
| **Business objective** | Faster kitchen go-live → same-day menu → orders without aggregator dependency. |
| **Why now** | Wave 2 QA gap; owners blocked on day-1 menu volume. |
| **Product gate** | **Y** — reduces time-to-menu; preserves truth-in-media (bulk heroes never go live as stock). |

---

## 2. Challenge & improvement

- **Challenged:** “Gallery bulk heroes can be active” — rejected; inactive drafts only until live-capture.
- **Improvement:** Sample `.xlsx` with fixed headers + `image_filename` map + ZIP/multi-image upload; combo ≥2 / single_dish = 1 enforced in marketing domain.
- **Out of scope:** Razorpay recurring for tiffin; async job queue for >100 rows; AI auto-tag cuisine; admin bulk-for-kitchen UI (owner path only).

---

## 3. Personas & journey

| Persona | Goal | Steps |
|---------|------|-------|
| Owner | Import menu | Add dish → Bulk → download template → fill → upload sheet + images → Menu → live-capture → activate |
| Owner | Share recipe | Community → cover live/gallery + body → share |
| Owner | Monthly pack | Tiffin → Combo (2+ dishes) or Single dish pack (1) → publish |
| Customer | Trust | Never sees bulk gallery as “live” hero on active menu |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | `GET …/dishes/bulk/template.xlsx` — predefined columns + samples + readme | Must |
| FR-2 | `POST …/dishes/bulk` — spreadsheet + `images[]` and/or `images_zip`; map via `image_filename` | Must |
| FR-3 | Cap 100 rows / 100 images; reject unknown cuisine/category slug | Must |
| FR-4 | Bulk creates `is_active=false`; gallery media `is_live_capture=false` | Must |
| FR-5 | Each accepted row emits `dish.created` (same as single create) | Must |
| FR-6 | Community `cover_url` on share + list; migration `002` | Must |
| FR-7 | `validate_plan_dish_selection`: combo ≥2, single_dish =1, thali/tiffin ≥1 | Must |

---

## 5. Non-functional

| ID | Target |
|----|--------|
| NFR-1 | Bulk p95 &lt; 15s for 50 rows + images (local MinIO) |
| NFR-2 | Tenant isolation: owner JWT + `verify_kitchen_owner` |
| NFR-3 | Memory: entire ZIP/sheet in request — hard caps; no unbounded lists |
| NFR-4 | Horizontal scale: stateless catalog; no global cache for import |

---

## 6. Business rules

| Rule | Layer |
|------|--------|
| Active dish requires live-capture hero | Pydantic `DishCreateRequest` + `create_dish` |
| Bulk always inactive | Domain `import_dishes_bulk` |
| `image_filename` must match uploaded basename (case-insensitive) | Domain |
| Combo / single_dish dish counts | `validate_plan_dish_selection` |

---

## 7. Permissions & super-admin gate

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | Template, bulk import, community cover, tiffin plans | Cross-kitchen |
| Customer | — | Bulk / cover write |
| Admin | Existing tiffin pending accept/deny | No bulk-import-as-kitchen (deferred) |

| # | Gate | Y/N | Delivery |
|---|------|-----|----------|
| 1 | Kitchen-scoped | Y | Owner APIs; admin tiffin already on kitchen panel |
| 2 | Entitlement | N for bulk; tiffin already module-gated | — |
| 3 | Ops override | Partial | Admin tiffin accept/deny only |
| 4 | Kill-switch | N | Reserved: future `catalog.bulk_import` module flag |
| 5 | Credentials | N | — |

---

## 8. Domain

```
Catalog: Dish + DishMedia (optional media on inactive draft)
Community: SharedRecipe.cover_url
Marketing: SubscriptionPlan.dishes_config.dish_ids + plan_type rules
```

---

## 9. Events

| Event | Producer | Stream | Payload notes |
|-------|----------|--------|---------------|
| `dish.created` | catalog | `ckac:catalog:dish` | Per bulk row (kitchen_id, dish_id, name, flags) |
| `recipe.shared` | community | `ckac:community:recipe` | + `cover_url` when set |
| `subscription.plan.created` | marketing | `ckac:marketing:subscription` | plan_type + price |

---

## 10. Database

| Change | Schema | Migration |
|--------|--------|-----------|
| `shared_recipes.cover_url` | `ckac_community` | `002_recipe_cover_url` |
| Dish bulk | none (uses dishes/media) | — |
| Tiffin rules | none (JSONB + validators) | — |

---

## 11. API

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/kitchens/{id}/dishes/bulk/template.xlsx` | Owner |
| POST | `/api/v1/kitchens/{id}/dishes/bulk` | Owner multipart |
| POST | `/api/v1/kitchens/{id}/community/recipes` | Owner (+ optional `cover_url`) |
| POST/PATCH | `/api/v1/kitchens/{id}/subscription-plans` | Owner (dish count rules) |

Gateway: `/dishes` → catalog (unchanged marker).

Excel columns:  
`name, cuisine_slug, category_slug, price, prep_time_min, delivery_time_min, max_time_min, description, ingredients_description, quality_measures, is_featured, is_chefs_special, is_unique_recipe, image_filename`

---

## 12. Workflow

```
Owner → template.xlsx → fill + name photos → POST bulk
  → store images → create_dish×N (inactive) → dish.created×N → invalidate menu cache
  → Menu → LiveCapturePhotoField → activate
```

---

## 14. Edge cases

| Case | Behavior |
|------|----------|
| Missing image for `image_filename` | Row rejected; others continue |
| Unused uploaded images | Listed in `images_unused` |
| Re-import same names | New dishes (no dedupe) — owner deactivates dupes |
| Active create without live hero | 422/400 truth-in-media |

---

## 15. Security

- Owner JWT only; no PII in bulk sheet (dish data).
- Magic-byte image sniff; 10MB/file; MIME allow-list JPEG/PNG/WebP.
- Excel via openpyxl (no macros executed).

---

## 16. Test plan

| Test | File |
|------|------|
| Template headers + sample | `catalog/tests/test_dish_bulk.py` |
| Image map + ZIP | same |
| Bulk emits `dish.created` | `catalog/tests/test_events.py` |
| Cover on share + event payload | `community/tests/test_community.py` + `test_events.py` |
| Combo/single validators | `marketing/tests/unit/test_subscriptions_unit.py` + API |
| Full suite | `scripts/run-tests.ps1` |

### BDD

```
Scenario: Bulk import with mapped photo
  Given an owner JWT and a filled template with image_filename=paneer.jpg
  And paneer.jpg uploaded in the same request
  When POST /dishes/bulk
  Then one inactive dish is created with non-live hero
  And dish.created is on ckac:catalog:dish
```

---

## 17. Implementation (done)

1. `services/catalog/app/dish_bulk.py` + routes + openpyxl dep  
2. `DishCreateRequest.media` optional when inactive  
3. Community migration `002` + UI cover  
4. `validate_plan_dish_selection` + owner UX  
5. This pack + event asserts + AGENTS.md  

**Deps:** rebuild catalog container after pull (`openpyxl`).
