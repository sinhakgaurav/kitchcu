#!/usr/bin/env python3
"""Generate Kitchcu Product Depth Complete Guide PDF — full product reference."""

from pathlib import Path

from fpdf import FPDF

from pdf_common import ACCENT, DARK, GRAY, LIGHT_BG, ORANGE, WHITE, ascii_safe

GUIDE_VERSION = "1.1"
GUIDE_DATE = "July 2026"


class ProductDepthPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, ascii_safe(f"Kitchcu Product Depth Complete Guide v{GUIDE_VERSION} | {GUIDE_DATE}"), align="C")

    def cover(self):
        self.add_page()
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 0, 210, 297, "F")
        self.set_xy(20, 55)
        self.set_font("Helvetica", "B", 42)
        self.set_text_color(*ORANGE)
        self.cell(0, 16, "Kitchcu")
        self.ln(18)
        self.set_x(20)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*DARK)
        self.multi_cell(170, 9, "Product Depth Complete Guide")
        self.ln(6)
        self.set_x(20)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(*GRAY)
        self.multi_cell(
            170,
            7,
            "Modules  |  Features  |  Flows  |  Architecture  |  APIs  |  "
            "Build Status  |  Roadmap  |  KPIs",
        )
        self.ln(8)
        self.set_x(20)
        self.set_font("Helvetica", "", 11)
        self.cell(0, 7, "Kitchcu cloud kitchen platform")
        self.ln(20)
        self.set_x(20)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.cell(0, 6, "Audience: CPO, Product, Engineering, Investors, Partners")
        self.ln(8)
        self.set_x(20)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        for b in [
            "48-feature catalog with implementation status (Sprints 1-4)",
            "Owner and customer pain points mapped to modules and code",
            "End-to-end application and event-driven data flows",
            "Full API reference, database schemas, and service topology",
            "Business model, KPIs, competitive position, and roadmap",
        ]:
            self.set_x(22)
            self.multi_cell(168, 6, f"- {ascii_safe(b)}")
        self.set_xy(20, 255)
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(*GRAY)
        self.cell(0, 6, f"Version {GUIDE_VERSION}  |  {GUIDE_DATE}  |  Confidential")

    def toc(self):
        self.add_page()
        self.set_xy(20, 25)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*ORANGE)
        self.cell(0, 10, "Table of Contents")
        self.ln(12)
        parts = [
            "Part I - Product Foundation (Executive Summary, Personas, Principles)",
            "Part II - Market Problems & Solutions (Owner + Customer Pains)",
            "Part III - Platform Modules Deep Dive (Identity, Catalog, Order, Notification)",
            "Part IV - 48-Feature Catalog (Phase 1, 2, 3)",
            "Part V - Application & Data Flows (WhatsApp, Lifecycle, EDD)",
            "Part VI - Technical Reference (Database, APIs, Stack)",
            "Part VII - Business, Delivery & Metrics (Model, Roadmap, KPIs)",
        ]
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*DARK)
        for i, p in enumerate(parts, 1):
            self.set_x(20)
            self.multi_cell(170, 7, ascii_safe(f"{i}. {p}"))
            self.ln(2)

    def part_title(self, part_num: int, title: str):
        self.add_page()
        self.set_fill_color(*ORANGE)
        self.rect(0, 0, 210, 40, "F")
        self.set_xy(20, 14)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 8, f"PART {part_num}")
        self.ln(10)
        self.set_x(20)
        self.set_font("Helvetica", "B", 22)
        self.cell(0, 12, ascii_safe(title))

    def chapter(self, num: int, title: str):
        if self.get_y() > 240:
            self.add_page()
        else:
            self.ln(6)
        self.set_x(20)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*ORANGE)
        self.multi_cell(170, 7, ascii_safe(f"{num}. {title}"))
        self.ln(2)

    def section(self, title: str):
        if self.get_y() > 260:
            self.add_page()
        self.set_x(20)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.multi_cell(170, 6, ascii_safe(title))
        self.ln(1)

    def body(self, text: str, size: int = 10):
        self.set_x(20)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(170, 5.5, ascii_safe(text))
        self.ln(2)

    def bullets(self, items: list[str], size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        for item in items:
            if self.get_y() > 270:
                self.add_page()
            self.set_x(22)
            self.cell(4, 5.5, "-")
            self.multi_cell(166, 5.5, ascii_safe(item))
        self.ln(2)

    def mono(self, text: str, size: int = 8):
        if self.get_y() > 220:
            self.add_page()
        y = self.get_y()
        lines = ascii_safe(text.strip()).split("\n")
        h = min(len(lines) * 4.2 + 6, 90)
        self.set_fill_color(*LIGHT_BG)
        self.rect(20, y, 170, h, "F")
        self.set_xy(22, y + 2)
        self.set_font("Courier", "", size)
        self.set_text_color(*DARK)
        for line in lines[:20]:
            self.cell(166, 4.2, line[:95])
            self.ln(4.2)
        self.set_y(y + h + 3)

    def table(self, headers: list[str], rows: list[list[str]], widths: list[int] | None = None, size: int = 8):
        if not widths:
            n = len(headers)
            widths = [170 // n] * n
            widths[-1] += 170 - sum(widths)
        if self.get_y() > 240:
            self.add_page()
        self.set_x(20)
        self.set_font("Helvetica", "B", size)
        self.set_fill_color(*ORANGE)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(widths[i], 6, ascii_safe(h)[:30], border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        fill = False
        for row in rows:
            if self.get_y() > 275:
                self.add_page()
            self.set_x(20)
            if fill:
                self.set_fill_color(*LIGHT_BG)
            for i, cell in enumerate(row):
                self.cell(widths[i], 5.5, ascii_safe(cell)[:38], border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(3)

    def stat_boxes(self, stats: list[tuple[str, str]]):
        if self.get_y() > 240:
            self.add_page()
        y = self.get_y() + 2
        w = 170 / len(stats)
        x = 20
        for label, value in stats:
            self.set_xy(x, y)
            self.set_fill_color(*LIGHT_BG)
            self.rect(x, y, w - 3, 22, "F")
            self.set_xy(x + 3, y + 2)
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(*ORANGE)
            self.cell(w - 6, 8, ascii_safe(value))
            self.set_xy(x + 3, y + 12)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GRAY)
            self.multi_cell(w - 6, 4, ascii_safe(label))
            x += w
        self.set_y(y + 26)


def build_pdf(output_path: Path) -> None:
    pdf = ProductDepthPDF()
    pdf.cover()
    pdf.toc()

    # PART I
    pdf.part_title(1, "Product Foundation")
    pdf.chapter(1, "Executive Summary")
    pdf.body(
        "Kitchcu is a B2B2C operating system for cloud kitchens - not a food aggregator. "
        "Owners capture WhatsApp and manual orders, manage honest menus with live-capture photos, "
        "and track order lifecycle. Phase 2 adds customer discovery, CRM, and analytics.",
    )
    pdf.stat_boxes([
        ("Owner promise", "WhatsApp to revenue same day"),
        ("Customer promise", "Live photos + fair delivery"),
        ("Platform model", "Subscription, 0% food cut"),
        ("MVP target", "10 pilot kitchens / 3 mo"),
    ])
    pdf.section("Differentiation")
    pdf.bullets([
        "WhatsApp-native operations (70%+ of owner orders today)",
        "Live-capture hero images enforced in catalog API",
        "Owner-owned CRM and customer data (Phase 2)",
        "Zero food commission - subscription SaaS model",
    ])

    pdf.chapter(2, "Personas & Principles")
    pdf.table(
        ["Persona", "Goal", "Surface Today", "Planned"],
        [
            ["Raj (Owner)", "Run kitchen", "kitchen.kitchcu.in PWA", "Reports LIVE"],
            ["Priya (Customer)", "Trusted food", "customer.kitchcu.in PWA", "Browse LIVE; checkout P2"],
            ["Admin", "Moderate/support", "admin.kitchcu.in", "Tickets LIVE"],
        ],
        [35, 40, 45, 50],
    )
    pdf.section("Non-Negotiable Principles")
    pdf.bullets([
        "Truth in media - hero photos must be live-capture",
        "Quality over speed - owner-set prep times",
        "Owner sovereignty - CRM belongs to kitchen",
        "Progressive complexity - unlock after traction",
        "WhatsApp-native - primary intake channel",
    ])

    # PART II
    pdf.part_title(2, "Market Problems & Solutions")
    pdf.chapter(3, "Owner Pain Points (P1-P8)")
    pdf.table(
        ["ID", "Pain", "Module", "Solution", "Status"],
        [
            ["P1", "WhatsApp chaos", "Order+Notify", "Parser, drafts", "Partial"],
            ["P2", "Commission 18-30%", "Billing", "Subscription", "S6"],
            ["P3", "No profit view", "Analytics", "Owner revenue LIVE", "Partial"],
            ["P4", "Stock photos", "Catalog", "Live-capture", "Done"],
            ["P5", "Taste variance", "Catalog", "Quality fields", "Partial"],
            ["P6", "No CRM", "Marketing", "Owner CRM", "P2"],
            ["P7", "Guesswork promos", "Growth", "Suggestions", "P2"],
            ["P8", "Channel silos", "Order", "One lifecycle", "Partial"],
        ],
        [12, 38, 30, 45, 45],
        size=7,
    )

    pdf.chapter(4, "Customer Pain Points (C1-C6)")
    pdf.table(
        ["ID", "Pain", "Answer", "Status"],
        [
            ["C1", "Untrustworthy photos", "Live-capture media", "Done"],
            ["C2", "Opaque fees", "PostGIS + owner rules", "Fields only"],
            ["C3", "No tracking", "Lifecycle + notify", "Partial"],
            ["C4", "Generic ratings", "Home-taste 1-5", "P2"],
            ["C5", "One kitchen/cart", "Multi-kitchen checkout", "P2"],
            ["C6", "No tiffin", "Meal plans", "P2"],
        ],
        [12, 50, 58, 50],
        size=8,
    )

    # PART III
    pdf.part_title(3, "Platform Modules")
    pdf.chapter(5, "Architecture & Module Map")
    pdf.mono(
        """
Gateway :18000 -> Identity :18001 | Catalog :18002 | Order :18003 | Notification :18005
PostgreSQL 16 + PostGIS (schema-per-domain) | Redis Streams + cache | MinIO media
        """
    )
    pdf.table(
        ["Module", "Schema", "Status", "Events"],
        [
            ["Identity", "ckac_identity", "DONE S1", "kitchen.created"],
            ["Catalog", "ckac_catalog", "DONE S2", "dish.created/updated"],
            ["Order", "ckac_orders", "DONE S3", "order.placed, status"],
            ["Notification", "ckac_support", "DONE S4", "whatsapp + support.ticket.*"],
            ["Billing", "ckac_billing", "S6", "payment.captured"],
            ["Analytics", "order svc", "S5 PARTIAL", "owner revenue/segments"],
            ["Marketing", "ckac_marketing", "P2", "CRM, coupons"],
        ],
        [38, 42, 35, 55],
        size=7,
    )

    pdf.chapter(6, "Service Deep Dives")
    pdf.section("Identity - Owners, Kitchens, OTP, JWT")
    pdf.bullets([
        "Kitchen code: CKPNQ001 format; PostGIS location on create",
        "APIs: register, OTP, POST/GET kitchens, owners/me",
    ])
    pdf.section("Catalog - Menu, Categories, Live Media (F13-F15)")
    pdf.bullets([
        "10 default categories auto-seeded; menu Redis cache TTL 300s",
        "Hero image validator rejects non-live-capture; PATCH dish updates",
    ])
    pdf.section("Order - Intake, Lifecycle, History (F03-F05)")
    pdf.bullets([
        "Manual orders, message parser, drafts, confirm flow",
        "State machine: received -> ... -> delivered | cancelled",
        "Order code: {kitchen_code}-BILL-{date}-{seq}",
    ])
    pdf.section("Notification - WhatsApp, AI Support Chat, Tickets (F01, F45)")
    pdf.bullets([
        "Meta webhook; kitchen lookup by whatsapp_phone_id",
        "POST /support/chat - owner & customer modes with AI escalation",
        "POST /support/tickets - public create; admin CRUD via /admin/tickets",
        "Schema ckac_support: support_tickets, support_ticket_messages",
    ])

    # PART IV
    pdf.part_title(4, "48-Feature Catalog")
    pdf.chapter(7, "Phase 1 Features")
    pdf.table(
        ["ID", "Feature", "Status"],
        [
            ["F01", "WhatsApp capture", "PARTIAL"],
            ["F02", "Message parser", "DONE"],
            ["F03", "Manual order", "DONE"],
            ["F04", "Lifecycle", "DONE"],
            ["F05", "Order history", "DONE"],
            ["F07", "Revenue report", "PARTIAL"],
            ["F13-F15", "Menu + live photo + categories", "DONE"],
            ["F26", "Subscription", "PARTIAL"],
            ["F30", "Prep time", "DONE"],
            ["F42-F43", "Payments", "S6"],
            ["F45", "Notify + AI chat + tickets", "PARTIAL"],
        ],
        [18, 100, 52],
        size=8,
    )
    pdf.stat_boxes([("Done", "8"), ("Partial", "4"), ("Total", "48 features")])

    pdf.chapter(8, "Phase 2 & 3 Features")
    pdf.section("Phase 2 - Growth")
    pdf.bullets([
        "F06 Multi-kitchen checkout | F16-F18 Home taste ratings",
        "F27-F33 Delivery + customer PWA | F34-F40 CRM, tiffin, coupons",
        "F44 Split payment via Razorpay Route",
    ], size=9)
    pdf.section("Phase 3 - Differentiation")
    pdf.bullets([
        "F19 Ingredient mapper | F21-F24 Learning + chef rankings",
        "F46-F48 Live kitchen streaming premium",
    ], size=9)

    # PART V
    pdf.part_title(5, "Application & Data Flows")
    pdf.chapter(9, "Key Flows")
    pdf.section("WhatsApp Order Intake")
    pdf.mono(
        "Webhook -> notification -> whatsapp.message.received\n"
        "-> order internal API -> draft -> owner confirm -> order.placed"
    )
    pdf.section("Order Lifecycle")
    pdf.mono(
        "PATCH status -> validate transition -> order_status_events\n"
        "-> order.status.changed -> (future) customer notify"
    )
    pdf.section("Event Catalog (EDD + Outbox)")
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
        size=8,
    )

    # PART VI
    pdf.part_title(6, "Technical Reference")
    pdf.chapter(10, "Database & APIs")
    pdf.table(
        ["Schema", "Tables", "Status"],
        [
            ["ckac_identity", "owners, kitchens", "LIVE"],
            ["ckac_catalog", "categories, dishes, dish_media", "LIVE"],
            ["ckac_orders", "orders, items, events, drafts", "LIVE"],
            ["ckac_events", "outbox, processed_events", "LIVE"],
            ["ckac_support", "support_tickets, messages", "LIVE"],
        ],
        [45, 85, 40],
    )
    pdf.section("API Summary (Gateway :18000/api/v1)")
    pdf.mono(
        "Identity: /auth/* /owners/* /kitchens\n"
        "Catalog: /kitchens/{id}/categories|menu|dishes\n"
        "Order: /kitchens/{id}/orders/* /orders/{id}/status /analytics/*\n"
        "Notification: /webhooks/whatsapp /support/chat /support/tickets\n"
        "Admin: /admin/tickets/*"
    )
    pdf.chapter(11, "Technology Stack")
    pdf.table(
        ["Layer", "Choice"],
        [
            ["Backend", "Python 3.12 FastAPI microservices"],
            ["Database", "PostgreSQL 16 + PostGIS"],
            ["Events/Cache", "Redis Streams + menu cache"],
            ["Frontend", "React + Vite + TS PWAs (portal, customer, kitchen, admin)"],
            ["Payments", "Razorpay Route (S6)"],
            ["Infra", "Docker Compose -> Kubernetes"],
        ],
        [45, 125],
        size=9,
    )

    # PART VII
    pdf.part_title(7, "Business & Metrics")
    pdf.chapter(12, "Business Model")
    pdf.table(
        ["Tier", "Price/mo", "Includes"],
        [
            ["Starter", "Rs 499", "WhatsApp, menu, basic reports"],
            ["Pro", "Rs 1,499", "CRM, marketing, analytics"],
            ["Enterprise", "Rs 3,999", "API, multi-branch, stream"],
        ],
        [35, 35, 100],
        size=9,
    )
    pdf.body("Zero food commission. Kitchen keeps 100% of food revenue.")

    pdf.chapter(13, "Build Status & Roadmap")
    pdf.stat_boxes([
        ("Sprints done", "S1-S4 done; S5 partial"),
        ("Tests", "90+ passing"),
        ("Services", "5 + gateway"),
    ])
    pdf.table(
        ["Sprint", "Deliverable", "Status"],
        [
            ["S1-S4", "Identity, Catalog, Order, Notification", "COMPLETE"],
            ["S5", "PWAs + owner analytics + support", "PARTIAL"],
            ["S6", "Billing + revenue", "Planned"],
        ],
        [22, 98, 50],
    )

    pdf.chapter(14, "KPIs & Competitive Position")
    pdf.table(
        ["Metric", "Target"],
        [
            ["Time to first order", "< 5 min"],
            ["WhatsApp parse rate", "95%"],
            ["Hero live-capture", "100%"],
            ["Owner retention M6", "80%"],
        ],
        [85, 85],
        size=9,
    )
    pdf.body(
        "vs Aggregators: zero commission, owner CRM, live-capture. "
        "vs POS: customer discovery + trust layer + WhatsApp analytics.",
        size=9,
    )

    pdf.add_page()
    pdf.set_xy(20, 50)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 10, "Kitchcu")
    pdf.ln(14)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, "hello@kitchcu.in  |  kitchcu.in")
    pdf.ln(10)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(170, 5, "See CKAC-PRODUCT-DEPTH-GUIDE.md for markdown source.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"Generated: {output_path} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    build_pdf(root / "docs" / "CKAC-PRODUCT-DEPTH-GUIDE.pdf")
