#!/usr/bin/env python3
"""Generate Kitchcu Complete Executive Guide PDF — CEO + CPO + CTO."""

from pathlib import Path

from pdf_common import DARK, GRAY, ORANGE
from pdf_guide import GuidePDF

GUIDE_VERSION = "1.1"
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
            "CEO — vision, market, business model, GTM, metrics, risks",
            "CPO — personas, pains, 48 features, modules, flows, KPIs",
            "CTO — architecture, services, DB, events, APIs, build status",
        ],
        bullets=[
            "Full strategic positioning vs food aggregators and POS systems",
            "48-feature catalog with implementation status (Sprints S1-S4 backend complete)",
            "Owner and customer pain points mapped to modules and live code",
            "Event-driven microservices, outbox pattern, and API reference",
            "Subscription tiers, unit economics, and development phases",
            "90+ automated tests; PWAs on customer.kitchcu.in / kitchen.kitchcu.in / admin.kitchcu.in",
            "Marketing portal with parallax UI, AI support chat, and admin ticketing",
        ],
    )

    pdf.toc([
        ("PART I — CEO Lens", [
            "1. Executive Summary",
            "2. Market & Strategic Positioning",
            "3. Business Model & Unit Economics",
            "4. Go-to-Market & Development Phases",
            "5. North-Star Metrics & Investment Thesis",
            "6. Risks & Mitigations",
        ]),
        ("PART II — CPO Lens", [
            "7. Product Vision & Personas",
            "8. Pain Points to Solutions",
            "9. Platform Modules & Feature Catalog",
            "10. Application Flows",
            "11. Product Principles & KPIs",
        ]),
        ("PART III — CTO Lens", [
            "12. Architecture Overview",
            "13. Services, Events & Data Flow",
            "14. Database & Caching",
            "15. API Reference & Security",
            "16. Build Status & Engineering Standards",
        ]),
        ("Appendices", [
            "A. Feature Implementation Matrix",
            "B. Document Index",
        ]),
    ])

    # ── PART I: CEO ──────────────────────────────────────────────────────
    pdf.lens_part("CEO", 1, "Executive Strategy")

    pdf.chapter("Executive Summary")
    pdf.body(
        "Kitchcu is a B2B2C cloud kitchen operating system — not a food aggregator. "
        "It gives kitchen owners full control over orders, quality, marketing, and "
        "customer relationships while giving diners real-time transparency into their food."
    )
    pdf.table(
        ["Stakeholder", "Pain Today", "Kitchcu Answer"],
        [
            ["Owner", "WhatsApp chaos, commissions", "Unified hub, zero commission"],
            ["Customer", "Stock photos, opaque delivery", "Live-capture, fair fees"],
            ["Market", "No quality benchmark", "Chef rankings (Phase 3)"],
        ],
        [28, 58, 84],
        size=7,
    )
    pdf.quote(
        "Keep the product simple for the owner on day one. "
        "First WhatsApp order in under 5 minutes of onboarding."
    )

    pdf.chapter("Market & Strategic Positioning")
    pdf.mono(
        "Aggregators          vs    Kitchcu\n"
        "Per-order commission       Monthly subscription\n"
        "Platform owns customer     Owner owns CRM\n"
        "Stock photos               Live-capture media\n"
        "Speed-first delivery       Quality-first SLA\n"
        "Single kitchen per cart    Multi-kitchen cart"
    )
    pdf.body(
        "Competitive moat: WhatsApp-native ops + live-capture integrity + "
        "owner-owned CRM + quality-first lifecycle."
    )

    pdf.chapter("Business Model & Unit Economics")
    pdf.table(
        ["Tier", "Monthly", "Includes"],
        [
            ["Starter", "Rs 499", "1 kitchen, WhatsApp, basic reports"],
            ["Pro", "Rs 1,499", "CRM, coupons, tiffin, marketing"],
            ["Enterprise", "Rs 3,999", "Live stream, API, branches"],
        ],
        [35, 30, 105],
        size=8,
    )
    pdf.body("Zero per-order food commission. Kitchen keeps 100% of food revenue.")
    pdf.table(
        ["Metric", "Year 1 Goal"],
        [
            ["CAC (owner)", "< Rs 2,000"],
            ["Owner LTV", "> Rs 18,000"],
            ["LTV:CAC", "> 3:1"],
            ["Gross margin", "> 75%"],
        ],
        [85, 85],
        size=8,
    )

    pdf.chapter("Go-to-Market & Development Phases")
    pdf.table(
        ["Phase", "Timeline", "Goal"],
        [
            ["1 Foundation", "Mo 1-3", "10 pilot kitchens, daily orders"],
            ["2 Growth", "Mo 4-6", "Customer PWA, CRM, multi-kitchen"],
            ["3 Differentiation", "Mo 7-10", "Rankings, live stream"],
            ["4 Scale", "Mo 11-12+", "National platform, white-label"],
        ],
        [40, 25, 105],
        size=7,
    )
    pdf.section("Phase 1 Milestones (Current)")
    pdf.table(
        ["Milestone", "Deliverable", "Status"],
        [
            ["M1.1", "Identity, gateway, Docker", "COMPLETE"],
            ["M1.2", "Catalog + live photo", "COMPLETE"],
            ["M1.3", "Order + WhatsApp intake", "COMPLETE"],
            ["M1.4", "Lifecycle + notifications", "PARTIAL"],
            ["M1.5", "Owner/customer/admin PWAs + portal", "S5 PARTIAL"],
            ["M1.6", "Razorpay billing", "S6"],
        ],
        [22, 88, 60],
        size=7,
    )

    pdf.chapter("North-Star Metrics & Investment Thesis")
    pdf.bullets([
        "Owner GMV managed on platform (primary north star)",
        "Repeat order rate (customer loyalty proxy)",
        "Dish rating consistency (quality standardization)",
        "Owner NPS (aggregator dependency reduction)",
    ])
    pdf.table(
        ["KPI", "MVP", "12-Month"],
        [
            ["Active kitchens", "10", "500"],
            ["Orders/day", "50", "5,000"],
            ["Owner retention", "80%", "90%"],
            ["Repeat rate (30d)", "25%", "40%"],
        ],
        [55, 55, 60],
        size=8,
    )
    pdf.body(
        "Investment thesis: Kitchcu captures the operating system layer for India's "
        "cloud kitchens — subscription SaaS with zero food commission. Phase 1 "
        "proves order throughput; Phase 2 unlocks customer network effects; "
        "Phase 3 builds community moats. Capital-efficient PWA-first approach."
    )

    pdf.chapter("Risks & Mitigations")
    pdf.table(
        ["Risk", "Mitigation"],
        [
            ["WhatsApp API changes", "Manual input always available"],
            ["Live stream complexity", "Managed provider; opt-in only"],
            ["Multi-kitchen disputes", "Per-kitchen sub-order IDs"],
            ["Scope creep", "Strict MoSCoW; Phase 1 sacred"],
            ["Onboarding friction", "WhatsApp-first; 5-min setup"],
        ],
        [55, 115],
        size=7,
    )

    # ── PART II: CPO ─────────────────────────────────────────────────────
    pdf.lens_part("CPO", 2, "Product Depth")

    pdf.chapter("Product Vision & Personas")
    pdf.body(
        "Empower every cloud kitchen to scale like a brand — with data, quality "
        "standards, and direct customer relationships — while giving diners honest "
        "visibility into their food."
    )
    pdf.table(
        ["Persona", "Goals", "Surface"],
        [
            ["Owner/Chef", "Orders, quality, marketing", "kitchen.kitchcu.in PWA"],
            ["Customer", "Discover, order, rate", "Customer PWA (Ph 2)"],
            ["Staff", "Lifecycle, inventory", "Staff PWA subset"],
            ["Admin", "Moderate, support tickets", "admin.kitchcu.in"],
        ],
        [30, 70, 70],
        size=7,
    )
    pdf.section("PWA-First Strategy")
    pdf.bullets([
        "One codebase: Android, iOS, desktop",
        "WhatsApp links open directly — critical for order capture",
        "Offline: menu, orders, draft queue via service workers",
        "Live dish photo via getUserMedia in browser",
        "Target: Lighthouse PWA score >= 90",
    ])

    pdf.chapter("Pain Points to Solutions")
    pdf.section("Owner Pains (P1-P8)")
    pdf.table(
        ["#", "Pain", "Module", "Status"],
        [
            ["P1", "WhatsApp chaos", "Order+Notify", "Partial"],
            ["P2", "Aggregator commission", "Billing", "S6"],
            ["P3", "No profit visibility", "Analytics", "Partial"],
            ["P4", "Stock photo deception", "Catalog", "Done"],
            ["P5", "Taste inconsistency", "Catalog", "Partial"],
            ["P6", "No owner CRM", "Marketing", "Ph 2"],
            ["P7", "Promotion guesswork", "Growth", "Ph 2"],
            ["P8", "Multi-channel chaos", "Order", "Partial"],
        ],
        [12, 58, 45, 55],
        size=7,
    )
    pdf.section("Customer Pains (C1-C6)")
    pdf.table(
        ["#", "Pain", "Solution", "Status"],
        [
            ["C1", "Untrustworthy photos", "Live-capture media", "Done"],
            ["C2", "Opaque delivery fees", "PostGIS + rules", "Fields only"],
            ["C3", "No tracking", "Lifecycle + notify", "Partial"],
            ["C4", "Generic ratings", "Home-taste score", "Ph 2"],
            ["C5", "Single-kitchen cart", "Multi-kitchen cart", "Ph 2"],
            ["C6", "No tiffin", "Meal plans", "Ph 2"],
        ],
        [12, 48, 55, 55],
        size=7,
    )

    pdf.chapter("Platform Modules & Feature Catalog")
    pdf.table(
        ["Module", "Schema", "Sprint", "Status"],
        [
            ["Gateway", "-", "S1", "Live"],
            ["Identity", "ckac_identity", "S1", "Live"],
            ["Catalog", "ckac_catalog", "S2", "Live"],
            ["Order", "ckac_orders", "S3", "Live"],
            ["Notification", "ckac_support", "S4", "Live"],
            ["Billing", "ckac_billing", "S6", "Planned"],
            ["Analytics", "order svc", "S5", "Partial"],
            ["Marketing", "ckac_marketing", "Ph 2", "Planned"],
        ],
        [35, 50, 25, 60],
        size=7,
    )
    pdf.section("48 Features by Phase")
    pdf.bullets([
        "Phase 1 (Must): F01-F05, F07, F13-F15, F26, F30, F42-F43, F45",
        "Phase 2 (Growth): F06, F08-F12, F16-F18, F25, F27-F33, F34-F41, F44",
        "Phase 3 (Differentiation): F19-F24, F46-F48",
        "Done: 8 features | Partial: 4 | Total spec: 48",
    ])

    pdf.chapter("Application Flows")
    pdf.section("Owner Day-1 Onboarding")
    pdf.mono(
        "Register -> OTP -> JWT -> Create kitchen (CKPNQ001)\n"
        "-> Add dishes (live photo required)\n"
        "-> Connect WhatsApp -> First order in inbox"
    )
    pdf.section("Order Lifecycle (F04)")
    pdf.mono(
        "received -> accepted -> preparing -> ready\n"
        "-> out_for_delivery -> delivered\n"
        "(cancelled with reason at any stage)"
    )
    pdf.section("WhatsApp Order (F01)")
    pdf.mono(
        "Meta webhook -> notification (lookup kitchen)\n"
        "-> whatsapp.message.received event\n"
        "-> order internal API -> parse -> draft\n"
        "-> owner confirms -> order.placed"
    )
    pdf.section("Multi-Kitchen Checkout (F06, Phase 2)")
    pdf.mono(
        "Cart: Kitchen A + Kitchen B items\n"
        "-> master_orders (1 payment)\n"
        "-> order A + order B (separate lifecycle)\n"
        "-> Razorpay Route split settlement"
    )

    pdf.chapter("Product Principles & KPIs")
    pdf.bullets([
        "WhatsApp-native order intake",
        "Quality over speed — owner-set prep windows",
        "Trust through media — live capture required",
        "Owner-owned CRM — customer data belongs to kitchen",
        "Progressive complexity — MVP first, growth layers later",
    ])
    pdf.table(
        ["Metric", "Phase 1 Target"],
        [
            ["Time to first order", "< 5 min"],
            ["Owner daily active", "80% paying kitchens"],
            ["Order capture rate", "95% parsed or manual"],
            ["Menu trust score", "100% live-capture heroes"],
            ["Owner retention M6", "80%"],
        ],
        [85, 85],
        size=8,
    )

    # ── PART III: CTO ────────────────────────────────────────────────────
    pdf.lens_part("CTO", 3, "Technical Architecture")

    pdf.chapter("Architecture Overview")
    pdf.mono(
        "Experience: kitchcu.in portal | customer.kitchcu.in | kitchen.kitchcu.in | admin.kitchcu.in\n"
        "    |\n"
        "Edge: API Gateway :18000 (JWT, routing)\n"
        "    |\n"
        "Application: identity | catalog | order | notification\n"
        "    |\n"
        "Data: PostgreSQL 16 + PostGIS | Redis Streams + cache\n"
        "    |\n"
        "Media: MinIO / S3 (live-capture URLs)"
    )
    pdf.body(
        "Event-driven microservices on Python 3.12 + FastAPI. "
        "Schema-per-bounded-context. Transactional outbox on all writes."
    )
    pdf.table(
        ["Layer", "Technology"],
        [
            ["API", "Python 3.12, FastAPI, Pydantic v2"],
            ["Database", "PostgreSQL 16 + PostGIS"],
            ["Events/Cache", "Redis 7 Streams + menu cache 300s"],
            ["Frontend", "React + Vite + TypeScript PWA"],
            ["Payments", "Razorpay (S6)"],
            ["WhatsApp", "Meta Business Cloud API"],
            ["Infra", "Docker Compose -> Kubernetes"],
        ],
        [45, 125],
        size=8,
    )

    pdf.chapter("Services, Events & Data Flow")
    pdf.table(
        ["Service", "Port", "Key Events"],
        [
            ["gateway", "18000", "-"],
            ["identity", "18001", "kitchen.created"],
            ["catalog", "18002", "dish.created/updated"],
            ["order", "18003", "order.placed, status.changed"],
            ["notification", "18005", "whatsapp.message.received, support.ticket.*"],
        ],
        [35, 25, 110],
        size=7,
    )
    pdf.section("Event Catalog")
    pdf.table(
        ["Event", "Producer", "Stream"],
        [
            ["kitchen.created", "identity", "ckac:identity:kitchen"],
            ["dish.created/updated", "catalog", "ckac:catalog:dish"],
            ["order.placed", "order", "ckac:orders:order"],
            ["order.status.changed", "order", "ckac:orders:order"],
            ["order.draft.created", "order", "ckac:orders:draft"],
            ["whatsapp.message.received", "notification", "ckac:notify:whatsapp"],
        ],
        [55, 40, 75],
        size=7,
    )
    pdf.section("Outbox Pattern (Critical)")
    pdf.bullets([
        "Domain write + outbox in same DB transaction",
        "flush_pending() after commit — no Redis-before-commit bug",
        "Relay worker for retry / Kafka migration — Phase 4",
        "pg_advisory_xact_lock for kitchen codes and bill IDs",
    ])

    pdf.chapter("Database & Caching")
    pdf.table(
        ["Schema", "Tables", "Status"],
        [
            ["ckac_identity", "owners, kitchens", "LIVE"],
            ["ckac_catalog", "categories, dishes, dish_media", "LIVE"],
            ["ckac_orders", "orders, items, events, drafts", "LIVE"],
            ["ckac_events", "outbox, processed_events", "LIVE"],
            ["ckac_support", "support_tickets, messages", "LIVE"],
            ["ckac_billing", "payments, subscriptions", "S6"],
            ["ckac_marketing", "customers, coupons", "Ph 2"],
        ],
        [45, 85, 40],
        size=7,
    )
    pdf.section("Naming Conventions")
    pdf.mono(
        "Kitchen code: CKPNQ001\n"
        "Bill ID: BILL-20260712-0001\n"
        "Order code: CKPNQ001-BILL-20260712-0001"
    )
    pdf.section("Cache Keys")
    pdf.table(
        ["Key", "TTL", "Invalidation"],
        [
            ["menu:{kitchen_id}", "5 min", "dish.updated"],
            ["dish:{dish_id}", "10 min", "rating update"],
            ["kitchen:{id}:profile", "15 min", "settings change"],
        ],
        [55, 25, 90],
        size=7,
    )
    pdf.section("SLO Targets")
    pdf.table(
        ["Metric", "Target"],
        [
            ["API p95 read", "< 200 ms"],
            ["API p95 write", "< 500 ms"],
            ["Order E2E", "< 3 s"],
            ["WhatsApp notify", "< 10 s from event"],
            ["Uptime", "99.9% (Ph 2+)"],
        ],
        [85, 85],
        size=8,
    )

    pdf.chapter("API Reference & Security")
    pdf.section("Gateway Routes (:18000/api/v1)")
    pdf.mono(
        "Identity: /auth/* /owners/* /kitchens\n"
        "Catalog: /kitchens/{id}/categories|menu|dishes\n"
        "Order: /kitchens/{id}/orders/* /orders/{id}/status /analytics/*\n"
        "Notification: /webhooks/whatsapp /support/chat /support/tickets\n"
        "Admin: /admin/tickets/* (notification service)\n"
        "Internal: /internal/... (X-Internal-Key)"
    )
    pdf.section("Security")
    pdf.table(
        ["Area", "Implementation"],
        [
            ["Auth", "JWT + OTP; Bearer on owner routes"],
            ["Tenant isolation", "kitchen_id + RLS (prod)"],
            ["Media", "Live-capture validator; signed URLs"],
            ["Internal", "X-Internal-Key header"],
            ["WhatsApp", "Verify token required outside dev"],
            ["Health", "/health/live + /health/ready"],
        ],
        [45, 125],
        size=7,
    )

    pdf.chapter("Build Status & Engineering Standards")
    pdf.stat_boxes([
        ("90+", "Tests passing"),
        ("S1-S5", "Backend + PWAs partial"),
        ("5+1", "Services + gateway"),
        ("48", "Features spec"),
    ])
    pdf.table(
        ["Sprint", "Deliverable", "Status"],
        [
            ["S1", "Identity, gateway, JWT", "COMPLETE"],
            ["S2", "Catalog, live-capture, EDD", "COMPLETE"],
            ["S3", "Order, lifecycle, history", "COMPLETE"],
            ["S4", "WhatsApp webhook + parser", "COMPLETE"],
            ["S5", "PWAs + analytics + support/tickets", "PARTIAL"],
            ["S6", "Billing + revenue", "Planned"],
        ],
        [22, 98, 50],
        size=7,
    )
    pdf.section("Engineering Standards")
    pdf.bullets([
        "TDD: RED -> GREEN -> REFACTOR for every feature",
        "EDD: DB commit first; session-bound EventPublisher",
        "Service template: main, routes, schemas, models",
        "No cross-schema writes; Alembic per service",
        "Run tests: scripts/run-tests.ps1",
    ])

    # ── APPENDIX ─────────────────────────────────────────────────────────
    pdf.lens_part("APPENDIX", 4, "Reference Tables")

    pdf.chapter("Feature Implementation Matrix (Phase 1)")
    pdf.table(
        ["ID", "Feature", "Status"],
        [
            ["F01", "WhatsApp capture", "Partial"],
            ["F02", "Message parser", "Done"],
            ["F03", "Manual order", "Done"],
            ["F04", "Lifecycle", "Done"],
            ["F05", "Order history", "Done"],
            ["F07", "Revenue report", "Partial"],
            ["F13", "Dish + live photo", "Done"],
            ["F14", "Price/quality fields", "Done"],
            ["F15", "Categories", "Done"],
            ["F26", "Subscription", "Partial"],
            ["F30", "Prep time", "Done"],
            ["F42-F43", "Payments", "S6"],
            ["F45", "Notify + AI chat + tickets", "Partial"],
        ],
        [18, 102, 50],
        size=7,
    )

    pdf.chapter("Document Index")
    pdf.table(
        ["Document", "Audience"],
        [
            ["CKAC-COMPLETE-GUIDE.md", "CEO, CPO, CTO (this guide)"],
            ["CKAC-IMPLEMENTATION-GUIDE.md", "Engineering (live code map)"],
            ["CKAC-ARCHITECTURE-CTO.md", "CTO, EM (layers + traceability)"],
            ["CKAC-SYSTEM-BENCHMARK.md", "CTO, DBA (deep spec)"],
            ["CKAC-CPO-PRODUCT-BLUEPRINT.md", "CPO, Product"],
            ["CKAC-PITCH-DECK.pdf", "CEO, Investors (33 slides)"],
            ["AGENTS.md", "Developers, AI agents"],
        ],
        [85, 85],
        size=7,
    )

    # Back cover
    pdf.add_page()
    pdf.set_xy(20, 50)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 10, "Kitchcu")
    pdf.ln(14)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(
        170,
        6,
        "Kitchcu cloud kitchen platform",
    )
    pdf.ln(8)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        170,
        5,
        f"Complete Executive Guide v{GUIDE_VERSION} | {GUIDE_DATE} | Confidential\n"
        "Regenerate: python scripts/generate_complete_guide_pdf.py",
    )

    return pdf


def main():
    pdf = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Generated: {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
