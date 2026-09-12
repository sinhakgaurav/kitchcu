# KitchCu Advancement Tracker

**Living release board** — sprint baseline + post-S18 product increments. Update this file whenever a feature ships to website, APIs, seed, or docs.

| Field | Value |
|-------|-------|
| Baseline | Phase 1 **S1–S18** complete (gateway + 13 domain services + 4 PWAs + GST) |
| Production | `*.kitchcu.com` (GCP VM + Caddy) |
| Local demo | `*.kitchcu.in` / `admin@kitchcu.dev` |
| Last updated | 2026-09-12 |
| Portals / QA pack | [PRODUCTION-PORTALS-CREDENTIALS-QA.md](./PRODUCTION-PORTALS-CREDENTIALS-QA.md) (+ PDF) |
| Tester book | [TESTER-INSTRUCTION-PACK.md](./TESTER-INSTRUCTION-PACK.md) (+ [PDF](./TESTER-INSTRUCTION-PACK.pdf)) — numbered UI + API steps |
| Architecture flows | [PLATFORM-ARCHITECTURE-FLOWS.md](./PLATFORM-ARCHITECTURE-FLOWS.md) |

---

## How to use

| Status | Meaning |
|--------|---------|
| ✅ Shipped | Code + tests + seed/docs touch as required |
| 🟡 Partial | Usable but gaps remain (note in Notes) |
| 🔜 Next | Design pack or queued sprint |
| ❌ Out of scope | Restaurant POS / dine-in / commission model |

For acceptance criteria of F01–F48 see [CKAC-COMPLETE-PLANNING-BENCHMARK.md](./CKAC-COMPLETE-PLANNING-BENCHMARK.md).  
For code map see [CKAC-IMPLEMENTATION-GUIDE.md](./CKAC-IMPLEMENTATION-GUIDE.md).  
For journeys see [CKAC-USERFLOWS.md](./CKAC-USERFLOWS.md).  
For **solution blueprint** (expectations → CEO/CPO solution → CTO impl → arch/DB per journey) see [PLATFORM-SOLUTION-BLUEPRINT.md](./PLATFORM-SOLUTION-BLUEPRINT.md).  
For **strategic waves** see [PLATFORM-STRATEGIC-ANALYSIS.md](./PLATFORM-STRATEGIC-ANALYSIS.md).  
For **persona lived experience** see [PLATFORM-PERSONA-DEEP-DIVE.md](./PLATFORM-PERSONA-DEEP-DIVE.md).  
For **architecture + end-to-end flows** see [PLATFORM-ARCHITECTURE-FLOWS.md](./PLATFORM-ARCHITECTURE-FLOWS.md).  
For **numbered tester steps** (UI + Swagger/API) see [TESTER-INSTRUCTION-PACK.md](./TESTER-INSTRUCTION-PACK.md) (+ [PDF](./TESTER-INSTRUCTION-PACK.pdf)).  
For **manual QA / release sign-off** (short Must/Should) see [QA-INSTRUCTION-PACK.md](./QA-INSTRUCTION-PACK.md) (+ [PDF](./QA-INSTRUCTION-PACK.pdf)).

---

## Platform snapshot (2026-07-20)

| Layer | State |
|-------|-------|
| Edge | Gateway `:18000` — CORS, correlation ID, OTP rate limits |
| Domains | 13 services (identity→streaming) — schema-per-domain + outbox EDD |
| PWAs | portal / customer / kitchen / admin under `apps/website/` |
| i18n | 12 locales (en + hi/mr/ta/te/kn/ml/bn/gu/pa/bho/mai) — catalog parity green; admin stays EN |
| Cities | Presence strip on portal / customer / kitchen; seed kitchens in Delhi NCR, UP, Dehradun, Mumbai |
| Delivery | Cost-share + Self/Porter modes; book on accept (P32/P32.1) |
| Trust | Admin RBAC + audit · HTML sanitize · API-key mask · login-hint gated (`ADMIN_LOGIN_REVEAL_PASSWORD`) · Swagger padlock only on JWT routes |
| Growth | Dual referral program + GST monthly Excel/PDF |
| Open | Kitchen staff build · tiffin recurring · Wave C/D |

---

## Sprint baseline (S1–S18)

| Sprint | Deliverable | Status |
|--------|-------------|--------|
| S1 | Gateway + identity (owners, OTP, kitchens) | ✅ |
| S2 | Catalog (categories, dishes, live-capture) | ✅ |
| S3 | Order lifecycle + history | ✅ |
| S4 | Notification (WhatsApp webhook, support) | ✅ |
| S5 | PWAs + customer checkout | ✅ |
| S6 | Billing, subscriptions, GST, refunds | ✅ |
| S7 | Discovery (F32) + order history/repeat (F33) | ✅ |
| S8 | Multi-kitchen cart + master receipt (F06) | ✅ |
| S9 | Split payment / Route (F44) | ✅ |
| S10 | CRM, coupons, promotions (F36–F38) | ✅ |
| S11 | Home-taste ratings (F16–F18) | ✅ |
| S12 | Growth intelligence + daily menu (F09–F11, F39) | ✅ |
| S13 | Delivery fees/distance/tracking (F27–F31) | ✅ |
| S14 | Tracking reminders + order WhatsApp (F29/F45) | ✅ |
| S15 | Ingredient mapper (F19) | ✅ |
| S15b | Bulk prep + deduct on prepared/ready (F19b) | ✅ |
| S16 | Learning portal + dish trials (F21–F22) | ✅ |
| S17 | Recipe rewards + chef rankings (F23–F24) | ✅ |
| S18 | Live streaming LiveKit (F46–F48) | ✅ |

---

## Post-S18 increments (release track)

| ID | Feature | Surfaces | Status | Notes |
|----|---------|----------|--------|-------|
| P19 | **Branded kitchen storefront** | Identity `branded_page` · customer `/k/:code` · owner **Brand page** nav (`/dashboard/brand`) + Overview teaser · admin kitchen **Brand** tab | ✅ | Shareable brand page → menu/checkout; verify: `node scripts/check-platform-ui-map.mjs` |
| P20 | **Golden performance day + ML comments** | Growth scorer + sentiment · owner Growth/Menu · notify golden day | ✅ | Pins recipes from peak days |
| P21 | **Kitchen WhatsApp + Razorpay workspace** | Owner Integrations · Admin kitchen detail (Profile/WA/Payments/Modules) | ✅ | Platform SaaS keys stay Admin → API Keys |
| P22 | **Go-live per-dish showcase** | Streaming dish_id + phases ingredients→prep→prepared · StreamPage · Nearby live filter | ✅ | Event `stream.showcase_updated` |
| P23 | **Admin password sync from env** | Identity `ensure_default_admin` resyncs hash · admin UI prod defaults | ✅ | Fixes `admin.kitchcu.com` invalid credentials after metadata rotate |
| P24 | **Release docs + tracker** | This file · Complete Guide / Userflows / Implementation Guide · portal features | ✅ | PDFs regenerable via `scripts/generate_*_pdf.py` |
| P25 | **Package mapper (features→packages→plans)** | Billing `platform_features` / `packages` / `plan_packages` / `kitchen_packages` · Admin → Packages · kitchen Package tab | ✅ | Alembic billing `008`; assign syncs module flags optionally |
| P26 | **Owner WA/email marketing templates** | Marketing `message_templates` · Owner Growth → Templates · Admin kitchen Marketing tab | ✅ | Alembic marketing `002`; module `marketing_broadcast` |
| P27 | **Platform employees CRUD + RBAC** | Identity `admin_permissions` / role grants · Admin → Employees · `require_admin_permission` | ✅ | Alembic identity `013`; roles superadmin/ops/support/finance |
| P28 | **Super-admin kitchen workspace expansion** | Kitchen tabs: Profile / WhatsApp / Payments / Package / Marketing / Modules / Streaming | ✅ | Cursor rule `kitchcu-superadmin-integration.mdc` (always-on gate) |
| P29 | **Wave A/B capability close** | Admin RBAC enforce + `/me` tabs · hard entitlements + owner nav · template send · customer Watch live | ✅ | Identity `014`; `ckac_common.admin_rbac`; billing entitlements API |
| P30 | **LiveKit embed + template fan-out + audit** | Customer/owner LiveKit player · notify `/template-blast` per phone · `admin_audit_events` + Admin Audit tab | ✅ | Identity `015`; `livekit-client` |
| P31 | **Wallet debit + Meta outbound + billing audit** | Template send deducts messaging wallet · Graph WhatsApp send · billing PG/package/refund → identity audit | ✅ | Identity `016` WA access token slot |
| P32 | **Porter + delivery cost share + camera fix** | In-range kitchen pays 100%; extended min-order → kitchen subsidy %; Porter quote/book; LiveKit camera preview | ✅ | Identity `017`; order `007` |
| P32.1 | **Checkout→order Porter wire-up** | Customer sends `delivery_mode`; order validates platform fees + cost share; Porter books on accept; owner delivery settings UI | ✅ | — |
| P33 | **Prod OTP WhatsApp + Porter webhooks** | Identity OTP → Redis + notify WhatsApp; `POST /webhooks/porter` → `courier_status`; kitchen staff design pack | ✅ | Order `008`; design `docs/design/KITCHEN-STAFF-RBAC-DESIGN.md` |
| P34 | **Delivery fee collection rules** | Shared → prepaid only; customer-only → pay-first or pay-on-delivery; Porter gated on prepaid capture | ✅ | Order `009` |
| P35 | **Porter auto-book + prep+delivery ETA** | Customer ETA = prep + delivery; auto-book Porter after accept delay (default 15m) + retry; owner toggle; admin Delivery tab + module/feature | ✅ | Order `010`; identity `018`; billing `009`; design `docs/design/PORTER-AUTO-BOOK-ETA-DESIGN.md` |
| P36 | **Tiffin / monthly subscriptions (F34/F35)** | Owner plans; customer request; accept/deny/activate/deactivate; Reports + Intelligence KPIs; admin Tiffin tab + `tiffin_plans` feature/module | ✅ | Marketing `003`; billing `010`; identity `019`; design `docs/design/TIFFIN-MONTHLY-SUBSCRIPTION-DESIGN.md` |
| P37 | **Dual referral program** | Customer→kitchen + kitchen→customer leads; ₹ rewards (default 10); credit ledger; owner/customer/admin UI; bulk CSV | ✅ | Identity `021`; design `docs/design/REFERRAL-PROGRAM-DESIGN.md`; stream `ckac:identity:referral` |
| P38 | **GST monthly Excel/PDF** | Owner GST finance downloads; admin kitchen GST tab (profile/report/export) | ✅ | `services/billing/app/gst_export.py` (xlsx + fpdf2) |
| P39 | **Super-admin ops console fill** | Kitchen Orders + Care/health strip; ticket triage (assignee/priority/resolution); customer order/ticket history; settlements under Refunds; deep-links | ✅ | Identity admin orders filters; notify ticket filters; `test_admin_ops_controls.py` |
| P40 | **Platform i18n + security harden** | Location language gate; 184-key catalogs × 10 locales; owner/customer/portal chrome on `t()`; dish HTML sanitize; API keys never echo full value | ✅ | `docs/design/PLATFORM-I18N-DESIGN.md`; `scripts/check-i18n-locale-parity.py` |
| P41 | **Audit gap close + live-capture-safe seed** | Owner kitchen profile PATCH (code immutable); owner dish list includes drafts; Ratings page; order filters/draft remap; settlements; payment-mix/compare; admin RBAC UI + 401 logout + stream summary (no publisher token); Super Admin links; weekly cron path `/opt/ckac`; GCP `bulk-seed.sh` | ✅ | Identity `023`; catalog `GET …/dishes`; `infra/gcp-vm/{bulk-seed.sh,weekly-seed.sh}` |
| P42 | **Live Razorpay Checkout** | Billing live Orders API + signed capture · customer Checkout.js · kitchen/platform keys · webhook backup | 🟡 | Demo path unchanged without keys; Route transfers still pending in prod. Design `LIVE-RAZORPAY-CHECKOUT-DESIGN.md` |
| P43 | **Order CSV + parse match-rate** | Owner `export.csv` + drafts parse-stats; admin kitchen Orders CSV/stats; first-party (no Meta/Razorpay) | ✅ | Design `ORDER-CSV-AND-PARSE-STATS-DESIGN.md`; cap 10k rows |
| P44 | **Admin API docs + login creds** | Super Admin Sign in shows username/password + Swagger/ReDoc/portal links; how-to Authorize in `API.md` §1.1 | ✅ | Admin login / sidebar / overview |
| P45 | **Gated admin login-hint** | `GET /admin/auth/login-hint` returns `ADMIN_PASSWORD` only in `development`/`test` **or** when `ADMIN_LOGIN_REVEAL_PASSWORD=1`; Sign in + portal/kitchen/customer strips print it when revealed; GCP/startup still write reveal=1 | ✅ | Identity `_should_reveal_admin_password`; `test_admin_password_sync.py` |
| P46 | **QA tracker close-out (13 issues, 3 sheets)** | Discovery `q` + KNN `nearest` fallback; honest demo-OTP response; dish photo truth table; nearby reveal CSS; social buttons; nav overlay; scroll listener; refund actions; orders empty state | ✅ | See table below. Guardrail `scripts/tests/test_dish_media_truth.py` |
| P47 | **Swagger tester + auth QA** | Aggregated OpenAPI: public ops `security: []` (no leftover token on Try it out); `POST /api/v1/auth/token` OAuth2 password form (admin email+password or owner/customer phone+OTP); owner JWT `type=owner`; `scripts/audit-api-auth.py`; community public recipes skip orphan kitchens; customer refunds list returns `[]` not 500 | ✅ | Gateway `openapi_aggregate.py`; identity `auth_token.py`; community `list_shared_recipes`; billing refunds SQL |

---

## P46 — QA issue tracker close-out

Source: QA workbook, sheets **Bug Issue** · **Bug Resolved** · **API Bug Report**. 13 open rows.

| ID | Pri | Reported | Root cause found | Fix |
|----|-----|----------|------------------|-----|
| ID-04 | High | "No kitchens" after *Use my location* | Two causes. `.reveal-stagger.reveal--visible .nearby-kitchens__list li` needed the stagger classes on an **ancestor**, but they sit on the `<ul>` itself — every card stayed at `opacity: 0` while the API returned kitchens. Out-of-range diners also had no path forward. | Reveal selector matches the list element (+ reduced-motion escape); `GET /kitchens/public/nearby` returns a bounded `nearest[]` KNN fallback when nothing is in radius; UI shows "closest is N km away in *city*" with the real cards |
| ID-05 | High | Search bar returns nothing | `/kitchens/public/nearby` ignored `q` entirely; the toolbar filtered client-side on kitchen name/city/code only, so no dish or cuisine term could ever match | `q` now filters server-side across kitchen name/code/city/tagline **and** active dish, cuisine, and category names (shared SQL with the discovery feed); UI debounces to the API |
| ID-08 | High | OTP not sent | Dev/demo mode returned `202 {"message": "OTP sent via WhatsApp"}` while sending nothing, so testers waited for a message that never existed | Both OTP routes return `delivered: false` + `demo_otp` in demo mode; owner, customer, and social sign-in surface "Demo mode — no SMS or WhatsApp message is sent. Enter 123456." |
| ID-16 | High | Dish images do not match names | One salad-bowl photo stood in for 13 curries; `biryani.jpg` (chicken) sat on "Veg Biryani", `skewers.jpg` (lamb chops) on "Paneer Tikka", `rice.jpg` (chicken) on "Veg Thali Combo"; `restaurant.jpg` / `dining.jpg` (venue) sat on dishes; tiffin plan covers were hardcoded and a re-seed only filled a *missing* image, never corrected a wrong one | `FOOD_ASSET_SUBJECTS` describes what every photo actually shows; `DISH_MEDIA_BY_NAME` binds one asset to one dish and is shared by both seeders; menu reshaped to 11 live dishes each with a truthful unique hero; house classics seed as drafts (absent from the public menu) until an owner captures a hero; plan covers derive from the lead dish; re-seed now corrects wrong heroes and unpublishes dishes that lost one |
| ID-01 | Med | Home page scroll lag | ~23 independent `scroll` listeners, each doing its own layout read | One shared rAF-batched scroll frame (`useParallax`), values rounded to whole pixels |
| ID-09 | Med | Social buttons not highlighted | Providers had no visual identity and read as disabled | Per-provider accent drives dot, border tint, hover lift, and busy state from one `--social-accent` custom property |
| ID-20 | Med | Nav menu dark overlay hides items | Mobile panel inherited the dark-theme glass on the light brand theme | Light-theme panel override: cream background, dark text, brand-teal links |
| ID-21 | Med | My Orders blank | Rendered the empty branch while auth was still resolving, and the empty state had no content | Loader covers `loading \|\| fetching`; empty state gets title, hint (12 locales), and a discovery CTA |
| ID-15 | Low | Refund gateway button alignment | Submit inherited the field-to-field gap, so spacing shifted as conditional fields appeared | `.owner-pay-panel__actions` owns the submit row; full-width under 640 px |
| BUG_01–04 | High | OTP/register accept >10-digit phone, echo uppercase email, accept invalid names | **Already fixed in `93cb604`** — re-verified live on `api.kitchcu.com` (422 on `987654321011`, `12345`, `123456`, `125@`, `Pooja123`; `QA.xxx@GMAIL.COM` → `qa.xxx@gmail.com`; `D'Souza Rao-Patil` → 201). Sheet is stale | Closed the one gap: HTTP-level parametrized OTP phone test |

**Regression guards:** `scripts/tests/test_dish_media_truth.py` (asset described, no reuse across dishes, no venue/branded photo as a hero, no meat or egg photo on a veg dish, unmapped dish ⇒ draft, both seeders agree, menu still browsable) · `services/identity/tests/test_kitchens.py` (`q` across dish/cuisine, `nearest` fallback) · `services/identity/tests/test_auth.py` (demo-OTP response shape, phone validation).

---

## Credentials (do not confuse)

| Environment | Admin email | Password |
|-------------|-------------|----------|
| Local / Docker demo | `admin@kitchcu.dev` | `admin123456` |
| Production (`admin.kitchcu.com`) | `admin@kitchcu.com` | GCE metadata `admin-password` → VM `ADMIN_PASSWORD` (printed on Sign in when `ADMIN_LOGIN_REVEAL_PASSWORD=1`; synced to DB on login) |

Owners (all envs with seed): `9876543210`–`9876543213`, OTP `123456`.  
Customers: `9123456789`, `9123456780`, `9988776655`, `9123456781`, `9123456782`, OTP `123456`.

After GCP reset: `infra/gcp-vm/reset-fresh.sh` re-exports `ADMIN_*` and re-seeds.

---

## Seed coverage checklist

Run `.\scripts\seed-all.ps1` (or GCP `run-seed=1`) after migrations.

| Persona / module | Seed path | Status |
|------------------|-----------|--------|
| Platform admin | identity bootstrap + extras login | ✅ |
| Owners + kitchens + menus | `seed-dev-data` / `seed-bulk-data` | ✅ |
| Customers + orders + ratings | `seed_platform_extras` | ✅ |
| WhatsApp + payment gateway per kitchen | `ensure_whatsapp_integration` / `ensure_payment_gateway` | ✅ |
| GST / refunds / delivery quote | extras | ✅ |
| Referral settings + demo leads | identity referral seed (extras/bulk) | 🟡 | Settings table seeded by migration; leads via UI or API |
| Branded storefront | `ensure_branded_page` | ✅ |
| Streaming + dish showcase | `ensure_streaming(..., dish_id=)` | ✅ |
| Growth suggestions (incl. golden day when data qualifies) | `ensure_growth_suggestions` | ✅ |
| Platform features / seed packages | billing migration `008` seed | ✅ |
| Learning trials / community | extras (`cover_url` on community recipe) | ✅ |
| Tiffin plans (thali / single_dish / combo) | `ensure_tiffin_plans` | ✅ |
| Weekly QA cohort (5 owners · 10 customers · 21 orders/kitchen over 7 days · Saturday 03:30 IST) | `scripts/weekly_test_data.py` via `kitchcu-weekly-seed.timer` | ✅ |
| GCP bulk seeder (30 kitchens · 6-month history · 15 cities · 3 customers/city · live-capture-safe) | `infra/gcp-vm/bulk-seed.sh` → `scripts/seed-bulk-data.py` · `kitchcu-bulk-seed.service` | ✅ |

### Weekly QA cohort

Systemd timer on the VM (`infra/gcp-vm/kitchcu-weekly-seed.{service,timer}`) runs every
Saturday 03:30 IST and adds a new cohort without touching earlier ones: **5 owners** with
kitchens and menus, **10 customers**, **21 delivered + rated orders per kitchen** (3/day
across the trailing 7 days, IST meal windows) mixing new and returning diners, a rotated
`QA{cohort}` coupon and promotion (previous cohort's deactivated), a tiffin plan with a
subscriber, CRM refresh, growth suggestions, and a support ticket. Identifiers are derived
from the ISO year+week
(`{prefix}{YY}{WW}{index}`; owners `7…`, customers `8…`), so re-running inside the same
week reuses the accounts and only tops orders up. Current cohort is written to
`/var/lib/ckac/weekly-cohort.json`. Repo on the VM is `/opt/ckac`. See [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §11.7–§11.7c.

### Six-month trading history

The bulk seeder **defaults to six months** (`CKAC_BULK_MONTHS=6` in
`infra/gcp-vm/bulk-seed.sh` and `scripts/seed-bulk-data.py`) so first-boot and
`kitchcu-bulk-seed.service` produce history that reads like six months a kitchen
actually worked.

```powershell
python scripts/seed-bulk-data.py
# 30-day smoke: $env:CKAC_BULK_MONTHS=0; python scripts/seed-bulk-data.py
```

| Control | Default | Purpose |
|---------|---------|---------|
| `CKAC_BULK_MONTHS` | `6` (183 days) | Set `0` to use `CKAC_BULK_BACKDATE_DAYS` (30) |
| `CKAC_BULK_ORDERS_PER_KITCHEN` | `max(40, window_days)` | ≥1 order/day so no daily bucket is empty |
| `CKAC_BULK_PRIMARY_ORDERS` | `window_days × 3` | Denser history on the demo kitchen |
| `CKAC_POSTGRES_CONTAINER` | auto | Force the target DB when several stacks are up |

The distribution lives in `scripts/order_history.py` and is asserted without a database in
`scripts/tests/test_order_history.py`:

- **Service hours (IST)** — breakfast/lunch/snacks/dinner windows with lunch and dinner
  peaks. The old `NOW() - random() * 12 hours` could not reach dinner at all, so the
  peak-hours report was an artefact of when the seeder happened to run.
- **Weekly rhythm and growth** — weekend lift plus a trend, so a 6-month revenue chart shows
  a kitchen that grew.
- **Age-aware status** — anything older than two days is delivered or cancelled; yesterday
  keeps only late-stage stragglers (`ready`, `out_for_delivery`); the live queue is today's.
- **Linked rows move too** — status events, payments, refunds, settlements, GST invoices
  (including `invoice_date`) and dish ratings shift with their parent order, so GST periods
  and payment mix line up with the orders they describe.
- **A diner pool that scales with volume** — roughly one distinct diner per 3.5 orders, split
  into a loyal core, regulars and a one-off tail, so CRM, customer segments and churn risk
  have something to segment. Registered city diners lead the core, keeping their logins rich.
  Every generated diner gets a distinct name and a `+9174…` number that cannot shadow a
  seeded login.
- **A plausible basket** — mostly one dish for one person. The old 1–3 dishes × quantity 1–3
  averaged four units, which billed a home-food order at over ₹1,000.
- **GST invoice numbers follow the dated month** — numbers minted as `CKCODE-GST-YYYYMM-SEQ`
  at create time are rewritten after dating so March filings are not a September series.
- **Owner Reports** expose a 6-month range; 90/180-day charts roll up to weeks/months instead
  of 180 unreadable daily bars. Period-over-period deltas hide when the prior window is empty.

Bugs found while verifying this, all of which also affected the previous backdating:

| Bug | Effect | Fix |
|-----|--------|-----|
| CRM profiles are aggregated on request (`?refresh=true`), and the only sync call sat inside the marketing-assets block | On any re-run the coupon already existed, the block short-circuited on 409, and the CRM page stayed empty — 2 profiles against 210 orders. The dish-trial step then found no invite candidates and skipped promote | Sync CRM after the dating pass (so `last_order_at` matches the dated history) and refresh on the reads that need candidates |
| `resolve_postgres_container()` returned the first `*-postgres-1` from `docker ps` | With the GCP parity dry-run also up, seed SQL updated `ckac-gcp-dry-postgres-1` while the API calls went to the dev gateway — every row matched, psql exited 0, dev data stayed undated | Deterministic preference for the dev stack, warn on ambiguity, and the dating step now raises if it matches fewer orders than it was given |
| psql input encoded as cp1252 on Windows | Any dash or rupee sign in the SQL aborted the transaction with `invalid byte sequence for encoding "UTF8"` | Pin `encoding="utf-8"` and `PGCLIENTENCODING=UTF8` |

---

## Next (prioritized — see strategic analysis)

| Wave | Item | Doc |
|------|------|-----|
| **A (trust)** | ✅ RBAC+tabs+hard entitlements · ✅ audit · ✅ prod OTP WhatsApp path · 🟡 live Razorpay Checkout (signed capture; Route transfers pending) | [LIVE-RAZORPAY-CHECKOUT-DESIGN.md](./design/LIVE-RAZORPAY-CHECKOUT-DESIGN.md) |
| **B (promises)** | ✅ Templates/Watch/Porter cost-share · ✅ Porter webhooks · ⏳ kitchen staff **build** (design pack ✅) | [KITCHEN-STAFF-RBAC-DESIGN.md](./design/KITCHEN-STAFF-RBAC-DESIGN.md) |
| **C (design)** | E1–E2 Kitchen Quality Loop | [E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| **D (scale)** | Cloud Run architecture · OTel · load SLOs | [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §1–10 |

---

## UI ↔ endpoint verification

```powershell
node scripts/check-platform-ui-map.mjs   # feature → UI → /api/v1 client paths
node scripts/check-ui-reach.mjs          # Brand + DataTable reach graph
```

Both must exit 0 before calling a UI surface “done.”

## API auth verification

```powershell
python scripts/audit-api-auth.py         # needs the stack up + demo seed
```

Probes every operation in the gateway's published OpenAPI and fails if enforcement
disagrees with the schema: declared-protected must reject anonymous, declared-public must
serve anonymous, and a real JWT must get a protected read through. Currently **301
operations, 0 mismatches**. Details and the per-class table are in
[API.md §1.2–1.3](./API.md).

---

## Release gate (kitchcu.com)

- [x] Admin login uses `admin@kitchcu.com` on production hosts (UI + env sync)
- [x] Seed covers integrations, branded page, dish showcase
- [x] Advancement tracker maintained (P19–P44)
- [x] Migrations ready: identity `013`–`023`, order `007`–`010`, billing `008`–`010`, marketing `002`–`003`
- [ ] Deploy: push `main` → GCP VM redeploy → smoke admin tabs + Packages + Templates send + Watch live + checkout Self/Porter modes
- [ ] Confirm `ADMIN_PASSWORD` in GCE metadata matches what operators use
- [ ] Smoke: support role sees Tickets only; finance sees Packages/Refunds; Starter kitchen hides Live stream nav
- [ ] Smoke: owner delivery settings + beyond-range quote shows subsidy split

*Update the checkboxes and Post-S18 table on every release cut.*

### GCP update (single-VM — production path today)

```bash
# 1) After push to origin/main — pull + rebuild (keeps DB)
gcloud compute ssh ckac-vm --zone=asia-south1-a --command="sudo google_metadata_script_runner startup"

# 2) Watch build
gcloud compute ssh ckac-vm --zone=asia-south1-a --command="sudo tail -f /var/log/ckac-startup.log"

# 3) Smoke
curl -sS https://api.kitchcu.com/health/ready
# Login admin.kitchcu.com → Packages + Employees; open a kitchen → Package / Marketing / Streaming

# Fresh wipe (DB reset + re-seed) — only when intentionally destroying demo data:
# gcloud compute ssh ckac-vm --zone=asia-south1-a --command="cd /opt/ckac && sudo git fetch origin main && sudo git reset --hard origin/main && sudo bash infra/gcp-vm/reset-fresh.sh"
```

Full runbook: [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §11.
