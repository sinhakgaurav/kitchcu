# KitchCu — Persona, Flow, Architecture & Implementation Deep Dive

**Living document.** Written as if each role used the product for a week, then the CEO/CPO/CTO staff synthesized what to keep, fix, and build.  

| Companion | Job |
|-----------|-----|
| [`PLATFORM-ARCHITECTURE-FLOWS.md`](./PLATFORM-ARCHITECTURE-FLOWS.md) | **Current topology, persona flows, events, scorecard** |
| [`PLATFORM-SOLUTION-BLUEPRINT.md`](./PLATFORM-SOLUTION-BLUEPRINT.md) | **Expectations → problem → solution → CTO impl → arch/DB/UX** per journey |
| [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) | Competitive + Waves A–D |
| [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) | Step APIs |

| Field | Value |
|-------|-------|
| Version | **1.1** |
| Date | 2026-07-19 |
| Baseline | S1–S18 + P19–P32.1 |
| Code roots | `apps/website/` · `services/*/` · `packages/ckac-common/` |

**How to read**

| Section | Lens |
|---------|------|
| §1–§7 | Lived experience: Customer, Owner (day-1 / service / marketer), Superadmin, Ops, Support, Finance, Kitchen staff (missing) |
| §8 | Cross-persona money path |
| §9 | Architecture deep (100k sessions) |
| §10 | Implementation deep (RBAC, packages, modules, streams) |
| §11 | Flow achievement scorecard |
| §12 | How to improve — concrete backlog by persona |

---

## 0. Multi-role control model (what we claim vs what works)

```
                    ┌─────────────────────────────────────┐
                    │         SUPERADMIN (*)              │
                    │  Employees · API Keys · Flags · All │
                    └──────────────┬──────────────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
        OPS                   SUPPORT                  FINANCE
   kitchens:write           tickets:write*          packages:*
   packages:read            kitchens:read           refunds:write*
   marketing:*              marketing:read          kitchens:read
   owners:write*            streaming:read
           │                       │                       │
           └───────────────────────┴───────────────────────┘
                                   │
                    Kitchen workspace (per kitchen)
           Profile · WA · Payments · Package · Marketing · Modules · Streaming
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
              KITCHEN OWNER                 CUSTOMER
           (JWT type:owner)              (JWT type:customer)
           Single phone today            OTP / OAuth
                    │
                    ✗ Kitchen staff (manager/cook) — NOT BUILT
```

\* Permissions **enforced** via `ckac_common.admin_rbac` + `/admin/me` tab filter (P29). Audit log on admin + billing writes (P30–P31).  
**Still open:** kitchen staff JWT (manager/cook) — see §7.

---

# Part I — Persona lived experience

---

## 1. Customer — “I just want honest food, on time”

**Surfaces:** `customer.kitchcu.com` · `apps/website/src/customer/App.tsx`  
**Auth:** WhatsApp OTP / OAuth · JWT `type:customer`

### 1.1 Who I am (sub-personas)

| Sub-persona | Intent | Primary path |
|-------------|--------|--------------|
| New | Find a kitchen, trust the photo, place first order | Nearby → login → menu → checkout |
| Returning | Repeat last order, track, rate | Orders → repeat / track / rate |
| Multi-kitchen | Order from two kitchens in one pay | Cart groups → master-order → one receipt |
| Brand-loyal | Friend shared `/k/CKPNQ001` | Branded storefront → menu → checkout |

### 1.2 Flow I actually walk (achievements)

```
Discover (nearby | code | /k/:code | live_only filter)
  → Auth (OTP/OAuth)
  → Menu (live-capture, diet, prep/delivery times)
  → Cart (local) → Delivery quote (Self vs Porter + ₹ split)
  → Choose delivery_mode → accept fee if customer share > 0
  → Place order (Idempotency-Key) → Pay (COD / online / UPI intent)
  → Confirm → Track (/t/:token) → Rate (home_taste + quality)
  → Optional Watch (/live/:sessionId) · Dashboard
```

**What feels good (as a customer)**

1. **I can see the food is real** — live-capture heroes and diet filters reduce bait-and-switch anxiety vs aggregator stock photos.  
2. **Branded kitchen page** — `/k/{code}` feels like *their* kitchen, not a marketplace tab (`BrandedStorefront.tsx`).  
3. **Delivery fee is explained before pay** — Self vs Porter/platform modes show kitchen vs my ₹ share (in-range = ₹0 to me).  
4. **Multi-kitchen checkout exists** — rare; master receipt PDF is a real win when I order from two places.  
5. **Home-taste rating** — language matches how I judge home food, not only “stars for packaging.”  
6. **Track link** — token page + Maps direction is usable without installing another app.  
7. **I can watch live** — Nearby live → `/live/:sessionId` LiveKit viewer (P30).  
8. **Dashboard depth** — savings / health / refunds / addresses show the product thinks beyond one order.

**What frustrates me**

1. **Cart dies when I switch phones** — cart is local storage, not server-persisted.  
2. **Payment failure is scary** — order may sit `received` / pending; weak “retry pay” story; mock PG risk in demo.  
3. ~~**English only**~~ — **P40:** language gate + 10 IN locales on dashboard chrome (auth/nav/home/checkout/orders); long-form page bodies still expanding.  
4. **Deep-link reload** — bookmark `/dashboard/...` can bounce depending on nginx history fallback.  
5. **No offline** — weak for flaky mobile networks.  
6. **Entitlement empty states** — why a kitchen can’t go live / take online pay still thin.  
7. **Porter status after book** — job id exists; live courier webhook sync not customer-visible yet.

### 1.3 Flow achievements vs gaps (customer)

| Flow stage | Achievement | Gap | How to improve |
|------------|-------------|-----|----------------|
| Discover | Nearby + filters + branded entry | Weak personalization / ranking | Rank by distance + taste + live; save favourites |
| Auth | OTP + OAuth | Dev OTP in demo; i18n chrome ✅ | Prod OTP; deepen page-body translations |
| Menu | Live-capture + timing | Media CDN latency unknown | CDN + skeleton; signed URLs |
| Checkout | Idempotent place + modes + cost-share | Address UX; coupon clarity | Default last address; clearer coupon errors |
| Pay | Domain complete | Mock Razorpay risk; retry UX | Live PG; “Complete payment” CTA |
| Track | Token + Maps | Push reliability depends on WA | In-app push later; WA status copy |
| Rate | Verified purchase | Prompt timing | Soft prompt 30–120 min after delivered |
| Live | Watch + LiveKit embed | Prod LiveKit credentials | Harden env + viewer count |
| Multi-kitchen | Atomic master order | Settlement opacity (OK) | Keep opacity; improve confirm UX |

### 1.4 Data I never see (correct vs wrong)

| Hidden | Correct? | Note |
|--------|----------|------|
| Other kitchen’s settlements in split pay | Yes | Privacy |
| Owner stock warnings | Yes | Ops noise |
| Why stream module disabled | **Wrong to hide forever** | Show “Kitchen not streaming today” vs blank |
| Platform Meta secrets | Yes | |

---

## 2. Kitchen owner — three days in my life

**Surfaces:** `kitchen.kitchcu.com` · `kitchen/App.tsx` · `OwnerLayout.tsx`  
**Auth:** Phone OTP · JWT `type:owner` · kitchen switcher if multi-kitchen

### 2.1 Day-1 owner — “Make me live before dinner”

**Flow achievement**

```
Register → OTP → Create kitchen → Setup / branded publish
  → Add dishes (live hero required) → Categories
  → WhatsApp phone id · Razorpay keys
  → First manual / WA draft order → Accept → Status
  → Share /k/{code} or kitchen code
```

**What’s good**

- Live-capture force is annoying day-1 and **correct** — protects brand promise.  
- Kitchen code + branded page give me something to share on WhatsApp Status today.  
- Manual order + parse-message means I don’t wait for PWA customers.  
- Commission panel / pricing story reminds me why I left Swiggy.

**What’s painful**

- Too many Account tabs before first order (WA, PG, GST, Subscription, Setup).  
- Progressive complexity is incomplete — Growth nav shows Templates/Stream/Learning even on trial with soft modules.  
- Media upload still feels “engineer path,” not camera-first.  
- I am the only user — cook can’t log in separately.

**How to improve (day-1)**

1. **Guided checklist:** Kitchen created → 3 dishes → WA linked → share link (block Growth until done).  
2. Camera-first dish create with `is_live_capture` default true.  
3. Soft-hide Growth items until package/module allows (server 403 + nav).  

### 2.2 Busy service owner — “Don’t make me think”

**Flow achievement**

```
Orders inbox → Drafts confirm → Accept (stock deduct + Porter book if platform)
  → preparing → ready → out_for_delivery → delivered
  → Delivery fulfillment (self vs platform) · cost-share visible
  → Refunds with evidence when needed
  → Ingredients stock warnings
```

**What’s good**

- Lifecycle is clear and audited (`order_status_events`).  
- Accept → stock deduct is real ops (F19); accept → Porter book when customer chose platform (P32.1).  
- Delivery settings: radius, min order, subsidy % — I control who pays beyond range.  
- Order detail refunds with gateway/direct + evidence match Indian reality.  
- Analytics (revenue, peak hours, segments) answer “what sold today.”

**What’s painful**

- No sound/badge urgency for `received` while cooking.  
- No kitchen staff role — I hand the phone to the cook (security disaster).  
- Profit is still “revenue theatre” without purchase costs (E1).  
- Multi-kitchen cart: I only see my sub-order (correct) but support calls confuse me.

**How to improve (service)**

1. Urgent inbox mode: auto-refresh + optional beep on `received`.  
2. Kitchen roles: `manager` (accept/menu) / `cook` (status only) — design pack required.  
3. One-tap status chips optimized for wet hands / gloves.  

### 2.3 Growth marketer owner — “I own my customers”

**Flow achievement**

```
CRM segments → Coupons / promotions
  → Templates CRUD (WA/email)
  → Daily menu push (module)
  → Growth intelligence / golden day
  → Stream opt-in → dish showcase phases
```

**What’s good**

- CRM + coupons + promotions = I don’t rent my list from an aggregator.  
- Golden performance day is a unique insight if I have ratings volume.  
- Stream phases (ingredients → prep → prepared) match how I cook and teach trust.  
- Templates with `{{ variables }}` are the right abstraction.

**What’s painful / hollow**

1. **Templates: I can save, I cannot send.** No audience picker, no wallet debit, no delivery receipt. Portal copy oversells this.  
2. **Stream: I’m told to “connect your LiveKit client.”** Customers can’t watch in-app.  
3. Daily menu push vs custom templates are disconnected product islands.  
4. Nav shows everything; package doesn’t prune my tools.

**How to improve (growth)**

1. `POST /templates/{id}/send` → CRM segment → notify + wallet → event.  
2. Embed LiveKit publisher on Stream page; customer Watch route.  
3. “Blast from template” and “Daily menu” share one send pipeline.  
4. Package-aware Growth nav.

### 2.4 Owner flow scorecard

| Flow | Score | Notes |
|------|-------|-------|
| Onboard → first dish | A− | Live-capture friction intentional |
| First order → accept | A | Strong |
| Busy lifecycle | A− | Needs staff + alerts |
| Refunds | B+ | Evidence path good; PG mock risk |
| CRM / coupons | B+ | Solid |
| Templates | D | CRUD only |
| Stream | C− | Phases good; watch/publish thin |
| Profit | D | Needs E1 |
| Subscription clarity | C | Owner sees tier; not feature matrix |

---

## 3. Superadmin — “I am the platform”

**Surface:** `admin.kitchcu.com` · tab shell `admin/App.tsx` (no React Router deep links)  
**Auth:** Email/password · JWT `type:admin` · role ideally `superadmin`

### 3.1 What I can do today (achievements)

| Job | Where | Quality |
|-----|-------|---------|
| Platform health | Overview stats/charts | Good for demo; not SLO dashboards |
| Hire staff | Employees CRUD + roles | UI good; enforcement incomplete |
| Sell / assign packages | Packages + kitchen Package tab | Mapper real; hard entitlement soft |
| Kitchen ops workspace | Profile / WA / Payments / Package / Marketing / Modules / Streaming | **Best admin achievement of P21/P28** |
| Kill switches | Control feature flags + journeys | Powerful |
| Platform secrets | API Keys (Meta, SaaS Razorpay, LiveKit, Maps, OAuth) | Correct separation from kitchen keys |
| Money oversight | Refunds / payments / settlements / money-stats | Usable |
| Support | Tickets | Usable |
| Customers / owners | Suspend, reset, force subscription | Powerful — **too open to non-superadmin** |

### 3.2 What scares me (as superadmin hiring a team)

1. I create a `support` employee — they still see **API Keys, Refunds, Packages, Control** in the UI.  
2. Many mutations check only “is admin JWT,” not permission (see §10.1).  
3. No audit trail UI: who changed Meta secret? who suspended a kitchen?  
4. Package assign without `kitchen_module_overrides` doesn’t really lock features.  
5. Single-VM production: one bad deploy / OOM and the whole platform blinks.

### 3.3 How I want the control plane to work

| Level | Name | Should control | Enforcement needed |
|-------|------|----------------|--------------------|
| L0 | Secrets | Platform API Keys | `api_keys:write` + audit + UI hide |
| L1 | Governance | Flags, journeys | `flags:write` |
| L2 | Monetization | Packages, plan map, kitchen assign | `packages:*` (partially done) |
| L3 | Staff | Employees | `employees:*` (done) |
| L4 | Kitchen workspace | WA, PG, modules, package, marketing inventory, streaming | Split `kitchens:write`, `billing:write`, `marketing:read` |
| L5 | Care | Tickets, customers | `tickets:*`, `customers:*` |
| L6 | Money | Refunds, settlements | `refunds:*` |

**How to improve**

1. Permission-aware tab render in `admin/App.tsx`.  
2. Assert permission on **every** admin mutation (billing/notification included).  
3. `admin_audit_events` table + UI filter.  
4. Kitchen list health strip: WA · PG · package · last order · live.  

---

## 4. Ops admin — “I onboard and unblock kitchens”

**Role:** `ops` · seeded grants: `kitchens:read/write`, `packages:read`, `marketing:read/write`, `streaming:read`, `owners:write`

### 4.1 Day in my life (intended)

1. Owner signs up → I verify kitchen → set WA phone_number_id.  
2. Help paste Razorpay kitchen keys.  
3. Assign Starter/Growth package; sync modules.  
4. Toggle streaming/livekit if abuse.  
5. Force subscription when billing glitches (`owners:write`).

### 4.2 What’s good

- Kitchen workspace is my home — WA / Payments / Modules / Package tabs match my job.  
- I should not need Meta App Secret (correctly under API Keys for superadmin).

### 4.3 What’s broken for my role

| Task | Seeded permission | Actually enforced? |
|------|-------------------|--------------------|
| WA upsert / kitchen status | `kitchens:write` | **Yes** (identity) |
| View packages | `packages:read` | **Yes** on package routes |
| Force owner subscription | `owners:write` | **No** — route ignores grants |
| Kitchen payment gateway put | (none / kitchens) | **Any admin JWT** |
| Module flags | (none) | **Any admin JWT** |
| Feature flags | (none) | **Any admin JWT** |
| UI | — | Sees Refunds, API Keys, Employees |

**Voice:** “You gave me a role name, not a job boundary.”

### 4.4 How to improve (ops)

1. Enforce `owners:write`, `kitchens:write` on PG + modules.  
2. Hide API Keys / Employees / Refunds write from ops UI.  
3. Ops playbook screen: “New kitchen checklist” inside kitchen workspace.  
4. Read-only packages for ops (already in matrix) — keep write for finance/superadmin.

---

## 5. Support admin — “Close the ticket, calm the human”

**Role:** `support` · seeded: `kitchens:read`, `marketing:read`, `streaming:read`, `tickets:write`

### 5.1 Day in my life (intended)

1. Ticket from AI chat escalation.  
2. Read kitchen WA / stream context (read-only).  
3. Reply / resolve ticket.  
4. Maybe view customer — suspend only with escalation to ops/superadmin.

### 5.2 What’s good

- Tickets tab + AI chat escalation path exists.  
- Kitchen Marketing tab lets me see template inventory when debugging “blast didn’t send” (once send exists).  
- Read-only kitchen context is the right instinct.

### 5.3 What’s broken

| Task | Intended | Actual |
|------|----------|--------|
| Tickets mutate | `tickets:write` | **Not checked** — any admin |
| Customer suspend / password clear | Should be limited | **Any admin** |
| Refunds | Should be finance | Support can open Refunds tab and mutate |
| API Keys | Never | Visible |

**Voice:** “I can accidentally nuke a Meta secret while looking for a ticket.”

### 5.4 How to improve (support)

1. Enforce `tickets:write`; add `customers:read` / `customers:write` split.  
2. UI: only Overview + Tickets + Kitchens (read) + Customers (limited).  
3. Ticket SLA fields + assignee (employee id).  
4. Macros / canned replies linked to templates later.  

---

## 6. Finance admin — “Money must reconcile”

**Role:** `finance` · seeded: `packages:read/write`, `refunds:write`, `kitchens:read`

### 6.1 Day in my life (intended)

1. Design packages / map plan tiers.  
2. Assign kitchen packages for enterprise deals.  
3. Review refunds, settlements, money-stats.  
4. Never touch Meta secrets or feature flags.

### 6.2 What’s good

- Package mapper is real product work — finance can own commercial SKUs.  
- Kitchen package assign + feature_keys list is auditable commercially.  
- Refunds domain (gateway vs direct + evidence) matches Indian ops.

### 6.3 What’s broken

| Task | Enforced? |
|------|-----------|
| Packages CRUD / plan map / kitchen assign | **Yes** `packages:*` |
| Refunds list/patch | **No** — any admin JWT |
| Payments / settlements / money-stats | **No** |
| Kitchen PG credentials | **No** (should be ops/superadmin, not silent open) |

**Voice:** “I control packages tightly and refunds loosely — inverted trust.”

### 6.4 How to improve (finance)

1. Gate all money admin routes with `refunds:read/write` / `billing:read`.  
2. Settlement drill-down per kitchen / master order.  
3. GST platform rollup view.  
4. Export CSV for accounting.  

---

## 7. Kitchen staff (manager / cook) — missing persona

**Status: NOT BUILT** — gap G-P1-5.

| Role | Should do | Today |
|------|-----------|-------|
| Manager | Accept orders, edit menu, view reports | Share owner phone |
| Cook | Advance prep statuses, see ingredients | Share owner phone |
| Cashier | COD confirm | Share owner phone |

**CEO note:** Every real cloud kitchen has ≥2 humans. Shipping without kitchen RBAC caps market to solo home chefs.  
**CTO note:** Needs `kitchen_members` table, invite OTP, JWT claims `{type:staff, kitchen_id, role}`, route guards — design pack before code.  
**CPO note:** Do not fake this with “second owner account.”

---

# Part II — Cross-cutting flows

---

## 8. Money path — every actor’s view

```
Customer checkout
  → order.placed / master_order.placed
  → billing payment create → capture / UPI / COD
  → (multi) Route settlements per kitchen
  → owner sees sub-order paid
  → refund? owner or finance/support (today: too many)
  → gst invoice / audit (owner GST page)
```

| Actor | Achievement | Gap | Improve |
|-------|-------------|-----|---------|
| Customer | Place + pay + receipt | Retry / mock PG | Live keys; clear pending pay |
| Owner | Refunds + GST | Settlement UX thin; mocks | Settlement list; prod PG |
| Finance | Packages strong | Refunds ungated | RBAC + exports |
| Support | Sees refunds UI | Shouldn’t write | Hide + deny |
| Superadmin | Full visibility + audit | Exports thin | CSV / GST rollup |
| Platform | Subscription SaaS + hard entitlements | Live PG / prod OTP | Wave A close |

**Idempotency:** Customer checkout sends `Idempotency-Key` — keep sacred; extend consistency to pay capture retries in UI.

---

## 9. Architecture deep dive (CTO · 100k sessions)

### 9.1 What is architecturally right

| Decision | Why it scales |
|----------|---------------|
| Schema-per-domain (`ckac_*`) | Independent migrate/deploy |
| Gateway-only public edge | Attack surface centralized |
| Stateless FastAPI services | Horizontal scale |
| Redis Streams + transactional outbox | Reliable EDD without dual-write lies |
| Tenant `kitchen_id` on tables + cache keys | Multi-tenant safety pattern |
| Correlation ID middleware | Debug distributed traces later |
| Module/feature flags | Kill switches without redeploy |
| Four PWA bundles one monorepo | Shared brand/API, independent deploy |

### 9.2 What will break at 100k concurrent sessions

| Risk | Today | Required |
|------|-------|----------|
| Single GCP VM (20 containers) | Demo posture | Cloud Run + Cloud SQL + Memorystore ([DEPLOYMENT-GCP](./DEPLOYMENT-GCP.md) §1–10) |
| Redis Streams as bus | Fine early | Kafka/PubSub Phase 3; consumer groups; lag alerts |
| Outbox flush in-request | Adds latency under load | Async dispatcher workers |
| Admin unscoped lists | OK for ops | Pagination + search indexes mandatory |
| Cross-schema reads from many services | Coupling | Internal BFF or projection tables for admin health |
| Soft module defaults (pre-P29) | Hard entitlements when package assigned | Keep default-deny for paid modules |
| Rate limit | Present on gateway (OTP) | Per-route + per-tenant broaden |
| Observability | Health endpoints | OTel traces + RED metrics + money SLOs |
| RLS | “when enabled” | Prove RLS on tenant tables in prod |

### 9.3 Data / event flow (canonical)

```
Actor → Gateway → Service route → Domain
  → DB commit (tenant schema) + outbox row
  → Redis XADD (post-commit)
  → Consumers (notify, growth, billing side-effects)
  → UI poll/refetch
```

**Missing events = incomplete feature.** Templates send + fan-out emit dispatch paths (P30–P31). Stream showcase + customer watch path shipped (P30). Porter book is best-effort on accept — webhook status sync still open.

### 9.4 Gateway notes (`services/gateway/app/main.py`)

- Path markers for billing/marketing/stream must stay ordered — regressions are silent 404/wrong service.  
- Admin billing prefixes registered before identity catch-all — correct for packages/refunds/PG.  
- Internal routes not proxied — correct.

---

## 10. Implementation deep dive

### 10.1 Admin RBAC — shipped (P29–P31)

**Roles:** `superadmin`, `ops`, `support`, `finance` (`013`+)  
**Shared:** `packages/ckac-common/ckac_common/admin_rbac.py`  
**UI:** `GET /admin/me` → permission-filtered tabs · Admin Audit tab (`015`)  
**Billing writes** → identity `POST /internal/admin-audit` (P31)

| Area | Status |
|------|--------|
| Employees / packages / kitchens / tickets / refunds / API keys | ✅ Enforced |
| Tab filter by role | ✅ |
| Audit trail breadth | 🟡 Expand to remaining admin mutations |
| Matrix tests role × route | 🟡 Keep growing |

### 10.2 Packages & modules — hard entitlements (P29)

When a kitchen has an assigned package, module access is **hard-gated**; owner nav uses `GET /billing/kitchens/{id}/entitlements`.

**Still soft / feature-flagged for non-package kitchens:** progressive complexity + global risk flags (`courier_porter_dunzo`, etc.).

**Remaining polish:** richer customer empty states when stream/pay blocked; owner plan matrix page.

### 10.3 Templates — shipped path (P26 / P29–P31)

| Exists | Notes |
|--------|-------|
| CRUD + Preview/Send | Owner Growth → Templates |
| Per-phone fan-out | `/template-blast` |
| Messaging wallet debit | 402 if insufficient |
| Meta Cloud outbound | Graph send client + identity access-token slot |

**Open:** CRM segment audience picker polish; delivery receipts analytics.

### 10.4 Streaming — shipped path (P22 / P30 / P32)

| Exists | Notes |
|--------|-------|
| Go-live + dish showcase phases | Owner Stream |
| LiveKit publish + viewer | `livekit-client` |
| Customer `/live/:sessionId` | Nearby Watch CTA |
| Camera preview fix | Re-issue publisher token on showcase |

**Open:** Prod LiveKit credentials; viewer count proof.

### 10.5 WhatsApp — split of duties (good architecture)

| Secret / id | Owner | Where |
|-------------|-------|-------|
| Meta App Secret / Verify Token | Platform | Admin → API Keys |
| Kitchen `phone_number_id` | Kitchen | Owner WA page + Admin kitchen WA tab |
| Outbound templates / blasts | Kitchen + wallet | ✅ Send path (P31) |

This split is **correct** — keep it. Don’t put App Secret on kitchen forms.

### 10.6 Delivery / Porter — shipped path (P32 / P32.1)

| Exists | Notes |
|--------|-------|
| Cost-share rules | In-range kitchen 100%; beyond + min order → subsidy % |
| Quote modes | Self \| platform (Porter/mock) |
| Checkout `delivery_mode` | Server fee re-validate |
| Porter book on accept | Avoids jobs for cancelled carts |
| Owner delivery settings UI | Radius, min order, subsidy % |

**Open:** Porter webhooks / live courier status; production `PORTER_API_KEY` + flag.

---

## 11. Flow achievement scorecard (platform)

| Journey | Persona | Achievement | Score |
|---------|---------|-------------|-------|
| Discover → menu | Customer | Nearby, filters, branded | A |
| Checkout → pay + delivery modes | Customer | Idempotent + cost-share + Porter mode | A− |
| Track → rate | Customer | Token + home_taste | A− |
| Watch live | Customer | LiveKit Watch page | A− |
| Owner onboard | Owner | OTP → kitchen → dish | A− |
| Order lifecycle + Porter | Owner | Full SM + book on accept | A |
| Refunds | Owner/Finance | Evidence paths + RBAC | B+ |
| CRM / coupons | Owner | Full CRUD | A− |
| Templates send | Owner | Send + wallet + Meta | A− |
| Stream cook + watch | Owner/Customer | LiveKit publish/view | A− |
| Package sell | Finance/Superadmin | Mapper + hard entitlements | A− |
| Entitlement enforce | All | Hard when packaged | A− |
| Admin hire safely | Superadmin | RBAC + tabs + audit | A− |
| Support tickets | Support | Permission-gated | B+ |
| Kitchen staff | Cook/Manager | — | F (missing) |
| Quality/profit loop | Owner | E1–E2 design only | — |

Canonical scorecard also in [`PLATFORM-ARCHITECTURE-FLOWS.md`](./PLATFORM-ARCHITECTURE-FLOWS.md) §7.

---

## 12. How to improve — backlog by persona (actionable)

### Customer
1. ~~Watch Live~~ ✅ · harden prod LiveKit.  
2. Server-side cart optional sync for logged-in users.  
3. Payment pending recovery + live Razorpay.  
4. ~~Hindi / regional UI~~ ✅ (P40 chrome) — deepen track/account body copy.  
5. Favourites + better ranking.  
6. Porter tracking UX after book (webhooks).  
7. Referrals tab ✅ (P37) — polish conversion UX.  

### Owner
1. Day-1 checklist wizard.  
2. ~~Template send / LiveKit / package nav~~ ✅ — polish Meta receipts.  
3. Design pack: kitchen staff RBAC.  
4. Inbox urgency UX.  
5. Porter webhook status on order detail.  
6. ~~GST Excel/PDF~~ ✅ (P38) · ~~Referrals + subscription credit~~ ✅ (P37).  

### Superadmin
1. ~~Permission-filtered tabs + audit~~ ✅ — broaden audit coverage.  
2. ~~Kitchen health strip + Orders tab + ticket triage~~ ✅ (P39).  
3. Impersonate / view-as-kitchen (deferred).  

### Ops / Support / Finance
1. ~~Assignee on tickets~~ ✅ (P39) — SLA timers next.  
2. ~~Settlements list + GST admin export~~ ✅ (P38/P39).  

### Platform (CTO)
1. Live Razorpay + prod OTP.  
2. Porter webhooks.  
3. Leave single-VM (Wave D) · OTel + money SLOs.  

### Product (CPO) / CEO
1. Kitchen staff design before E1 if multi-user kitchens are sales-critical.  
2. Measure: time-to-first-order, rating attach, blast→order, live→order, delivery subsidy attach rate.  

---

## 13. Document control

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-07-18 | First full persona/flow/architecture/implementation deep dive |
| **1.1** | 2026-07-19 | Refresh post P29–P32.1: RBAC/audit/Watch/templates/Porter; scorecard + §10 |

**Update policy:** When a persona-blocking gap closes, update that persona’s scorecard + §12 item in the same PR as the code. Keep Waves in sync. Architecture snapshot: [`PLATFORM-ARCHITECTURE-FLOWS.md`](./PLATFORM-ARCHITECTURE-FLOWS.md).

**Related**

- Architecture flows: [`PLATFORM-ARCHITECTURE-FLOWS.md`](./PLATFORM-ARCHITECTURE-FLOWS.md)  
- Strategic waves: [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md)  
- Step APIs: [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md)  
- Tracker: [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md)  
- Super-admin gate: `.cursor/rules/kitchcu-superadmin-integration.mdc`  

---

*KitchCu Persona Deep Dive v1.1 — Confidential — July 2026*
