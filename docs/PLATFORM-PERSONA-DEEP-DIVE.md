# KitchCu — Persona, Flow, Architecture & Implementation Deep Dive

**Living document.** Written as if each role used the product for a week, then the CEO/CPO/CTO staff synthesized what to keep, fix, and build.  
Companion to [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) (waves & prioritization) and [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) (step APIs).

| Field | Value |
|-------|-------|
| Version | **1.0** |
| Date | 2026-07-18 |
| Baseline | S1–S18 + P19–P28 |
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

\* Permission **seeded** but often **not enforced** on the route — see §10.1.  
**UI reality:** Admin SPA shows **every tab to every role**. Tab hiding by permission does not exist (`admin/App.tsx` `TABS`).

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
  → Cart (local) → Delivery quote (accept fee)
  → Place order (Idempotency-Key) → Pay (COD / online / UPI intent)
  → Confirm → Track (/t/:token) → Rate (home_taste + quality)
  → Dashboard (savings, addresses, refunds, complaints)
```

**What feels good (as a customer)**

1. **I can see the food is real** — live-capture heroes and diet filters reduce bait-and-switch anxiety vs aggregator stock photos.  
2. **Branded kitchen page** — `/k/{code}` feels like *their* kitchen, not a marketplace tab (`BrandedStorefront.tsx`).  
3. **Delivery fee is explained before pay** — quote accept is honest; payer modes (owner in-range / customer extended) are product-real.  
4. **Multi-kitchen checkout exists** — rare; master receipt PDF is a real win when I order from two places.  
5. **Home-taste rating** — language matches how I judge home food, not only “stars for packaging.”  
6. **Track link** — token page + Maps direction is usable without installing another app.  
7. **Dashboard depth** — savings / health / refunds / addresses show the product thinks beyond one order.

**What frustrates me**

1. **“Live now” but I can’t watch** — filter exists; `fetchViewerToken` exists in `shared/api.ts`; **no Watch page** in customer routes. I feel lied to.  
2. **Cart dies when I switch phones** — cart is local storage, not server-persisted.  
3. **Payment failure is scary** — order may sit `received` / pending; I don’t get a clear “retry pay” story.  
4. **English only** — Hindi promised in charter; not in UI.  
5. **Deep-link reload** — bookmark `/dashboard/...` can bounce depending on nginx history fallback.  
6. **No offline** — weak for flaky mobile networks.  
7. **I don’t know why a kitchen can’t go live / take online pay** — no entitlement empty states (“this kitchen hasn’t enabled online pay”).

### 1.3 Flow achievements vs gaps (customer)

| Flow stage | Achievement | Gap | How to improve |
|------------|-------------|-----|----------------|
| Discover | Nearby + filters + branded entry | Weak personalization / ranking | Rank by distance + taste + live; save favourites |
| Auth | OTP + OAuth | Dev OTP in demo; Hindi copy | Prod OTP; i18n |
| Menu | Live-capture + timing | Media CDN latency unknown | CDN + skeleton; signed URLs |
| Checkout | Idempotent place + fee accept | Address UX; coupon clarity | Default last address; clearer coupon errors |
| Pay | Domain complete | Mock Razorpay risk; retry UX | Live PG; “Complete payment” CTA |
| Track | Token + Maps | Push reliability depends on WA | In-app push later; WA status copy |
| Rate | Verified purchase | Prompt timing | Soft prompt 30–120 min after delivered |
| Live | Discovery badge | **No player** | `/live/:sessionId` + LiveKit viewer |
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
Orders inbox → Drafts confirm → Accept (stock deduct)
  → preparing → ready → out_for_delivery → delivered
  → Delivery fulfillment (self vs platform)
  → Refunds with evidence when needed
  → Ingredients stock warnings
```

**What’s good**

- Lifecycle is clear and audited (`order_status_events`).  
- Accept → stock deduct is real ops (F19).  
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
| Superadmin | Full visibility | No audit | Audit log |
| Platform | Subscription SaaS model | Entitlement soft | Hard modules |

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
| Soft module defaults | Entitlement lie | Default-deny for paid modules |
| Rate limit | Present on gateway | Per-route + per-tenant + OTP-specific |
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

**Missing events = incomplete feature.** Templates CRUD emits template events; **send does not exist** so no blast events. Stream showcase emits; **customer watch path unused**.

### 9.4 Gateway notes (`services/gateway/app/main.py`)

- Path markers for billing/marketing/stream must stay ordered — regressions are silent 404/wrong service.  
- Admin billing prefixes registered before identity catch-all — correct for packages/refunds/PG.  
- Internal routes not proxied — correct.

---

## 10. Implementation deep dive

### 10.1 Admin RBAC — seed vs enforce

**Seeded roles** (`013_admin_rbac_employees.py`): `superadmin`, `ops`, `support`, `finance`  
**Helper:** `services/identity/app/rbac.py` · billing duplicate `_assert_admin_perm`

| Permission | Checked on | NOT checked (examples) |
|------------|------------|------------------------|
| `employees:*` | Employee CRUD | — |
| `kitchens:write` | WA put, kitchen status | Module flags, customers, PG |
| `packages:*` | Package/feature/plan/kitchen package | — |
| `marketing:read` | Admin kitchen templates list | — |
| `refunds:write` | — | All refund/payment/settlement admin routes |
| `tickets:write` | — | Ticket list/patch/reply |
| `api_keys:write` | — | API key mutations |
| `owners:write` | — | Force subscription |
| `streaming:read` | — | No assert found |

**Implementation change required**

1. Shared `ckac_common.admin_rbac.assert_permission(session, role, code)` used by identity/billing/notification.  
2. Decorator / Depends factory `RequirePerm("refunds:write")`.  
3. Admin UI: `GET /admin/me` returns `permissions[]`; filter `TABS`.  
4. Tests: each role × forbidden route → 403 (matrix test).  

### 10.2 Packages & modules — soft gating mechanics

```
is_kitchen_module_enabled():
  if global feature off → False
  if kitchen_module_overrides feature OFF → True   # ← soft world
  else look up kitchen_module_flags row
  if row missing → default True                    # ← soft world
```

**File:** `packages/ckac-common/ckac_common/platform_config.py`

**Hard checks today (examples)**

- `marketing_broadcast` → templates + daily-menu push  
- `live_streaming` feature → go-live / viewer-token  
- `multi_kitchen_checkout` feature → master orders  

**Not package-keyed:** most catalog/order/growth APIs.

**Implementation change required**

1. On kitchen package assign: always sync module flags from feature→module map when `sync_module_flags=true` (default true).  
2. Strategy decision (product):  
   - **A)** Turn `kitchen_module_overrides` ON globally for paid envs, or  
   - **B)** Change default to deny when kitchen has an assigned package.  
3. Owner nav + API must share same entitlement resolver.  
4. Customer empty states when module/feature blocks stream/pay.  

### 10.3 Templates — implementation hole

| Exists | Missing |
|--------|---------|
| Model `message_templates` | `send` endpoint |
| CRUD routes + events | Audience resolution (CRM segment) |
| Variable extract | Wallet debit + notify dispatch |
| Admin list | Admin edit (optional) |
| Owner UI create/list | Preview with sample CRM row |

**Proposed contract**

```
POST /api/v1/kitchens/{id}/templates/{template_id}/send
{
  "audience": "crm_segment" | "phones",
  "segment": "vip" | "churn" | ...,
  "phones": ["+91..."],   // capped
  "dry_run": false
}
→ { "queued": N, "wallet_debited": ..., "dispatch_id": ... }
Events: template.send_requested → notify.dispatch → template.send_completed
```

### 10.4 Streaming — implementation hole

| Exists | Missing |
|--------|---------|
| Go-live + dish + phases | In-browser LiveKit publisher |
| Viewer-token API | Customer `/live/:sessionId` page calling token |
| Live kitchens list | Watch CTA on nearby cards |
| Admin streaming modules | Permission-gated streaming:read usage |

### 10.5 WhatsApp — split of duties (good architecture)

| Secret / id | Owner | Where |
|-------------|-------|-------|
| Meta App Secret / Verify Token | Platform | Admin → API Keys |
| Kitchen `phone_number_id` | Kitchen | Owner WA page + Admin kitchen WA tab |
| Outbound templates / blasts | Kitchen + wallet | Incomplete send path |

This split is **correct** — keep it. Don’t put App Secret on kitchen forms.

---

## 11. Flow achievement scorecard (platform)

| Journey | Persona | Achievement | Score |
|---------|---------|-------------|-------|
| Discover → menu | Customer | Nearby, filters, branded | A |
| Checkout → pay | Customer | Idempotent + multi-kitchen | B+ |
| Track → rate | Customer | Token + home_taste | A− |
| Watch live | Customer | — | F |
| Owner onboard | Owner | OTP → kitchen → dish | A− |
| Order lifecycle | Owner | Full state machine | A |
| Refunds | Owner/Finance | Evidence paths | B |
| CRM / coupons | Owner | Full CRUD | A− |
| Templates send | Owner | — | F |
| Stream cook phases | Owner | ingredients→prepared | B |
| Stream watch proof | Owner/Customer | — | D |
| Package sell | Finance/Superadmin | Mapper | B+ |
| Entitlement enforce | All | Soft | D |
| Admin hire safely | Superadmin | Employees UI | C− (RBAC hole) |
| Support tickets | Support | Queue exists | B− (over-privileged) |
| Kitchen staff | Cook/Manager | — | F (missing) |
| Quality/profit loop | Owner | E1–E2 design only | — |

---

## 12. How to improve — backlog by persona (actionable)

### Customer
1. Ship Watch Live page + CTA on live kitchens.  
2. Server-side cart optional sync for logged-in users.  
3. Payment pending recovery screen.  
4. Hindi strings for auth/checkout/track.  
5. Favourites + better ranking.  

### Owner
1. Day-1 checklist wizard.  
2. Template send pipeline.  
3. Embedded LiveKit publish.  
4. Package-aware nav.  
5. Design pack: kitchen staff RBAC.  
6. Inbox urgency UX.  

### Superadmin
1. Permission-filtered tabs.  
2. Audit log.  
3. Kitchen health strip.  
4. Enforce RBAC everywhere.  

### Ops
1. Enforce owners/kitchens/PG/modules permissions.  
2. Onboarding checklist in kitchen workspace.  
3. Hide money secrets tabs.  

### Support
1. Enforce tickets permission.  
2. Narrow UI.  
3. Assignee + SLA.  

### Finance
1. Enforce refunds/billing permissions.  
2. Settlements + GST rollups + CSV.  

### Platform (CTO)
1. Hard entitlements strategy.  
2. Live Razorpay + prod OTP.  
3. Leave single-VM (Wave D).  
4. OTel + money SLOs.  
5. Shared admin RBAC package.  

### Product (CPO)
1. Stop marketing send/live-watch until shipped.  
2. Align portal Features copy with scorecard.  
3. Approve kitchen staff design before E1 if multi-user kitchens are sales-critical.  

### CEO
1. Hire ops/support **only after** Wave A RBAC.  
2. Price packages against hard modules, not slideware.  
3. Measure: time-to-first-order, rating attach, blast→order (post-send), live→order (post-watch).  

---

## 13. Document control

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-07-18 | First full persona/flow/architecture/implementation deep dive |

**Update policy:** When a persona-blocking gap closes, update that persona’s scorecard + §12 item in the same PR as the code. Keep [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) Waves in sync.

**Related**

- Strategic waves: [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md)  
- Step APIs: [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md)  
- Tracker: [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md)  
- Super-admin gate: `.cursor/rules/kitchcu-superadmin-integration.mdc`  

---

*KitchCu Persona Deep Dive v1.0 — Confidential — July 2026*
