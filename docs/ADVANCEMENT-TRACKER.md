# KitchCu Advancement Tracker

**Living release board** — sprint baseline + post-S18 product increments. Update this file whenever a feature ships to website, APIs, seed, or docs.

| Field | Value |
|-------|-------|
| Baseline | Phase 1 **S1–S18** complete (gateway + 13 domain services + 4 PWAs + GST) |
| Production | `*.kitchcu.com` (GCP VM + Caddy) |
| Local demo | `*.kitchcu.in` / `admin@kitchcu.dev` |
| Last updated | 2026-07-19 |
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

## Platform snapshot (2026-07-19)

| Layer | State |
|-------|-------|
| Edge | Gateway `:18000` — CORS, correlation ID, OTP rate limits |
| Domains | 13 services (identity→streaming) — schema-per-domain + outbox EDD |
| PWAs | portal / customer / kitchen / admin under `apps/website/` |
| Delivery | Cost-share + Self/Porter modes; book on accept (P32/P32.1) |
| Trust | Admin RBAC + audit · hard package entitlements · LiveKit Watch |
| Open | Kitchen staff · live Razorpay / prod OTP · Porter webhooks · Wave C/D |

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
| P19 | **Branded kitchen storefront** | Identity `branded_page` · customer `/k/:code` · owner Overview publish | ✅ | Shareable brand page → menu/checkout |
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
| Branded storefront | `ensure_branded_page` | ✅ |
| Streaming + dish showcase | `ensure_streaming(..., dish_id=)` | ✅ |
| Growth suggestions (incl. golden day when data qualifies) | `ensure_growth_suggestions` | ✅ |
| Platform features / seed packages | billing migration `008` seed | ✅ |
| Learning trials / community | extras | ✅ |

---

## Next (prioritized — see strategic analysis)

| Wave | Item | Doc |
|------|------|-----|
| **A (trust)** | ✅ RBAC+tabs+hard entitlements · ✅ audit (+ billing writes) · ⏳ live Razorpay / prod OTP | [PLATFORM-SOLUTION-BLUEPRINT.md](./PLATFORM-SOLUTION-BLUEPRINT.md) E3 |
| **B (promises)** | ✅ Template send + fan-out + wallet · ✅ Meta outbound · ✅ Watch/LiveKit · ✅ Porter cost-share · ⏳ kitchen staff · ⏳ Porter webhooks | Solution Blueprint A2/B2 |
| **C (design)** | E1–E2 Kitchen Quality Loop | [E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| **D (scale)** | Cloud Run architecture · OTel · load SLOs | [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §1–10 |

---

## Release gate (kitchcu.com)

- [x] Admin login uses `admin@kitchcu.com` on production hosts (UI + env sync)
- [x] Seed covers integrations, branded page, dish showcase
- [x] Advancement tracker maintained (P19–P32.1)
- [x] Migrations ready: identity `013`–`017` (RBAC + audit + WA token + subsidy), order `007` (courier), billing `008`, marketing `002`
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
