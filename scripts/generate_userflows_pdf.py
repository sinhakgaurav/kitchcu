#!/usr/bin/env python3
"""Generate Kitchcu User Flow Documentation Pack PDF v1.0 — detailed flow encyclopedia.

Source of truth: docs/CKAC-USERFLOWS.md v1.0 (July 2026).
Shared layout: scripts/pdf_guide.py (GuidePDF) — same pattern as generate_complete_guide_pdf.py.
"""

from pathlib import Path

from pdf_guide import GuidePDF

GUIDE_VERSION = "1.1"
GUIDE_DATE = "July 2026"
OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "CKAC-USERFLOWS.pdf"
UI = Path(__file__).resolve().parent.parent / "docs" / "assets" / "ui"


def build() -> GuidePDF:
    pdf = GuidePDF(
        title="Kitchcu User Flow Documentation Pack",
        version=GUIDE_VERSION,
        date=GUIDE_DATE,
    )

    # ── Cover ────────────────────────────────────────────────────────────
    pdf.cover(
        subtitle="Detailed User Flow Encyclopedia — Every Screen, API, Event, Diagram",
        audience="Audience: CPO, Product, Engineering, QA, Investors",
        lenses=[
            "Product — goal, persona, entry URL, preconditions, step-by-step UI actions",
            "Engineering — exact /api/v1 routes, request/response notes, domain events",
            "QA — success screens, failure paths, order status state machine",
        ],
        bullets=[
            "9 major flows: owner onboarding, daily ops, customer checkout, multi-kitchen",
            "split settlement, GST close, admin ops, customer login, coupons, live stream",
            "Order status state machine + JWT auth types table",
            "Gateway proxy map + cross-links to API.md, Complete Guide, UI screenshots",
            "Every route/event traced directly from services/*/app source, July 2026",
        ],
    )

    # ── TOC ──────────────────────────────────────────────────────────────
    pdf.toc([
        ("PART 0 — Reference", [
            "0.1 Purpose and document map",
            "0.2 Persona surfaces + ports",
            "0.3 Auth JWT types + demo credentials",
            "0.4 Order status state machine",
        ]),
        ("PART I — Owner Flows", [
            "1. Owner onboarding: register -> OTP -> kitchen -> dish -> order -> accept -> revenue",
            "2. Owner daily ops: login -> WhatsApp/manual order -> lifecycle -> tracking",
            "5. Owner GST: profile -> sync -> report -> close audit",
        ]),
        ("PART II — Customer Flows", [
            "3. Customer checkout: discover -> menu -> quote -> pay -> track -> rate",
            "4. Multi-kitchen cart -> master order -> split settlement -> master receipt",
            "7. Customer WhatsApp OTP / OAuth login",
        ]),
        ("PART III — Platform & Growth Flows", [
            "6. Admin: login -> overview -> Customers/Refunds/Control/Tickets",
            "8. Coupon apply / CRM promotion path",
            "9. Live stream opt-in (owner go-live, customer live filter)",
        ]),
        ("PART IV — Operating Reference", [
            "13. Gateway proxy map",
            "14. Cross-references",
            "Appendix: UI reference figures (8 surfaces)",
            "Document control",
        ]),
    ])

    # ═════════════════════════════════════════════════════════════════════
    # PART 0 — Reference
    # ═════════════════════════════════════════════════════════════════════
    pdf.lens_part("REFERENCE", 0, "Purpose, Personas & Auth")

    pdf.chapter("Purpose & Document Map")
    pdf.body(
        "This pack is the single source of truth for how a user actually moves through "
        "KitchCu: every UI step, every API call, every domain event, every failure path. "
        "It expands Complete Guide Part IV (17.1-17.8) into full encyclopedia depth, plus "
        "three flows the Guide only summarizes: multi-kitchen split settlement, coupons/CRM, "
        "and live streaming opt-in."
    )
    pdf.table(
        ["Question", "Answered by"],
        [
            ["What is KitchCu / why built this way?", "CKAC-COMPLETE-GUIDE.md Parts 0-III"],
            ["Step-by-step flows, encyclopedia depth?", "This document (CKAC-USERFLOWS.md/.pdf)"],
            ["Exact request/response shape?", "API.md; Gateway /docs /redoc /openapi.json; Portal /openapi"],
            ["What does the screen look like?", "docs/assets/ui/ screenshots"],
            ["What is built vs. designed?", "CKAC-IMPLEMENTATION-GUIDE.md"],
        ],
        [55, 115],
        size=7,
    )
    pdf.quote(
        "Read order: Complete Guide Parts 0-III -> this pack -> API.md for exact schemas -> "
        "live /openapi when writing code against a specific route."
    )

    pdf.chapter("Persona Surfaces")
    pdf.table(
        ["Persona", "Surface", "Host : Port", "JWT type"],
        [
            ["Guest / prospect", "Portal", "kitchcu.in : 13000", "none"],
            ["Owner / chef", "Kitchen", "kitchen.kitchcu.in : 13002", "owner"],
            ["Customer / diner", "Customer", "customer.kitchcu.in : 13001", "customer"],
            ["Platform admin", "Admin", "admin.kitchcu.in : 13003", "admin"],
        ],
        [45, 30, 75, 20],
        size=7,
    )
    pdf.table(
        ["Edge / service", "Port(s)", "Role"],
        [
            ["API Gateway", "18000", "Sole public HTTP edge for /api/v1/*; path routing; correlation ID"],
            ["identity..streaming (12 services)", "18001-18012", "Domain services; never called directly by clients"],
            ["PostgreSQL 16 + PostGIS", "15432", "ckac_<domain> schema per service"],
            ["Redis 7", "16379", "Streams (events) + tenant-scoped cache"],
        ],
        [55, 30, 85],
        size=7,
    )

    pdf.chapter("Auth JWT Types & Demo Credentials")
    pdf.table(
        ["Type", "Issued via", "Validated by", "Notes"],
        [
            ["owner", "auth/otp/verify", "get_current_owner", "Dev OTP fixed 123456"],
            ["customer", "customer/whatsapp/verify or oauth/complete", "get_current_customer", "type==customer checked"],
            ["admin", "admin/auth/login", "get_current_admin", "Platform scope only"],
            ["internal", "shared secret (not JWT)", "X-Internal-Key dependency", "Gateway blocks /internal/* (404)"],
        ],
        [22, 60, 55, 33],
        size=6,
    )
    pdf.table(
        ["Role", "Identifier", "Secret", "Notes"],
        [
            ["Owner (primary)", "9876543210", "OTP 123456", "Raj Sharma - CKPNQ001, Pune"],
            ["Owner", "9876543211", "OTP 123456", "Priya Mehta - Mehta Tiffins"],
            ["Owner", "9876543212", "OTP 123456", "Amit Desai - Desai Cloud Kitchen"],
            ["Owner", "9876543213", "OTP 123456", "Sneha Kulkarni - Kulkarni Home Food"],
            ["Customer", "9123456789", "OTP 123456", "Priya Customer - default diner"],
            ["Customer", "9123456780", "OTP 123456", "Rahul Menon - repeat/VIP segment"],
            ["Customer", "9988776655", "OTP 123456", "Ananya Guest - guest checkout"],
            ["Admin", "admin@kitchcu.dev", "admin123456", "Platform scope only"],
        ],
        [30, 42, 38, 60],
        size=6,
    )

    pdf.chapter("Order Status State Machine")
    pdf.body(
        "Enforced server-side by can_transition() in services/order/app/models.py. "
        "cancelled is reachable from any non-terminal state; delivered/cancelled are terminal."
    )
    pdf.mono(
        "received -> accepted -> preparing -> ready -> out_for_delivery -> delivered\n"
        "   |            |            |          |             |\n"
        "   +------------+------------+----------+-------------+--> cancelled (terminal)\n"
        "\n"
        "Every transition writes ckac_orders.order_status_events (immutable audit trail)\n"
        "and publishes order.status.changed on ckac:orders:order. Notification consumes\n"
        "this for WhatsApp status pushes (F45) and tracking-interval reminders (F29) --\n"
        "never a fabricated ETA, only owner-set prep/delivery windows."
    )

    # ═════════════════════════════════════════════════════════════════════
    # PART I — Owner Flows
    # ═════════════════════════════════════════════════════════════════════
    pdf.lens_part("OWNER", 1, "Onboarding, Daily Ops & GST")

    pdf.chapter("Flow 1 -- Owner Onboarding to First Revenue")
    pdf.body(
        "Goal: zero to same-day revenue in one sitting. Persona: Owner. "
        "Entry: kitchen.kitchcu.in login/register."
    )
    pdf.mono(
        "1. POST /owners/register                 (new owner)\n"
        "2. POST /auth/otp/request -> POST /auth/otp/verify   -> owner JWT\n"
        "3. POST /kitchens                         -> kitchen.created (code CKxxxnnn)\n"
        "4. POST /kitchens/{id}/media/upload       (live-capture hero, getUserMedia)\n"
        "5. POST /kitchens/{id}/dishes             -> dish.created\n"
        "   (server REJECTS heroes with is_live_capture:false)\n"
        "6. POST /kitchens/{id}/orders/manual      -> order.placed (status=received)\n"
        "7. PATCH /orders/{id}/status {accepted}   -> order.status.changed\n"
        "   -> internal deduct-order call to Catalog -> ingredient.stock.deducted\n"
        "8. GET /kitchens/{id}/analytics/summary   -> same-day revenue visible"
    )
    pdf.section("Failure paths")
    pdf.bullets([
        "Wrong/expired OTP -> 401; unregistered phone -> 404 on verify",
        "Gallery photo as hero -> 400/422, UI blocks save, prompts camera capture",
        "Invalid status jump (received->ready) -> 400",
        "Low/zero mapped-ingredient stock on accept -> 200 with stock-warning banner (not blocked)",
    ])

    pdf.chapter("Flow 2 -- Owner Daily Login + Order Intake + Lifecycle + Tracking")
    pdf.body("Goal: steady-state daily ops loop. Persona: Owner. Entry: kitchen.kitchcu.in dashboard.")
    pdf.mono(
        "Customer WA message -> Meta webhook -> Notification\n"
        "  -> POST /internal/kitchens/{id}/orders/from-whatsapp (X-Internal-Key)\n"
        "  -> order_drafts row -> order.draft.created\n"
        "Owner: GET .../orders/drafts -> review -> POST .../drafts/{id}/confirm\n"
        "  -> order.placed (status=received)          [manual alt: POST .../orders/manual]\n"
        "Owner advances lifecycle: PATCH /orders/{id}/status at each stage\n"
        "  received->accepted->preparing->ready->out_for_delivery->delivered\n"
        "  each hop -> order.status.changed -> Notification: WA push (F45) +\n"
        "  tracking-interval reminders (F29, ckac:notify:tracking)\n"
        "Public: GET /delivery/track/{token} -> current stage, no fake ETA"
    )
    pdf.section("Failure paths")
    pdf.bullets([
        "Confirm draft referencing a deleted dish -> 400/409, owner edits line items first",
        "Skipping a lifecycle stage (preparing->delivered) -> 400",
        "Expired/invalid tracking token -> 404 on public page",
    ])

    pdf.chapter("Flow 5 -- Owner GST: Profile -> Sync -> Report -> Close Audit")
    pdf.body(
        "Goal: delivered orders -> GST-compliant invoices -> closed monthly audit for "
        "accountant handoff. GST registration is optional; dormant until is_active=true."
    )
    pdf.mono(
        "PUT /kitchens/{id}/gst/profile         -> gst.profile.created/updated\n"
        "POST /kitchens/{id}/gst/sync?year&month -> gst.invoice.created x N\n"
        "GET .../gst/reports/monthly  + GET .../gst/reports/balance-sheet\n"
        "GET .../gst/audit  (pre-close review)\n"
        "POST .../gst/audit/close                -> gst.audit.closed (immutable snapshot)"
    )
    pdf.section("Failure paths")
    pdf.bullets([
        "Malformed GSTIN -> 422 validation",
        "Sync before registration date -> zero new invoices (documented, not an error)",
        "Closing an already-closed month -> 409; close is one-way (no un-close in v1)",
    ])

    # ═════════════════════════════════════════════════════════════════════
    # PART II — Customer Flows
    # ═════════════════════════════════════════════════════════════════════
    pdf.lens_part("CUSTOMER", 2, "Checkout, Multi-Kitchen & Login")

    pdf.chapter("Flow 3 -- Discover -> Menu -> Quote -> Checkout -> Pay -> Track -> Rate")
    pdf.body("Goal: core trust-to-purchase loop. Persona: Customer. Entry: customer.kitchcu.in.")
    pdf.mono(
        "GET /kitchens/public/nearby?diet&live_capture&live_only   (PostGIS-sorted)\n"
        "GET /kitchens/{id}/menu                (cached menu:{kitchen_id}, TTL 5 min)\n"
        "POST /delivery/quote                   -> fee shown BEFORE payment (closes C2)\n"
        "  status: ok | out_of_range -- checkout blocked cleanly if out of range\n"
        "[optional] POST /marketing/coupons/validate\n"
        "POST /kitchens/{id}/orders/customer     -> order.placed + delivery.tracking_created\n"
        "POST /billing/payments/customer -> .../upi-intent -> .../{id}/capture\n"
        "  -> payment.created -> payment.captured\n"
        "Owner advances lifecycle (Flow 2) ... GET /delivery/track/{token}\n"
        "delivered -> POST /customers/me/orders/{id}/ratings\n"
        "  (verifies delivered + ownership) -> rating.created / rating.aggregate.updated\n"
        "  overall = 0.6*home_taste + 0.4*quality"
    )
    pdf.section("Failure paths")
    pdf.bullets([
        "Distance beyond max_delivery_radius_km -> out_of_range, checkout blocked, no silent fee inflation",
        "Payment capture fails/times out -> order stays received/payment pending, retry same payment_id",
        "Rate a non-delivered or not-owned order -> 403/400",
    ])

    pdf.chapter("Flow 4 -- Multi-Kitchen Cart -> Master Order -> Split Settlement -> Master Receipt")
    pdf.body(
        "Goal: one cart across 2+ kitchens, one payment, fair independent per-kitchen "
        "payout. Kitchen A never sees Kitchen B was in the same cart."
    )
    pdf.mono(
        "Cart grouped by kitchen_id\n"
        "POST /customers/me/master-orders  (Idempotency-Key header)\n"
        "  -> ATOMIC: any invalid group rolls back the WHOLE master order\n"
        "  -> master_order.created (MORD-YYYYMMDD-XXXX) + order.placed per sub-order\n"
        "POST /billing/payments/customer/master  -> one aggregated payment\n"
        "POST .../master/{payment_id}/capture\n"
        "  -> payment.captured + payment.split.completed\n"
        "  -> settlement.created per kitchen (net_to_owner, Route-style, NO take-rate)\n"
        "GET /customers/me/master-orders/{id}/bill.pdf  -> ONE master receipt\n"
        "Each owner: GET /orders/{sub_order_id} -> sees only their own sub-order"
    )
    pdf.section("Failure paths")
    pdf.bullets([
        "One group has an unavailable dish -> 400/409, entire request fails, nothing partially created",
        "Duplicate submit with same Idempotency-Key -> returns original MasterOrderResponse",
        "Split capture fails mid-way -> no partial settlement marked paid, retried on same payment_id",
    ])

    pdf.chapter("Flow 7 -- Customer WhatsApp OTP / OAuth Login")
    pdf.body("Goal: least-friction auth via whichever channel the diner already uses.")
    pdf.table(
        ["Path", "Step 1", "Step 2", "Step 3"],
        [
            ["WhatsApp OTP", "POST .../whatsapp/request", "OTP 123456 (dev)", "POST .../whatsapp/verify -> customer JWT"],
            ["Social OAuth", "GET .../oauth/providers", "GET .../oauth/{p}/start", "POST .../oauth/{p}/complete -> customer JWT"],
        ],
        [30, 55, 45, 40],
        size=7,
    )
    pdf.body(
        "customer.created (ckac:identity:customer) fires only on first-time provisioning, "
        "from either path. Wrong/expired OTP -> 401; OAuth denial/state mismatch -> "
        "login failed, no partial customer record created."
    )

    # ═════════════════════════════════════════════════════════════════════
    # PART III — Platform & Growth Flows
    # ═════════════════════════════════════════════════════════════════════
    pdf.lens_part("PLATFORM", 3, "Admin, Coupons & Live Stream")

    pdf.chapter("Flow 6 -- Admin Login -> Overview -> Tickets")
    pdf.body(
        "Goal: platform-scope oversight -- is the platform healthy, who is stuck -- "
        "never owner-scope menu/order mutation."
    )
    pdf.mono(
        "POST /admin/auth/login              -> admin JWT (type=admin)\n"
        "GET /admin/stats                    -> platform counters\n"
        "GET /admin/owners | /admin/kitchens | /admin/orders  -> platform-wide lists\n"
        "PATCH /admin/kitchens/{id}/status   -> moderate (suspend etc.)\n"
        "GET /admin/tickets -> GET /admin/tickets/{id} -> PATCH ... -> POST .../reply\n"
        "  -> support.ticket.created / .updated / .replied (ckac:notify:support)"
    )
    pdf.body(
        "Admin JWT used against an owner-mutation route -> 403 by design (scope is "
        "intentionally narrow). Wrong password -> 401."
    )

    pdf.chapter("Flow 8 -- Coupon Apply / CRM Promotion Path")
    pdf.body(
        "Goal: owner runs a promotion from their own customer data; customer redeems at "
        "checkout -- no cross-tenant data sale, no commission."
    )
    pdf.mono(
        "Owner: GET /kitchens/{id}/crm/customers -> tag segment (PATCH .../crm/customers/{cid})\n"
        "Owner: POST /kitchens/{id}/coupons        -> coupon.created\n"
        "Owner: POST /kitchens/{id}/promotions      -> promotion.created\n"
        "Customer: GET /kitchens/{id}/promotions/active  (banner on menu)\n"
        "Customer: POST /marketing/coupons/validate  -> valid + discount_amount, or reason\n"
        "  (checkout continues per Flow 3 with discounted total)"
    )
    pdf.body(
        "Note: no separate promotion-redeem-at-checkout endpoint exists -- promotions "
        "surface passively via promotions/active; only coupons have an explicit "
        "checkout-time validate call. CRM tag on a customer who never ordered here -> 404."
    )

    pdf.chapter("Flow 9 -- Live Stream Opt-In (Go-Live / Live Filter)")
    pdf.body(
        "Goal: owner opt-in live prep sessions (never mandatory); customers filter "
        "discovery to kitchens live right now -- reinforces live-capture trust."
    )
    pdf.mono(
        "Owner: PATCH /kitchens/{id}/stream/settings   -> stream.settings_updated\n"
        "Owner: POST /kitchens/{id}/stream/go-live      -> stream.started\n"
        "Customer: GET /kitchens/public/nearby?live_only=true\n"
        "  (alt) GET /stream/live-kitchens\n"
        "Customer: POST /stream/sessions/{id}/viewer-token  -> LiveKit viewer join\n"
        "Owner: POST /kitchens/{id}/stream/end          -> stream.ended"
    )
    pdf.bullets([
        "go-live without opt-in enabled -> 403",
        "go-live while a session is already active -> 409, UI shows existing session",
        "viewer-token for ended/nonexistent session -> 404",
    ])

    # ═════════════════════════════════════════════════════════════════════
    # PART IV — Operating Reference
    # ═════════════════════════════════════════════════════════════════════
    pdf.lens_part("REFERENCE", 4, "Gateway Map & Cross-Links")

    pdf.chapter("Gateway Proxy Map")
    pdf.body(
        "Public clients only ever call the gateway (port 18000). resolve_service_url() "
        "routes by path prefix/marker to the owning service -- never by client-controlled host."
    )
    pdf.table(
        ["Path prefix / marker", "Upstream service"],
        [
            ["/api/v1/auth/*, /owners/*, /customers/* (base), /admin/* (non-ticket)", "identity"],
            ["/api/v1/customers/me/orders*, master-orders*, /orders/*", "order"],
            [".../customers/me/orders/.../ratings", "ratings"],
            ["/kitchens/* + categories|menu|dishes|cuisines|ingredients|media", "catalog"],
            ["/kitchens/* + orders|analytics", "order"],
            ["/kitchens/* + ratings|suggestions", "ratings"],
            ["/kitchens/* + crm|coupons|promotions", "marketing"],
            ["/kitchens/* + gst", "billing"],
            ["/kitchens/* + growth | learning | community | stream", "growth / learning / community / streaming"],
            ["/kitchens/* (fallback base CRUD)", "identity"],
            ["/billing/*, /webhooks/razorpay", "billing"],
            ["/marketing/*, /delivery/*, /growth/*, /learning/*, /community/*, /stream/*", "matching service"],
            ["/webhooks/* (non-razorpay), /support/*, /admin/tickets*", "notification"],
            ["/internal/*", "NOT PROXIED -- gateway returns 404"],
        ],
        [95, 75],
        size=6,
    )
    pdf.body(
        "Gateway-owned (not forwarded): GET /, /health/live, /health/ready, "
        "/openapi.json (aggregated, ?refresh=true), /docs, /redoc. Portal /openapi "
        "renders this same aggregated schema for non-technical browsing."
    )

    pdf.chapter("Cross-References")
    pdf.table(
        ["Need", "Go to"],
        [
            ["Exact request/response JSON", "docs/API.md; gateway /docs /redoc /openapi.json; Portal /openapi"],
            ["CEO/CPO/CTO narrative", "CKAC-COMPLETE-GUIDE.md 17.1-17.10 (condensed version)"],
            ["UI reference screenshots", "docs/assets/ui/ (8 surfaces)"],
            ["Feature acceptance criteria F01-F48", "CKAC-COMPLETE-PLANNING-BENCHMARK.md"],
            ["Architecture / scale / TDD+EDD", "CKAC-ARCHITECTURE-CTO.md, KITCHCU-ENGINEERING-STANDARDS.md"],
            ["Build status per module", "CKAC-IMPLEMENTATION-GUIDE.md"],
        ],
        [55, 115],
        size=7,
    )

    pdf.chapter("UI Reference — Flows in Context")
    pdf.figure(
        UI / "03-kitchen-login-pdf.jpg",
        "Kitchen login — Flow 1/2 entry + AuthLoginHighlights (zero commission, timing, "
        "delivery payer, Maps). Demo: 9876543210 / OTP 123456.",
        max_h=70,
    )
    pdf.figure(
        UI / "04-owner-dashboard-pdf.jpg",
        "Owner dashboard — Flow 2/5 home; CommissionAdvantagePanel reinforces SaaS model.",
        max_h=70,
    )
    pdf.figure(
        UI / "06-customer-login-pdf.jpg",
        "Customer login — Flow 7 entry; highlights ready-within, Maps, dashboard, in-range fee.",
        max_h=70,
    )
    pdf.figure(
        UI / "02-customer-home-pdf.jpg",
        "Customer home — Flow 3/4 discovery entry. Demo: CKPNQ001 near Koregaon Park.",
        max_h=70,
    )
    pdf.figure(
        UI / "07-admin-login-pdf.jpg",
        "Admin login — Flow 6: platform-control highlights before credentials.",
        max_h=70,
    )
    pdf.figure(
        UI / "05-admin-overview-pdf.jpg",
        "Admin overview — Flow 6: Customers/Refunds/Control nav + health tiles.",
        max_h=70,
    )
    pdf.figure(
        UI / "08-admin-control-pdf.jpg",
        "Admin Control — Flow 6 governance: journeys, feature flags, subscription overrides.",
        max_h=70,
    )

    pdf.chapter("Document Control")
    pdf.table(
        ["Field", "Value"],
        [
            ["Document", "CKAC-USERFLOWS.md / .pdf"],
            ["Version", "1.1"],
            ["Date", "July 2026"],
            ["Traceability", "Every route/event read directly from services/*/app source"],
            ["Change policy", "Update .md whenever a route/event/status changes; regenerate PDF same change"],
            ["Supersedes", "v1.2; aligned with Complete Guide v3.2.3 (P37–P40)"],
        ],
        [40, 130],
        size=7,
    )
    pdf.quote(
        "KitchCu User Flow Documentation Pack v1.1 - Confidential - July 2026."
    )

    return pdf


def main():
    pdf = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
