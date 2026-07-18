# KitchCu — Platform Solution Blueprint

**Living operating document.** For every user type and control surface:  
**Expectations → Problem (CEO/CPO) → Solution (product) → Implementation (CTO) → Achievements · Gaps · Architecture · DB · UX.**

| Field | Value |
|-------|-------|
| Version | **1.0** |
| Date | 2026-07-18 |
| Baseline | S1–S18 + P19–P28 |
| Persona lived experience | [`PLATFORM-PERSONA-DEEP-DIVE.md`](./PLATFORM-PERSONA-DEEP-DIVE.md) |
| Strategic waves | [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) |
| Step APIs | [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) |
| Tracker | [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md) |

**Method (every section below)**

| Lens | Asks |
|------|------|
| **User** | What do I expect? What breaks trust? |
| **CEO** | Does this grow kitchens / unit economics / zero-commission story? |
| **CPO** | Clear journey? Progressive complexity? Honest claims? |
| **CTO** | Service boundary, events, tenant safety, indexes, idempotency, 100k sessions? |
| **DBA** | Schema, keys, migrations, RLS, query shape? |
| **QA** | Happy / auth fail / tenant / empty / concurrency? |

Status tags: ✅ Done well · 🟡 Partial · 🔴 Gap / not built · 📋 Design only

---

# A. Customer journeys

---

## A1. Discover → trust menu

| | |
|--|--|
| **Expectations** | Find nearby kitchens fast; believe the food photo; filter by diet / live / distance; open a kitchen’s own brand page when shared. |
| **Problem (CEO)** | Aggregators win on liquidity but lose trust (stock photos, opaque kitchens). We win if discovery feels local and honest. |
| **Problem (CPO)** | First session must not look like a marketplace dump — branded entry and live-capture must be first-class. |
| **Solution** | Nearby map/list + filters; `/k/{code}` branded storefront; live-capture as trust signal; optional live_only badge. |
| **Implementation (CTO)** | Identity `GET /kitchens/public/nearby` (PostGIS distance); public by-code; catalog menu; customer PWA `NearbyKitchensList`, `BrandedStorefront`. Cache `menu:{kitchen_id}` TTL 5m. |
| **Achievements / done well** | ✅ Nearby + diet/live-capture/live filters · ✅ Branded `/k/:code` (P19) · ✅ Live-capture enforcement on dish heroes |
| **Gaps** | 🔴 Weak personalization/ranking · 🟡 Favourites missing · 🟡 Hindi UI missing |
| **Architecture enhancements** | Projection `kitchen_discovery_cards` (denormalized: open, live, rating_avg, has_live_capture) refreshed on events; avoid N+1 menu fetches on list. |
| **DB enhancements** | Indexes `(status, city)` + GiST on location (exists pattern); materialize `avg_home_taste` on kitchen or dish aggregate table for sort; `customer_favourite_kitchens(customer_id, kitchen_id)`. |
| **UX enhancements** | Skeleton loaders; “Open now” chip; save kitchen; share branded link sheet. |

---

## A2. Auth → cart → checkout → pay

| | |
|--|--|
| **Expectations** | Login once; cart survives; fee explained before pay; pay or COD; clear failure recovery; one receipt for multi-kitchen. |
| **Problem (CEO)** | Abandoned checkout kills unit economics; fake fees destroy trust. |
| **Problem (CPO)** | Delivery payer modes and multi-kitchen are differentiators — must feel simple, not engineer. |
| **Solution** | OTP/OAuth; local cart → quote accept → idempotent place order → billing create/capture/UPI/COD; master-order for multi-kitchen + PDF. |
| **Implementation (CTO)** | Order `POST .../orders/customer` + `Idempotency-Key`; delivery quote; billing customer/master pay; feature `multi_kitchen_checkout`; gateway path markers. |
| **Achievements / done well** | ✅ Idempotent place · ✅ Fee accept UX · ✅ Multi-kitchen master receipt (S8/S9 model) · ✅ COD + online domain |
| **Gaps** | 🔴 Cart not server-persisted · 🟡 Razorpay mock/prod risk · 🔴 Weak pay-retry screen · 🟡 Coupon error clarity |
| **Architecture enhancements** | Optional `cart_snapshots` service or order-draft for logged-in carts; payment state machine UI bound to billing events; never cache payments. |
| **DB enhancements** | `ckac_orders.customer_carts` / `cart_lines` (kitchen_id, dish_id, qty, updated_at) keyed by customer_id; index `(customer_id, updated_at DESC)`; payment idempotency keys unique. |
| **UX enhancements** | Default last address; “Complete payment” for pending; multi-kitchen confirm one screen. |

---

## A3. Track → rate → repeat → dashboard

| | |
|--|--|
| **Expectations** | Know where food is; rate home taste; reorder in one tap; see savings/refunds/addresses. |
| **Problem (CEO)** | Repeat rate is the SaaS flywheel for kitchens (and our retention of kitchens). |
| **Problem (CPO)** | Rating must be post-delivery only; language = home taste not hotel stars. |
| **Solution** | Track token page + Maps; ratings API; repeat endpoint; customer dashboard tabs. |
| **Implementation (CTO)** | Delivery track; ratings verified purchase; `POST .../orders/{id}/repeat`; dashboard aggregate API; notify tracking intervals (S14). |
| **Achievements / done well** | ✅ Track `/t/:token` · ✅ Home-taste ratings · ✅ Repeat · ✅ Dashboard depth |
| **Gaps** | 🟡 Prompt timing after delivery · 🟡 WA/push reliability · 🟡 Complaints → ticket UX polish |
| **Architecture enhancements** | Event `order.delivered` → notify schedule rate prompt; dashboard from read model not live joins. |
| **DB enhancements** | `rating_prompt_sent_at` on orders; indexes for customer order history `(customer_id, created_at DESC)`. |
| **UX enhancements** | Soft rate banner 30–120m after delivered; one-tap repeat with address confirm. |

---

## A4. Watch live (customer)

| | |
|--|--|
| **Expectations** | If kitchen is “live,” I can watch prep in-app; see ingredients → prep → prepared. |
| **Problem (CEO)** | Over-claiming live without watch burns brand. |
| **Problem (CPO)** | Live filter without Watch CTA is a broken journey. |
| **Solution** | Nearby live card → Watch → LiveKit viewer token → phase overlay from showcase API. |
| **Implementation (CTO)** | Exists: go-live, showcase phases, `POST .../viewer-token`. Missing: customer route + player. Feature `live_streaming`; module `streaming`/`livekit`. |
| **Achievements / done well** | ✅ Session + phases + live discovery filter · ✅ Viewer-token API · ✅ Customer `/live/:sessionId` Watch + Nearby CTA · ✅ Showcase phase poll |
| **Gaps** | ✅ Embedded LiveKit player · 🟡 Viewer count proof · 🟡 Prod LiveKit credentials |
| **Architecture enhancements** | Short-lived viewer tokens; rate-limit token mint; CDN for LiveKit; kill via module flags. |
| **DB enhancements** | Already on `live_sessions` (dish_id, showcase_phase, prepared_at); add `viewer_joins` counters table if analytics needed. |
| **UX enhancements** | Phase chips read-only; embed LiveKit JS SDK when `LIVEKIT_URL` set. |

---

# B. Kitchen owner journeys

---

## B1. Day-1 onboard → first shareable kitchen

| | |
|--|--|
| **Expectations** | Register, create kitchen, add 3 dishes, get a link to share before dinner. |
| **Problem (CEO)** | Time-to-first-order is the north-star activation metric. |
| **Problem (CPO)** | Account tabs (WA/PG/GST) overwhelm; progressive complexity broken. |
| **Solution** | Guided checklist: kitchen → 3 live dishes → WA optional → publish branded page → share. Defer Growth until checklist done. |
| **Implementation (CTO)** | Exists: register/OTP/kitchen/dishes/branded_page. Missing: checklist state machine + nav gating. |
| **Achievements / done well** | ✅ OTP onboard · ✅ Live-capture force · ✅ Branded publish · ✅ Kitchen code |
| **Gaps** | 🔴 No guided checklist · 🟡 Media upload friction · 🟡 Growth nav always visible |
| **Architecture enhancements** | `kitchen_activation` JSONB on kitchen settings; feature flag `owner_onboarding_v2`. |
| **DB enhancements** | `kitchens.settings.onboarding` `{dishes_ok, wa_ok, branded_ok, shared_at}`; or table `kitchen_onboarding_steps`. |
| **UX enhancements** | Single “Get live today” wizard; camera-first dish create. |

---

## B2. Busy service — orders & stock

| | |
|--|--|
| **Expectations** | Hear new orders; accept; advance status; stock warns; refund when needed; cook can help without my OTP. |
| **Problem (CEO)** | Shared owner phone = churn + security risk at scale. |
| **Problem (CPO)** | Inbox must be glove-friendly; staff roles are table-stakes for real kitchens. |
| **Solution** | Strong lifecycle (done) + urgency UX + **kitchen staff RBAC** (design → build) + stock warnings (done) + refunds evidence (done). |
| **Implementation (CTO)** | Order state machine + stock deduct on accept; refunds billing; **new** `kitchen_members` + staff JWT. |
| **Achievements / done well** | ✅ Full lifecycle · ✅ Stock deduct/warnings (F19) · ✅ Refunds with evidence · ✅ Analytics |
| **Gaps** | 🔴 Kitchen staff roles · 🟡 Inbox urgency · 🔴 Profit without E1 purchases |
| **Architecture enhancements** | Staff JWT `type:staff` scoped to one kitchen; permissions subset; events unchanged. |
| **DB enhancements** | `ckac_identity.kitchen_members(id, kitchen_id, phone, role, is_active)` + unique (kitchen_id, phone); RLS by kitchen_id. |
| **UX enhancements** | Beep on `received`; big status chips; cook mode UI. |

---

## B3. Growth marketer — CRM, templates, stream

| | |
|--|--|
| **Expectations** | Own my customer list; send WA/email from templates; go live with dish phases; see golden days. |
| **Problem (CEO)** | CRM ownership is the anti-aggregator moat — only if blasts actually send. |
| **Problem (CPO)** | Portal promises templates/live; product stops at CRUD/session plumbing. |
| **Solution** | Templates CRUD (done) + **send pipeline** + CRM segments + wallet; Stream phases (done) + **in-app publish/watch**; golden day (done). |
| **Implementation (CTO)** | `POST .../templates/{id}/send` → marketing → notify → billing wallet; LiveKit embed; package module `marketing_broadcast` / `streaming` hard-gated. |
| **Achievements / done well** | ✅ CRM/coupons/promos · ✅ Template CRUD (P26) · ✅ **Send** Preview/Send + `message_template.send_requested` · ✅ Stream phases · ✅ Customer Watch · ✅ Package-gated Growth nav |
| **Gaps** | 🟡 Meta outbound delivery + wallet debit · 🟡 Send receipt history table · ✅ LiveKit embed · ✅ Per-phone fan-out |
| **Architecture enhancements** | Notify consumer per phone; wallet debit idempotent; send job table. |
| **DB enhancements** | `message_template_sends(...)` for history; indexes `(kitchen_id, created_at DESC)`. |
| **UX enhancements** | Confirm cost → receipt; embed player when LiveKit configured. |

---

## B4. Integrations — WhatsApp & payments

| | |
|--|--|
| **Expectations** | Connect my WA number and Razorpay without seeing platform secrets; admin can help. |
| **Problem (CEO)** | Credential confusion = support load and security incidents. |
| **Problem (CPO)** | Split platform vs kitchen secrets must stay visible in UX copy. |
| **Solution** | Owner WA/PG pages + Admin kitchen tabs (done); platform secrets only API Keys (done). |
| **Implementation (CTO)** | Identity WA fields; billing `kitchen_payment_gateways`; encrypt secrets; admin routes. |
| **Achievements / done well** | ✅ Correct secret split (P21) · ✅ Admin + owner surfaces · ✅ Encrypt/mask patterns |
| **Gaps** | 🟡 Outbound WA reliability · 🟡 Live Razorpay in prod · ✅ Hard module gate when packaged |
| **Architecture enhancements** | Health probe “WA reachable” / “PG keys valid” cached 5m for admin strip. |
| **DB enhancements** | Already; add `last_validated_at` on WA/PG rows. |
| **UX enhancements** | Green/red connected badges; never show raw secrets. |

---

# C. Multilevel admin & control plane

---

## C1. Superadmin — full control

| | |
|--|--|
| **Expectations** | See platform health; hire staff with real boundaries; sell packages; kill features; hold platform secrets; audit who did what. |
| **Problem (CEO)** | Cannot hire ops/support until RBAC is real — one mistake = Meta secret leak. |
| **Problem (CPO)** | Control plane must match org chart: secrets ≠ tickets ≠ refunds. |
| **Solution** | Employees + roles (done) + **enforce permissions on all mutations** + **tab filtering** + **audit log** + kitchen workspace (done) + packages (done) + flags (done). |
| **Implementation (CTO)** | Shared `RequirePerm`; `GET /admin/me` → permissions[]; `admin_audit_events`; UI filter `TABS`. |
| **Achievements / done well** | ✅ Kitchen workspace (P28) · ✅ Packages (P25) · ✅ Employees (P27) · ✅ Shared `admin_rbac` enforced on identity/billing/tickets · ✅ `GET /admin/me` → permissions + allowed_tabs · ✅ UI tab filter + role badge · ✅ Overview `allSettled` |
| **Gaps** | ✅ Audit tab + `admin_audit_events` · 🟡 Billing mutations not yet audited · 🟡 Single-VM ops risk |
| **Architecture enhancements** | Audit write in same TX as mutation; correlation id on audit. |
| **DB enhancements** | `ckac_identity.admin_audit_events(...)` + indexes; identity `014` expands customers/flags/refunds:read grants. |
| **UX enhancements** | Kitchen health strip; audit timeline (next). |

---

## C2. Ops admin — onboard & unblock kitchens

| | |
|--|--|
| **Expectations** | Fix WA/PG/modules; assign view of packages; force subscription when billing glitches; never touch Meta App Secret. |
| **Problem (CEO)** | Ops is the scale lever for kitchen activation. |
| **Problem (CPO)** | Role exists in seed; job boundary doesn’t in routes/UI. |
| **Solution** | Enforce `kitchens:write`, `owners:write`, PG/modules perms; hide API Keys/Refunds write/Employees; ops checklist in kitchen workspace. |
| **Implementation (CTO)** | Add asserts on subscription force, module flags, PG put; UI perm map. |
| **Achievements / done well** | ✅ WA/status/PG/modules gated · ✅ Workspace tabs · ✅ Role grants · ✅ UI tabs filtered by `/admin/me` |
| **Gaps** | 🟡 Ops checklist UX · 🟡 Audit trail |
| **Architecture enhancements** | Ops playbook as read model from kitchen health. |
| **DB enhancements** | Reuse audit; optional `ops_notes` on kitchen. |
| **UX enhancements** | “New kitchen checklist” panel. |

---

## C3. Support admin — tickets & calm

| | |
|--|--|
| **Expectations** | Own ticket queue; read kitchen context; limited customer actions; no secrets/money write. |
| **Problem (CEO)** | Support with secret access = existential risk. |
| **Problem (CPO)** | `tickets:write` seeded but not enforced; UI shows everything. |
| **Solution** | Enforce tickets; `customers:read` / `customers:write` split; narrow UI; assignee + SLA. |
| **Implementation (CTO)** | Assert on notification ticket routes; identity customer routes; UI filter. |
| **Achievements / done well** | ✅ Tickets + AI escalation · ✅ `tickets:write` enforced on list/get/patch/reply · ✅ UI tabs narrowed via allowed_tabs |
| **Gaps** | 🟡 No SLA/assignee · 🟡 Support-specific Overview metrics |
| **Architecture enhancements** | Ticket assignment events; support metrics on Overview for support role. |
| **DB enhancements** | `tickets.assignee_admin_id`, `first_response_at`, `sla_due_at`; index `(status, sla_due_at)`. |
| **UX enhancements** | Assignee + SLA chips. |

---

## C4. Finance admin — packages & money

| | |
|--|--|
| **Expectations** | Design packages; map plans; assign kitchen packages; run refunds/settlements; export for accounting. |
| **Problem (CEO)** | Packages are how we monetize without food commission — must be real entitlements. |
| **Problem (CPO)** | Package write is gated; refunds are not — inverted trust. |
| **Solution** | Keep package RBAC; gate all money admin routes; hard entitlements on assign; CSV exports; GST rollup. |
| **Implementation (CTO)** | `refunds:read/write` on billing admin; entitlement sync; export endpoints. |
| **Achievements / done well** | ✅ Feature→package→plan→kitchen mapper · ✅ Seed packages · ✅ Package + refunds RBAC · ✅ Hard entitlements when package assigned · ✅ `GET .../entitlements` |
| **Gaps** | 🟡 No CSV/GST platform view · 🟡 Entitlement snapshot audit |
| **Architecture enhancements** | Cache `entitlements:{kitchen_id}` TTL 60s; invalidate on assign. |
| **DB enhancements** | Add `package_prices` / billing period if selling in-app; `entitlement_snapshots` for audit. |
| **UX enhancements** | Assign wizard with module preview; money console for finance-only. |

---

## C5. Package planner (product surface)

| | |
|--|--|
| **Expectations** | Platform features catalog; compose packages; map to subscription tiers; assign/override per kitchen; customer packages if needed. |
| **Problem (CEO)** | Without hard gates, Pro vs Starter is a slide, not a product. |
| **Problem (CPO)** | Planner UI exists; owner/customer don’t feel the plan. |
| **Solution** | Planner (done) + **hard entitlement mode** + owner “Your plan includes” page + customer empty states. |
| **Implementation (CTO)** | Turn on overrides strategy; map every sellable capability to `platform_features.key` + `module_key`; enforce `require_kitchen_module` / feature on hot paths; owner nav filter from entitlement API. |
| **Achievements / done well** | ✅ Admin Packages UI · ✅ Seed features/packages · ✅ Kitchen Package tab · ✅ Assign syncs **all** module keys on/off · ✅ Hard default-deny for packaged kitchens · ✅ Owner nav gated by entitlements |
| **Gaps** | 🟡 Owner “Your plan includes” matrix page · 🟡 Not every hot path package-keyed yet |
| **Architecture enhancements** | Cache entitlements; enforce `require_kitchen_module` on remaining growth/stream edges. |
| **DB enhancements** | Ensure every module_key in `KITCHEN_MODULE_KEYS` has a feature row; `plan_packages` cover tiers. |
| **UX enhancements** | Package compare on Subscription; admin assign diff view. |

**Seed packages (reference)**

| Package | Intent | Example features |
|---------|--------|------------------|
| starter | Core ops | whatsapp, razorpay, customer_checkout, loyalty_crm |
| growth | Scale marketing | + marketing_broadcast, ratings, refunds |
| pro | Full stack | + streaming, livekit, discovery |
| customer_free | Diner default | customer_checkout, discovery, ratings |

---

## C6. Control plane — flags, journeys, API keys

| | |
|--|--|
| **Expectations** | Kill refunds/streaming/registrations instantly; see journey health; rotate platform secrets without redeploy. |
| **Problem (CEO)** | Kill switches save the company during incidents. |
| **Problem (CPO)** | Powerful tools need RBAC + audit. |
| **Solution** | Control tab (done) + perm `flags:write` / `api_keys:write` enforced + audit. |
| **Implementation (CTO)** | Asserts on feature-flag + api-key routes; audit rows. |
| **Achievements / done well** | ✅ Flags + journeys UI · ✅ DB-backed secrets · ✅ `flags:*` + `api_keys:write` enforced · ✅ Tabs hidden without perms |
| **Gaps** | ✅ Audit trail UI · 🟡 Confirm modal on secret rotate polish |
| **Architecture / DB** | As C1 audit. |
| **UX** | Confirm modal on secret rotate; last-rotated display. |

---

# D. Cross-cutting platform systems

---

## D1. Money path (all actors)

| | |
|--|--|
| **Expectations** | Pay once; kitchens get settlements; refunds fair; no food commission; GST for India. |
| **CEO** | Subscription SaaS preserved; Route split for multi-kitchen credibility. |
| **CPO** | Customer shouldn’t see Route complexity; owner sees paid/refund clearly. |
| **CTO** | State machines + idempotency + webhooks; mocks off in prod. |
| **Achievements** | ✅ Payments/settlements/refunds/GST/wallets modeled + events |
| **Gaps** | 🔴 Live provider maturity · 🟡 Capture/orphan UX · ✅ Refund admin RBAC |
| **Arch** | Webhook workers; no pay cache; outbox for settlement events |
| **DB** | Unique idempotency; refund evidence tables (exist); settlement indexes by kitchen_id |
| **UX** | Pending pay recovery; owner settlement list |

---

## D2. Notifications & WhatsApp

| | |
|--|--|
| **Expectations** | Order updates arrive; blasts send; inbound becomes drafts. |
| **CEO** | WhatsApp-native is distribution. |
| **CPO** | Inbound drafts strong; outbound + templates incomplete. |
| **CTO** | Notify service owns dispatch; marketing owns template content; wallet owns cost. |
| **Achievements** | ✅ Webhook → drafts · ✅ Order/status notify (S14) · ✅ Support chat/tickets |
| **Gaps** | ✅ Per-phone fan-out · 🟡 Meta Cloud outbound · 🟡 Prod OTP · 🟡 Wallet UX |
| **Arch** | Single dispatch pipeline for daily-menu + template send |
| **DB** | `notify_dispatches` already patterned; link `template_send_id` |
| **UX** | Delivery receipts on owner Templates page |

---

## D3. Entitlements & progressive complexity

| | |
|--|--|
| **Expectations** | Trial kitchen sees core ops; Pro unlocks stream/blasts; UI doesn’t tease locked tools without upgrade path. |
| **CEO** | Monetization integrity. |
| **CPO** | Progressive complexity charter. |
| **CTO** | Packaged kitchens default-deny missing module flags. |
| **Achievements** | ✅ Feature/module flags · ✅ Package mapper · ✅ Hard mode + entitlements API · ✅ Owner nav filter |
| **Gaps** | 🟡 Unpackaged kitchens still soft-open · 🟡 Upgrade CTA copy on locked routes |
| **Arch** | Cache entitlements; invalidate on assign |
| **DB** | Snapshot entitlements on assign |
| **UX** | Locked nav → “Upgrade to Growth” |

---

## D4. Scale architecture (100k sessions)

| Area | Done well | Enhancement |
|------|-----------|-------------|
| Services | Stateless FastAPI + schema split | Cloud Run / SQL / Memorystore |
| Events | Outbox + Redis Streams | Kafka Phase 3; async outbox workers |
| Edge | Gateway + rate limit + correlation | Per-tenant quotas; WAF |
| Tenant | kitchen_id discipline | Prove RLS on |
| Admin | Workspace + packages | Pagination everywhere; projections |
| Obs | /health live/ready | OTel + money SLOs |
| Compute | Single VM demo | Leave VM for Wave D |

---

## D5. Kitchen staff (future persona)

| | |
|--|--|
| **Expectations** | Manager accepts orders; cook advances status; no shared OTP. |
| **CEO** | Unlocks multi-person kitchens → larger TAM. |
| **CPO** | Separate from platform employees. |
| **CTO** | `kitchen_members` + staff JWT; never platform admin roles. |
| **Status** | 🔴 Not built · 📋 Needs MODULE-DESIGN-PACK |
| **DB** | `kitchen_members`, `kitchen_member_invites` |
| **UX** | Invite by phone; role picker; cook mode |

---

## D6. Quality & profit loop (E1–E2)

| | |
|--|--|
| **Expectations** | Know true food cost; lock chef standard from ratings/volume. |
| **CEO** | Margin intelligence = pricing power. |
| **CPO** | Completes Growth OS story. |
| **CTO** | Design pack ready — implement after Wave A trust. |
| **Status** | 📋 [`E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md`](./E1-E2-KITCHEN-QUALITY-LOOP-DESIGN.md) |
| **DB** | purchases, movements, recipe_standard_versions (spec) |

---

# E. Master matrices

---

## E1. Journey scoreboard

| Journey | Persona | Score | Blocker to A |
|---------|---------|-------|--------------|
| Discover → menu | Customer | A | Ranking |
| Checkout → pay | Customer | B+ | Live PG + retry |
| Track → rate | Customer | A− | Prompt timing |
| Watch live | Customer | A− | Prod LiveKit config |
| Owner day-1 | Owner | A− | Checklist |
| Order lifecycle | Owner | A | Staff roles |
| Templates send | Owner | A− | Meta outbound + wallet debit |
| Stream cook | Owner | A− | Prod LiveKit + camera UX polish |
| Package plan | Finance | A− | Owner plan matrix page |
| Admin hire safely | Superadmin | A− | Billing audit + exports |
| Support tickets | Support | A− | SLA/assignee |
| Kitchen staff | Cook | F | Not built |

---

## E2. Control level × permission × enforce

| Level | Surface | Permission | Enforced today? |
|-------|---------|------------|-----------------|
| L0 Secrets | API Keys | `api_keys:write` | ✅ Yes |
| L1 Governance | Flags/journeys | `flags:read/write` | ✅ Yes |
| L2 Monetization | Packages | `packages:*` | ✅ Yes |
| L3 Staff | Employees | `employees:*` | ✅ Yes |
| L4 Kitchen | WA/status | `kitchens:write` | ✅ Yes |
| L4 Kitchen | PG/modules | kitchens/billing | ✅ Yes |
| L5 Care | Tickets | `tickets:write` | ✅ Yes |
| L5 Care | Customers | `customers:read/write` | ✅ Yes |
| L6 Money | Refunds | `refunds:read/write` | ✅ Yes |

---

## E3. Solution backlog (CEO priority order)

| # | Solution | Primary lens | Wave | Status |
|---|----------|--------------|------|--------|
| 1 | Enforce admin RBAC + tab filter + audit | CEO trust / hire | A | ✅ |
| 2 | Hard package entitlements + owner nav | CEO monetization | A | ✅ |
| 3 | Live Razorpay + prod OTP posture | CEO / CTO | A | ⏳ |
| 4 | Template send pipeline | CPO honesty | B | ✅ Preview/Send + per-phone fan-out |
| 5 | Customer Watch + LiveKit embed | CPO honesty | B | ✅ |
| 6 | Kitchen staff design→build | CEO TAM | B/C | ⏳ |
| 7 | E1–E2 quality/profit | CPO OS | C | ⏳ |
| 8 | Cloud Run scale path | CTO 100k | D | ⏳ |

---

## E4. Doc map (how these files work together)

| Doc | Job |
|-----|-----|
| **This file** | Expectations → problem → solution → implementation → arch/DB/UX per journey |
| [`PLATFORM-PERSONA-DEEP-DIVE.md`](./PLATFORM-PERSONA-DEEP-DIVE.md) | Lived voice + friction detail |
| [`PLATFORM-STRATEGIC-ANALYSIS.md`](./PLATFORM-STRATEGIC-ANALYSIS.md) | Competitive + Waves A–D |
| [`CKAC-USERFLOWS.md`](./CKAC-USERFLOWS.md) | Step-by-step API calls |
| [`ADVANCEMENT-TRACKER.md`](./ADVANCEMENT-TRACKER.md) | Ship status board |
| [`CKAC-COMPLETE-GUIDE.md`](./CKAC-COMPLETE-GUIDE.md) | Encyclopedia |

---

## F. Document control

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-07-18 | Full solution blueprint: every major journey with CEO/CPO/CTO triad, achievements, gaps, arch/DB/UX enhancements; admin multilevel + package planner |
| **1.1** | 2026-07-18 | Wave A/B gap-fill: admin RBAC enforced + tab filter; hard entitlements + owner nav; template send; customer Watch live |
| **1.2** | 2026-07-18 | P30: LiveKit embed (watch+publish), template per-phone fan-out, admin audit events + Audit tab |

**Update policy:** Closing a 🔴 gap updates the matching section score + E1/E3 in the same PR as code. Regenerate Complete Guide PDF only when encyclopedia status tables change materially.

---

*KitchCu Platform Solution Blueprint v1.2 — Confidential — July 2026*
