# Module Design Pack — Order CSV + parse match-rate (P43 / F05 / F01)

**Feature ID:** F05 (CSV) · F01 (parse rate) · **Service owner:** `services/order/` (+ identity admin) · **Sprint:** Wave A first-party · **Author:** Platform · **Date:** 2026-09-07

---

## 1. Business understanding

- **Problem:** Owners cannot take order history to a CA. WhatsApp parse quality is unmeasured, so we cannot prove the 60%/85% match-rate promise.
- **Vision:** Accountant downloads CSV with current inbox filters. Owner and support see “8 of 10 lines mapped” from stored drafts — no Meta API.
- **Business objective:** Close first-party Must gaps without waiting on Razorpay / Meta / Porter.
- **Why now:** CPO board Must rows F05 + F01. Independent of third-party APIs.
- **KitchCu product gate:** Y — owners keep the ledger; ops can troubleshoot parse quality per kitchen.

---

## 2. Challenge & improvement

- **Assumptions challenged:** “Export later” leaves accountants in the PWA. Parse rate is not a new ML model — drafts already store `parsed_items` / `unmatched_lines`.
- **Improvements:** Same filters as `GET …/orders`. Hard cap 10,000 rows (narrow dates) so the export path survives 100k-session kitchens. Match rate = matched lines / total parsed lines over `days` (default 30, max 90), including confirmed drafts.
- **Out of scope:** Redis today’s-orders cache; full history pagination; kitchen staff; live Razorpay; Meta parse improvements; F40 event menus.

---

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| Owner | CA / GST pack | Orders → filters → Export CSV |
| Owner | WhatsApp trust | Orders drafts tab → match-rate KPI |
| Super-admin | Support | Kitchen → Orders → CSV + parse-stats |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | `GET /kitchens/{id}/orders/export.csv` owner JWT, same filters as list | Must |
| FR-2 | Cap 10,000 rows; `400` if more — ask to narrow dates | Must |
| FR-3 | CSV: order_code, created_at, status, source, customer, items, totals, payment | Must |
| FR-4 | `GET /kitchens/{id}/orders/drafts/parse-stats?days=` | Must |
| FR-5 | Admin kitchen CSV + parse-stats (`kitchens:read`) | Must |
| FR-6 | Tenant isolation; 401 without JWT | Must |

---

## 5. Super-admin gate

| # | Question | Y/N | Delivery |
|---|----------|-----|----------|
| 1 | Kitchen-scoped? | Y | Admin → Kitchens → Orders: CSV + parse-stats |
| 2 | Entitlement? | N | Existing orders / WhatsApp modules |
| 3 | Ops? | Y | `kitchens:read`; identity admin routes |
| 4 | Cross-tenant? | Y | `kitchen_id` on every query |
| 5 | Kill-switch? | N | Not a monetized flag |
| 6 | Credentials? | N | No new secrets |

---

## 6. Data & events

`Owner → GET export.csv → list_kitchen_orders + items join → CSV bytes`  
`Owner → GET parse-stats → order_drafts (all statuses in window) → match_rate`

No new writes → no new events.

CSV columns (owner and admin identical):  
`order_code,created_at,status,source,customer_name,customer_phone,items,subtotal,delivery_fee,discount_amount,total,payment_method,delivery_type`

---

## 7. Tests

Owner: 401, 403 other kitchen, filter rows, header/items, cap message.  
Parse-stats: mixed matched/unmatched JSON fixtures, window.  
Admin: kitchen-scoped CSV + stats, `kitchens:read`.
