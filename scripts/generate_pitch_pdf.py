#!/usr/bin/env python3
"""Generate Kitchcu CPO Product Blueprint PDF — modules, flows, pain points, solutions."""

from pathlib import Path

from fpdf import FPDF

ORANGE = (230, 81, 0)
DARK = (33, 33, 33)
GRAY = (97, 97, 97)
WHITE = (255, 255, 255)
LIGHT_BG = (250, 248, 245)
ACCENT = (0, 105, 92)
GREEN = (46, 125, 50)
AMBER = (245, 124, 0)


def ascii_safe(text: str) -> str:
    """FPDF Helvetica is Latin-1 only; normalize Unicode to ASCII."""
    if not text:
        return text
    replacements = {
        "\u2014": " - ",
        "\u2013": "-",
        "\u2192": "->",
        "\u2022": "-",
        "\u2026": "...",
        "\u2265": ">=",
        "\u20b9": "Rs ",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


class CPOProductPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.slide_num = 0

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, "Kitchcu CPO Product Blueprint v3.0 | Confidential | July 2026", align="C")

    def new_slide(self, tag: str = ""):
        self.add_page()
        self.slide_num += 1
        self.set_fill_color(*ORANGE)
        self.rect(0, 0, 297, 18, "F")
        self.set_xy(12, 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*WHITE)
        title = "Kitchcu Product Blueprint"
        if tag:
            title = f"{title}  |  {tag}"
        self.cell(200, 8, title)
        self.set_xy(-30, 5)
        self.cell(20, 8, str(self.slide_num), align="R")

    def section_title(self, title: str, y: float = 28):
        self.set_xy(20, y)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*ORANGE)
        self.multi_cell(257, 10, ascii_safe(title))
        self.ln(2)

    def sub_title(self, text: str):
        self.set_x(20)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ACCENT)
        self.multi_cell(257, 7, ascii_safe(text))
        self.ln(1)

    def body(self, text: str, size: int = 11):
        self.set_x(20)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(257, 6, ascii_safe(text))

    def bullets(self, items: list[str], size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        for item in items:
            self.set_x(22)
            self.cell(4, 6, "-")
            self.multi_cell(250, 6, ascii_safe(item))
            self.ln(0.5)

    def mono(self, text: str, size: int = 8):
        self.set_x(20)
        self.set_font("Courier", "", size)
        self.set_text_color(*DARK)
        self.set_fill_color(*LIGHT_BG)
        text = ascii_safe(text)
        lines = text.strip().split("\n")
        h = len(lines) * 4.5 + 4
        y = self.get_y()
        self.rect(20, y, 257, min(h, 120), "F")
        self.set_xy(22, y + 2)
        for line in lines:
            self.cell(253, 4.5, line)
            self.ln(4.5)
        self.set_y(y + min(h, 120) + 2)

    def table(self, headers: list[str], rows: list[list[str]], widths: list[int] | None = None, size: int = 8):
        if not widths:
            widths = [257 // len(headers)] * len(headers)
        self.ln(2)
        self.set_x(20)
        self.set_font("Helvetica", "B", size)
        self.set_fill_color(*ORANGE)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, ascii_safe(h), border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        fill = False
        for row in rows:
            self.set_x(20)
            if fill:
                self.set_fill_color(*LIGHT_BG)
            for i, cell in enumerate(row):
                self.cell(widths[i], 6, ascii_safe(cell), border=1, fill=fill)
            self.ln()
            fill = not fill

    def stat_row(self, stats: list[tuple[str, str]]):
        self.ln(4)
        x = 20
        w = 257 / len(stats)
        y = self.get_y()
        for label, value in stats:
            self.set_xy(x, y)
            self.set_fill_color(*LIGHT_BG)
            self.rect(x, y, w - 4, 26, "F")
            self.set_xy(x + 4, y + 3)
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(*ORANGE)
            self.cell(w - 8, 9, ascii_safe(value))
            self.set_xy(x + 4, y + 14)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*GRAY)
            self.multi_cell(w - 8, 4, ascii_safe(label))
            x += w
        self.set_y(y + 30)

    def two_col_bullets(self, left_title: str, left: list[str], right_title: str, right: list[str]):
        y0 = self.get_y() + 2
        col_w = 125
        self.set_xy(20, y0)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.cell(col_w, 7, ascii_safe(left_title))
        self.ln(7)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        for item in left:
            self.set_x(22)
            self.multi_cell(col_w, 5, f"  - {ascii_safe(item)}")
        y_left = self.get_y()
        self.set_xy(150, y0)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.cell(col_w, 7, ascii_safe(right_title))
        y = y0 + 7
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        for item in right:
            self.set_xy(152, y)
            self.multi_cell(col_w, 5, f"  - {ascii_safe(item)}")
            y += 5 + (len(item) // 38) * 5
        self.set_y(max(y_left, y) + 3)


def build_pdf(output_path: Path) -> None:
    pdf = CPOProductPDF()

    # 1 — Cover
    pdf.new_slide()
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(0, 18, 297, 192, "F")
    pdf.set_xy(20, 55)
    pdf.set_font("Helvetica", "B", 44)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 18, "Kitchcu")
    pdf.ln(20)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 10, "CPO Product Blueprint")
    pdf.ln(14)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        257, 8,
        "Modules  |  Functionalities  |  Data Flows  |  Application Flows  |  "
        "Pain Points  |  Solutions  |  Roadmap",
    )
    pdf.ln(8)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Kitchcu cloud kitchen platform")
    pdf.set_xy(20, 168)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 7, "Version 3.0  |  July 2026  |  Confidential")

    # 2 — North Star
    pdf.new_slide("Strategy")
    pdf.section_title("Product North Star")
    pdf.body(
        "Kitchcu is the operating system for cloud kitchens — not an aggregator. "
        "Subscription SaaS with zero food commission. Owners run everything from one PWA; "
        "customers trust what they order through live media and home-taste ratings.",
    )
    pdf.stat_row([
        ("Owner promise", "WhatsApp to revenue same day"),
        ("Customer promise", "Live photos + fair delivery"),
        ("Platform model", "Subscription, 0% food cut"),
        ("MVP target", "10 pilot kitchens / 3 mo"),
    ])
    pdf.sub_title("Non-Negotiable Principles")
    pdf.bullets([
        "Truth in media — hero dish photos must be live-capture (no stock deception)",
        "Quality over speed — owner-set prep/delivery windows, never fake 10-min races",
        "Owner sovereignty — CRM, coupons, and customer history belong to the kitchen",
        "Progressive complexity — advanced features unlock after kitchen traction (50+ orders)",
        "WhatsApp-native — meet owners where 70%+ of orders already happen",
    ])

    # 3 — Owner pain points
    pdf.new_slide("Pain Points")
    pdf.section_title("Owner Pain Points (Market Reality)")
    pdf.table(
        ["Pain", "Business Impact", "Severity"],
        [
            ["Orders trapped in WhatsApp chats", "Lost orders, zero analytics", "Critical"],
            ["Aggregator 18-30% commission", "Margin erosion, no customer ownership", "Critical"],
            ["No daily profit visibility", "Cash flow guesswork, bad decisions", "High"],
            ["Stock photos mislead customers", "Refunds, reputation damage", "High"],
            ["Inconsistent taste batch-to-batch", "Repeat customer loss", "High"],
            ["No CRM or targeted marketing", "Cannot win back regulars", "Medium"],
            ["Promotions based on guesswork", "Wasted discounts", "Medium"],
            ["Walk-in + call + chat silos", "Double booking, chaos", "Medium"],
        ],
        [95, 110, 52],
        size=7,
    )

    # 4 — Customer pain points
    pdf.new_slide("Pain Points")
    pdf.section_title("Customer Pain Points")
    pdf.table(
        ["Pain", "Why It Matters", "Kitchcu Answer"],
        [
            ["Cannot trust menu photos", "Expectation vs reality gap", "Live-capture dish media"],
            ["Opaque delivery fees", "Cart abandonment", "PostGIS distance + owner rules"],
            ["Generic star ratings", "No home-food signal", "Home-taste benchmark 1-5"],
            ["One kitchen per cart", "Inconvenient lunch combos", "Multi-kitchen checkout (P2)"],
            ["No order transparency", "Anxiety, support calls", "Lifecycle + WhatsApp updates"],
            ["No tiffin subscription", "Daily meal friction", "Kitchen meal plans (P2)"],
        ],
        [70, 85, 102],
        size=8,
    )
    pdf.ln(2)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(257, 6, ascii_safe('"I run 80 orders a day on WhatsApp and still do not know my profit." - Typical owner'))

    # 5 — Solution matrix
    pdf.new_slide("Solutions")
    pdf.section_title("Pain Point to Solution Mapping")
    pdf.table(
        ["Pain ID", "Problem", "Kitchcu Module", "Solution"],
        [
            ["P1", "WhatsApp chaos", "Order + Notification", "Unified inbox, parser, manual fallback"],
            ["P2", "Aggregator commission", "Billing", "Flat subscription; kitchen keeps food revenue"],
            ["P3", "No profit view", "Analytics", "Revenue, dish, pattern reports"],
            ["P4", "False menu photos", "Catalog + Media", "Live-capture enforced for hero images"],
            ["P5", "Taste inconsistency", "Catalog + Ingredient", "Per-dish standards, stock mapper (P3)"],
            ["P6", "No customer ownership", "Marketing", "Owner CRM, coupons, tiffin"],
            ["P7", "Guesswork promos", "Growth Engine", "Seasonal, win-back, combo suggestions"],
            ["P8", "Multi-channel chaos", "Order Service", "Single lifecycle for all sources"],
        ],
        [18, 52, 45, 142],
        size=7,
    )

    # 6 — Platform architecture
    pdf.new_slide("Architecture")
    pdf.section_title("Platform Architecture (Microservices)")
    pdf.mono(
        """
                    +------------------+
                    |   API Gateway    |  :18000  (path-based routing)
                    +--------+---------+
                             |
        +--------------------+--------------------+
        v                    v                    v
 +-------------+     +-------------+     +-------------+
 |  Identity   |     |   Catalog   |     |    Order    |   ... Billing, Notification
 |  S1 DONE    |     |  S2 DONE    |     |  S3 DONE    |
 +------+------+     +------+------+     +------+------+
        |                   |                   |
        +-------------------+-------------------+
                            v
              +---------------------------+
              |  PostgreSQL 16 + PostGIS  |
              |  schema-per-domain (ACID) |
              +-------------+-------------+
                            |
              +-------------+-------------+
              v                           v
        Redis Streams                 MinIO/S3
        (event bus + cache)           (dish media)
        """
    )
    pdf.body("Event-driven design: every write publishes EventEnvelope after DB commit.", size=9)

    # 7 — Module catalog
    pdf.new_slide("Modules")
    pdf.section_title("Platform Modules & Build Status")
    pdf.table(
        ["Module", "Responsibility", "Schema", "Status"],
        [
            ["Gateway", "Auth routing, service proxy", "-", "DONE v0.3"],
            ["Identity", "Owners, kitchens, OTP, JWT", "ckac_identity", "DONE S1"],
            ["Catalog", "Dishes, categories, live media", "ckac_catalog", "DONE S2"],
            ["Order", "Manual orders, lifecycle, history", "ckac_orders", "DONE S3"],
            ["Notification", "WhatsApp, push, SMS, support chat & tickets", "ckac_support", "S4 LIVE"],
            ["Billing", "Subscriptions, UPI, split pay", "ckac_billing", "Sprint 6"],
            ["Analytics", "Owner revenue, segments, peak hours", "order svc", "S5 PARTIAL"],
            ["Marketing", "CRM, coupons, tiffin", "ckac_marketing", "Phase 2"],
            ["Rating", "Home taste, A/V reviews", "ckac_ratings", "Phase 2"],
            ["Delivery", "Radius, fees, tracking", "geo rules", "Phase 2"],
            ["Growth", "AI-ready suggestions", "ckac_growth", "Phase 2-3"],
            ["Learning / Stream", "Recipes, live prep", "ckac_learning", "Phase 3"],
        ],
        [38, 95, 52, 72],
        size=7,
    )

    # 8 — Identity module
    pdf.new_slide("Module Detail")
    pdf.section_title("Module: Identity Service")
    pdf.two_col_bullets(
        "Functionalities",
        [
            "Owner registration (phone + OTP)",
            "JWT access + refresh tokens",
            "Kitchen onboarding with PostGIS location",
            "Kitchen code generation (e.g. CKPNQ001)",
            "Owner-kitchen authorization checks",
        ],
        "API Endpoints (via Gateway)",
        [
            "POST /api/v1/owners/register",
            "POST /api/v1/auth/otp/request | verify",
            "POST /api/v1/kitchens",
            "GET  /api/v1/kitchens/me",
        ],
    )
    pdf.sub_title("Data Model (ckac_identity)")
    pdf.bullets(["owners: id, phone, name, subscription_tier, status", "kitchens: id, owner_id, code, name, location (geography)"], size=9)

    # 9 — Catalog module
    pdf.new_slide("Module Detail")
    pdf.section_title("Module: Catalog Service")
    pdf.two_col_bullets(
        "Functionalities (F13-F15)",
        [
            "10 default categories seeded per kitchen",
            "Dish CRUD with price, prep time, quality notes",
            "Live-capture rule: hero image must be is_live_capture",
            "Public menu endpoint (cacheable)",
            "Publishes dish.created / dish.updated events",
        ],
        "Business Rules",
        [
            "No stock photo as hero — CPO trust mandate",
            "Cross-schema read: verify kitchen ownership",
            "No cross-schema writes",
            "Menu invalidation on dish.updated (Redis)",
        ],
    )
    pdf.sub_title("Events")
    pdf.body("dish.created -> ckac:catalog:dish stream", size=9)

    # 10 — Order module
    pdf.new_slide("Module Detail")
    pdf.section_title("Module: Order Service")
    pdf.two_col_bullets(
        "Functionalities (F03-F05, F30)",
        [
            "Manual order creation (walk-in, phone)",
            "Line items from catalog (price snapshot)",
            "Lifecycle state machine with audit trail",
            "Order history with status/source filters",
            "Per-dish prep time drives ETA",
        ],
        "Order Code Format",
        [
            "{kitchen_code}-BILL-{YYYYMMDD}-{SEQ}",
            "Example: CKPNQ001-BILL-20260712-0001",
            "Bill ID: BILL-20260712-0001",
        ],
    )
    pdf.sub_title("Lifecycle States")
    pdf.mono(
        "received -> accepted -> preparing -> ready -> out_for_delivery -> delivered\n"
        "Any pre-delivered state -> cancelled (reason required)\n"
        "Each transition -> order_status_events row + order.status.changed event"
    )

    # 11 — Planned modules
    pdf.new_slide("Modules")
    pdf.section_title("Planned Modules (Sprints 4-6 & Phase 2)")
    pdf.table(
        ["Module", "Key Features", "Events / Integrations"],
        [
            ["Notification S4", "WhatsApp webhook, message parser, push", "Consumes order.*; F01-F02, F45"],
            ["Billing S6", "Owner subscription, UPI, COD, Razorpay", "payment.captured; F26, F42-F44"],
            ["Analytics S6+", "Revenue, best dishes, patterns", "Consumes order.delivered; F07-F12"],
            ["Marketing P2", "CRM, coupons, tiffin, daily push", "F34-F40"],
            ["Delivery P2", "Radius, fee quote, tracking links", "PostGIS; F27-F31"],
            ["Rating P2", "Home taste + A/V anonymous reviews", "F16-F18"],
            ["Growth P2", "Seasonal, win-back, combo suggestions", "F11"],
        ],
        [45, 110, 102],
        size=7,
    )

    # 12 — Owner app flow
    pdf.new_slide("Application Flows")
    pdf.section_title("Owner Application Flow — Day 1 to Daily Ops")
    pdf.mono(
        """
DAY 1 ONBOARDING
  Register phone -> OTP (JWT) -> Create kitchen (geo pin)
  -> Add 5 dishes (live camera) -> Publish menu
  -> Connect WhatsApp Business (S4) -> First order in inbox

DAILY OPERATIONS
  Home Inbox: new orders + WhatsApp drafts + today stats
  -> Tap order -> Confirm / edit items -> Advance lifecycle (1 tap)
  -> Customer notified (WhatsApp + push)
  -> End of day: revenue report, top dish, growth tip

OWNER PWA NAV (target)
  Home | Orders (Active/History/Drafts) | Menu | Customers | Analytics
  | Marketing | Subscriptions | Payments | Settings
        """
    )

    # 13 — Customer app flow
    pdf.new_slide("Application Flows")
    pdf.section_title("Customer Application Flow (Phase 2 PWA)")
    pdf.mono(
        """
DISCOVERY & ORDER
  Open PWA link or Discover map (PostGIS nearby)
  -> Filter: distance, rating, live-prep premium
  -> Kitchen profile: live photos, home-taste scores
  -> Add items (multi-kitchen cart supported)
  -> Delivery fee breakdown shown -> Pay UPI or COD
  -> Track: received ... delivered (WhatsApp + push)

POST-ORDER
  -> Rate home taste (1-5) + quality + optional 15s video
  -> Repeat order in 2 taps from history
  -> Subscribe to tiffin plan (optional)

CUSTOMER PWA NAV
  Discover | Cart | Orders & Tracking | Subscriptions | Ratings | Profile
        """
    )

    # 14 — Order intake flow
    pdf.new_slide("Data Flow")
    pdf.section_title("Order Intake — Multi-Source Data Flow")
    pdf.mono(
        """
SOURCES                    INTAKE PATH                         OUTPUT
---------                  -----------                         ------
WhatsApp message    ->    Webhook -> Parser -> Draft order  ->  Owner confirms
Phone / walk-in     ->    Owner manual entry (S3 DONE)      ->  order.placed
Customer PWA        ->    Cart checkout (Phase 2)           ->  order.placed

order.placed event:
  DB commit (ckac_orders) -> Redis Stream ckac:orders:order
  -> Notification service (owner alert + customer confirm)
  -> Analytics worker (counters, daily stats)
  -> Billing worker (payment capture when online)
        """
    )

    # 15 — Lifecycle data flow
    pdf.new_slide("Data Flow")
    pdf.section_title("Order Lifecycle — Event-Driven Data Flow")
    pdf.mono(
        """
Owner taps status advance (PATCH /orders/{id}/status)
        |
        v
Validate transition (state machine) -> Update orders.status
        |
        v
Insert order_status_events (from, to, note, created_by)
        |
        v
Publish order.status.changed -> ckac:orders:order
        |
   +----+----+----+
   v    v    v    v
 Push  WA   CRM  Analytics
 (F45)      update  (future)
        """
    )
    pdf.body("Cancel requires reason. Terminal states: delivered, cancelled.", size=9)

    # 16 — EDD event catalog
    pdf.new_slide("Data Flow")
    pdf.section_title("Event Catalog (Event-Driven Design)")
    pdf.table(
        ["Event", "Producer", "Stream", "Consumers"],
        [
            ["kitchen.created", "identity", "ckac:identity:kitchen", "analytics"],
            ["dish.created", "catalog", "ckac:catalog:dish", "search, cache"],
            ["dish.updated", "catalog", "ckac:catalog:dish", "menu cache invalidation"],
            ["order.placed", "order", "ckac:orders:order", "notify, analytics, billing"],
            ["order.status.changed", "order", "ckac:orders:order", "notify, tracking UI"],
            ["payment.captured", "billing", "ckac:billing:payment", "settlement, reports"],
            ["whatsapp.message.received", "notification", "ckac:notify:wa", "order parser"],
        ],
        [52, 38, 58, 109],
        size=7,
    )
    pdf.body("Contract: DB commit first, then publish. Outbox table in ckac_events for reliability.", size=8)

    # 17 — Database schemas
    pdf.new_slide("Data Architecture")
    pdf.section_title("Database Architecture — Schema-per-Domain")
    pdf.table(
        ["Schema", "Tables", "Phase", "Status"],
        [
            ["ckac_identity", "owners, kitchens", "1", "LIVE"],
            ["ckac_catalog", "categories, dishes, dish_media", "1", "LIVE"],
            ["ckac_orders", "orders, order_items, order_status_events", "1", "LIVE"],
            ["ckac_events", "outbox, processed_events", "1", "LIVE"],
            ["ckac_billing", "payments, subscriptions, settlements", "1-2", "Planned S6"],
            ["ckac_marketing", "kitchen_customers, coupons, plans", "2", "Planned"],
            ["ckac_ratings", "dish_ratings, suggestions", "2", "Planned"],
            ["ckac_growth", "suggestions, seasonal_patterns", "2-3", "Planned"],
        ],
        [45, 95, 25, 92],
        size=7,
    )
    pdf.body("Scaling: 0-500 kitchens single PG; read replica + PgBouncer at 500-5K; partition events by month at 5K+.", size=8)

    # 18 — Gateway routing
    pdf.new_slide("Integration")
    pdf.section_title("API Gateway Routing & Service Ports")
    pdf.table(
        ["Path Pattern", "Target Service", "Port (host)"],
        [
            ["/api/v1/auth/*, /api/v1/owners/*", "Identity", "18001"],
            ["/api/v1/kitchens/{id}/categories|menu|dishes", "Catalog", "18002"],
            ["/api/v1/kitchens/{id}/orders/*", "Order", "18003"],
            ["/api/v1/orders/*", "Order", "18003"],
            ["/api/v1/kitchens (create/list)", "Identity", "18001"],
            ["Gateway entry", "Gateway", "18000"],
        ],
        [110, 55, 92],
        size=8,
    )

    # 19 — Phase 1 features
    pdf.new_slide("Features")
    pdf.section_title("Phase 1 Features — Owner Can Run Kitchen")
    pdf.table(
        ["ID", "Feature", "Module", "Sprint", "Status"],
        [
            ["F01", "WhatsApp order capture", "notification", "S4", "PARTIAL"],
            ["F02", "Message parser", "notification", "S4", "DONE"],
            ["F03", "Manual order input", "order", "S3", "DONE"],
            ["F04", "Order lifecycle", "order", "S3", "DONE"],
            ["F05", "Order history", "order", "S3", "DONE"],
            ["F07", "Revenue report", "analytics", "S6", "Planned"],
            ["F13-F15", "Menu + live photo + categories", "catalog", "S2", "DONE"],
            ["F26", "Owner subscription", "billing", "S6", "Planned"],
            ["F30", "Per-dish prep time", "order+catalog", "S3", "DONE"],
            ["F42-F43", "UPI / COD payments", "billing", "S6", "Planned"],
            ["F45", "WhatsApp + app notifications + AI support", "notification", "S4", "PARTIAL"],
        ],
        [18, 75, 45, 22, 97],
        size=7,
    )

    # 20 — Phase 2 features
    pdf.new_slide("Features")
    pdf.section_title("Phase 2 Features — Growth (Months 4-6)")
    pdf.two_col_bullets(
        "Customer Experience",
        [
            "F06 Multi-kitchen single checkout",
            "F32 Kitchen discovery (map + distance)",
            "F33 Order history + repeat order",
            "F16-F18 Home taste ratings + A/V",
            "F41 Custom cooking requests",
        ],
        "Owner Growth",
        [
            "F34-F35 Tiffin / meal plans",
            "F36-F38 CRM, coupons, targeted pricing",
            "F39 Daily menu WhatsApp push",
            "F07-F11 Analytics + growth suggestions",
            "F44 Aggregated payment + split settlement",
            "F27-F31 Delivery radius, fees, tracking",
        ],
    )

    # 21 — Phase 3 features
    pdf.new_slide("Features")
    pdf.section_title("Phase 3 Features — Differentiation (Moat)")
    pdf.bullets([
        "F19 Ingredient balance mapper — stock deduct, low-stock alerts",
        "F20 Customer recipe suggestions (owner accept/reject workflow)",
        "F21-F23 Learning portal, trial batches, recipe rewards",
        "F24 Best cloud chef rankings (city / state / national)",
        "F46-F48 Live kitchen streaming (optional owner opt-in premium)",
        "F12 Performance report with recipe improvement suggestions",
    ], size=10)
    pdf.sub_title("Ranking Formula (Benchmark)")
    pdf.body(
        "Monthly score = 30% avg rating + 20% recipe shares + 25% review volume "
        "+ 15% repeat rate + 10% consistency index.",
        size=9,
    )

    # 22 — Build status
    pdf.new_slide("Delivery")
    pdf.section_title("Current Build Status — July 2026")
    pdf.stat_row([
        ("Sprints done", "S1-S4 complete; S5 partial"),
        ("Services live", "5 (+ gateway)"),
        ("Automated tests", "90+ passing"),
        ("Apps live", "Portal + 3 PWAs"),
    ])
    pdf.table(
        ["Sprint", "Deliverable", "Status"],
        [
            ["S1", "Identity, gateway, Docker, JWT, TDD foundation", "COMPLETE"],
            ["S2", "Catalog, live-capture, dish.created events", "COMPLETE"],
            ["S3", "Order manual, lifecycle, order.placed events", "COMPLETE"],
            ["S4", "WhatsApp webhook + parser + AI support chat", "COMPLETE"],
            ["S5", "PWAs + portal + analytics + ticketing", "PARTIAL LIVE"],
            ["S6", "Billing + revenue reports", "Planned"],
        ],
        [25, 170, 62],
        size=8,
    )

    # 23 — Multi-kitchen checkout
    pdf.new_slide("Application Flows")
    pdf.section_title("Multi-Kitchen Checkout Flow (F06 — Phase 2)")
    pdf.mono(
        """
Customer cart:
  [Kitchen A: 2 dishes] + [Kitchen B: 1 dish]
              |
              v
       master_orders (1 customer payment)
              |
      +-------+-------+
      v               v
  order (CKA-...)   order (CKB-...)
  separate lifecycle, separate bills, separate tracking
              |
              v
  Razorpay Route: automatic split to each kitchen linked account
  Customer: unified receipt + per-kitchen tracking tabs
        """
    )

    # 24 — Delivery fee flow
    pdf.new_slide("Application Flows")
    pdf.section_title("Delivery Fee Decision Flow (F27-F28)")
    pdf.mono(
        """
1. Compute distance (PostGIS) owner kitchen <-> customer address
2. If distance <= free_delivery_radius -> fee = 0
3. If > radius -> apply owner rules (flat / per-km / min order)
4. Show breakdown at checkout BEFORE payment
5. Customer denies fee:
   a. Owner can cancel order
   b. Owner can waive (min order rule)
   c. Customer switches to self-pickup
        """
    )

    # 25 — Growth engine
    pdf.new_slide("Intelligence")
    pdf.section_title("Owner Growth Intelligence Engine (F11)")
    pdf.table(
        ["Suggestion Type", "Trigger", "Example"],
        [
            ["Seasonal", "Calendar + regional patterns", "Diwali in 3 weeks — add mithai combo"],
            ["Dish promo", "High rating, low volume", "Paneer Tikka 4.8 but 5% orders — promote"],
            ["Win-back", "Regular inactive 21+ days", "12 customers — send coupon MAAS20"],
            ["Combo", "Order association mining", "Naan + Dal ordered together 68% — bundle"],
            ["Peak staffing", "Historical volume by hour", "Fri 12-2 PM is 3x avg — prep extra"],
        ],
        [40, 75, 142],
        size=7,
    )

    # 26 — Rating trust layer
    pdf.new_slide("Trust")
    pdf.section_title("Rating & Trust Layer (F16-F18)")
    pdf.table(
        ["Dimension", "Scale", "Purpose"],
        [
            ["Home taste", "1-5", "Tastes like authentic home cooking"],
            ["Quality", "1-5", "Freshness, portion, packaging"],
            ["Optional A/V", "15-30 sec", "Anonymous video/audio review"],
        ],
        [55, 40, 162],
        size=9,
    )
    pdf.bullets([
        "Ratings only from verified completed orders — no fake reviews",
        "Aggregated on dish page without customer identity",
        "Feeds chef rankings and growth suggestions",
    ], size=9)

    # 27 — Business model
    pdf.new_slide("Business")
    pdf.section_title("Business Model — Subscription, Not Commission")
    pdf.table(
        ["Tier", "Price/mo", "Includes"],
        [
            ["Starter", "Rs 499", "WhatsApp orders, menu, basic reports"],
            ["Pro", "Rs 1,499", "CRM, marketing, tiffin, coupons, analytics"],
            ["Enterprise", "Rs 3,999", "Live stream, API, multi-branch"],
        ],
        [45, 40, 172],
        size=9,
    )
    pdf.bullets([
        "Zero per-order food commission — kitchen keeps 100% food revenue",
        "Customer tiffin: 0% Kitchcu cut",
        "Payments: pass-through via Razorpay Route (multi-kitchen split)",
        "Yearly plans: 2 months free",
    ], size=9)

    # 28 — KPIs
    pdf.new_slide("Metrics")
    pdf.section_title("CPO Success Metrics & KPIs")
    pdf.table(
        ["Metric", "Phase 1 Target", "How Measured"],
        [
            ["Time to first order", "< 5 min post-signup", "Onboarding funnel"],
            ["WhatsApp parse rate", "95% parsed or manual", "Parser accuracy log"],
            ["Lifecycle notify latency", "< 2s event to push", "Event SLA monitoring"],
            ["Hero live-capture rate", "100%", "Catalog audit"],
            ["Owner retention M6", "80%", "Subscription churn"],
            ["Repeat customer rate", "40%+", "CRM aggregates"],
            ["Owner GMV on platform", "North star", "Sum of order totals"],
        ],
        [65, 55, 137],
        size=8,
    )

    # 29 — Competitive position
    pdf.new_slide("Market")
    pdf.section_title("Competitive Position")
    pdf.bullets([
        "vs Aggregators (Swiggy/Zomato): zero commission, owner owns CRM, live-capture integrity",
        "vs POS (PetPooja): customer-facing discovery, quality trust layer, WhatsApp analytics",
        "Unique combination: WhatsApp-native ops + live menu + multi-kitchen cart + home-taste ratings",
        "Kitchcu occupies high owner-control quadrant WITH customer discovery — not either/or",
    ], size=10)
    pdf.stat_row([
        ("TAM India delivery GMV", "Rs 2.5L Cr+"),
        ("SAM semi-formal kitchens", "~50,000"),
        ("SOM Year 3 target", "500 kitchens"),
        ("ARR at Rs 1,499/mo", "Rs 9 Cr"),
    ])

    # 30 — GTM
    pdf.new_slide("Go-To-Market")
    pdf.section_title("Go-To-Market Strategy")
    pdf.bullets([
        "Pilot clusters: 10 kitchens in one locality — network effect for customer discovery",
        "WhatsApp-first onboarding in Hindi and regional languages",
        "Kitchen-branded PWA links shared on Instagram / WhatsApp status",
        "Monthly city chef rankings for organic PR and community buzz",
        "Aggregator escape narrative: Keep 100% of your food revenue",
        "Progressive feature unlock — simple Day 1, powerful Month 3",
    ], size=10)

    # 31 — Tech stack
    pdf.new_slide("Technology")
    pdf.section_title("Technology Stack (Scalable Foundation)")
    pdf.table(
        ["Layer", "Choice", "Rationale"],
        [
            ["Frontend", "PWA React + Vite + TS", "WhatsApp deep links, one codebase"],
            ["Backend", "Python FastAPI microservices", "Async, OpenAPI, event-driven"],
            ["Database", "PostgreSQL 16 + PostGIS", "ACID, geo queries, schema isolation"],
            ["Cache / Events", "Redis Streams", "Menu cache, event bus (Kafka Phase 4)"],
            ["Media", "MinIO / S3", "Live-capture dish photos"],
            ["Payments", "Razorpay Route", "Multi-kitchen split settlement"],
            ["Notify", "WhatsApp Cloud API + Web Push", "Dual channel reach"],
            ["Infra", "Docker -> Kubernetes", "500 kitchens today, 50K path"],
        ],
        [40, 75, 142],
        size=8,
    )

    # 32 — Vision
    pdf.new_slide("Vision")
    pdf.set_fill_color(*LIGHT_BG)
    pdf.rect(0, 18, 297, 192, "F")
    pdf.set_xy(20, 45)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*ORANGE)
    pdf.multi_cell(257, 12, "Every cloud kitchen deserves to operate like a brand")
    pdf.ln(6)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*DARK)
    pdf.bullets([
        "Data instead of guesswork — revenue, patterns, growth suggestions",
        "Trust instead of stock photos — live capture + home-taste ratings",
        "Direct relationships instead of rented customers — owner CRM",
        "Community instead of isolation — chef rankings, recipe rewards",
    ], size=12)
    pdf.ln(6)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, ascii_safe("Kitchcu is infrastructure - not the next food aggregator."))

    # 33 — Contact
    pdf.new_slide("Contact")
    pdf.set_xy(20, 55)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 16, "Kitchcu")
    pdf.ln(20)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 15)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 9, "Kitchcu cloud kitchen platform")
    pdf.ln(14)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "hello@kitchcu.in  |  kitchcu.in  |  Pilot waitlist open")
    pdf.ln(10)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(
        257, 6,
        "Full specs: CKAC-COMPLETE-PLANNING-BENCHMARK.md | CKAC-SYSTEM-BENCHMARK.md | "
        "CKAC-CPO-PRODUCT-BLUEPRINT.md",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"Generated: {output_path} ({pdf.slide_num} slides)")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "docs" / "CKAC-PITCH-DECK.pdf"
    build_pdf(out)
