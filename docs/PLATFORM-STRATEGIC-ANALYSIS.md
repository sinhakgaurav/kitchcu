# KitchCu — Platform Strategic Analysis

**Living executive brief** — CEO · CPO · CTO · UX · DBA · QA  
Use this for release planning, investor diligence, and “what do we build next?” decisions.  
Update whenever a journey ships, a gap closes, or competitive posture changes.

| Field | Value |
|-------|-------|
| Version | **1.0** |
| Date | 2026-07-18 |
| Baseline | Phase 1 **S1–S18** + post-S18 **P19–P28** |
| Production | `*.kitchcu.com` (GCP single-VM today) |
| Canonical status board | [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md) |
| Journeys (step APIs) | [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) |
| Encyclopedia | [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) v3.2.2 |
| Next design (not built) | [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| Super-admin gate | `.cursor/rules/kitchcu-superadmin-integration.mdc` |
| **Persona deep dive** | [`PLATFORM-PERSONA-DEEP-DIVE.md`](./PLATFORM-PERSONA-DEEP-DIVE.md) — lived voice per role |
| **Solution blueprint** | **[`PLATFORM-SOLUTION-BLUEPRINT.md`](./PLATFORM-SOLUTION-BLUEPRINT.md)** — expectations → CEO/CPO problem → solution → CTO impl → achievements/gaps/arch/DB/UX for every journey & control surface |

> **Note on stale docs:** [`CKAC-GAPS.md`](./CKAC-GAPS.md) is stale for many open rows. Prefer Advancement Tracker + Solution Blueprint.  
> **Read order:** Solution Blueprint (what to build) → Persona Deep Dive (how it feels) → this file (waves) → Userflows (APIs).

---

## 0. Executive verdict

| Lens | Verdict |
|------|---------|
| **CEO** | We have a real Growth OS wedge vs aggregators: **0% food commission**, owner-owned CRM channel, trust media, branded storefront. Unit economics story is sellable. Risk: over-claiming live video, CRM blast, and plan gating before they are end-to-end. |
| **CPO** | Customer discover→checkout→track→rate and owner ops/growth surfaces are product-complete enough for demos and early kitchens. Several “promised” features stop at CRUD/session plumbing. Progressive complexity is mostly honored; entitlement UX is not. |
| **CTO** | Microservices + outbox + tenant schemas are the right spine for 100k sessions. Money domain is modeled hard; provider integration and admin RBAC enforcement are soft. Single-VM prod is a **demo/ops** posture, not the scale target. |
| **Decision** | Stabilize trust paths (RBAC, hard entitlements, live Razorpay, template send, LiveKit watch) **before** E1–E2 Quality Loop — unless margin/stock is the explicit next sales blocker. |

---

## 1. Platform positioning (vs other platforms)

### 1.1 Competitive map

| Platform type | Examples | What they optimize | Where KitchCu differs |
|---------------|----------|--------------------|------------------------|
| Food aggregators | Swiggy, Zomato, Uber Eats | Demand liquidity, delivery SLA races, take rate on food | **No food commission**; owner subscription; quality/truth timing not fake “10 min” races |
| Restaurant POS / KDS | Petpooja, Toast, Square | Dine-in, tables, waiters, kitchen display | **Out of scope by charter** — cloud kitchen / home food only |
| WhatsApp commerce kits | Generic WA Business + sheets | Chat chaos, no lifecycle | Structured drafts → order state machine → events → notifications |
| Generic SaaS storefronts | Shopify + delivery plugins | SKU commerce, weak food trust | Live-capture heroes, home-taste ratings, dish timing, delivery payer modes |
| Social / reels food | Instagram shops | Attention, not ops | Per-dish go-live **ingredients → prep → prepared** tied to recipe truth |

### 1.2 Moat candidates (ranked by defensibility)

1. **Trust loop** — live-capture menu + home-taste ratings + optional live dish showcase (hard for aggregators to copy without fighting their own stock-photo culture).
2. **Owner CRM ownership** — coupons, CRM, templates, daily menu; kitchen owns the relationship (commission platforms rent it).
3. **Branded storefront** `/k/{code}` — direct shareable brand page → checkout (relationship, not marketplace tab).
4. **Growth OS intelligence** — golden performance day, combos/patterns/suggestions (becomes stronger after E1–E2 stock truth).
5. **Subscription economics** — Starter/Growth/Pro narrative with package mapper (P25) to sell modules without per-order take.

### 1.3 Claims vs product depth (honesty gate)

| Portal / sales claim | Product depth today | Risk if oversold |
|----------------------|---------------------|------------------|
| 0% food commission | Strong (pricing + owner panel + model) | Low |
| Live-capture menu | Strong (validator + UX) | Low |
| WhatsApp order hub | Partial (webhook + drafts; prod Meta ops-heavy) | Medium |
| Live dish showcase | Partial (phases + APIs; thin LiveKit client / no customer player) | **High** |
| Marketing templates | Partial (CRUD only; no send/blast) | **High** |
| Package / plan features | Partial (mapper + optional module sync; soft gate) | Medium |
| Golden performance day | Usable ML + pins | Medium (needs volume) |

**CPO rule:** Do not put “CRM blasts” or “watch live prep in-app” on the homepage until send + viewer ship.

---

## 2. User types & control levels

### 2.1 Personas

| Persona | Goal | Surface | Auth |
|---------|------|---------|------|
| **Customer** | Trust food, order, track, rate, repeat | `customer.kitchcu.com` | OTP / OAuth JWT `type:customer` |
| **Kitchen owner** | Run day ops + grow revenue without aggregator take | `kitchen.kitchcu.com` | OTP JWT `type:owner` |
| **Platform employee** | Ops, support, finance, package sales | `admin.kitchcu.com` | Email/password JWT `type:admin` + role |
| **Superadmin** | Full platform control, kill-switches, secrets | Admin (role `superadmin`) | Same + permission `*` |

### 2.2 Super-admin control levels (as designed vs as enforced)

| Level | Intended | Shipped UI | Enforcement today |
|-------|----------|------------|-------------------|
| L0 Platform secrets | Meta / SaaS Razorpay / LiveKit in API Keys | ✅ Control → API Keys | Any admin JWT (not fine-grained) |
| L1 Governance | Feature flags, journeys | ✅ Control | Any admin JWT |
| L2 Monetization | Features → packages → plans → kitchen assign | ✅ Packages + kitchen Package tab | `packages:read/write` on package routes |
| L3 Staff | Employees CRUD + roles | ✅ Employees | `employees:read/write` |
| L4 Kitchen workspace | Profile, WA, Payments, Package, Marketing, Modules, Streaming | ✅ Kitchen detail tabs | Partial: `kitchens:write` on some identity kitchen writes; billing PG / refunds mostly admin-JWT only |
| L5 Support money | Refunds, tickets, customers | ✅ Tabs | Tickets/customers/refunds **not** fully RBAC-gated |

**Roles seeded:** `superadmin` · `ops` · `support` · `finance`  
**Gap:** Creating a `support` employee does **not** reliably prevent access to Packages, API Keys, or Refunds mutations. Treat P27 as **RBAC foundation**, not **RBAC complete**.

### 2.3 Kitchen module / package control

```
Platform feature catalog (billing)
        ↓ mapped into
Package (feature_keys + plan_tiers)
        ↓ assigned to
Kitchen package (override) OR plan default
        ↓ optionally syncs
Kitchen module_flags (identity)
        ↓ enforced when
kitchen_module_overrides global flag is ON
```

**Gap:** Default module behavior is **enabled**. Without turning on `kitchen_module_overrides`, package assignment is commercial labeling more than hard entitlement. That is unacceptable for paid tier differentiation at scale.

---

## 3. Journey deep-dive

### 3.1 Customer journey (happy path)

```
Discover (nearby / code / branded /k/:code / live_only)
  → Auth (OTP/OAuth)
  → Menu (live-capture, timing, diet)
  → Cart (single or multi-kitchen)
  → Checkout + pay (COD / online intent)
  → Track (/t/:token + Maps)
  → Rate (home_taste + quality)
  → Repeat / dashboard
```

| Stage | Status | Optimization opportunity |
|-------|--------|--------------------------|
| Discovery | ✅ Map/list, diet, live-capture, live filter | Rank by distance + taste aggregate + “live now”; save preferred kitchens |
| Branded entry | ✅ P19 | Deep-link from WA templates with UTM + kitchen code |
| Checkout | ✅ S5/S8 | Reduce fields; remember address; clearer delivery payer explanation |
| Pay | 🟡 Domain strong / provider mock-first | Live Razorpay per kitchen; failure UX; idempotent retry education |
| Track | ✅ | Richer status copy; push/WA intervals already S14 |
| Rate | ✅ | Prompt only on delivered; A/V review adoption |
| Watch live | 🟡 Discovery only | **Missing customer LiveKit watch surface** |

**Flow changes required (customer)**

1. Add **Watch live** route: session → viewer token → embedded player (or deep-link to external LiveKit if intentional).
2. Branded page CTA should prefer **order** over generic nearby when entered via `/k/:code`.
3. After checkout, single “receipt + track + rate later” continuity screen (multi-kitchen master receipt already exists — tighten UX).
4. Entitlement-aware empty states (“This kitchen’s live stream is not on their plan”) once hard gating exists.

### 3.2 Kitchen (owner) journey

```
Register → OTP → Create kitchen → Menu (live heroes) → Integrations (WA + Razorpay)
  → Orders inbox → Accept → Ready (stock deduct) / Bulk prep → Lifecycle → Delivery
  → Growth (analytics, suggestions, golden day)
  → CRM / coupons / templates
  → Stream (opt-in → go-live → dish phases)
  → Subscription / GST
```

| Stage | Status | Pain / gap |
|-------|--------|------------|
| Onboarding | ✅ | Still phone-OTP heavy; GST optional later |
| Menu truth | ✅ | Media upload UX / MinIO signed flow still ops-ish |
| WhatsApp | 🟡 | Phone id wired; outbound reliability depends on Meta + wallet |
| Payments | 🟡 | Kitchen keys UI; create/capture often mock in non-prod |
| Orders | ✅ | Strong lifecycle; staff roles absent (single owner) |
| Ingredients | ✅ F19 | No purchase ledger → profit still incomplete (E1) |
| Templates | 🟡 CRUD | **No send to CRM segment / daily menu** |
| Stream | 🟡 | Phases good; publish UX / viewer proof weak |
| Growth | ✅ | Golden day needs enough ratings volume |

**Flow changes required (kitchen)**

1. **Templates → Send**: pick template → audience (CRM segment / last N customers) → channel → confirm → notify service dispatch + wallet debit.
2. **Stream day-of flow**: select dish → go live → phase chips → end; show “customers can see you” proof (viewer count or last join).
3. **Package-aware nav**: hide/disable Growth modules not in package (server-enforced, UI mirrors).
4. **Staff (future):** kitchen roles (manager/cook) — currently platform employees only; kitchen multi-user is still a gap vs real cloud kitchens.

### 3.3 Super-admin journey

```
Login → Overview health
  → Employees (hire/roles)
  → Packages (compose SKUs)
  → Kitchens workspace (creds, package, modules, marketing inventory, streaming kill)
  → Customers / Refunds / Tickets
  → Control (flags, journeys, API Keys)
```

**Flow changes required (admin)**

1. **Permission matrix UI**: show which permissions each role has; audit log on sensitive writes.
2. **Package assign wizard**: select package → preview modules enabled → confirm sync flags ON by default for paid assign.
3. **Kitchen health strip**: WA connected · PG configured · package · last order · live now — one glance.
4. Enforce RBAC on refunds, API keys, feature flags, customer suspend, payment-gateway before hiring non-superadmin staff.

---

## 4. Achievements (what we actually won)

### 4.1 Product / market

| Achievement | Why it matters |
|-------------|----------------|
| Full Phase 1 feature breadth (F01–F48 track + P19–P28) | Rare for a cloud-kitchen OS this early — not a single-purpose app |
| Zero food commission narrative with owner UX proof | Unlocks sales against aggregator fatigue |
| Trust stack: live-capture + ratings + dish timing + delivery payer modes | Differentiates from stock-photo marketplaces |
| Branded storefront `/k/{code}` | Direct relationship channel |
| Multi-kitchen cart + master receipt + Route settlement model | Supports real city behavior (order from multiple kitchens) |
| Growth OS beginnings (suggestions, golden day, CRM, coupons) | Positions as OS, not POS |
| Super-admin kitchen workspace + package mapper + employees | Sellable B2B ops story |

### 4.2 Engineering

| Achievement | Why it matters |
|-------------|----------------|
| 13 domain services + gateway, schema-per-domain | Correct boundaries for scale |
| Transactional outbox + Redis Streams on writes | EDD reliability |
| Tenant `kitchen_id` discipline + module/feature flags | Multi-tenancy foundation |
| Four PWAs one monorepo | Speed + brand consistency |
| Money domain depth (payments, GST, refunds, wallets, subscriptions) | Hardest part modeled early |
| Cursor charter + super-admin integration rule | Prevents owner-only feature drift |
| GCP VM runbook + seed path | Demo/prod operable |

### 4.3 Post-S18 increments (P19–P28)

Branded page · golden day · kitchen WA/Razorpay workspace · per-dish live showcase · admin password sync · package mapper · marketing templates CRUD · employees RBAC foundation · expanded kitchen workspace tabs.

---

## 5. Gaps (prioritized)

### P0 — Trust & revenue integrity (fix before scale sales)

| ID | Gap | Impact | Owner |
|----|-----|--------|-------|
| G-P0-1 | **Admin RBAC incomplete** — many admin routes accept any admin JWT | Support/finance hire = privilege explosion | CTO |
| G-P0-2 | **Package entitlements soft** — modules default on; overrides flag off | Cannot honestly sell tiers | CTO + CPO |
| G-P0-3 | **Razorpay live path** — mocks / webhook-wait refunds | Real money risk | CTO |
| G-P0-4 | **Prod OTP** still demo-shaped if `demo-mode`/dev OTP left on | Security / brand trust | CTO |
| G-P0-5 | **Docs drift** (`CKAC-GAPS.md`, parts of Implementation Guide) | Bad investor/ops decisions | CPO |

### P1 — Claimed journeys that stop short

| ID | Gap | Impact | Owner |
|----|-----|--------|-------|
| G-P1-1 | Templates **CRUD without send/broadcast** | Marketing claim hollow | CPO |
| G-P1-2 | LiveKit **session without customer watch UX** | Live claim hollow | CPO + CTO |
| G-P1-3 | WhatsApp outbound reliability + wallet UX | Order updates / blasts fragile | CTO |
| G-P1-4 | Media upload / signed URL owner flow | Friction on live-capture promise | Full-stack |
| G-P1-5 | Kitchen staff roles (multi-user kitchen) | Real kitchens ≠ one phone | CPO |

### P2 — Optimization & scale

| ID | Gap | Impact | Owner |
|----|-----|--------|-------|
| G-P2-1 | Single-VM prod vs Cloud Run target architecture | Won’t survive 100k sessions | CTO |
| G-P2-2 | OpenTelemetry + centralized metrics | Blind ops at load | CTO |
| G-P2-3 | Gateway rate limit maturity / WAF | Abuse on OTP & pay | CTO |
| G-P2-4 | Profit/margin (needs E1 purchase ledger) | Pricing AI blocked | CPO |
| G-P2-5 | Chef standard lock (E2) | Taste consistency loop incomplete | CPO |
| G-P2-6 | Admin platform-wide revenue analytics | Ops flying on counts | CPO |
| G-P2-7 | PWA offline / deep-link nginx quirks | Field reliability | Full-stack |

### P3 — Explicit non-goals (do not build)

- Restaurant POS, dine-in tables, waiters, classic KDS, hotel features  
- Per-order food commission model  
- Fake delivery-timer races  

---

## 6. Improvements (product & application optimization)

### 6.1 Application optimization (perf / UX / conversion)

| Area | Improvement |
|------|-------------|
| Customer first session | Geo permission → nearby results in <2s; skeleton states; fewer filter chips |
| Checkout | Address book default; fee breakdown before pay; coupon apply with clear invalid reason |
| Owner inbox | Keyboard status transitions; sound/badge for `received`; batch accept cautiously |
| Growth | One “today’s action” card (golden day / low stock / win-back) above the fold |
| Admin | Kitchen health strip; RBAC-aware nav (hide forbidden tabs) |
| Caching | Keep menu/analytics TTLs; never cache payments; invalidate on dish/order events (already patterned) |
| Mobile | Touch targets on Stream phase buttons; branded page mobile share sheet |

### 6.2 Monetization optimization

1. Turn package assign into **hard entitlement** (module flags sync + `kitchen_module_overrides` default strategy for paid kitchens).  
2. Map every sellable portal feature to a `platform_features.key` (already seeded — keep catalog authoritative).  
3. Customer-facing packages only when we have a clear customer SKU (most value is owner packages today).  
4. Messaging wallet: show remaining blasts before send (once send exists).

### 6.3 Competitive optimization

| Move | Against |
|------|---------|
| Lead with trust + zero commission, not “another food app” | Aggregators |
| Prove live dish phases with customer watch | Social-only kitchens |
| Template send from CRM = owned channel | WhatsApp-sheet chaos |
| Golden day + (future) E2 lock = quality OS | Commodity menus |

---

## 7. Flow changes required (summary)

| Journey | Change | Priority |
|---------|--------|----------|
| Customer | Watch-live page + deep link from live card | P1 |
| Customer | Branded checkout continuity + clearer delivery payer | P1 |
| Owner | Template compose → audience → send → receipt | P1 |
| Owner | Stream “proof of viewers” + dish-first go-live default | P1 |
| Owner | Nav gated by package modules | P0 |
| Admin | RBAC on all mutating `/admin/*` | P0 |
| Admin | Package assign preview + force module sync | P0 |
| Admin | Audit log for secrets, refunds, suspend, package assign | P1 |
| Cross | Post-send / post-pay event → notify → UI reflection always | P0 (EDD hygiene) |

---

## 8. Implementation changes required

### 8.1 P0 engineering backlog

| Work | Service(s) | Notes |
|------|------------|-------|
| Extend `assert_admin_permission` to **all** identity admin mutations + shared helper for billing/notification admin | identity, billing, notification, gateway | Permissions: `refunds:*`, `api_keys:*`, `flags:*`, `customers:*`, `tickets:*` |
| Seed role→permission matrix for ops/support/finance | identity migration/seed | Document matrix in this file §8.3 |
| Hard entitlement: resolve kitchen package → feature keys → module flags on assign; enforce `require_kitchen_module` / feature checks on hot paths | billing + identity + each domain | Turn on overrides strategy carefully (migrate existing kitchens) |
| Live Razorpay path + refund webhook completion | billing | Kill mocks in prod (`APP_ENV` / feature flag) |
| Prod OTP via WhatsApp/SMS; disable fixed `123456` when not demo | identity, notification | |

### 8.2 P1 engineering backlog

| Work | Service(s) | Notes |
|------|------------|-------|
| `POST .../templates/{id}/send` + CRM segment query + notify dispatch + wallet | marketing, notification, billing | Events on `ckac:marketing:template` + notify streams |
| Customer LiveKit viewer page | streaming, website customer | Reuse viewer-token API |
| Owner media upload signed URL flow | media/MinIO, catalog | |
| Admin audit table `admin_audit_events` | identity | Who changed what |
| Kitchen health aggregate endpoint for admin list | identity + billing reads | |

### 8.3 Suggested RBAC permission catalog

| Permission | Roles (proposed) |
|------------|------------------|
| `*` | superadmin |
| `kitchens:read/write` | superadmin, ops, support(read) |
| `customers:read/write` | superadmin, support |
| `employees:read/write` | superadmin |
| `packages:read/write` | superadmin, ops(read), finance(read) |
| `refunds:read/write` | superadmin, finance, support(read) |
| `api_keys:read/write` | superadmin |
| `flags:read/write` | superadmin, ops |
| `tickets:read/write` | superadmin, support, ops |
| `marketing:read` | superadmin, ops, support |
| `billing:read` | superadmin, finance, ops |

### 8.4 E1–E2 (next major product — design ready)

Do **not** start until P0 entitlement/RBAC/money trust is acceptable for hired ops staff.

- E1: purchase ledger → stock truth → profit reporting  
- E2: chef standard lock from ratings/volume  
- Spec: [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md)

---

## 9. Recommended release sequencing

```
Wave A — Trust the control plane (1–2 sprints)
  A1 Admin RBAC complete + audit
  A2 Hard package entitlements + owner nav gating
  A3 Live Razorpay + prod OTP posture on kitchcu.com

Wave B — Complete promised journeys
  B1 Template send / CRM blast
  B2 Customer live watch + Stream polish
  B3 Media upload UX

Wave C — Quality & margin OS
  C1 E1 purchases
  C2 E2 chef standard lock
  C3 Admin platform analytics

Wave D — Scale architecture
  D1 Move off single-VM to Cloud Run / SQL / Memorystore (DEPLOYMENT-GCP §1–10)
  D2 OTel + SLOs + load tests on money paths
```

---

## 10. Success metrics (what “good” looks like)

| Metric | Target (directional) | Reads from |
|--------|----------------------|------------|
| Owner time-to-first-order | < 1 day after menu publish | orders |
| % orders with live-capture menu kitchen | > 95% | catalog |
| Checkout completion rate | Track by kitchen | order + billing |
| Rating attach rate (delivered) | > 25% | ratings |
| Template send → order within 24h | Track after B1 | marketing + orders |
| Live session → order conversion | Track after B2 | streaming + orders |
| Support MTTR on tickets | Track | notification |
| Zero cross-tenant incidents | 0 | QA + audit |
| p95 gateway health | Per system benchmark | gateway |

---

## 11. Document control

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-07-18 | Initial deep analysis after P19–P28: achievements, gaps, journey/flow/impl changes, competitive honesty gate, Wave A–D sequencing |

**Update policy:** On every release cut, refresh §4 achievements, §5 gaps, §9 sequencing, and Advancement Tracker in the same PR.

**Related**

- Advancement: [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md)  
- Deploy: [`DEPLOYMENT-GCP.md`](./DEPLOYMENT-GCP.md)  
- Gaps (legacy): [`CKAC-GAPS.md`](./CKAC-GAPS.md) — superseded for open items by §5 here  
- Agents: [`../AGENTS.md`](../AGENTS.md)  

---

*KitchCu Platform Strategic Analysis v1.0 — Confidential — July 2026*
