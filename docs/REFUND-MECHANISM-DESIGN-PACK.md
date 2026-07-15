# Module Design Pack — Order Refunds (owner-initiated)

**Feature ID:** Refund / settlement reverse (extends F42–F44) · **Service owner:** `services/billing/` (+ `identity` payout profile) · **Sprint:** S6+ · **Date:** 2026-07-15

---

## 1. Business understanding

- **Problem:** Owners need a truthful way to return money after disputes, cancellations, or partial issues without platform commission games.
- **Vision:** Per-order refund switch (full vs partial) with two rails — payment-gateway reverse for full online captures, and owner direct UPI/bank transfer (remark = order id) with proof screenshot.
- **Business objective:** Keep trust and cash accountability; customer owns payout instruments; owner proves direct refunds.
- **Why now:** Payments/settlements exist; `refunded` status is unused; customers have no payout profile.
- **KitchCu product gate:** Yes — owners retain CRM/money relationship; no aggregator dependency for refunds.

---

## 2. Challenge & improvement

- **Assumptions challenged:** Gateway refund is not always available (COD / UPI not captured / already settled cash). Partial refunds via gateway reverse-transfers are complex — force **direct transfer** for partial.
- **Improvements:** Snapshot destination at create time from customer payout profile; require evidence before completing direct refunds; emit EDD events; mask account numbers in responses.
- **Out of scope:** Auto-debit kitchen settlements; multi-kitchen master partial saga orchestration UI; production Razorpay signature verification (dev mock kept, webhook wired).

---

## 3. Personas & user journey

| Persona | Goal | Journey |
|---------|------|---------|
| Customer | Store UPI/QR/bank for refunds | Account → payout details → save |
| Owner | Refund an order | Order detail → full/partial → gateway or direct → evidence → complete |
| Customer | See refund status | Orders / refund list |

---

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Per-order switch: full vs partial refund | Must |
| FR-2 | Full + gateway (online/UPI captured): reverse via payment gateway | Must |
| FR-3 | Full + direct OR any partial: transfer to customer UPI or bank; remark = order id | Must |
| FR-4 | Owner attaches screenshot evidence for completed direct refunds | Must |
| FR-5 | Customer dashboard: UPI id, QR/scanner image, bank account details | Must |
| FR-6 | Gateway webhook / process path updates refund + payment status | Must |

---

## 5–7. NFRs / rules / permissions

- Tenant scope: `kitchen_id` on every refund; owner JWT owns kitchen; customer reads own refunds only.
- Partial amount ∈ (0, payment.amount − already_refunded].
- COD / uncaptured payments cannot use gateway channel.
- Evidence required before `completed` for `direct_transfer`.
- Owner creates/processes; customer manages payout profile; admin N/A this sprint.

---

## 8. Domain model

```
Refund (billing) — aggregate
  kind: full | partial
  channel: gateway | direct_transfer
  status: requested | processing | completed | failed
  destination snapshot + transfer_remark (= order_code)
  evidence_url, razorpay_refund_id

Customer payout profile (identity.customers columns)
  upi_vpa, upi_qr_url, bank_*

Payment.status += partially_refunded | refunded (full)
Stream: ckac:billing:refund — refund.created | refund.completed | refund.failed
```

---

## 9. API (summary)

- `PATCH /customers/me/payout` · `POST /customers/me/payout/qr`
- `POST /billing/refunds` · `GET /billing/refunds` · `GET /billing/refunds/{id}`
- `POST /billing/refunds/{id}/evidence` · `POST /billing/refunds/{id}/complete`
- `POST /billing/refunds/{id}/process` (gateway)
- Webhook: `refund.processed` / `payment.refunded`

---

## 10. Test plan

- Schema: amount/kind/channel rules
- API: full gateway, partial direct + evidence, reject gateway partial, customer payout CRUD
- Events: refund.created / refund.completed on stream
