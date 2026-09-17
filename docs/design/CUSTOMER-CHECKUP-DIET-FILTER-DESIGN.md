# Customer checkup diet filter (P52)

**Feature:** P52 · **Service:** `services/identity/` · **Date:** 2026-09-15

## 1. Business understanding

- **Problem:** Diners with lab/checkup notes still browse every sweet, fried, or high-salt plate. They want a private way to upload a latest report and, if they opt in, see only kitchens that actually cook food they can have.
- **Vision:** Trust-first discovery — report text is parsed with an in-process ML classifier + lab rules, then mapped onto F19 recipes / dish names. Zero food commission preserved.
- **Business objective:** More confident first orders from health-conscious households without turning kitchCU into a clinic.
- **Why now:** P50 already scores plates from recipes; this reuses that catalog as a compatibility index.
- **KitchCu product gate:** Yes — home kitchens win when the diner can trust the menu against their own report.

## 2. Challenge & improvement

- **Assumptions challenged:** “Upload a PDF and magically diagnose.” We parse **text** (text PDFs + optional notes). Photos without readable text are rejected unless the diner adds a short summary. Copy is **not** medical advice.
- **Improvements:** Opt-in filter (ask after parse). Rank remaining kitchens by how many compatible dishes they serve (“better for this report”). Admin sees structured conditions, never the file.
- **Out of scope:** Diagnosis, prescriptions, allergen certification, UIDAI, selling reports, per-order commission, restaurant calorie theatre, silent OCR hallucination.

## 3. Personas & user journey

| Persona | Goal | Journey steps |
|---------|------|----------------|
| Customer | Only see plates they can have | Home **As per my report** (or Health → upload → Yes) → nearby lists only kitchens that cook matching food/variety |
| Customer | Browse everyone | Filter **All kitchens** (or Health No) → normal nearby list |
| Support | Troubleshoot empty discovery | Admin → Customers → diet conditions + filter on/off (no PDF) |
| Super-admin | Kill feature | Control → `customer_diet_report` |

## 4. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Authenticated customer uploads latest checkup (PDF / JPEG / PNG / WebP) | Must |
| FR-2 | In-process ML (+ lab thresholds) builds a diet profile | Must |
| FR-3 | After parse, ask whether to show only compatible food | Must |
| FR-4 | If yes, nearby / discovery / menu show only matching dishes/kitchens; better kitchens ranked first | Must |
| FR-5 | Kill-switch `customer_diet_report` | Must |
| FR-6 | Admin Customers: structured summary, not the file | Must |
| FR-7 | Customer discovery/nearby/menu control **As per my report** — select matching food (and preferred variety when the profile has one); only kitchens that cook that food stay listed | Must |

## 5. Non-functional

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Compatibility for ≤100 nearby kitchens | One catalog query, not N+1 |
| NFR-2 | Tenant / customer isolation | Profile keyed by `customer.id` only |
| NFR-3 | PHI | Never log report text, OTP, or file URLs; events carry conditions only |

## 6. Business rules

| Rule | Layer |
|------|--------|
| Conservative exclude (category / name token / ingredient). Unmapped dish still matched on name + category | domain |
| Filter applies only when `diet_filter_enabled` and flag on | API |
| Empty extractable text → 422 (ask for text PDF or notes) | API |
| Disclaimer on every profile | domain + UX |

## 7. Permissions

| Actor | Can | Cannot |
|-------|-----|--------|
| Customer | Upload own report, toggle filter, see own profile | See other customers’ reports |
| Owner | — | Read diner reports |
| Admin `customers:read` | Conditions, avoid lists, filter flag, `has_checkup_report` | Download PDF / image |

### 7.1 Super-admin gate

| # | Y/N | Delivery |
|---|-----|----------|
| 1 Kitchen-scoped | Yes | Discovery/menu filter (no kitchen workspace tab — diner PHI) |
| 2 Entitlement | No | Core trust, not a paid module |
| 3 Ops/support | Yes | Admin → Customers diet summary · `customers:read` |
| 4 Cross-tenant | Yes | Customer-id scoped; catalog read is public active dishes |
| 5 Kill-switch | Yes | `customer_diet_report` |
| 6 Credentials | No | Platform AI vision deferred; no kitchen secrets |

## 8. Domain

```
Aggregate: Customer
  diet_profile JSONB
  diet_filter_enabled bool
  checkup_report_url (storage only, not in public APIs)
  checkup_parsed_at
Invariants:
  - Filter off by default
  - Profile never includes raw report text
```

## 9. Events

| Event | Stream | Payload | Idempotency |
|-------|--------|---------|-------------|
| `customer.diet_profile.updated` | `ckac:identity:customer` | customer_id, conditions, diet_filter_enabled, has_report, confidence | customer_id + parsed_at |

## 10. Database

| Change | Schema | Migration |
|--------|--------|-----------|
| columns on `customers` + flag | `ckac_identity` | Alembic `028` |

## 11. API

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/customers/me/checkup-report` | customer JWT multipart |
| GET | `/api/v1/customers/me/diet-profile` | customer JWT |
| PATCH | `/api/v1/customers/me/diet-filter` | customer JWT `{enabled}` |
| GET | `/api/v1/customers/me/diet-compatible-dishes?kitchen_id=` | customer JWT |
| GET | `/api/v1/kitchens/public/nearby` | optional customer JWT |
| GET | `/api/v1/discovery/home` | optional customer JWT |

## 12. Flow

```
Customer → POST checkup-report → extract text → ML+labs → store profile
        → UI asks filter? → PATCH diet-filter
        → nearby/discovery/menu read catalog dishes once → exclude incompatibles
        → rank remaining kitchens by compatible dish count
```

## 13. Security

- PII: report file, conditions, avoid lists
- OWASP: size/type sniff, parameterized SQL, no secrets in code
- Audit: domain event only (no file URL)

## 14. Tests

| Test | File |
|------|------|
| ML + matching unit | `tests/test_diet_report_ml.py` |
| Upload / filter / nearby / flag / event / admin | `tests/test_customer_diet_report.py` |
