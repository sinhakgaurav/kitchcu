# kitchCU — Public API Reference

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Base URL | Gateway `http://localhost:18000` (or same-origin `/api` via PWAs) |
| Prefix | `/api/v1` |
| Live explorer | Portal [`/openapi`](http://localhost:13000/openapi) · Gateway [`/docs`](http://localhost:18000/docs) · [`/redoc`](http://localhost:18000/redoc) |
| Spec JSON | [`/openapi.json`](http://localhost:18000/openapi.json) (aggregated from all domain services) |
| Error shape | `{"detail": "<message>"}` — never OTP, tokens, or full PII |

> **Source of truth for field-level docs** is each service’s FastAPI/Pydantic OpenAPI (Field descriptions, route `summary`/`description`/`responses`). This file is the human index and auth cheat-sheet.

---

## 1. Authentication

| Caller | How to get a token | Header |
|--------|--------------------|--------|
| **Owner** | `POST /api/v1/auth/otp/request` → `POST /api/v1/auth/otp/verify` | `Authorization: Bearer <jwt>` (`type: owner`) |
| **Customer** | WhatsApp OTP or OAuth via `/api/v1/customers/...` | `Authorization: Bearer <jwt>` (`type: customer`) |
| **Admin** | `POST /api/v1/admin/auth/login` | `Authorization: Bearer <jwt>` (`type: admin`) |
| **Internal** | Service-to-service only | `X-Internal-Key: <INTERNAL_API_KEY>` |

**Dev OTP:** always `123456` for owner/customer WhatsApp OTP when `APP_ENV=development`.

---

## 2. Conventions

| Topic | Rule |
|-------|------|
| Versioning | All public paths under `/api/v1/` |
| Tenant | Kitchen-scoped resources include `{kitchen_id}`; ownership checked against JWT |
| Money | Amounts are floats in INR unless noted; **no per-order food commission** |
| Media | Dish **hero** images must be live-capture (`is_live_capture: true`) |
| Status machine | `received → accepted → preparing → ready → out_for_delivery → delivered \| cancelled` |
| Order total | `total = subtotal + delivery_fee` |
| Idempotency | Prefer `Idempotency-Key` on payments when calling from clients (when implemented on route) |

---

## 3. Quick start examples

### 3.1 Owner register → OTP → JWT

**Request** `POST /api/v1/owners/register`

```json
{
  "phone": "9876543210",
  "name": "Raj Sharma",
  "email": "raj@example.com"
}
```

**Response `201`** — `OwnerResponse`

```json
{
  "id": "…",
  "phone": "+919876543210",
  "name": "Raj Sharma",
  "email": "raj@example.com",
  "subscription_tier": "starter",
  "subscription_status": "trial"
}
```

**Request** `POST /api/v1/auth/otp/verify`

```json
{ "phone": "9876543210", "otp": "123456" }
```

**Response `200`** — `TokenResponse`

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 28800
}
```

**Errors:** `401` invalid OTP · `404` owner not registered · `422` validation

---

### 3.2 Delivery fee quote (before checkout)

**Request** `POST /api/v1/delivery/quote`

```json
{
  "kitchen_id": "…",
  "latitude": 18.5362,
  "longitude": 73.8958,
  "subtotal": 350
}
```

**Response `200`** — `DeliveryQuoteResponse`

```json
{
  "kitchen_id": "…",
  "distance_km": 2.4,
  "fee": 0,
  "status": "ok",
  "within_free_radius": true,
  "free_delivery_radius_km": 3,
  "max_delivery_radius_km": 10,
  "breakdown": { "rule": "within_free_radius" },
  "quote_id": "…"
}
```

`status` may be `ok` or `out_of_range`. Fee rules: free inside `free_delivery_radius_km`, then per-km + optional flat beyond, capped by `max_delivery_radius_km`.

---

### 3.3 Customer single-kitchen order

**Auth:** Customer JWT  

**Request** `POST /api/v1/kitchens/{kitchen_id}/orders/customer`

```json
{
  "items": [{ "dish_id": "…", "quantity": 2, "special_instructions": "Less spicy" }],
  "delivery_type": "delivery",
  "payment_method": "online",
  "delivery_fee": 20,
  "delivery_fee_accepted": true,
  "distance_km": 4.1,
  "customer_latitude": 18.54,
  "customer_longitude": 73.89
}
```

**Response `201`** — `OrderResponse` (includes `order_code`, `status: received`, `items[]`, `tracking_token` when delivery)

Then create/capture payment under `/api/v1/billing/payments/customer…`.

---

### 3.4 Multi-kitchen master order

**Request** `POST /api/v1/customers/me/master-orders`

```json
{
  "payment_method": "online",
  "groups": [
    {
      "kitchen_id": "…",
      "items": [{ "dish_id": "…", "quantity": 1 }],
      "delivery_type": "delivery",
      "delivery_fee": 15,
      "delivery_fee_accepted": true
    },
    {
      "kitchen_id": "…",
      "items": [{ "dish_id": "…", "quantity": 1 }],
      "delivery_type": "pickup",
      "delivery_fee": 0
    }
  ]
}
```

**Response `201`** — `MasterOrderResponse` with sub-orders. Capture via  
`POST /api/v1/billing/payments/customer/master` → `…/master/{payment_id}/capture` (Route settlements per kitchen).

---

## 4. Domain map (tags in OpenAPI)

Gateway aggregation prefixes service name (e.g. `Identity: Auth`, `Order: Customer Checkout`).

| Service | Example tags | Owns |
|---------|--------------|------|
| Identity | Auth, Owners, Kitchens, Discovery, Customer Auth, Admin, Employees | OTP/JWT, kitchens, nearby, admin RBAC |
| Catalog | Menu, Dishes, Ingredients, Media | Live-capture menu, stock recipes |
| Order | Owner Orders, Customer Checkout, Master Orders, Analytics, Bills | Lifecycle, PDFs |
| Billing | Payments, Settlements, Subscriptions, GST, Refunds, Packages | Money + tax + package mapper |
| Delivery | Delivery | Quotes + public tracking |
| Marketing | CRM, Coupons, Promotions, Templates | Owner CRM + WA/email templates |
| Ratings | Ratings, Suggestions | Verified home-taste |
| Growth | Suggestions, Combos, Patterns, Daily Menu | Growth cards |
| Notification | WhatsApp, Support Chat, Support Tickets | Webhooks + tickets |
| Learning | Curated Recipes, Dish Trials | Skill portal |
| Community | Community Recipes, Rewards, Chef Rankings | Rankings |
| Streaming | Live Streaming | LiveKit + per-dish showcase phases |

---

## 5. Common HTTP errors

| Code | When |
|------|------|
| `400` | Business rule (e.g. invalid status transition, delivery out of range) |
| `401` | Missing/invalid JWT or OTP |
| `403` | JWT valid but not owner of `{kitchen_id}` |
| `404` | Resource missing |
| `409` | Duplicate (e.g. phone already registered) |
| `422` | Pydantic validation (wrong types / missing required fields) |
| `503` | Gateway cannot reach upstream service |

Body always: `{"detail": "…"}`.

---

## 6. Regenerating / viewing docs

```powershell
docker compose up -d
# Swagger (aggregated):
start http://localhost:18000/docs
# Portal explorer (same schema via proxy):
start http://localhost:13000/openapi
# Force refresh aggregate cache after route changes:
curl "http://localhost:18000/openapi.json?refresh=true"
```

After editing routes/schemas, restart the touched service container so FastAPI reloads its `/openapi.json`; then refresh the gateway cache as above.
