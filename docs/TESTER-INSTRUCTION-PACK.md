# KitchCu — Tester Instruction Pack

**Step-by-step UI and API testing for every persona**

| Field | Value |
|-------|-------|
| Version | **1.1** |
| Date | 2026-09-17 |
| Audience | QA testers, release sign-off, founders doing a full pass |
| Companion PDF | [`docs/TESTER-INSTRUCTION-PACK.pdf`](./TESTER-INSTRUCTION-PACK.pdf) — `python scripts/generate_tester_instruction_pdf.py` |
| Aligned with | Complete Guide **v3.2.7** · Userflows **v1.6** · API.md **v1.2** · QA pack **v1.3** |

This pack is the **how to click / how to call** book. The existing [QA Instruction Pack](./QA-INSTRUCTION-PACK.md) is the short Must/Should checklist. Use **this** document when you need every numbered step.

**Product rule you must never fail:** KitchCu is owner-subscription SaaS. There is **no per-order food commission**. Do not file “missing commission %” as a bug.

**Out of scope (do not test / do not raise):** restaurant POS, dine-in, tables, waiters, KDS, bar, hotel features.

---

## 0. How to run a test session

1. Pick **one environment** (local Docker **or** production). Never mix credentials across them.
2. Confirm the stack is up (**§1**). If smoke fails, **stop** — do not continue deep UI/API.
3. Work persona by persona: Portal → Customer → Kitchen (owner) → Super Admin → **Sales** → store shells (if a device is available) → API (Swagger).
4. For every case write **Pass / Fail / Blocked** plus the exact URL, what you typed, and what you saw.
5. On Fail, fill the defect template in **§10**. Include screenshot + `X-Correlation-ID` from the Network tab if an API failed.

**Pass rule:** every **Must** case Pass. **Should** may Fail only with a written waiver.

**Browser:** Chrome or Edge. After a frontend rebuild, hard-refresh (`Ctrl+Shift+R`) or unregister the PWA service worker if the screen looks stale or black.

---

## 1. Lab setup (Must — do this first)

### 1.1 Local URLs

| Surface | URL | Who |
|---------|-----|-----|
| Marketing portal | http://localhost:13000 | Guest / prospect |
| Customer PWA | http://localhost:13001 | Diner |
| Kitchen (owner) PWA | http://localhost:13002 | Kitchen owner |
| Super Admin | http://localhost:13003 | Platform staff |
| **kitchCU - customers** (store) | Same as Customer PWA | Play/App `in.kitchcu.customer` |
| **kitchCU - kitchen owner** (store) | Same as Kitchen PWA | Play/App `in.kitchcu.kitchen` |
| **kitchCU - admin** (store) | Same as Super Admin | Play/App `in.kitchcu.admin` |
| API gateway | http://localhost:18000 | All clients |
| Swagger | http://localhost:18000/docs | API tester |
| ReDoc | http://localhost:18000/redoc | Read-only API |
| Portal OpenAPI explorer | http://localhost:13000/openapi | Non-technical API browse |

Production substitutes: `https://kitchcu.com`, `https://customer.kitchcu.com`, `https://kitchen.kitchcu.com`, `https://admin.kitchcu.com`, `https://api.kitchcu.com/docs`.

### 1.2 Confirm the stack

1. Open a browser tab to http://localhost:18000/health/live — expect HTTP 200 / `{"status":"ok"}` (or equivalent live payload).
2. Open http://localhost:18000/health/ready — expect 200. If this fails, **do not test UI**. Services are not ready.
3. Open each PWA URL in **§1.1**. Each must render (not a blank/black page, not a connection refused).
4. If a PWA is down: ask engineering to start Vite / `docker compose up -d`. Testers do not call service ports `18001–18012` directly.

### 1.3 Demo credentials (local / demo only)

| Persona | Identifier | Secret | Land on |
|---------|------------|--------|---------|
| Owner (primary) | `9876543210` | OTP `123456` | Kitchen `CKPNQ001` — Sharma Home Kitchen, Pune |
| Owner (alt) | `9876543211`–`9876543213` | OTP `123456` | Other seeded kitchens (use for tenant-isolation) |
| Customer (primary) | `9123456789` | OTP `123456` | Priya — discovery home |
| Customer (repeat) | `9123456780` | OTP `123456` | Rahul — richer order history |
| Customer (guest path) | `9988776655` | OTP `123456` | Ananya |
| Super Admin | `admin@kitchcu.dev` | `admin123456` | Admin Overview |
| Sales (field) | `sales@kitchcu.dev` | `sales123456` | Admin **Sales** only (extras seed; role `sales`) |

**Production:** Super Admin is `admin@kitchcu.com` + the live `ADMIN_PASSWORD`. OTP `123456` is **refused** when `APP_ENV=production`. Never use `.dev` on `*.kitchcu.com`.

**Demo OTP banner:** owner and customer sign-in should say demo mode does **not** send SMS/WhatsApp — enter `123456`. If the UI claims “OTP sent” and you wait for a phone message, that is a fail (ID-08 regression).

### 1.4 Seeded data you should already see

After `.\scripts\seed-all.ps1` or `$env:CKAC_BULK_MONTHS=6; python scripts/seed-bulk-data.py`:

- Primary kitchen **CKPNQ001** has months of orders (not only “today”).
- Owner **Reports** offers a **6-month** range; 90/180-day charts roll up to weeks/months.
- Owner **Orders** can filter 90 / 180 days.
- Owner **GST** has year options that match dated invoices.
- CRM has more than a handful of contacts on CKPNQ001.
- Public dish heroes are live-capture (no stock-photo venue as a hero). Drinks without a hero stay **inactive**.

If Reports look empty or CRM shows 0–2 profiles against hundreds of orders, the six-month seed was not applied or CRM refresh failed — **Blocked**, not “product empty state”.

---

## 2. Smoke (Must — ~15 minutes)

Do these in order. Fail on S1–S4 → stop the session.

| ID | Steps | Expected |
|----|-------|----------|
| S1 | Browser → gateway `/health/live` then `/health/ready` | Both 200 |
| S2 | Kitchen `:13002/login` → phone `9876543210` → Request OTP → enter `123456` → Continue | Lands Overview / Orders. Hero shows kitchen **name + CKPNQ001**. No blank screen |
| S3 | Customer `:13001/login` → `9123456789` → OTP `123456` | Discovery home loads kitchens / cities |
| S4 | Admin `:13003` → `admin@kitchcu.dev` / `admin123456` | Overview KPIs load. Sign in card shows username + password **when** reveal gate is on (`development`/`test` or `ADMIN_LOGIN_REVEAL_PASSWORD=1`) |
| S5 | Portal `:13000` | Brand hero; cities strip; no console crash |
| S6 | Gateway `/docs` | Schema loads. Public ops have **no padlock**. **Authorize → OAuth2Password** accepts the three demo logins in §1.3 |
| S7 | Admin logout → `sales@kitchcu.dev` / `sales123456` | Nav is **Sales + Kitchens only**. Overview / Employees / API Keys / Control **must not** appear. Overview KPIs must **not** load |
| S8 | Customer / Kitchen / Admin first-run tour | Overlay **Skip / Next / Done**. **Show tips** in the header restarts it. Completing or skipping does not block the page |

---

## 3. UI — Marketing portal (`:13000`)

**Must.** Guest, no login.

1. Open http://localhost:13000.
2. Confirm the **Kitchcu** brand hero (cream / teal / orange — not a generic purple splash).
3. Scroll: Features, How it works, cities presence (`#cities`), pricing, contact / support.
4. **Cities:** Live chips include Pune, Mumbai, Delhi, Gurugram, Noida, Lucknow, Kanpur, Prayagraj, Varanasi, Jhansi, Dehradun. Coming soon: Bengaluru, Hyderabad, Chennai, Kolkata.
5. Open **language** switcher. Switch **English → Hindi → English**. Visible chrome (nav, hero CTA, footer) must change, then restore.
6. Open `/openapi` (or `/api-docs`). The explorer loads the aggregated spec. You can read operations without a token.
7. Open `/terms`, `/privacy`, `/refund-policy`, `/platform-refund-policy`. Each page has policy text (not a 404).
8. Footer / tiles: links to customer and kitchen hosts resolve (new tab OK).
9. Support chat (if visible): options-first answers; raising a ticket must not crash the page.

**Fail if:** blank page, cities missing, Hindi switcher does nothing, `/openapi` is empty, legal routes 404.

---

## 4. UI — Customer PWA (`:13001`)

**Must** unless marked Should.

### 4.1 Login

1. Open http://localhost:13001/login.
2. Confirm demo-account strip / “enter 123456 — no SMS is sent”.
3. Type phone `9123456789`. Invalid phones (`12345`, `987654321011`) must be rejected **before** a success toast.
4. Request OTP. Banner still says demo — do **not** wait for WhatsApp.
5. Enter `123456` → submit.
6. You land on **discovery home** (`/`). Navbar shows the signed-in diner.

**Wrong OTP:** enter `000000` → error, stay on login.  
**Logout:** use account / nav logout → return to login or guest home; cart must not keep another diner’s items after a new login.

### 4.1b First-run tips (P55) — Must

1. After login, a **tour overlay** appears on discovery home (unless you already completed it in this browser).
2. Read step 1. Click **Next** through the remaining steps, or **Skip**.
3. After Done/Skip the overlay is gone. Header **Show tips** brings it back.
4. Completing the tour must **not** hide kitchens or change search results.

### 4.2 Discovery home

1. On `/`, confirm nearby / featured kitchens and the **cities** strip.
2. Type a dish or cuisine in search (e.g. `paneer` or `thali`). Wait ~1s (debounced). Results must include kitchens that serve that dish — not only name matches.
3. Click **Use my location** (allow browser permission). If you are far from Pune, you should still see a **nearest** fallback (“closest is N km away in *city*”) with visible cards — not a blank “No kitchens” with invisible list items.
4. Open a kitchen card (prefer **Sharma Home Kitchen / CKPNQ001**).
5. You reach `/kitchen/{id}/menu` or a branded `/k/CKPNQ001/menu`.

### 4.3 Menu and cart

1. Menu lists **active** dishes only. Inactive / draft dishes (no live hero) must **not** appear.
2. Each visible dish hero looks like that dish (not a dining-room photo, not the same salad bowl on every curry).
3. Add **one** dish, quantity 1. Cart drawer opens / badge increments.
4. Change quantity, then remove. Totals update. Empty cart has a clear empty state.
5. Add the dish again. Open checkout (`/checkout` or kitchen-scoped checkout).

### 4.4 Checkout and pay (dev)

1. Delivery address: use a Pune-area address if asked, or the seeded default.
2. Delivery quote appears (fee ≥ 0). Out-of-radius should **deny** or explain — not silently charge ₹0 forever without a message.
3. Optional: apply a seeded coupon if one is shown as active. Invalid code shows an error, not a crash.
4. Choose a pay path available in demo (dev capture / COD / UPI intent — whichever the screen offers).
5. Submit. You land on an order confirm page (`/orders/{id}/confirm` or master-order confirm).
6. Note the **order id / code**. You will need it for owner + track.

**Should — multi-kitchen (F06):** add one dish from CKPNQ001 and one from a second kitchen → checkout → **master receipt** id `MORD-…` plus per-kitchen sub-orders.

### 4.5 Orders, track, rate

1. Open **My orders** (`/orders`). While loading, you must see a **loader**, not a false empty page.
2. Empty state (if you used a brand-new diner) has title + hint + discovery CTA — not a blank white main.
3. Open a **delivered** order (seeded history on Priya / Rahul).
4. Track (`/t/{token}` if a tracking link is shown): status chip matches owner status.
5. Rate (`/orders/{id}/rate`) on a **delivered** order: set home-taste and quality 1–5, submit. Success; you cannot silently rate an undelivered order.
6. **Reorder** (if the button exists): cart fills with the previous lines.

### 4.6 Account, dashboard, branded storefront, live

1. `/account` — profile / addresses / UPI payout fields load; save persists after reload.
2. `/dashboard` — diner “My space” loads without a crash.
3. Open branded storefront http://localhost:13001/k/CKPNQ001 (or `/k/CKPNQ001/menu`). Brand name matches the kitchen. Menu is the public menu.
4. **Should — live:** if a session is live, `/live/{sessionId}` plays or shows an honest “not live” empty state (no fake countdown).

### 4.7 i18n (Should)

Switch `hi` on customer chrome. Nav, discovery headings, and empty-state strings change. Admin is English-only (do not expect Hindi there).

---

## 5. UI — Kitchen / owner PWA (`:13002`)

Login as `9876543210` / `123456` unless a step says otherwise. After login, kitchen context should prefer **CKPNQ001**.

### 5.1 Landing + login

1. Open http://localhost:13002 — marketing landing (not a crash).
2. Open `/login`. Demo strip lists owner phones. OTP story matches §1.3 (no fake SMS).
3. Login. Land on `/dashboard` (Overview) or inbox-first Orders — never a black screen.
4. Hero: kitchen **name + code CKPNQ001** on the left; primary CTAs (New order / Brand) **same row, top-right**.
5. **First-run tips:** overlay Skip / Next / Done; **Show tips** restarts. Must not block Orders.

### 5.2 Overview (`/dashboard`)

1. Greeting, subscription pill, drafts/live pills readable (no clip).
2. Recent orders list: rows are clickable; status chips use the real machine (`received` → `delivered` / `cancelled`).
3. Open a recent order → `/dashboard/orders/{id}`. Back returns to the list.

### 5.3 Orders (`/dashboard/orders`) — Must

1. Toolbar is visible: search, sort, tabs, filters.
2. Search by customer name or bill fragment — list shrinks; count updates.
3. Sort **Newest**, **Customer A–Z**, **Z–A**. Drafts tab also sorts.
4. Tabs: **Active / All / Drafts**. Drafts are unconfirmed intake, not live kitchen tickets.
5. Filters: status, source, date. Use **90 days** and **180 days** — seeded 6-month history must still show rows on CKPNQ001 (not an empty “today only” list).
6. Open one **received** or **accepted** order.
7. Advance status in order: `accepted` → `preparing` → `ready` → `out_for_delivery` → `delivered`. Do **not** skip backwards except **cancel**.
8. Cancel path: cancelled order leaves Active; appears under All / cancelled filter.
9. **New order** (`/dashboard/orders/new`): add a live dish, customer phone, place. Order appears in Active as `received`.
10. Draft remap (if a WhatsApp/text draft exists): remap is **disabled** until a matched item is chosen.

### 5.4 Menu (`/dashboard/menu`) and add dish

1. Search, sort, highlight + diet chips work; count updates.
2. Live dishes show a live-capture hero. Drafts without a hero stay off the public menu.
3. **Add dish** (`/dashboard/menu/new`): you cannot set a gallery/stock photo as the **hero** without live-capture. Camera / live-capture path is the honest path.
4. Save. Dish appears in the owner list. If it has no live hero it must stay **inactive**.

### 5.5 Ingredients + bulk prep (F19 / F19b) — Must

1. `/dashboard/ingredients` — pantry form (4-column). Add one ingredient. Adjust stock +100 then −10. Number updates; no 404.
2. **Low stock** chip hides healthy rows.
3. Select a dish → edit recipe lines (ingredient / qty / unit **above** controls) → save → reload persists. Pantry **kcal / 100** (or per piece) fills the running plate total. Optional calories note saves with the recipe. **Healthy** appears only when the map is complete, kcal ≤ the Super Admin Control cap (default 500), and health score ≥ the Control floor (default 65).
4. `/dashboard/prep` — modes **Order Ready** and **Bulk prep only**. No “Not Found”.
5. Mode **Order Ready**: helper text says orders deduct when marked Ready.
6. Create a combo batch (≥2 dishes, portions > 0). Table shows expanded ingredient lines.
7. Edit qty → save. Totals persist.
8. **Mark prepared** → status `prepared`; pantry stock **decreases**.
9. Switch to **Bulk prep only**. On a new order, mark **Ready** — stock must **not** drop. Only Mark prepared deducts.
10. Back on **Order Ready**: first Ready deducts **once**. Repeat Ready does not double-deduct. Accept does **not** deduct (warnings OK).

### 5.6 Reports, ratings, GST, payments

1. `/dashboard/reports` — choose **6 months**. Revenue / top dishes / peak hours populate from seed (not a flat zero). 90/180-day views roll up (not 180 unreadable daily bars). Period-over-period hides if the prior window is empty.
2. `/dashboard/ratings` — aggregates load; empty state is honest if a kitchen has no ratings.
3. `/dashboard/gst` — year selector includes seeded invoice years. Export Excel/PDF **Should** download without 500.
4. `/dashboard/payment-gateway` — kitchen Razorpay / Route fields (not platform SaaS secrets). Settlements list + status filter if data exists.

### 5.7 CRM, coupons, tiffin, templates, brand

1. `/dashboard/crm` — search; sort Spend / Orders / Name; VIP / Repeat / Tagged chips. CKPNQ001 after a 6-month seed must **not** be empty.
2. `/dashboard/coupons` — create a test code, set active, save. List search + Active/Inactive chips.
3. `/dashboard/tiffin` — plans list; combo plans need ≥2 dishes; single-dish = 1. Customer request / accept path **Should**.
4. `/dashboard/templates` — list WhatsApp/email templates; dropdowns use the themed chevron (not a raw system control).
5. `/dashboard/brand` — branded page fields; open customer `/k/CKPNQ001` and confirm the public page matches.

### 5.8 Setup, growth, learning, community, stream, referrals, WhatsApp, plan

1. `/dashboard/setup` — name, address, map pin stay editable. **Kitchen code does not change** after save.
2. `/dashboard/growth` — suggestions / combos / patterns. Empty state allowed if the kitchen has no qualifying data; crash is a fail.
3. `/dashboard/learning` — modules load (package-gated; empty/locked state OK).
4. `/dashboard/community` — recipe list; no 500 splash.
5. `/dashboard/stream` — go-live / sessions. **No publisher token** dumped on screen.
6. `/dashboard/referrals` — owner referral code / leads load.
7. `/dashboard/whatsapp` — kitchen `phone_number_id` (not Meta app secret).
8. `/dashboard/subscription` — current SaaS plan. No per-order commission line.

### 5.9 Tenant isolation (Must)

1. Log out. Log in as `9876543211`.
2. Orders, CRM, ingredients, prep batches, GST must belong to **that** kitchen only. You must never see CKPNQ001’s customers or bill ids.
3. Log back in as `9876543210` and confirm the reverse.

### 5.10 Layout polish (Must)

1. Owner panels use the **full** board width (not a ~560px stub).
2. Listing **Sort** dropdowns show chevron + theme fill.
3. Table headers align with cells. No nested card-in-card double shadow on CRM / Ingredients.

---

## 6. UI — Super Admin (`:13003`)

Admin UI stays **English**. Login `admin@kitchcu.dev` / `admin123456`.

### 6.1 Sign in

1. Open http://localhost:13003.
2. Username + password are printed / prefilled **only** when `APP_ENV` is `development`/`test` **or** `ADMIN_LOGIN_REVEAL_PASSWORD=1`. Local Docker should show them.
3. Confirm links to Swagger, ReDoc, and portal `/openapi`.
4. Sign in. Overview loads KPIs (owners, kitchens, customers, orders, open refunds).
5. Expired / cleared token returns you to Sign in (not a broken shell).

### 6.2 Walk every top tab

For each tab: open it, wait for load, confirm no white-crash, then do the action.

| Tab | What to do | Expected |
|-----|------------|----------|
| Overview | Read tiles; click an attention tile | Navigates to the matching tab |
| Kitchens | Search `CKPNQ001`; open kitchen workspace | Profile shows name + **immutable code** |
| Owners | Search `9876543210` | Raj Sharma / CKPNQ001 linked |
| Customers | Search `9123456789` | Profile, addresses, recent orders, tickets |
| Orders | Filter by kitchen or customer | Platform list; no owner “mark ready” mutation |
| Refunds | Open list + settlements | Status chips; no 500 |
| Tickets | Open one ticket | Assignee / priority / reply fields; deep-link to kitchen |
| Packages | View feature → package → plan map | Read-only OK without `packages:write` |
| Employees | List staff | Write hidden without `employees:write`; role list includes **sales** |
| Sales | Onboard owner+kitchen; tick Train | Kitchen code issued; playbook 8 steps; other sales cannot open it |
| API Keys | Open a key | Value **masked** after save — never full secret |
| Referrals | Settings + leads | Loads; settings save **Should** if you have write |
| Control | Flags / journeys / Dish calories & Healthy | Toggles persist; kcal cap saves; no raw secrets |
| Audit | Recent admin actions | Sensitive writes appear; no OTP/token in the log text |

### 6.3 Kitchen workspace (open CKPNQ001)

Open each workspace tab and confirm it loads:

| Tab | Check |
|-----|-------|
| Profile | Status, address, branded summary; **code cannot be edited** |
| Train | 8-step owner playbook; sales can tick kitchens they onboarded |
| WhatsApp | Kitchen phone number id only — not Meta app secret |
| Payments | Kitchen Razorpay / Route — not platform SaaS Razorpay |
| Modules | Per-kitchen module flags |
| Package | Assigned package + feature checklist |
| Marketing | Template / broadcast summary |
| Streaming | Session summary — **no publisher token** |
| Orders / Care | Recent orders + open tickets / refunds strip |
| GST | Profile / report / export paths load |

Admin must **not** mutate owner menu items or cook-line status from this console.

### 6.4 Sales onboard + Train (P55) — Must

Use a **fresh** browser profile or log out of Super Admin first. Seed extras so `sales@kitchcu.dev` exists (`.\scripts\seed-all.ps1` or `python scripts/seed_platform_extras.py`).

1. Open http://localhost:13003. Sign in `sales@kitchcu.dev` / `sales123456`.
2. Nav shows **Sales** and **Kitchens** only. **Fail** if Overview, Employees, API Keys, Control, Packages, Refunds, or Audit appear.
3. Open **Sales**. Form: owner name, phone, kitchen name, address, city, map pin.
4. Use a **new** 10-digit phone that is not a seeded owner (e.g. `9000012345`). Submit **Onboard**.
5. Success: a kitchen **code** (`CK…`) is issued. The kitchen appears in **this sales book**.
6. Open that kitchen → **Train**. Confirm **8 steps**:
   1. Kitchen profile is true
   2. Live-capture a dish hero
   3. Map the first recipe
   4. Set delivery radius
   5. Owner KYC photos
   6. Place a test order
   7. WhatsApp number check
   8. Owner can login alone
7. Tick step 1 (profile). Count becomes **1/8**. Reload persists.
8. Open **Kitchens** as this sales user: you see **only** kitchens you onboarded (plus none of CKPNQ001 unless you onboarded it).
9. Log out. Log in as Super Admin. Employees lists role **sales**. Kitchen workspace **Train** still shows the ticks.
10. **Isolation (Should if a second sales user exists):** another `sales` JWT must get **403** on this kitchen’s training PATCH.

Training ticks **do not** block the kitchen going live.

### 6.5 Store apps (P55) — Must when a device/emulator is available

Three **different downloads**. Product is still the PWA; the shell only opens the matching host.

| Store name | Package / bundle | Host |
|------------|------------------|------|
| **kitchCU - customers** | `in.kitchcu.customer` | `customer.kitchcu.com` · local `:13001` |
| **kitchCU - kitchen owner** | `in.kitchcu.kitchen` | `kitchen.kitchcu.com` · local `:13002` |
| **kitchCU - admin** | `in.kitchcu.admin` | `admin.kitchcu.com` · local `:13003` |

1. Confirm three **distinct** application ids (installing customers must not replace kitchen owner).
2. Customer app lands on the diner PWA (discovery / login). Kitchen owner app lands on owner login. Admin app lands on Super Admin / Sales.
3. If Play TWA: `https://{host}/.well-known/assetlinks.json` lists that package’s SHA-256. If iOS: AASA lists the bundle id (replace `TEAMID` before store submit).
4. Play hosting steps (engineering, not a tester click-path): `apps/android/README.md` — three Play Console apps, three AABs (`bundleCustomerRelease` / `bundleKitchenRelease` / `bundleAdminRelease`), app-signing SHA-256 into Digital Asset Links.

**Web still counts as the product:** first-run tips, Sales, calories/Healthy, checkup diet filter are on the PWAs. Store shells do not ship a second checkout.

---

## 7. API testing — Swagger (Must)

Public clients use the **gateway only**: http://localhost:18000. Do not call `:18001`–`:18012` from the browser.

### 7.1 Open the contract

1. Open http://localhost:18000/docs (Swagger).
2. Confirm the filter box and **Authorize** button.
3. Scan a few tags (`Identity: Auth`, `Order`, `Billing`). Every operation should have a summary.
4. Open http://localhost:18000/redoc — read-only render of the same spec.
5. Open http://localhost:13000/openapi — portal explorer, same schema.
6. After a gateway restart, `GET http://localhost:18000/openapi.json?refresh=true` if a new route is missing.

### 7.2 How padlocks work

| What you see | Meaning | What you do |
|--------------|---------|-------------|
| **No padlock** | Public (`security: []`) | Try it out **without** Authorize. A leftover token must **not** be sent |
| Padlock | JWT required | Authorize first, then Try it out |
| Optional | Token optional | Works anonymously; richer with a token |

### 7.3 Authorize (do this before protected calls)

1. Click **Authorize**.
2. Prefer **OAuth2Password** (`POST /api/v1/auth/token`):
   - Owner: username `9876543210`, password `123456`.
   - Customer: username `9123456789`, password `123456`.
   - Admin: username `admin@kitchcu.dev`, password `admin123456`.
   - Sales: username `sales@kitchcu.dev`, password `sales123456` (same token endpoint; JWT `type=admin`, role `sales`).
3. Click Authorize / Close.
4. Alternative: obtain a JWT from login/OTP verify, then paste **only** the token into **HTTPBearer** (Swagger adds `Bearer`).
5. Logout of Authorize (or close the token) before switching persona — **do not** call owner routes with a customer token.

`401` = missing / wrong / wrong `type`. `403` = valid JWT but not this kitchen or RBAC denied. Treat them as different results.

### 7.4 Public API steps (no token)

1. Clear Authorize (so you are anonymous).
2. `GET /health/live` → 200. Confirm the request has **no** `Authorization` header.
3. `GET /health/ready` → 200.
4. Discovery / public kitchen read (paths marked public, e.g. nearby / public kitchen / public community recipes) → 200, not 401.
5. `GET /api/v1/community/recipes` → 200 and a list (or `[]`). **Must not 500** (orphan recipes are skipped).
6. Dummy UUID on a public detail route → **404**, not 500.

### 7.5 Owner API steps

1. Authorize as owner (`9876543210` / `123456`).
2. `GET /api/v1/owners/me` → 200, owner profile. **Must not** succeed with a customer token (switch token and expect 401).
3. From `/owners/me` or kitchens list, copy the **CKPNQ001 kitchen id**.
4. `GET /api/v1/kitchens/{kitchen_id}/orders` → 200, seeded history (not only today).
5. `GET /api/v1/kitchens/{kitchen_id}/analytics` (or reports/analytics path in the spec) → 200; 6-month style series present if seeded.
6. `GET /api/v1/kitchens/{kitchen_id}/menu` or dishes → 200.
7. `GET /api/v1/kitchens/{kitchen_id}/crm/contacts` (or CRM list in the spec) → 200; after 6-month seed this is **not** 0–2 rows on CKPNQ001.
8. `GET /api/v1/kitchens/{kitchen_id}/stock-settings` → 200 (not identity 404).
9. `GET /api/v1/kitchens/{kitchen_id}/prep-batches` → 200.
10. `GET /api/v1/kitchens/{kitchen_id}/gst/...` export or report path → 200 or an honest 404/422, **not 500**.
11. Open a real order id from step 4. `PATCH`/`POST` status **only** if you intend to mutate. Prefer advancing a **new** manual order, not rewriting six-month history.
12. Call the same orders URL with kitchen id of **another** owner (`9876543211`) while still holding CKPNQ001’s token → **403**, not 200.

### 7.6 Customer API steps

1. Authorize as customer (`9123456789` / `123456`).
2. Customer `me` / dashboard / orders list → 200.
3. `GET /api/v1/billing/refunds/customer/me` → 200 and a **JSON list** (`[]` is OK). **Must not 500**.
4. Owner-only route (e.g. `GET /owners/me` or kitchen CRM) → **401**.
5. Place/list flows that require `{order_id}`: use an id from the customer’s own history. A random UUID → 404.

### 7.7 Admin API steps

1. Authorize as admin (`admin@kitchcu.dev` / `admin123456`).
2. `GET /api/v1/admin/me` → 200, `allowed_tabs`.
3. `GET /api/v1/admin/stats` → 200.
4. `GET /api/v1/admin/kitchens?q=CKPNQ001` (or equivalent search) → 200, contains Sharma Home Kitchen.
5. `GET /api/v1/admin/customers?q=9123456789` → 200.
6. `GET /api/v1/admin/orders` → 200.
7. `GET /api/v1/admin/refunds` → 200.
8. `GET /api/v1/admin/tickets` → 200.
9. `GET /api/v1/admin/auth/login-hint` → password field present locally when reveal=1; production without the flag hides it.
10. Repeat **one** admin GET with the **owner** token → **401**.
11. `GET /api/v1/internal/anything` via gateway → **404** (never proxied).
12. **Sales (P55):** Authorize as `sales@kitchcu.dev` / `sales123456`.
    - `GET /api/v1/admin/me` → 200; `allowed_tabs` is **sales** + **kitchens** only.
    - `GET /api/v1/admin/stats` → **403**.
    - `POST /api/v1/admin/sales/onboard` with a unique owner phone + kitchen pin → **201**, kitchen code.
    - `GET /api/v1/admin/kitchens/{id}/training` → 8 steps.
    - `PATCH /api/v1/admin/kitchens/{id}/training` body `{ "key": "profile", "completed": true }` → completed ≥ 1.
    - Super-admin token can read any kitchen training; a **different** sales token → **403**.

### 7.8 Negative / security API (Must)

1. Protected route with no Authorize → 401.
2. Garbage Bearer `abc` → 401.
3. Customer token on owner route → 401.
4. Owner token on admin route → 401.
5. Owner token on another kitchen’s write → 403.
6. Webhooks: do **not** send unsigned production-like payloads. Local WhatsApp POST may accept unsigned bodies; production must fail closed.

### 7.9 Automated auth audit (Should for API testers)

From the repo root, with the gateway up:

```powershell
python scripts/audit-api-auth.py
```

Expect **0 FAIL**. INFO rows on webhooks are allowed. Any FAIL is a release blocker.

Do **not** run `.\scripts\run-tests.ps1` or identity/community/billing pytest on a shared demo DB if you were told to **keep the 6-month seed** — those suites TRUNCATE kitchens/orders/billing.

---

## 8. Cross-cutting UI + API cases

| ID | Type | Steps | Expected |
|----|------|-------|----------|
| X1 | Security | Owner JWT against `/api/v1/admin/stats` | 401 |
| X2 | Security | Gateway logs during OTP login | No OTP, no full token, no full raw phone dump |
| X3 | Observability | Send `X-Correlation-ID: qa-demo-1` on any gateway call | Same id on the response |
| X4 | Isolation | Owner A CRM vs owner B | No shared rows |
| X5 | i18n | Portal + customer `en` / `hi` | Chrome strings change; admin stays EN |
| X6 | Cities | Portal, customer home, kitchen landing | Same live / coming-soon set |
| X7 | Media truth | Customer menu vs owner menu | Public heroes match the dish; drafts stay off the diner menu |
| X8 | Commission | Owner subscription + reports | No “platform commission % of food” line |
| X9 | Sales scope | Sales JWT vs `/admin/stats` and `/admin/api-keys` | 403 |
| X10 | Tours | C / O / A first-run overlay | Skip or complete; Show tips restarts |

---

## 9. Production extras (when testing `*.kitchcu.com`)

1. `GET https://api.kitchcu.com/health/ready` → 200.
2. Open all five hosts (portal, www, customer, kitchen, admin).
3. Admin login is `admin@kitchcu.com` only.
4. Confirm OTP `123456` is **rejected**.
5. Do not paste production API secrets into tickets or chat.
6. Prefer the current **weekly QA cohort** phones (`7{YY}{WW}…` owners, `8{YY}{WW}…` customers) if ops provided them — see [PRODUCTION-PORTALS-CREDENTIALS-QA.md](./PRODUCTION-PORTALS-CREDENTIALS-QA.md).
7. Store listings (when published): three Play URLs for `in.kitchcu.customer` / `.kitchen` / `.admin`. Do not treat a single “KitchCu” APK as a pass.

---

## 10. Defect template

```text
Title:
Environment: local | production
Surface: portal | customer | kitchen | admin | store app | Swagger | other API
Case ID: (e.g. 5.3 step 7)
Severity: S1 blocker | S2 major | S3 minor | S4 polish
Steps:
1.
2.
3.
Expected:
Actual:
URL:
Request (method + path):
Status / body:
X-Correlation-ID:
Screenshot:
Workaround:
```

---

## 11. Sign-off

| Role | Name | Date | Verdict | Notes |
|------|------|------|---------|-------|
| Tester | | | Pass / Fail | |
| QA Lead | | | Go / No-Go | |
| Eng / CTO | | | | |

**Go criteria:** §2 smoke Pass (including S7 sales + S8 tours); §4 customer Must Pass; §5 owner Must (orders, stock, isolation, reports seed) Pass; §6 admin tabs + kitchen workspace + **§6.4 Sales** Pass; §6.5 store ids Pass when a device is in the run; §7 API public/owner/customer/admin/sales + negatives Pass; §8 X1–X4, X8–X10 Pass.

---

## 12. Cross-references

| Need | Doc |
|------|-----|
| Short Must/Should checklist | [`QA-INSTRUCTION-PACK.md`](./QA-INSTRUCTION-PACK.md) |
| Journeys (screens + events) | [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) |
| Auth / OpenAPI cheat-sheet | [`API.md`](./API.md) §1.1–1.2 |
| Prod URLs + feature matrix | [`PRODUCTION-PORTALS-CREDENTIALS-QA.md`](./PRODUCTION-PORTALS-CREDENTIALS-QA.md) |
| Seed + credentials | [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md) |
| Product encyclopedia | [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) v3.2.7 |
| Store shells | [`apps/android/README.md`](../apps/android/README.md) · [`apps/ios/README.md`](../apps/ios/README.md) |

---

## Document control

| Change | Date |
|--------|------|
| P55 — store apps (kitchCU - customers / kitchen owner / admin), sales onboard + Train, first-run tips, sales API | 2026-09-17 |
| Initial tester pack — numbered UI + Swagger/API steps for all personas | 2026-09-12 |
