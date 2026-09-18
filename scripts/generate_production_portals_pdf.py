#!/usr/bin/env python3
"""Generate Production Portals, Credentials & Feature QA PDF.

Source: docs/PRODUCTION-PORTALS-CREDENTIALS-QA.md
"""

from pathlib import Path

from pdf_guide import GuidePDF

GUIDE_VERSION = "1.4"
GUIDE_DATE = "September 2026"
OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "PRODUCTION-PORTALS-CREDENTIALS-QA.pdf"


def build() -> GuidePDF:
    pdf = GuidePDF(
        title="KitchCu Production Portals & Feature QA",
        version=GUIDE_VERSION,
        date=GUIDE_DATE,
    )

    pdf.cover(
        subtitle="Portal links · credentials policy · feature ownership · test steps",
        audience="Audience: CEO, CPO, CTO, QA, Ops, Support",
        lenses=[
            "Portals — kitchcu.com surfaces and who uses each",
            "Credentials — demo vs production (never commit prod secrets)",
            "QA — feature responsibility + Must test steps",
        ],
        bullets=[
            "Production: kitchcu.com, customer / kitchen / admin / api.kitchcu.com",
            "Three store apps: kitchCU - customers / kitchen owner / admin",
            "Demo logins for local QA including sales@kitchcu.dev; production admin@kitchcu.com",
            "Weekly QA cohort + GCP bulk-seed.sh / systemd timer at /opt/ckac",
            "Cities presence: Delhi NCR, UP belt, Dehradun, Mumbai + coming soon",
            "F01-F48 condensed matrix with test steps",
        ],
    )

    pdf.toc(
        [
            (
                "PART 0 — Portals & Access",
                [
                    "1. Production portal URLs",
                    "2. Credentials policy",
                    "3. Cities presence",
                    "4. i18n",
                ],
            ),
            (
                "PART I — Feature QA",
                [
                    "5. Orders & intake",
                    "6. Growth, menu, ratings",
                    "7. Delivery, discovery, payments",
                    "8. Platform smoke",
                ],
            ),
        ]
    )

    pdf.lens_part("ACCESS", 0, "Portals & Credentials")

    pdf.chapter("Production portal URLs")
    pdf.table(
        ["Surface", "URL", "Persona"],
        [
            ["Marketing portal", "https://kitchcu.com", "Prospects / owners"],
            ["Customer PWA", "https://customer.kitchcu.com", "Diners"],
            ["Kitchen PWA", "https://kitchen.kitchcu.com", "Owners"],
            ["Admin console", "https://admin.kitchcu.com", "Staff + sales"],
            ["kitchCU - customers", "in.kitchcu.customer", "Diners (store)"],
            ["kitchCU - kitchen owner", "in.kitchcu.kitchen", "Owners (store)"],
            ["kitchCU - admin", "in.kitchcu.admin", "Admin + sales (store)"],
            ["API gateway", "https://api.kitchcu.com", "All clients"],
            ["Media", "https://media.kitchcu.com", "Assets"],
        ],
        widths=[40, 85, 45],
    )
    pdf.body(
        "Local: portal :13000, customer :13001, kitchen :13002, admin :13003, gateway :18000."
    )

    pdf.chapter("Credentials policy")
    pdf.section("Local / demo (QA)")
    pdf.table(
        ["Persona", "Login", "Notes"],
        [
            ["Owner", "9876543210 / OTP 123456", "CKPNQ001 + 3211-3215 / 3301-3303"],
            ["Customer", "9123456789 / OTP 123456", "Extra phones in AGENTS.md + 6/city"],
            ["Admin", "admin@kitchcu.dev / admin123456", "Dev only"],
            ["Ops/support/finance", "ops@ / support@ / finance@", "RBAC; Admin English"],
            ["Sales", "sales@ / sales.west@ / sales123456", "Role sales; Sales + Kitchens"],
        ],
        widths=[35, 75, 60],
    )
    pdf.section("Production")
    pdf.bullets(
        [
            "Super Admin: admin@kitchcu.com + ADMIN_PASSWORD from GCE / Secret Manager",
            "Do NOT use admin@kitchcu.dev on production",
            "OTP 123456 is refused when APP_ENV=production",
            "Razorpay / WhatsApp / OAuth secrets via Admin Control -> API Keys (masked)",
            "Never commit production passwords or live API secrets",
        ]
    )
    pdf.section("How to hit login-required APIs")
    pdf.bullets(
        [
            "Swagger: localhost:18000/docs (prod https://api.kitchcu.com/docs)",
            "Swagger Authorize: OAuth2Password POST /api/v1/auth/token (admin email+password or owner/customer phone+OTP) or HTTPBearer JWT",
            "Public operations have no padlock — leftover tokens are not sent on Try it out",
            "Login-hint prints username/password only when APP_ENV is development/test or ADMIN_LOGIN_REVEAL_PASSWORD=1",
            "Owner JWT must be type=owner — docs/API.md 1.1-1.2",
        ]
    )

    pdf.chapter("Cities presence")
    pdf.bullets(
        [
            "Live: Pune, Mumbai, Delhi, Gurugram, Noida, Lucknow, Kanpur, Prayagraj, Varanasi, Jhansi, Dehradun",
            "Coming soon: Bengaluru, Hyderabad, Chennai, Kolkata",
            "Shown on portal home, kitchen landing (services), customer discovery (#cities)",
            "Seed: DEMO_KITCHENS_CITIES via seed-dev-data / seed-all.ps1",
        ]
    )

    pdf.chapter("Multilingual")
    pdf.bullets(
        [
            "Locales: en hi mr ta te kn ml bn gu pa bho mai",
            "Parity: python scripts/check-i18n-locale-parity.py",
            "Sync: python scripts/sync-i18n-missing-keys.py",
            "Admin UI stays English by policy",
        ]
    )

    pdf.lens_part("QA", 1, "Feature Responsibility & Tests")

    pdf.chapter("Orders & intake (F01-F06)")
    pdf.table(
        ["ID", "Responsible for", "Test steps"],
        [
            ["F01-F02", "WA / message -> draft", "Draft appears; confirm creates order"],
            ["F03", "Manual / walk-in order", "New order -> Active tab"],
            ["F04", "Lifecycle statuses", "Advance received->delivered; C track updates"],
            ["F05", "History", "O All + C My orders"],
            ["F06", "Multi-kitchen cart", "2 kitchens -> one checkout -> sub-orders"],
        ],
        widths=[25, 55, 90],
    )

    pdf.chapter("Growth, menu, ratings")
    pdf.table(
        ["ID", "Responsible for", "Test steps"],
        [
            ["F07-F12", "Reports / tips / golden days", "Reports KPIs; pin golden recipe"],
            ["F13-F15", "Live menu & categories", "Add dish with times; category filter"],
            ["F19/F19b", "Stock + bulk prep", "Accept deducts; prep batch prepared"],
            ["F16-F18", "Home-taste ratings", "Deliver -> rate -> aggregate"],
            ["F21-F24", "Learn / trials / ranks", "Learning nav; city rankings"],
            ["F39", "Daily menu WA", "Template / daily menu send path"],
        ],
        widths=[25, 55, 90],
    )

    pdf.chapter("Delivery, discovery, payments, live")
    pdf.table(
        ["ID", "Responsible for", "Test steps"],
        [
            ["F27-F31", "Radius, fee, track, ETA", "Quote at checkout; track link"],
            ["F32", "Discovery + cities", "Search; #cities Live chips"],
            ["F33-F38", "Reorder / plans / CRM", "Reorder; coupon; CRM list"],
            ["F42-F44", "Pay + split", "Checkout intent; multi-kitchen settle"],
            ["Refunds", "UPI/bank payout", "C Account UPI; O refund status"],
            ["F45-F48", "Notify + live stream", "Status notify; Go live / watch"],
            ["P52-P54", "Diet / calories / Healthy", "Report filter; Control kcal cap"],
            ["P55", "Store apps + sales", "sales@ onboard; Train 8 steps; three listings"],
            ["P56", "Owner Today OS", "Do this now + live board; open=true&limit=50"],
        ],
        widths=[25, 55, 90],
    )

    pdf.chapter("Platform smoke (production)")
    pdf.bullets(
        [
            "GET https://api.kitchcu.com/health/ready",
            "Open kitchcu.com, customer, kitchen, admin -> HTTP 200",
            "Admin login with production credentials only",
            "Customer #cities section visible; language switcher works",
            "Confirm APP_ENV=production rejects OTP 123456",
            "Store apps (when listed): three Play/App names kitchCU - customers / kitchen owner / admin",
        ]
    )

    pdf.chapter("Source of truth")
    pdf.body(
        "Markdown: docs/PRODUCTION-PORTALS-CREDENTIALS-QA.md. "
        "Regenerate: python scripts/generate_production_portals_pdf.py. "
        "Deep acceptance: CKAC-COMPLETE-PLANNING-BENCHMARK.md. "
        "Deploy: DEPLOYMENT-GCP.md."
    )

    return pdf


def main() -> None:
    pdf = build()
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
