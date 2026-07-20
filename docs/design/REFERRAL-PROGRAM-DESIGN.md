# Referral Program — Design Pack (P20)

**Feature:** Dual referral leads + configurable INR credits · **Owner:** identity (+ billing apply) · **Date:** 2026-07-20

## 1. Business
- **Problem:** Grow kitchen + customer acquisition without paid ads.
- **Gate:** Helps kitchens grow via trusted intros; rewards both sides with subscription credit.
- **Model:** Lead referral (not invite codes). Credits are platform INR balances.

## 2. Programs
| Direction | Referrer | Lead payload | Reward when | Credit to |
|-----------|----------|--------------|-------------|-----------|
| customer→kitchen | Customer | Kitchen name, contacts, city, address | Kitchen onboards (phone match) | Customer credit (₹ configurable, default 10) |
| kitchen→customer | Kitchen owner | Customer name, phone, email | Customer onboards **or** first order | Owner credit applied to SaaS subscription |

## 3. Schema (`ckac_identity`)
- `referral_settings` — singleton rewards + enabled
- `referral_leads` — direction, referrer ids, contact fields, status, match ids
- `referral_credits` — holder_type/holder_id balance
- `referral_credit_ledger` — audit trail

## 4. Events
`ckac:identity:referral` — `referral.lead_submitted`, `referral.rewarded`, `referral.credit_applied`

## 5. Bulk
CSV templates (Excel-compatible UTF-8 BOM). Upload max 200 rows. Multi-row form in UI.

## 6. Admin
Configure rewards; list/filter leads; reject/manual grant.
