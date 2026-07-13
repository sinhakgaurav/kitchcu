# F06 Multi-Kitchen Checkout — Module Design Pack

**Feature ID:** F06 · **Service owner:** `services/order/` · **Sprint:** S8 · **Author:** Kitchcu Engineering · **Date:** 2026-07-13

## 1. Business understanding

- **Problem:** Customers currently lose their cart when they add a dish from another kitchen and must place separate checkouts.
- **Vision:** One cart groups dishes by kitchen, one checkout creates a master receipt, and every kitchen independently fulfills only its own sub-order.
- **Business objective:** Increase cross-kitchen conversion without compromising tenant isolation or owner control.
- **Why now:** F32 discovery and F33 customer history are complete; F06 is the next Phase 2 dependency before F44 settlements.
- **Kitchcu product gate:** Yes. Cross-kitchen discovery can convert into direct orders without aggregator dependency or food commission.

## 2. Challenge & improvement

- **Assumptions challenged:** A single checkout does not imply one shared fulfillment lifecycle. Each kitchen must retain its own order code, pricing snapshot, lifecycle, and visibility.
- **Improvements over raw requirement:** Atomic master/sub-order creation, server-side price and active-dish validation, customer ownership checks, and idempotent checkout.
- **Out of scope:** Razorpay Route transfers, settlements, linked-account KYC, partial refunds, and online multi-kitchen capture. Those belong to F44/S9.
- **Safety boundary:** Until F44 is implemented, multi-kitchen checkout accepts COD only. Online/UPI cannot be represented as a truthful production flow without split settlement, so the API rejects those methods for two or more kitchens.

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| Customer | Buy from multiple kitchens without rebuilding carts | Discover → add dishes from kitchens → grouped cart → COD checkout → master receipt → track each sub-order |
| Kitchen owner | Fulfill only their portion | Receive normal `order.placed` → view own sub-order → update independent lifecycle |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Cart preserves and groups active dishes from multiple kitchens | Must |
| FR-2 | Checkout atomically creates one master order and one sub-order per kitchen | Must |
| FR-3 | Each sub-order keeps `{kitchen_code}-{bill_id}` and independent lifecycle | Must |
| FR-4 | Master receipt returns all sub-orders and aggregate totals | Must |
| FR-5 | Owners can only read their existing kitchen-scoped order endpoints | Must |
| FR-6 | Duplicate checkout keys return the original master order | Must |
| FR-7 | Multi-kitchen online/UPI is rejected until F44 | Must |

## 5. Non-functional requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Write latency p95 | < 500 ms excluding external payment |
| NFR-2 | Atomicity | Master and all sub-orders commit or roll back together |
| NFR-3 | Tenant isolation | No owner API exposes master totals or other kitchens |
| NFR-4 | Idempotency | Unique customer + idempotency key |
| NFR-5 | Pricing integrity | Ignore client prices; snapshot active catalog prices server-side |

## 6. Business rules & validation

| Rule | Enforcement layer |
|------|-------------------|
| Two or more distinct kitchens for master checkout | Pydantic/domain |
| One group per kitchen; at least one item per group | Pydantic |
| Dish must be active and belong to its group kitchen | Domain query |
| Quantity must be positive | Pydantic |
| Aggregate total equals sub-order totals | Domain + DB transaction |
| Multi-kitchen method is COD until F44 | Pydantic/domain |
| Idempotency key cannot create a different second order | DB unique constraint + domain lookup |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Owner | Read/update their sub-order | Read master receipt or another kitchen's sub-order |
| Customer | Create/read their master order and sub-orders | Read another customer's master order |
| Admin | Existing platform capabilities only | Impersonate checkout |

## 8. Domain model & bounded context

```text
Aggregate: MasterOrder (order bounded context)
  Entities: MasterOrder, Order (sub-order), OrderItem
  Value objects: MasterOrderCode, IdempotencyKey, Money
  Invariants:
    - master has at least two distinct kitchen sub-orders
    - every sub-order belongs to exactly one master
    - master totals equal the sum of immutable sub-order price snapshots
    - sub-order lifecycle remains independent
```

`master_orders` belongs to `ckac_orders`; no cross-service write is needed. Billing will reference `master_order_id` in S9.

## 9. Events

| Event | Producer | Stream | Subscribers | Idempotency key |
|-------|----------|--------|-------------|-----------------|
| `master_order.created` | order | `ckac:orders:master_order` | billing (S9), notification | event UUID / master ID |
| `order.placed` | order | `ckac:orders:order` | notification, analytics | event UUID / sub-order ID |

Both are written through the transactional outbox in the same transaction as the aggregate.

## 10. Database

| Table | Schema | Indexes | Migration |
|-------|--------|---------|-----------|
| `master_orders` | `ckac_orders` | unique code; unique `(customer_id, idempotency_key)`; `(customer_id, created_at DESC)` | Alembic `003_master_orders` |
| `orders` | `ckac_orders` | index `master_order_id` + FK to master | Alembic `003_master_orders` |

Financial values use `NUMERIC(12,2)`. The master stores customer ownership, aggregate totals, method, status, currency, and audit timestamps. Existing orders keep their kitchen-scoped fields.

## 11. API contracts

| Method | Path | Auth | Request | Response | Errors |
|--------|------|------|---------|----------|--------|
| POST | `/api/v1/customers/me/master-orders` | Customer JWT + `Idempotency-Key` | kitchen groups, delivery options, `payment_method=cod` | master receipt with sub-orders | 400, 401, 409, 422 |
| GET | `/api/v1/customers/me/master-orders/{id}` | Customer JWT | — | owned master receipt | 401, 404 |

OpenAPI updated: Yes, through FastAPI schemas.

## 12. Workflow & notifications

```text
1. Customer submits grouped cart and idempotency key.
2. Order service resolves customer profile and checks an existing key.
3. It validates every kitchen/dish and snapshots current prices.
4. It creates master order, N sub-orders, items, and initial status events.
5. It writes N `order.placed` events and one `master_order.created` event to the outbox.
6. One transaction commits; the gateway returns the master receipt.
7. Each owner sees only the normal sub-order in their kitchen order list.
```

Existing order notifications consume each `order.placed`; no new customer channel is added in S8.

## 13. Analytics & reports

| Question answered | Metric | Storage |
|-------------------|--------|---------|
| How often do customers cross-shop? | master order count and kitchens per master | `ckac_orders.master_orders` + linked orders |
| What revenue belongs to an owner? | existing sub-order totals only | `ckac_orders.orders` |

Master totals must not be added to owner revenue, avoiding double counting.

## 14. Edge cases · failures · recovery

| Case | Behavior | Recovery |
|------|----------|----------|
| Duplicate request | Return original master receipt | Client may safely retry |
| Inactive/missing dish | Reject entire checkout before commit | Customer refreshes menu/cart |
| One kitchen group | Reject master endpoint; use existing single-kitchen checkout | Frontend routes correctly |
| Same kitchen repeated | Validation error | Client groups lines |
| Any DB/event write fails | Roll back master and all sub-orders | Retry same idempotency key |
| Online/UPI selected | Reject until F44 | Customer uses COD or waits for S9 |

## 15. Security & privacy

- **PII fields:** Customer name and phone already required for fulfillment; never log them.
- **OWASP considerations:** Pydantic UUID/quantity validation, parameterized SQLAlchemy queries, JWT type enforcement, object ownership query on GET.
- **Audit log needed:** Domain events and status events provide the S8 audit trail.

## 16. Test plan

| Test | Type | File |
|------|------|------|
| Requires customer JWT and idempotency key | API/security | `services/order/tests/test_master_orders.py` |
| Creates grouped sub-orders and aggregate receipt | API | `services/order/tests/test_master_orders.py` |
| Revalidates current prices and active dishes | API/domain | `services/order/tests/test_master_orders.py` |
| Duplicate key returns same aggregate | API | `services/order/tests/test_master_orders.py` |
| Rejects duplicate/one kitchen and online method | schema/API | `services/order/tests/test_master_orders.py` |
| Other customer cannot read receipt | security | `services/order/tests/test_master_orders.py` |
| Emits master and sub-order events | event | `services/order/tests/test_events.py` |
| Frontend production build | build | `apps/website/` |

### BDD scenarios

```text
Scenario: Atomic multi-kitchen COD checkout
  Given an authenticated customer has active dishes from two kitchens
  When they submit one grouped checkout with an idempotency key
  Then one master receipt and two independently trackable kitchen orders are created
  And retrying the same request returns the same master receipt

Scenario: One invalid kitchen group
  Given one cart dish became inactive
  When the customer checks out
  Then no master order or sub-order is persisted
```

**Acceptance criteria (from benchmark):**

- [x] Design groups cart items by kitchen.
- [x] Design preserves separate order codes and lifecycle.
- [x] Design exposes a customer-owned master receipt while preserving owner isolation.
- [ ] F44 split settlement and one online payment (S9 dependency).

## 17. Implementation plan

| Step | Task | Estimate |
|------|------|----------|
| 1 | RED tests for contracts, atomicity, ownership, events, idempotency | S8 |
| 2 | Alembic migration and SQLAlchemy models | S8 |
| 3 | Domain schemas/functions and routes | S8 |
| 4 | Multi-kitchen cart, grouped checkout, master receipt UI | S8 |
| 5 | Targeted tests, frontend build, full `run-tests.ps1` | S8 |

## 18. Future AI & expansion

- **AI enhancement:** None required; checkout correctness must remain deterministic.
- **Service split trigger:** Extract checkout saga coordinator only when external payment/settlement workflow or deployment ownership requires it.

## Approval

- [x] CPO acceptance criteria matched within the explicit S8/S9 dependency boundary.
- [x] CTO architecture/events reviewed against order-service ownership and outbox rules.
- [x] DBA schema reviewed for UUIDs, indexes, numeric money, and ownership.
- [x] QA test plan covers atomicity, idempotency, security, and failure recovery.
