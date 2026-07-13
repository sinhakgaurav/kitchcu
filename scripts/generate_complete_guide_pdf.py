#!/usr/bin/env python3
"""Generate Kitchcu Complete Executive Guide PDF v2.0 — CEO + CPO + CTO."""

from pathlib import Path

from pdf_guide import GuidePDF

GUIDE_VERSION = "2.0"
GUIDE_DATE = "July 2026"
OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "CKAC-COMPLETE-GUIDE.pdf"


def build() -> GuidePDF:
    pdf = GuidePDF(
        title="Kitchcu Complete Executive Guide",
        version=GUIDE_VERSION,
        date=GUIDE_DATE,
    )

    pdf.cover(
        subtitle="Complete Executive Guide — CEO, CPO & CTO",
        audience="Audience: CEO, CPO, CTO, Product, Engineering, Investors",
        lenses=[
            "CEO — positioning, subscription economics, risks, current platform scale",
            "CPO — every module defined with challenges solved + journeys + KPIs",
            "CTO — architecture, event/data flows, logical ER, APIs, security",
        ],
        bullets=[
            "18 product modules (Gateway through Live Stream + GST + Quality Loop design)",
            "Sprints S1-S18 shipped: microservices, PWAs, billing, GST, ratings, growth",
            "Challenge map: owner P1-P12 and customer C1-C6 mapped to modules",
            "CTO diagrams: system architecture, order/payment/GST/quality flows, ER",
            "Zero per-order food commission; owner-owned CRM; live-capture truth",
            "Next: E1 purchase inventory + E2 chef standard lock (design pack ready)",
        ],
    )

    pdf.toc([
        ("PART I — CEO Lens", [
            "1. Executive Summary & Current State",
            "2. Market Positioning & Business Model",
            "3. Go-to-Market Phases & Risks",
        ]),
        ("PART II — CPO Lens", [
            "4. Vision, Personas & Principles",
            "5. Challenges to Module Solutions",
            "6. Module Catalog (full definitions)",
            "7. Product Journeys & Capability Ladder",
            "8. Product KPIs",
        ]),
        ("PART III — CTO Lens", [
            "9. System Architecture Diagram",
            "10. Event & Data Flow Diagrams",
            "11. Logical ER / Schema Diagram",
            "12. Services, APIs, Security & Standards",
            "13. Build Status Matrix",
        ]),
        ("Appendices", [
            "A. Feature bands F01-F48",
            "B. Document index",
        ]),
    ])

    # ── PART I: CEO ──────────────────────────────────────────────────────
    pdf.lens_part("CEO", 1, "Executive Strategy")

    pdf.chapter("Executive Summary & Current State")
    pdf.body(
        "Kitchcu is a B2B2C cloud kitchen operating system — not a food aggregator "
        "and not a restaurant POS. Owners run orders, menu, quality, CRM, payments, "
        "GST, and growth from one PWA. Customers get live-capture honesty, fair fees, "
        "home-taste ratings, and multi-kitchen checkout without surrendering ownership "
        "or paying per-order commission."
    )
    pdf.table(
        ["Stakeholder", "Challenge", "Kitchcu answer"],
        [
            ["Owner/chef", "WhatsApp chaos, commissions", "Unified hub + subscription SaaS"],
            ["Customer", "Fake photos, opaque fees", "Live media + fee quotes + tracking"],
            ["Platform", "Capital-efficient SaaS", "PWA-first event-driven services"],
        ],
        [32, 58, 80],
        size=7,
    )
    pdf.quote(
        "Keep day-one simple: accept an order and see revenue in minutes. "
        "Growth layers unlock after traction."
    )
    pdf.stat_boxes([
        ("Sprints shipped", "S1-S18"),
        ("Domain services", "13"),
        ("GST finance", "Live"),
        ("E1/E2 quality loop", "Design"),
    ])

    pdf.chapter("Market Positioning & Business Model")
    pdf.mono(
        "Aggregators (marketplace)          Kitchcu (operating system)\n"
        "-------------------------          -------------------------\n"
        "Per-order commission 18-30%        Flat subscription\n"
        "Platform owns the customer         Owner owns CRM + data\n"
        "Stock / studio photos              Live-capture dish media\n"
        "Speed race delivery timers         Owner-set quality SLA\n"
        "Single kitchen cart                Multi-kitchen master checkout\n"
        "No GST / quality OS                GST + ingredients + standards"
    )
    pdf.body("Non-negotiable: zero per-order food commission. Kitchen keeps food revenue.")
    pdf.table(
        ["Tier", "Monthly", "Role"],
        [
            ["Starter", "Rs 499", "Operations + basic reports"],
            ["Growth", "Rs 999", "CRM, coupons, deeper insight"],
            ["Pro", "Rs 1,999", "Multi-kitchen, priority support"],
        ],
        [40, 35, 95],
        size=8,
    )
    pdf.table(
        ["Metric", "Year 1 target"],
        [
            ["CAC (owner)", "< Rs 2,000"],
            ["Owner LTV", "> Rs 18,000"],
            ["LTV:CAC", "> 3:1"],
            ["Gross margin", "> 75% SaaS"],
        ],
        [85, 85],
        size=8,
    )

    pdf.chapter("Go-to-Market Phases & Risks")
    pdf.table(
        ["Phase", "Goal", "Status"],
        [
            ["1 Foundation", "Owner runs kitchen end-to-end", "COMPLETE S1-S18"],
            ["2 Growth polish", "Offline PWA, CRM automation", "Continuous"],
            ["3 Quality loop", "Purchases + locked chef standards", "Design pack"],
            ["4 Scale", "National / white-label", "Future"],
        ],
        [35, 85, 50],
        size=7,
    )
    pdf.table(
        ["Risk", "Mitigation"],
        [
            ["WhatsApp API change", "Manual + PWA intake always on"],
            ["Scope creep", "Design pack gate before code"],
            ["Rating fraud", "Verified purchase only"],
            ["Multi-kitchen refunds", "Sub-orders + Route settlements"],
            ["Onboarding friction", "5-min kitchen -> dish -> order"],
        ],
        [55, 115],
        size=7,
    )

    # ── PART II: CPO ─────────────────────────────────────────────────────
    pdf.lens_part("CPO", 2, "Product Modules & Challenges")

    pdf.chapter("Vision, Personas & Principles")
    pdf.body(
        "Every cloud kitchen scales like a brand — with data, taste standards, and "
        "direct customers — while diners see honest, real-time food truth."
    )
    pdf.table(
        ["Persona", "Promise", "Surface"],
        [
            ["Owner / Chef", "WhatsApp -> revenue same day", "kitchen.kitchcu.in"],
            ["Customer", "Trust, fair delivery, rate taste", "customer.kitchcu.in"],
            ["Admin", "Support + attention queue", "admin.kitchcu.in"],
            ["Market visitor", "Brand story & signup", "portal kitchcu.in"],
        ],
        [32, 70, 68],
        size=7,
    )
    pdf.bullets([
        "Quality over speed — owner-set prep/delivery windows",
        "Truth in media — live-capture heroes; no stock photo deception",
        "Owner owns CRM — spend, coupons, patterns stay with kitchen",
        "Progressive complexity — hide advanced until traction",
        "Growth OS, not restaurant POS / dine-in / KDS",
    ])

    pdf.chapter("Challenges to Module Solutions")
    pdf.section("Owner challenges (P1-P12)")
    pdf.table(
        ["ID", "Challenge", "Modules"],
        [
            ["P1", "Orders trapped in WhatsApp/calls", "Order + Notification"],
            ["P2", "Aggregator commission kills margin", "Billing subscription"],
            ["P3", "No daily revenue / segments", "Analytics + Growth + Reports"],
            ["P4", "Stock photos erode trust", "Catalog live-capture"],
            ["P5", "Taste drifts batch to batch", "Recipes + Ratings + E2"],
            ["P6", "Customer data owned by platforms", "Marketing CRM"],
            ["P7", "Promotions are guesswork", "Growth + daily menu"],
            ["P8", "Multi-channel lifecycle chaos", "Order status machine"],
            ["P9", "Stock unknown mid-service", "Ingredients + E1 purchases"],
            ["P10", "GST / monthly audit pain", "Billing GST"],
            ["P11", "Skills & trials hard to run", "Learning + Community"],
            ["P12", "Trust without ad spend", "Streaming live opt-in"],
        ],
        [12, 78, 80],
        size=6,
    )
    pdf.section("Customer challenges (C1-C6)")
    pdf.table(
        ["ID", "Challenge", "Modules"],
        [
            ["C1", "Cannot trust menu photos", "Catalog"],
            ["C2", "Opaque delivery fees", "Delivery"],
            ["C3", "Weak tracking", "Order + Notify + Delivery"],
            ["C4", "Generic star ratings", "Ratings home-taste"],
            ["C5", "One kitchen per cart", "Master checkout + Billing"],
            ["C6", "Hard to re-find local kitchens", "Identity nearby discovery"],
        ],
        [12, 88, 70],
        size=7,
    )

    pdf.chapter("Module Catalog — Definitions & Challenges")
    pdf.body(
        "Each module is a bounded product context. Definition = what it is. "
        "Description = what it does. Challenge = kitchen/customer pain it removes."
    )

    modules = [
        ("M01 API Gateway", "Public edge for /api/v1.",
         "Path proxy, CORS, correlation IDs; no business logic.",
         "Clients never hit internals; unified auth surface."),
        ("M02 Identity & Kitchen", "Auth + tenant roots.",
         "Owner OTP/JWT; customer OAuth/OTP; PostGIS kitchens; codes CKPNQ001.",
         "Onboarding bootstrap; nearby discovery; multi-kitchen ownership."),
        ("M03 Catalog & Live Media", "Menu of truth.",
         "Categories, dishes, prices; hero must be live-capture; menu cache.",
         "Ends stock-photo deception; consistent menus across PWAs."),
        ("M04 Ingredients & Recipes", "Pantry + dish standards (F19).",
         "Stock, thresholds, recipe lines, prep steps; deduct on accept.",
         "Stops mid-service stock outs; foundation for taste standards."),
        ("M05 Order Operations", "Intake, lifecycle, bills, analytics.",
         "Manual/WA/PWA; status machine; PDF bills; revenue/peak/segments.",
         "Single operational truth for chaotic multi-channel demand."),
        ("M06 Multi-Kitchen Checkout", "One cart, many kitchens (F06).",
         "Master order + atomic sub-orders + master receipt PDF.",
         "Removes aggregator-style one-kitchen cart limit without commission."),
        ("M07 Billing & Settlements", "Money movement.",
         "Payments, UPI, subscriptions; Route splits (F44).",
         "Subscription replaces commission; fair multi-kitchen payouts."),
        ("M08 GST Finance", "Tax profile, invoices, monthly audit.",
         "GSTIN profiles; sync from delivered orders; balance sheet close.",
         "Accountant-ready monthly GST for home/cloud kitchens."),
        ("M09 Notification & Support", "WhatsApp + tickets + tracking nudges.",
         "Webhook intake; F45 updates; F29 reminders; AI support tickets.",
         "Closes communication gaps owners cannot staff manually."),
        ("M10 Marketing & CRM", "Owner-owned relationships.",
         "Customer spend history, coupons, targeted promotions.",
         "Recaptures customers aggregators monopolized."),
        ("M11 Ratings & Tips", "Verified home-taste + F20 tips.",
         "0.6 taste + 0.4 quality; A/V reviews; owner tip workflow.",
         "Quality benchmark customers believe; fuel for chef briefs."),
        ("M12 Growth Intelligence", "Actionable suggestions, not vanity charts.",
         "Combos, patterns, grow cards, daily menu WhatsApp push.",
         "Ends promotion guesswork with evidence-backed actions."),
        ("M13 Delivery & Tracking", "Distance fees + shareable track.",
         "PostGIS quotes; free/max radius; tracking tokens/links.",
         "Transparent fees and journey visibility."),
        ("M14 Learning & Trials", "Skills + controlled experiments.",
         "Curated learning; dish trials with promote-to-menu path.",
         "Helps home chefs professionalize without outside help."),
        ("M15 Community & Rankings", "Recipes + chef leagues.",
         "Recipe rewards; rankings from quality/activity signals.",
         "Differentiation and motivation vs pure marketplaces."),
        ("M16 Live Streaming", "Owner opt-in LiveKit sessions.",
         "Go-live controls; customer live kitchen filter.",
         "Trust and engagement without paid advertising."),
        ("M17 Website PWAs", "Installable surfaces for all personas.",
         "React+Vite; Workbox; owner command-center UX; maps; RTE.",
         "App-store-free distribution; WhatsApp-native deep links."),
        ("M18 Quality Loop E1+E2", "Purchases + lock winning standards.",
         "Purchase ledger stock-in; chef brief from volume/ratings; lock.",
         "Closes taste drift + pantry truth as one product loop."),
    ]
    for title, definition, description, challenge in modules:
        pdf.section(title)
        pdf.bullets([
            f"Definition: {definition}",
            f"Description: {description}",
            f"Challenges solved: {challenge}",
        ], size=8)

    pdf.chapter("Product Journeys & Capability Ladder")
    pdf.section("Owner day-1")
    pdf.mono(
        "Register -> OTP -> JWT -> Create kitchen (geo + code)\n"
        "-> Add dish (live hero) -> Optional GST profile\n"
        "-> First manual / WhatsApp order -> Accept -> Deduct stock\n"
        "-> Same-day revenue report"
    )
    pdf.section("Customer trust -> rate")
    pdf.mono(
        "Nearby map -> Menu (live photos) -> Fee quote -> Checkout\n"
        "-> Pay (single or multi-kitchen) -> Track -> Delivered\n"
        "-> Home-taste rating (+ optional tip)"
    )
    pdf.section("Capability ladder (progressive complexity)")
    pdf.bullets([
        "1. Menu + Orders + Reports",
        "2. CRM + Coupons + Delivery quotes",
        "3. Ingredients + GST + Growth suggestions",
        "4. Learning + Community + Live stream",
        "5. Quality loop lock (E1 purchases + E2 chef standards)",
    ])

    pdf.chapter("Product KPIs")
    pdf.table(
        ["KPI", "Near-term", "12-month"],
        [
            ["Active kitchens", "10 pilots", "500"],
            ["Platform orders/day", "50", "5,000"],
            ["Owner monthly retention", "80%", "90%"],
            ["30-day customer repeat", "25%", "40%"],
            ["Locked standards / kitchen", "-", ">= 3 post-E2"],
            ["GST audits closed on time", "-", ">= 80% GST kitchens"],
        ],
        [70, 45, 55],
        size=7,
    )

    # ── PART III: CTO ────────────────────────────────────────────────────
    pdf.lens_part("CTO", 3, "Architecture, Flows & Data")

    pdf.chapter("System Architecture Diagram")
    pdf.body(
        "Rule: one bounded context per container; cross-service writes via events; "
        "cross-schema reads only for ownership/evidence; gateway is sole public edge."
    )
    pdf.mono(
        "             PWAs / Portal\n"
        "   portal · customer · kitchen · admin\n"
        "                    |\n"
        "                    v  HTTPS /api/v1\n"
        "             +----------------------+\n"
        "             |     API GATEWAY      |\n"
        "             | route CORS corr-ID   |\n"
        "             +--+---+---+---+--+----+\n"
        "                |   |   |   |  |\n"
        "     +----------+   |   |   |  +-----------+\n"
        "     v              v   v   v              v\n"
        " IDENTITY      CATALOG ORDER BILLING   STREAMING\n"
        " kitchens         |     |      |            +\n"
        " customers        v     v      v            |\n"
        "              MARKET RATING DELIV LEARN COMMUNITY GROWTH\n"
        "                    |      |      |      |      |\n"
        "                    +------+------+------+------+\n"
        "                    |             |             |\n"
        "                    v             v             v\n"
        "           PostgreSQL+PostGIS   Redis 7      MinIO\n"
        "           schema-per-domain   Streams+cache  media\n"
        "           + ckac_events.outbox",
        size=6,
        max_lines=40,
        line_h=3.2,
    )

    pdf.chapter("Event & Data Flow Diagrams")
    pdf.section("Order + stock + notify")
    pdf.mono(
        "Owner/Customer place|accept\n"
        "        |\n"
        "        v\n"
        "   ORDER SERVICE\n"
        "   - persist order + status_events\n"
        "   - publish order.placed / order.status.changed\n"
        "   - on accept --internal HTTP--> CATALOG deduct\n"
        "                                   publish stock.deducted\n"
        "        |\n"
        "        v Redis ckac:orders:order\n"
        "        +--> NOTIFICATION (WhatsApp F45, tracking nudge)",
        size=6.5,
    )
    pdf.section("Multi-kitchen payment (F06/F44)")
    pdf.mono(
        "Cart [K1, K2] -> ORDER master_order + sub-orders\n"
        "             -> BILLING master payment capture\n"
        "             -> settlements[] net_to_owner per kitchen\n"
        "             -> events payment.captured / settlement.*\n"
        "             -> master bill PDF for customer",
        size=6.5,
    )
    pdf.section("GST monthly loop")
    pdf.mono(
        "GSTIN profile -> kitchen_gst_profiles\n"
        "Delivered orders --sync--> gst_tax_invoices\n"
        "Monthly report + balance sheet\n"
        "Close audit -> gst_monthly_audits snapshot",
        size=7,
    )
    pdf.section("Quality loop E1/E2 (planned)")
    pdf.mono(
        "Purchase post -> stock_movements(+) -> pantry\n"
        "Accept order  -> stock_movements(-) via recipe\n"
        "Ratings+volume+F20 tips -> GROWTH chef_brief\n"
        "Owner Lock -> recipe_standard_versions + dish_ingredients",
        size=7,
    )
    pdf.section("Representative Redis streams")
    pdf.table(
        ["Stream", "Example events"],
        [
            ["ckac:orders:order", "placed, status.changed"],
            ["ckac:catalog:*", "dish/ingredient stock.*"],
            ["ckac:billing:gst", "profile, invoice, audit"],
            ["ckac:ratings:*", "created, aggregate.updated"],
            ["ckac:growth:suggestion", "generated (+ chef_standard)"],
            ["ckac:notify:*", "whatsapp, tracking"],
        ],
        [55, 115],
        size=7,
    )
    pdf.body("Every write publish uses transactional outbox (ckac_events.outbox).")

    pdf.chapter("Logical ER / Schema Diagram")
    pdf.body(
        "Schemas are separate Postgres schemas (no cross-schema FKs). "
        "Lines below are logical relationships only. Tenant tables carry kitchen_id."
    )
    pdf.mono(
        "ckac_identity              ckac_catalog                 ckac_orders\n"
        "------------              ------------                 -----------\n"
        "owners 1--* kitchens      categories 1--* dishes       master_orders\n"
        "customers                 dishes 1--* dish_media         1--* orders\n"
        "                          dishes *--* ingredients       orders 1--*\n"
        "                          dish_prep_steps               order_items\n"
        "                                                       status_events\n"
        "\n"
        "ckac_billing              ckac_ratings                 ckac_marketing\n"
        "------------              ------------                 --------------\n"
        "subscriptions             dish_ratings                 kitchen_customers\n"
        "payments 1--* settlements dish_rating_aggregates       coupons\n"
        "gst_profiles/invoices     dish_suggestions             promotions\n"
        "gst_monthly_audits\n"
        "\n"
        "ckac_growth  delivery  learning  community  streaming  |  ckac_events\n"
        "suggestions  quotes*   trials    rewards    sessions   |  outbox\n"
        "seasonal_*   track*    lessons   rankings              |  processed",
        size=6,
        max_lines=42,
        line_h=3.2,
    )

    pdf.chapter("Services, APIs, Security & Standards")
    pdf.table(
        ["Service", "Port", "Highlights"],
        [
            ["gateway", "18000", "/api/v1/* edge"],
            ["identity", "18001", "auth, kitchens, customers"],
            ["catalog", "18002", "menu, dishes, ingredients"],
            ["order", "18003", "orders, analytics, PDF"],
            ["billing", "18004", "payments, GST"],
            ["notification", "18005", "webhooks, support"],
            ["marketing", "18006", "CRM, coupons, promos"],
            ["ratings", "18007", "ratings, suggestions"],
            ["growth", "18008", "suggestions, daily menu"],
            ["delivery", "18009", "fees, tracking"],
            ["learning", "18010", "portal, trials"],
            ["community", "18011", "recipes, rankings"],
            ["streaming", "18012", "LiveKit sessions"],
        ],
        [35, 22, 113],
        size=6,
    )
    pdf.bullets([
        "Security: JWT Bearer, tenant filters, Pydantic, env secrets, mask PII, X-Internal-Key",
        "Health: /health/live + /health/ready on every service",
        "Method: TDD + EDD; MODULE-DESIGN-PACK before new features; Alembic only",
        "Forbidden: per-order commission, restaurant POS/dine-in/KDS, cross-schema writes",
    ])

    pdf.chapter("Build Status Matrix")
    pdf.table(
        ["Module band", "Sprint", "Status"],
        [
            ["Gateway / Identity / Catalog / Order / Notify", "S1-S4", "DONE"],
            ["PWAs + checkout + analytics", "S5", "DONE"],
            ["Billing + GST", "S6+GST", "DONE"],
            ["Discovery / history", "S7", "DONE"],
            ["Multi-kitchen cart", "S8", "DONE"],
            ["Split payment Route", "S9", "DONE"],
            ["CRM / coupons / promos", "S10", "DONE"],
            ["Ratings", "S11", "DONE"],
            ["Growth", "S12", "DONE"],
            ["Delivery", "S13", "DONE"],
            ["Tracking notify", "S14", "DONE"],
            ["Ingredients", "S15", "DONE"],
            ["Learning / Community / Streaming", "S16-S18", "DONE"],
            ["E1 Purchases + E2 Chef lock", "S19", "DESIGN"],
        ],
        [95, 25, 50],
        size=6,
    )

    # ── Appendices ───────────────────────────────────────────────────────
    pdf.lens_part("APPENDIX", 4, "Reference")

    pdf.chapter("Feature bands F01-F48")
    pdf.table(
        ["Band", "Features", "Status"],
        [
            ["Orders & lifecycle", "F01-F05, F30, F45", "Done / WA AI partial"],
            ["Multi-kitchen & pay", "F06, F42-F44", "Done"],
            ["Analytics & growth", "F07-F12, F39", "Done"],
            ["Catalog & media", "F13-F15", "Done"],
            ["Ratings", "F16-F18, F20", "Done (F20 UI thin)"],
            ["Ingredients", "F19", "Done (E1 extends)"],
            ["Delivery / discover", "F27-F33", "Done"],
            ["Marketing", "F34-F41", "Core done"],
            ["Learning / community", "F21-F24", "Done"],
            ["Live", "F46-F48", "Done"],
            ["GST finance", "Billing extension", "Done"],
            ["Quality loop", "E1/E2", "Design pack"],
        ],
        [50, 60, 60],
        size=6,
    )
    pdf.body("Full acceptance criteria: docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md")

    pdf.chapter("Document index")
    pdf.table(
        ["Document", "Role"],
        [
            ["CKAC-COMPLETE-GUIDE.md/.pdf", "This master CEO/CPO/CTO guide"],
            ["E1-E2-*-DESIGN.md", "Next sprint quality-loop design"],
            ["CKAC-IMPLEMENTATION-GUIDE.md", "Built features mapped to code"],
            ["KITCHCU-ENGINEERING-STANDARDS.md", "Engineering constitution"],
            ["MODULE-DESIGN-PACK.md", "Mandatory pre-code template"],
            ["AGENTS.md", "Agent/engineer quick spec"],
            ["Feature packs F*.md", "Per-sprint design packs"],
        ],
        [70, 100],
        size=7,
    )
    pdf.quote("Kitchcu Complete Executive Guide v2.0 — Confidential — July 2026")

    return pdf


def main():
    pdf = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
