# KitchCu QA Instruction Pack

| Field | Value |
|-------|-------|
| Document | `QA-INSTRUCTION-PACK.md` |
| Version | 1.0 |
| Date | July 2026 |
| Audience | QA Lead, engineers, founders doing release verification |
| Companion PDF | `docs/QA-INSTRUCTION-PACK.pdf` — generate via `python scripts/generate_qa_instruction_pdf.py` |
| Scope | Local Docker demo + GCP production smoke; owner kitchen lists/UI polish; F19/F19b stock + bulk prep |

---

## 0. How to use this pack

1. Run **§1 Setup** once per environment.
2. Execute **§2 Smoke** (blocking — must pass before deep QA).
3. Run persona suites **§3–§6** as checklists; mark Pass / Fail / Blocked.
4. Log defects with the template in **§8**.
5. Sign off with **§9**.

**Pass rule:** every *Must* case Pass; *Should* cases may Fail only with an accepted waiver.

---

## 1. Setup

### 1.1 Local stack

| Item | Value |
|------|-------|
| Repo | `CKAC` |
| Start | `docker compose up -d` (postgres `15432`, redis `16379`, gateway `18000`) |
| Seed | `.\scripts\seed-all.ps1` or `python scripts/seed-dev-data.py` + extras as needed |
| Tests (backend) | `.\scripts\run-tests.ps1` after backend changes |

| Surface | URL | Port |
|---------|-----|------|
| Portal | http://localhost:13000 | 13000 |
| Customer | http://localhost:13001 | 13001 |
| Kitchen (owner) | http://localhost:13002 | 13002 |
| Admin | http://localhost:13003 | 13003 |
| Gateway | http://localhost:18000 | 18000 |

After frontend rebuilds: hard-refresh or unregister the PWA service worker if UI looks stale.

### 1.2 Demo credentials

| Persona | Login | Notes |
|---------|-------|-------|
| Owner | Phone `9876543210`, OTP `123456` | Primary kitchen `CKPNQ001` (Sharma Home Kitchen) |
| Customer | WhatsApp OTP phone `9123456789`, OTP `123456` | Other demo phones in `AGENTS.md` |
| Admin | `admin@kitchcu.dev` / `admin123456` | Platform JWT only |

### 1.3 GCP smoke (optional)

Follow `docs/DEPLOYMENT-GCP.md`. Confirm `*.kitchcu.com` health and same persona logins against production seed policy.

---

## 2. Smoke suite (Must — ~15 min)

| ID | Step | Expected | Result |
|----|------|----------|--------|
| S1 | Gateway `GET /health/live` and `/health/ready` | 200 | |
| S2 | Kitchen login OTP → land on Overview | Hero shows kitchen name + code; no blank/black screen | |
| S3 | Customer login OTP → home | Menu/discovery loads | |
| S4 | Admin login → overview | Dashboard KPIs/panels load | |
| S5 | Portal home | Brand-first hero; no console crash | |
| S6 | OpenAPI via gateway `/docs` or portal `/openapi` | Schema loads | |

**Fail any of S1–S4 → stop deep QA; fix infra first.**

---

## 3. Owner UI — headers, lists, filters, dropdowns (Must)

Focus: kitchen PWA `:13002`. Login as owner `9876543210`.

### 3.1 Home / Overview header

| ID | Check | Expected |
|----|-------|----------|
| H1 | Hero layout | Greeting + kitchen name + code on left; primary CTAs (e.g. New order / Brand) on the **same row top-right** — not a tall empty column with button at bottom |
| H2 | Pills / meta | Subscription + drafts/live pills readable; no overflow clip |
| H3 | Recent orders list | Rows clickable; status chips coherent |

### 3.2 Listing toolbar (search / sort / filters)

For each page below: toolbar visible, search filters rows, sort changes order, filter chips toggle, result count updates.

| ID | Page | Route | Checks |
|----|------|-------|--------|
| L1 | Orders | `/dashboard/orders` | Search; sort Newest / Customer A–Z / Z–A; **drafts tab also sorts**; tabs Active/All/Drafts |
| L2 | Menu | `/dashboard/menu` | Search; sort; highlight + diet chips |
| L3 | Ingredients (pantry) | `/dashboard/ingredients` | Search; sort Name/Stock; **Low stock** chip |
| L4 | Bulk prep (batches) | `/dashboard/prep` | Search; sort; Open / Prepared chips |
| L5 | CRM | `/dashboard/crm` | Search; sort Spend/Orders/Name; VIP / Repeat / Tagged chips |
| L6 | Coupons | `/dashboard/coupons` | Search; sort; Active / Inactive chips |

### 3.3 Layout / dropdown CSS

| ID | Check | Expected |
|----|-------|----------|
| U1 | Panels | Owner panels use full content width of the board (not a ~560px stub column for list editors) |
| U2 | Selects | Dropdowns show chevron, theme fill, no raw unstyled system control on Templates / Tiffin / Coupons / listing Sort |
| U3 | Tables | Headers align with cells; horizontal scroll only if needed; no nested “card-in-card” double shadow on CRM/Ingredients tables |
| U4 | Recipe cards (Ingredients) | Ingredient / Qty / Unit labels **above** controls in one aligned row; Remove button compact (not full-width) |

---

## 4. F19 / F19b — Ingredients + Bulk prep + stock deduct (Must)

### 4.1 Ingredients mapper

| ID | Step | Expected |
|----|------|----------|
| I1 | Open Ingredients | Pantry form 4-column grid; Add ingredient works |
| I2 | Adjust stock +100 / −10 | Stock number updates; no 404 |
| I3 | Select dish → edit recipe lines + prep steps → Save | Success toast/message; reload persists |
| I4 | Low-stock filter | Only low items when chip on |

### 4.2 Stock deduct mode + bulk prep

| ID | Step | Expected |
|----|------|----------|
| B1 | Open Bulk prep | Mode buttons **Order Ready** / **Bulk prep only**; no “Not Found” |
| B2 | Mode Order Ready (default) | Message that orders deduct when marked Ready |
| B3 | Create combo batch (≥2 dishes, portions > 0) | Batch appears in table with expanded ingredient lines |
| B4 | Edit qty → save | Totals persist |
| B5 | Mark prepared | Status `prepared`; pantry stock decreases for those ingredients |
| B6 | Switch to **Bulk prep only** | Orders must **not** deduct on Ready; only Mark prepared deducts |
| B7 | Gateway routes | `GET /api/v1/kitchens/{id}/stock-settings` and `.../prep-batches` return 200 with owner JWT (not identity 404) |

### 4.3 Order lifecycle vs stock

| ID | Step | Expected |
|----|------|----------|
| O1 | Create/confirm order with mapped recipe dish | Order `received` |
| O2 | Accept | Porter may book if platform delivery; **stock unchanged** (warnings OK) |
| O3 | → Preparing → Ready (mode `order_ready`) | First Ready triggers deduct; stock drops once |
| O4 | Repeat Ready / further status | No double deduct |
| O5 | With mode `prep_batch_only` | Ready does **not** deduct |

---

## 5. Cross-persona regression (Should)

| ID | Area | Check |
|----|------|-------|
| R1 | Customer checkout | Quote → place → pay path (dev); order appears for owner |
| R2 | Multi-kitchen cart | Master receipt path still loads if seeded |
| R3 | Ratings | Delivered order can rate home_taste |
| R4 | Admin tickets / refunds | Admin can open tickets; refund list loads |
| R5 | Tenant isolation | Owner A never sees kitchen B’s CRM / ingredients / prep batches |

---

## 6. Security & observability (Must for release)

| ID | Check | Expected |
|----|-------|----------|
| X1 | Owner JWT on admin APIs | Rejected |
| X2 | Logs | No OTP, full phone, or tokens in gateway/service logs |
| X3 | Correlation | `X-Correlation-ID` present on proxied responses when sent |
| X4 | Internal routes | Public `GET /api/v1/internal/*` via gateway → 404 |

---

## 7. Automated tests (Must after backend change)

```powershell
.\scripts\run-tests.ps1
```

Focused (when touching F19b):

```powershell
# catalog prep batches + order ready deduct
cd services/catalog; python -m pytest tests/test_prep_batches.py -q
cd ../order; python -m pytest tests/test_stock_deduct_on_ready.py -q
cd ../gateway; python -m pytest tests/test_gateway.py::test_resolve_service_url_catalog -q
```

---

## 8. Defect report template

```text
Title:
Environment: local | GCP
Surface: portal | customer | kitchen | admin | API
Severity: S1 blocker | S2 major | S3 minor | S4 polish
Steps:
1.
2.
Expected:
Actual:
Screenshot / correlation ID:
Workaround:
```

---

## 9. Sign-off

| Role | Name | Date | Verdict (Go / No-Go) | Notes |
|------|------|------|----------------------|-------|
| QA Lead | | | | |
| CTO / eng | | | | |
| CPO | | | | |

**Go criteria:** §2 Smoke Pass; §3 list/UI Must Pass; §4 F19b Must Pass; §6 security Must Pass; automated tests green for touched services.

---

## 10. Cross-references

| Need | Doc |
|------|-----|
| Flows + APIs | `docs/CKAC-USERFLOWS.md` (Flow 8b Ingredients + Bulk prep) |
| F19 / F19b design | `docs/F19-INGREDIENTS-DESIGN.md`, `docs/design/F19B-BULK-PREP-STOCK-ON-PREPARED-DESIGN.md` |
| Feature acceptance | `docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md` |
| Release board | `docs/ADVANCEMENT-TRACKER.md` |
| Agent rules | `AGENTS.md` |

---

## Document control

| Change | Date |
|--------|------|
| Initial QA pack (lists/UI polish + F19b stock/bulk prep) | 2026-07-20 |
