# KitchCu — Production Portals, Credentials & Feature QA

**Audience:** CEO · CPO · CTO · QA · Ops · Support  
**Last updated:** 2026-09-07  
**Related:** [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) · [QA-INSTRUCTION-PACK.md](./QA-INSTRUCTION-PACK.md) · [ADVANCEMENT-TRACKER.md](./ADVANCEMENT-TRACKER.md)

This pack is the single place for **production portal URLs**, **who logs in where**, **demo vs production credentials policy**, and a **feature → responsibility → test steps** matrix.

---

## 1. Production portals (`*.kitchcu.com`)

| Surface | URL | Who uses it | Responsible for |
|---------|-----|-------------|-----------------|
| **Marketing portal** | https://kitchcu.com | Prospects, owners exploring SaaS | Brand story, features, cities presence, pricing, pilot contact, support chat |
| **WWW alias** | https://www.kitchcu.com | Same as portal | Canonical redirect / same app |
| **Customer PWA** | https://customer.kitchcu.com | Diners | Discovery by city/GPS, kitchen code, cart, checkout, track, rate, My space |
| **Kitchen (owner) PWA** | https://kitchen.kitchcu.com | Kitchen owners / chefs | Day ops: orders, menu (incl. drafts), setup/profile, ratings, brand page, CRM, reports, WhatsApp, payments |
| **Admin console** | https://admin.kitchcu.com | Platform employees | Super Admin / RBAC ops, kitchens, tickets, rate limits, API keys |
| **API gateway** | https://api.kitchcu.com | All clients (via PWAs) | `/api/v1/*`, OpenAPI `/docs`, health |
| **Media** | https://media.kitchcu.com | Signed/public media | Dish heroes, QR uploads (when configured) |

Local equivalents (dev): portal `:13000` · customer `:13001` · kitchen `:13002` · admin `:13003` · gateway `:18000`.

---

## 2. Credentials policy

### 2.1 Local / demo stack (safe to share with QA)

| Persona | Login | Secret | Notes |
|---------|-------|--------|-------|
| **Owner** | Phone `9876543210` | OTP `123456` | Primary kitchen `CKPNQ001` (Pune). Extra owners `9876543211`–`9876543213` |
| **Customer** | Phone `9123456789` | OTP `123456` | Also `9123456780`, `9988776655`, `9123456781`, `9123456782` |
| **Super Admin** | `admin@kitchcu.dev` | `admin123456` | Dev only — never use on production |

Seed: `.\scripts\seed-all.ps1` (includes multi-city kitchens: Delhi, Gurugram, Noida, Dehradun, Prayagraj, Varanasi, Kanpur, Lucknow, Jhansi, Mumbai).

### 2.1b Weekly QA cohort (fresh accounts every Monday)

A systemd timer on the VM seeds a new set of test accounts each ISO week and leaves
earlier cohorts intact, so QA never has to reuse dirty accounts. Numbers are derived
from the ISO year + week — `{prefix}{YY}{WW}{index}`, owners `7…`, customers `8…`.

| Persona | Login pattern | Example (2026-W37) | Secret |
|---------|---------------|--------------------|--------|
| **Owner** (5/week) | `7{YY}{WW}{00001…}` | `7263700001` … `7263700005` | OTP `123456` |
| **Customer** (10/week) | `8{YY}{WW}{00001…}` | `8263700001` … `8263700010` | OTP `123456` |

Each run also produces, per cohort kitchen:

| Data | Volume | Why QA needs it |
|------|--------|-----------------|
| Kitchen + full menu | 1 kitchen, rotating city | Discovery, menu, and storefront screens |
| Delivered orders | 10 per kitchen | Owner inbox, analytics, revenue, receipts |
| Diner mix | ~⅔ this week's new, ~⅓ last week's returning | CRM `repeat`/`vip` segments are non-empty |
| Ratings | one per delivered order | Home-taste aggregates, dish scores |
| Coupon | `QA{cohort}` (e.g. `QAW2636`) | Checkout discount path; earlier QA codes are deactivated so only one is live |
| Promotion | `QA cohort {tag} special`, 7-day window | Targeted-promo surfaces; previous cohort's promo is ended |
| Tiffin plan + subscription | 1 plan, 1 subscriber | Owner subscription inbox, customer subscriptions tab |
| Growth suggestions | generated from the week's orders | Combos, patterns, suggestion cards |
| Support ticket | 1 open | Support triage queue |

The current week's cohort and per-kitchen totals are written to
`/var/lib/ckac/weekly-cohort.json` on the VM.

Preview locally without touching the API: `python scripts/weekly_test_data.py --dry-run`.
Override volumes with `--owners`, `--customers`, `--orders-per-kitchen`, `--week 2026-W40`.

### 2.1c Bulk demo seed (first boot + on demand)

First boot with metadata `run-seed=1` runs `infra/gcp-vm/bulk-seed.sh` → `scripts/seed-bulk-data.py` (default 30 kitchens, full extras). Dishes without a live-capture hero stay inactive; orders use active dishes only. Re-run on the VM:

```bash
gcloud compute ssh ckac-vm --zone=asia-south1-a --command="sudo systemctl start kitchcu-bulk-seed.service"
```

Locally: `python scripts/seed-bulk-data.py` or `.\scripts\seed-bulk-data.ps1`. Cron install: [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §11.7c.

### 2.2 Production (`*.kitchcu.com`)

| Persona | Login | Secret | Notes |
|---------|-------|--------|-------|
| **Super Admin** | `admin@kitchcu.com` | From GCE / Secret Manager (`ADMIN_PASSWORD`) | See [DEPLOYMENT-GCP.md](./DEPLOYMENT-GCP.md) §7. **Not** `admin@kitchcu.dev` |
| **Owner** | Owner WhatsApp / phone | Real OTP via WhatsApp (or provider) | Fixed OTP `123456` is **disabled** when `APP_ENV=production` |
| **Customer** | WhatsApp OTP or social OAuth | Provider-issued | Same production OTP posture |
| **API / payments** | — | Razorpay + WhatsApp + OAuth secrets in Admin → Control → API Keys | Masked after save |

**Never commit production passwords or live API secrets to git.**

### 2.3 How to hit the API (docs + login-required routes)

| Docs | Local | Production |
|------|-------|------------|
| Swagger | http://localhost:18000/docs | https://api.kitchcu.com/docs |
| ReDoc | http://localhost:18000/redoc | https://api.kitchcu.com/redoc |
| Portal explorer | http://localhost:13000/openapi | https://kitchcu.com/openapi |
| Super Admin (shows username/password + these links) | http://localhost:13003 | https://admin.kitchcu.com |

1. Open Super Admin — username and password are printed on the Sign in card (and prefilled locally).
2. `POST /api/v1/admin/auth/login` with that email + password → `access_token`.
3. Swagger **Authorize** → paste the JWT. Or `Authorization: Bearer <token>` on curl.
4. Owner/customer routes use OTP (`123456` in demo), not the admin password.

Full cheat-sheet: [`API.md`](./API.md) §1.1.

---

## 3. Cities presence

Marketing + customer surfaces show **Our presence in cities** (`#cities`):

| Status | Cities |
|--------|--------|
| **Live** | Pune, Mumbai, Delhi, Gurugram, Noida, Lucknow, Kanpur, Prayagraj, Varanasi, Jhansi, Dehradun |
| **Coming soon** | Bengaluru, Hyderabad, Chennai, Kolkata |

Data: `apps/website/src/data/citiesPresence.ts` · kitchen codes: identity `CITY_CODES`.  
Shown on: portal home, kitchen landing (owner marketing / services), customer discovery home.

---

## 4. Multilingual support

| Item | Detail |
|------|--------|
| Locales | `en` `hi` `mr` `ta` `te` `kn` `ml` `bn` `gu` `pa` `bho` `mai` |
| Parity gate | `python scripts/check-i18n-locale-parity.py` |
| Sync missing keys | `python scripts/sync-i18n-missing-keys.py` |
| Admin UI | English only (product policy) |
| Quality bar | Hindi + English; other locales may mirror EN until MT pass |

---

## 5. Feature matrix — responsibility & test steps

Legend: **O** = Owner · **C** = Customer · **A** = Admin · **P** = Platform/system

### 5.1 Orders & intake (F01–F06)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F01 | WhatsApp order capture | Turn WA messages into drafts for O | Seed webhook / paste sample order → O sees draft → confirm → order created |
| F02 | Normal message order | Same for free-text intake | Submit unstructured text → draft items parse → confirm |
| F03 | Manual order | O creates walk-in / phone order | Kitchen → New order → add dishes → place → appears in Active |
| F04 | Order lifecycle | Status machine received→delivered | Advance each status; C track page updates; cancel path |
| F05 | Order history | Past orders for O/C | O All tab; C My orders; filters work |
| F06 | Multi-kitchen checkout | One cart / master receipt | C add from 2 kitchens → checkout → sub-orders + master id |

### 5.2 Growth & reports (F07–F12, F39)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F07 | Revenue report | O sees money in / trends | Reports page · 7d KPI matches completed orders |
| F08 | Top dishes | Best sellers | Reports → top dishes after seeded sales |
| F09 | Combos | Suggested dish pairs | Growth tips / intelligence shows combos |
| F10 | Order patterns | Repeat behaviour | CRM / patterns after multiple C orders |
| F11 | Growth suggestions | Actionable tips | Home / Growth tips list non-empty or empty state |
| F12 | Performance + recipes | Golden days / pins | Pin golden recipe from home |
| F39 | Daily menu push | WA daily menu | Owner templates / daily menu send path (dev mock OK) |

### 5.3 Menu & media (F13–F15, F19)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F13 | Live-capture dish photo | Trust hero images | Add dish with live flag / camera path |
| F14 | Price & quality copy | Dish detail honesty | Edit price, prep time, description |
| F15 | Categories | Menu organisation | Filter by category on menu |
| F19 | Ingredient mapper | Stock deduct on accept/prepared | Accept order → stock drops; low-stock warn |
| F19b | Bulk prep batches | Cook once, many portions | Prep batches → mark prepared → ready stock |

### 5.4 Ratings & community (F16–F18, F21–F24)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F16–F18 | Home-taste ratings | Post-delivery trust | Deliver order → C rate → aggregates update |
| F21 | Learning portal | Curated learning | O Learning nav loads modules |
| F22 | Dish trials | Sample promote | Create trial → invite C |
| F23 | Recipe rewards | Share for points | Community submit / reward |
| F24 | Chef rankings | City leaderboard | Rankings scope=city |

### 5.5 Delivery (F27–F31)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F27–F28 | Radius & fee quote | Fair delivery fee | Quote at checkout; out-of-radius denied |
| F29 | Tracking + intervals | C track link / reminders | Out for delivery → track URL; notify intervals |
| F30–F31 | Prep/delivery time + distance | Honest ETA | Dish times; map distance fee |

### 5.6 Customer discovery & loyalty (F32–F38)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F32 | Discovery | Near you / featured / code | C home search; city kitchens; `#cities` section |
| F33 | History + reorder | One-tap repeat | Orders → Reorder → cart filled |
| F34–F35 | Tiffin / meal plans | Monthly subscriptions | C plans tab; O tiffin plans CRUD |
| F36–F38 | Coupons / CRM / promos | Owner-owned offers | Create coupon → apply at checkout; CRM list |

### 5.7 Payments & billing (F42–F44) + refunds / GST

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F42–F43 | Online pay / UPI / COD | Collect payment | Checkout intent; owner UPI path |
| F44 | Split settlement | Multi-kitchen pay split | Multi-kitchen pay → settlements |
| Refunds | Full/partial refunds | O refund → C payout details | C Account UPI → O refund → status |
| GST | Invoices / export | Compliance | O GST page; admin export if enabled |
| Subscriptions | Owner SaaS plans | Platform revenue | O Your plan; admin package sales |

### 5.8 Notifications & live (F45–F48)

| ID | Feature | Responsible for | Test steps |
|----|---------|-----------------|------------|
| F45 | App + WA notifications | Status updates | Order status change → notify log / WA mock |
| F46–F48 | Live streaming | Opt-in cook live | O Go live settings; C live filter / watch |

### 5.9 Platform & trust

| Area | Responsible for | Test steps |
|------|-----------------|------------|
| Identity / OTP | Auth for O/C | Request + verify OTP; invalid phone rejected |
| Admin RBAC | Platform ops | Admin login; expired JWT returns to sign-in; write buttons hidden without `*:write`; kitchen Streaming tab has no publisher token |
| Kitchen profile | Owner + admin | Setup name/address/pin stay editable after create; kitchen **code** does not change |
| Gateway rate limits | Abuse protection | Burst OTP from a browser → 429; admin preset for test phase. On-host ops traffic (seed scripts hitting `127.0.0.1:18000` with no `X-Forwarded-For`) is exempt — anything arriving through Caddy is not |
| i18n | Language switcher | Switch hi/en on portal + customer; labels update |
| Support AI | FAQ / tickets | Portal chat options → answer; raise ticket |
| Cities presence | Expansion signal | Portal / kitchen / customer show Live + Coming soon chips |
| Tenant isolation | Security | Owner A cannot read kitchen B orders |

---

## 6. Smoke checklist (production)

1. `GET https://api.kitchcu.com/health/ready` → OK  
2. Open each portal URL (portal, customer, kitchen, admin) → 200  
3. Admin login with production email/password only  
4. Create or use a real owner kitchen → publish brand page  
5. Customer discovery shows cities section; search works  
6. Place one paid/test order end-to-end in a non-prod kitchen if available  
7. Confirm `APP_ENV=production` rejects OTP `123456`

---

## 7. Regenerate PDF

```bash
python scripts/generate_production_portals_pdf.py
```

Output: `docs/PRODUCTION-PORTALS-CREDENTIALS-QA.pdf`
