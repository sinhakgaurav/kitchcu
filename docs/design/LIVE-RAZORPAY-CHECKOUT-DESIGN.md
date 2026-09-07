# Module Design Pack — Live Razorpay Checkout (P42 / F42–F44)

**Feature ID:** F42–F44 · **Service owner:** `services/billing/` · **Sprint:** Wave A · **Author:** Platform · **Date:** 2026-09-07

---

## 1. Business understanding

- **Problem:** Customer checkout auto-captures with `pay_dev_*` ids. Pilot kitchens cannot take real prepaid.
- **Vision:** When Razorpay keys exist (kitchen Payments tab or platform API Keys), Checkout.js collects money; signature-verified capture; webhook remains backup. Demo hosts without keys keep the mock path.
- **Business objective:** Trust the money promise. Zero per-order food commission unchanged.
- **Why now:** CPO Must gap #1. Wave A item still open after P41.
- **KitchCu product gate:** Y — kitchens keep 100% of food revenue; platform is SaaS subscription.

---

## 2. Challenge & improvement

- **Assumptions challenged:** “Webhook later” is not diner-facing capture. Client-only capture without HMAC is theft.
- **Improvements:** Live vs demo is credential-driven, not `APP_ENV` alone. Capture of a live order requires `order_id|payment_id` HMAC. No Checkout if keys missing in production.
- **Out of scope:** Owner UPI dynamic QR (F43 follow-up); Razorpay Subscriptions for tiffin (F34); live Route transfers (settlements stay pending until Route API).

---

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|---------------|
| Customer | Pay prepaid | Checkout → create payment → Razorpay modal → signed capture → confirm |
| Owner | Get paid | Configure key_id/secret on Payment Gateway (or platform fallback) |
| Super-admin | Kill / configure | API Keys `razorpay_key_*`; kitchen Payments tab |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Resolve kitchen gateway keys, else platform keys | Must |
| FR-2 | Create Razorpay order; return `provider_mode=live` + public `razorpay_key_id` | Must |
| FR-3 | No keys + non-prod → existing `order_dev_*` mock | Must |
| FR-4 | No keys + prod → 400, never mock | Must |
| FR-5 | Live capture requires verified checkout signature | Must |
| FR-6 | Webhook `payment.captured` still idempotent | Must |
| FR-7 | Customer PWA opens Checkout.js when live | Must |

---

## 5. Super-admin gate

| # | Question | Y/N | Delivery |
|---|----------|-----|----------|
| 1 | Kitchen-scoped? | Y | Existing kitchen Payments tab |
| 2 | Entitlement? | Y | Existing `razorpay` module |
| 3 | Ops? | Y | Platform API Keys |
| 4 | Cross-tenant? | Y | Payment still kitchen/customer scoped |
| 5 | Kill-switch? | Y | Clear keys → no live Checkout |
| 6 | Credentials? | Y | Kitchen secrets on kitchen form; platform only under API Keys |

---

## 6. Data & events

`Customer → POST /billing/payments/customer → create Razorpay order → Checkout.js → POST …/capture {payment_id, signature} → payment.captured → order UI`

Stream: `ckac:billing:payment` (`payment.created` payload `provider_mode`: `live` \| `demo`).

---

## 7. Tests

HMAC unit tests; API live create/capture with mocked Razorpay HTTP; existing demo capture tests stay green.
