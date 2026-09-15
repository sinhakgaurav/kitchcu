# Owner identity (profile + live photo + Aadhaar + PAN)

**Feature:** P49 · **Service:** `services/identity/` · **Date:** 2026-09-15

## 1. Business

Kitchen owners identify themselves the same way diners do — display photo + live-capture — plus Indian government IDs. Support can match a face to Aadhaar/PAN last-4 when refunds, settlements, or kitchen activation are disputed.

Helps kitchens grow: platform trust without aggregator KYC lock-in; zero food commission preserved.

## 2. Out of scope

- UIDAI / NSDL e-KYC API (numbers + live photo only)
- Card-scan OCR
- Face-match ML

## 3. Flow

`Owner → PATCH /owners/me + POST avatar|live-photo → identity (ckac_identity.owners) → MinIO owner-{id}/… → outbox owner.updated → GET /owners/me (masked) + Admin kitchen KYC tab`

## 4. Rules

| Rule | Layer |
|------|--------|
| Aadhaar: 12 digits, first digit 2–9 | domain |
| PAN: `AAAAA9999A` | domain |
| Reads return masked IDs only (last 4 / last 5+letter) | response builder |
| Events carry flags, never ID numbers or URLs | EDD |
| Live photo requires `is_live_capture=true` | route |
| Kill-switch `owner_kyc` | `require_feature` |

## 5. Super-admin gate

| # | Applies | Delivery |
|---|---------|----------|
| 1 Kitchen-scoped | Yes | Admin → Kitchens → **KYC** tab (owner identity for that kitchen) |
| 2 Entitlement | No | Core trust, not a paid module |
| 3 Ops/support | Yes | Masked Aadhaar/PAN + photos · `kitchens:read` |
| 4 Cross-tenant | Yes | Owner-scoped; kitchen detail loads owning owner only |
| 5 Kill-switch | Yes | `owner_kyc` |
| 6 Credentials | No | IDs are PII, not platform secrets |
