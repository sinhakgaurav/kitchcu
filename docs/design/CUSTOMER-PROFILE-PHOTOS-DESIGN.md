# Customer profile + live photo

**Feature:** P48 · **Service:** `services/identity/` · **Date:** 2026-09-15

## 1. Business

Customers can set a **display photo** (gallery or camera) and a separate **live photo** (camera-only). Live photo is the diner-side counterpart of dish live-capture: kitchens and support can trust who they are refunding or handing food to.

Helps kitchens grow: fewer “wrong person / fake account” refund fights; stronger home-delivery trust without a per-order commission model.

## 2. Out of scope

- Owner CRM / order ticket showing live photo (cross-service read; defer)
- Face-match / liveness ML
- Deleting photos (replace by re-upload)

## 3. Flow

`Customer → POST /customers/me/avatar | /live-photo → identity domain → ckac_identity.customers (tenant = customer_id) → MinIO key customer-{id}/{context}/… → outbox customer.updated → GET /customers/me + Admin Customers`

## 4. Rules

| Rule | Layer |
|------|--------|
| Profile photo: JPEG/PNG/WebP, ≤10MB | upload sniff |
| Live photo: same bytes + `is_live_capture=true` required | route |
| Cannot set `live_photo_url` via PATCH JSON | domain (field omitted) |
| Events carry flags, not URLs | EDD payload |
| Kill-switch `customer_profile_photos` | `require_feature` |

## 5. Super-admin gate

| # | Applies | Delivery |
|---|---------|----------|
| 1 Kitchen-scoped | No | Customer-owned identity, not kitchen workspace |
| 2 Entitlement | No | Core account, not a paid module |
| 3 Ops/support | Yes | Admin → Customers detail photos · `customers:read` |
| 4 Cross-tenant | N/A | Customer-scoped object keys |
| 5 Kill-switch | Yes | `customer_profile_photos` |
| 6 Credentials | No | — |

## 6. Events

Stream `ckac:identity:customer` · `customer.updated` · payload `{customer_id, photo_kind, has_avatar, has_live_photo}`
