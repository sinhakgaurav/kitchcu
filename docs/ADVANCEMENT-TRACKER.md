# KitchCu Advancement Tracker

**Living release board** — sprint baseline + post-S18 product increments. Update this file whenever a feature ships to website, APIs, seed, or docs.

| Field | Value |
|-------|-------|
| Baseline | Phase 1 **S1–S18** complete (gateway + 13 domain services + 4 PWAs + GST) |
| Production | `*.kitchcu.com` (GCP VM + Caddy) |
| Local demo | `*.kitchcu.in` / `admin@kitchcu.dev` |
| Last updated | 2026-07-20 |
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

---

## Platform snapshot (2026-07-20)

| Layer | State |
|-------|-------|
| Edge | Gateway `:18000` — CORS, correlation ID, OTP rate limits |
| Domains | 13 services (identity→streaming) — schema-per-domain + outbox EDD |
| PWAs | portal / customer / kitchen / admin under `apps/website/` |
| i18n | 10 IN locales (en/hi/mr/ta/te/kn/ml/bn/gu/pa) — dashboard chrome wired; admin stays EN |
| Delivery | Cost-share + Self/Porter modes; book on accept (P32/P32.1) |
| Trust | Admin RBAC + audit · HTML sanitize · API-key mask · login-hint flag-gated |
| Growth | Dual referral program + GST monthly Excel/PDF |
| Open | Kitchen staff build · live Razorpay · Wave C/D |

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
| P40 | **Platform i18n + security harden** | Location language gate; 184-key catalogs × 10 locales; owner/customer/portal chrome on `t()`; dish HTML sanitize; API keys never echo full value; `ADMIN_LOGIN_REVEAL_PASSWORD` only | ✅ | `docs/design/PLATFORM-I18N-DESIGN.md`; `scripts/check-i18n-locale-parity.py` |

---

## Credentials (do not confuse)

| Environment | Admin email | Password |
|-------------|-------------|----------|
| Local / Docker demo | `admin@kitchcu.dev` | `admin123456` |
| Production (`admin.kitchcu.com`) | `admin@kitchcu.com` | GCE metadata `admin-password` → VM `ADMIN_PASSWORD` (synced to DB on login) |

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

---

## Next (prioritized — see strategic analysis)

| Wave | Item | Doc |
|------|------|-----|
| **A (trust)** | ✅ RBAC+tabs+hard entitlements · ✅ audit · ✅ prod OTP WhatsApp path · ⏳ live Razorpay Checkout | [PLATFORM-SOLUTION-BLUEPRINT.md](./PLATFORM-SOLUTION-BLUEPRINT.md) E3 |
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

---

## Release gate (kitchcu.com)

- [x] Admin login uses `admin@kitchcu.com` on production hosts (UI + env sync)
- [x] Seed covers integrations, branded page, dish showcase
- [x] Advancement tracker maintained (P19–P32.1)
- [x] Migrations ready: identity `013`–`017`, order `007`–`008` (courier + status), billing `008`, marketing `002`
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
