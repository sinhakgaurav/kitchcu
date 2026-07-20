#!/usr/bin/env python3
"""Generate KitchCu QA Instruction Pack PDF.

Source of truth: docs/QA-INSTRUCTION-PACK.md
Layout: scripts/pdf_guide.py (GuidePDF) — same pattern as userflows / complete guide.
"""

from pathlib import Path

from pdf_guide import GuidePDF

GUIDE_VERSION = "1.0"
GUIDE_DATE = "July 2026"
OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "QA-INSTRUCTION-PACK.pdf"


def build() -> GuidePDF:
    pdf = GuidePDF(
        title="KitchCu QA Instruction Pack",
        version=GUIDE_VERSION,
        date=GUIDE_DATE,
    )

    pdf.cover(
        subtitle="QA Instruction Pack — Smoke, Lists/UI, F19b Stock & Bulk Prep",
        audience="Audience: QA Lead, Engineering, CPO release sign-off",
        lenses=[
            "Product — clear owner/customer/admin journeys and expected screens",
            "Engineering — gateway routes, stock deduct timing, automated test hooks",
            "QA — Must/Should cases, defect template, Go / No-Go sign-off",
        ],
        bullets=[
            "Local Docker + optional GCP smoke credentials and ports",
            "Owner list toolbars: search, sort, filter chips (Orders, Menu, Ingredients,",
            "Bulk prep, CRM, Coupons) + header/dropdown/layout polish checks",
            "F19/F19b: pantry, recipes, deduct modes, mark prepared, Ready-time stock",
            "Security, correlation IDs, tenant isolation, pytest focus commands",
        ],
    )

    pdf.toc(
        [
            (
                "PART 0 — Setup",
                [
                    "0. How to use",
                    "1. Environments, ports, credentials",
                    "2. Smoke suite (blocking)",
                ],
            ),
            (
                "PART I — Owner UI",
                [
                    "3. Headers, listing toolbars, dropdowns, panels",
                    "4. Orders / Menu / Ingredients / Bulk prep / CRM / Coupons",
                ],
            ),
            (
                "PART II — Stock & Ops",
                [
                    "5. F19 / F19b Ingredients + Bulk prep",
                    "6. Order lifecycle vs stock deduct",
                    "7. Cross-persona + security",
                ],
            ),
            (
                "PART III — Close",
                [
                    "8. Automated tests",
                    "9. Defect template + sign-off",
                    "10. Cross-references",
                ],
            ),
        ]
    )

    # ── Setup ────────────────────────────────────────────────────────────
    pdf.lens_part("SETUP", 0, "How to Run QA")

    pdf.chapter("How to use this pack")
    pdf.bullets(
        [
            "Run Setup once per environment.",
            "Execute Smoke (Must) before deep QA — fail stops the run.",
            "Mark each case Pass / Fail / Blocked.",
            "Pass rule: every Must case Pass; Should may Fail only with waiver.",
            "Source markdown: docs/QA-INSTRUCTION-PACK.md — keep PDF in sync.",
        ]
    )

    pdf.chapter("Environments & credentials")
    pdf.section("Local stack")
    pdf.table(
        ["Item", "Value"],
        [
            ["Start", "docker compose up -d"],
            ["Seed", ".\\scripts\\seed-all.ps1"],
            ["Backend tests", ".\\scripts\\run-tests.ps1"],
            ["Portal", "http://localhost:13000"],
            ["Customer", "http://localhost:13001"],
            ["Kitchen (owner)", "http://localhost:13002"],
            ["Admin", "http://localhost:13003"],
            ["Gateway", "http://localhost:18000"],
        ],
        widths=[45, 125],
    )
    pdf.body(
        "After kitchen-web rebuilds: hard-refresh or unregister the PWA service worker "
        "if the UI looks stale or black."
    )

    pdf.section("Demo credentials")
    pdf.table(
        ["Persona", "Login", "Notes"],
        [
            ["Owner", "9876543210 / OTP 123456", "Kitchen CKPNQ001"],
            ["Customer", "9123456789 / OTP 123456", "See AGENTS.md for more"],
            ["Admin", "admin@kitchcu.dev / admin123456", "Platform JWT only"],
        ],
        widths=[35, 70, 65],
    )

    pdf.chapter("Smoke suite (Must — ~15 min)")
    pdf.table(
        ["ID", "Step", "Expected"],
        [
            ["S1", "Gateway /health/live + /ready", "200"],
            ["S2", "Kitchen OTP login -> Overview", "Hero + kitchen; no blank screen"],
            ["S3", "Customer OTP login -> home", "Discovery/menu loads"],
            ["S4", "Admin login -> overview", "Dashboard loads"],
            ["S5", "Portal home", "Brand hero; no crash"],
            ["S6", "Gateway /docs or portal /openapi", "Schema loads"],
        ],
        widths=[18, 72, 80],
    )
    pdf.body("Fail any of S1-S4 -> stop deep QA; fix infra first.")

    # ── Owner UI ─────────────────────────────────────────────────────────
    pdf.lens_part("OWNER UI", 1, "Headers, Lists, Filters, Dropdowns")

    pdf.chapter("Home / Overview header")
    pdf.table(
        ["ID", "Check", "Expected"],
        [
            ["H1", "Hero layout", "CTAs top-right on same row; not button under empty column"],
            ["H2", "Pills / meta", "Readable; no overflow clip"],
            ["H3", "Recent orders", "Clickable rows; status chips coherent"],
        ],
        widths=[18, 40, 112],
    )

    pdf.chapter("Listing toolbar coverage")
    pdf.body(
        "For each page: toolbar visible; search filters; sort reorders; chips toggle; "
        "result count updates."
    )
    pdf.table(
        ["ID", "Page", "Route", "Extra"],
        [
            ["L1", "Orders", "/dashboard/orders", "Drafts tab also sorts"],
            ["L2", "Menu", "/dashboard/menu", "Highlight + diet chips"],
            ["L3", "Ingredients", "/dashboard/ingredients", "Low stock chip"],
            ["L4", "Bulk prep", "/dashboard/prep", "Open / Prepared chips"],
            ["L5", "CRM", "/dashboard/crm", "VIP / Repeat / Tagged"],
            ["L6", "Coupons", "/dashboard/coupons", "Active / Inactive"],
        ],
        widths=[16, 32, 62, 60],
    )

    pdf.chapter("Layout & dropdown CSS")
    pdf.table(
        ["ID", "Check", "Expected"],
        [
            ["U1", "Panel width", "Full board width; not ~560px stub for list editors"],
            ["U2", "Selects", "Chevron + theme fill (Templates, Tiffin, Coupons, Sort)"],
            ["U3", "Tables", "Aligned columns; no nested card-in-card shadow"],
            ["U4", "Recipe cards", "Label above control; compact Remove button"],
        ],
        widths=[18, 35, 117],
    )

    # ── Stock ────────────────────────────────────────────────────────────
    pdf.lens_part("STOCK & OPS", 2, "F19 / F19b + Lifecycle")

    pdf.chapter("Ingredients mapper (F19)")
    pdf.table(
        ["ID", "Step", "Expected"],
        [
            ["I1", "Open Ingredients", "4-col pantry form; Add works"],
            ["I2", "Adjust +100 / -10", "Stock updates; no 404"],
            ["I3", "Save recipe + prep steps", "Persists after reload"],
            ["I4", "Low-stock chip", "Only low items shown"],
        ],
        widths=[18, 55, 97],
    )

    pdf.chapter("Bulk prep + deduct modes (F19b)")
    pdf.table(
        ["ID", "Step", "Expected"],
        [
            ["B1", "Open Bulk prep", "Mode buttons; no Not Found"],
            ["B2", "Order Ready mode", "Orders deduct on Ready"],
            ["B3", "Create combo batch", "Batch + ingredient lines"],
            ["B4", "Edit qty + save", "Totals persist"],
            ["B5", "Mark prepared", "Status prepared; stock drops"],
            ["B6", "Bulk prep only mode", "Orders do NOT deduct on Ready"],
            ["B7", "Gateway stock/prep APIs", "200 with owner JWT (catalog)"],
        ],
        widths=[18, 50, 102],
    )

    pdf.chapter("Order lifecycle vs stock")
    pdf.table(
        ["ID", "Step", "Expected"],
        [
            ["O1", "Place order (mapped dish)", "status received"],
            ["O2", "Accept", "Stock unchanged; Porter may book"],
            ["O3", "Mark Ready (order_ready)", "Stock deducts once"],
            ["O4", "Further status changes", "No double deduct"],
            ["O5", "Ready under prep_batch_only", "No order deduct"],
        ],
        widths=[18, 55, 97],
    )

    pdf.chapter("Cross-persona + security")
    pdf.table(
        ["ID", "Check", "Expected"],
        [
            ["R1", "Customer checkout", "Order reaches owner inbox"],
            ["R5", "Tenant isolation", "No cross-kitchen CRM/stock data"],
            ["X1", "Owner JWT on admin APIs", "Rejected"],
            ["X2", "Logs", "No OTP / full phone / tokens"],
            ["X3", "Correlation ID", "Forwarded when sent"],
            ["X4", "Public /internal/*", "Gateway 404"],
        ],
        widths=[18, 55, 97],
    )

    # ── Close ────────────────────────────────────────────────────────────
    pdf.lens_part("CLOSE", 3, "Automation, Defects, Sign-off")

    pdf.chapter("Automated tests")
    pdf.body("After backend changes run:")
    pdf.mono(".\\scripts\\run-tests.ps1")
    pdf.body("Focused F19b:")
    pdf.mono(
        "cd services/catalog\n"
        "python -m pytest tests/test_prep_batches.py -q\n"
        "cd ../order\n"
        "python -m pytest tests/test_stock_deduct_on_ready.py -q\n"
        "cd ../gateway\n"
        "python -m pytest tests/test_gateway.py::test_resolve_service_url_catalog -q"
    )

    pdf.chapter("Defect report template")
    pdf.mono(
        "Title:\n"
        "Environment: local | GCP\n"
        "Surface: portal | customer | kitchen | admin | API\n"
        "Severity: S1 blocker | S2 major | S3 minor | S4 polish\n"
        "Steps:\n"
        "1.\n"
        "2.\n"
        "Expected:\n"
        "Actual:\n"
        "Screenshot / correlation ID:\n"
        "Workaround:"
    )

    pdf.chapter("Sign-off")
    pdf.table(
        ["Role", "Name", "Date", "Go / No-Go", "Notes"],
        [
            ["QA Lead", "", "", "", ""],
            ["CTO / eng", "", "", "", ""],
            ["CPO", "", "", "", ""],
        ],
        widths=[32, 35, 30, 30, 43],
    )
    pdf.body(
        "Go criteria: Smoke Pass; Owner list/UI Must Pass; F19b Must Pass; "
        "security Must Pass; automated tests green for touched services."
    )

    pdf.chapter("Cross-references")
    pdf.bullets(
        [
            "docs/QA-INSTRUCTION-PACK.md — living checklist (this PDF companion)",
            "docs/CKAC-USERFLOWS.md — Flow 8b Ingredients + Bulk prep",
            "docs/F19-INGREDIENTS-DESIGN.md + docs/design/F19B-...-DESIGN.md",
            "docs/CKAC-COMPLETE-PLANNING-BENCHMARK.md — F01-F48 acceptance",
            "docs/ADVANCEMENT-TRACKER.md — release board",
            "AGENTS.md — demo phones, ports, conventions",
        ]
    )

    pdf.chapter("Document control")
    pdf.table(
        ["Field", "Value"],
        [
            ["Version", GUIDE_VERSION],
            ["Date", GUIDE_DATE],
            ["Markdown", "docs/QA-INSTRUCTION-PACK.md"],
            ["Regenerate", "python scripts/generate_qa_instruction_pdf.py"],
        ],
        widths=[40, 130],
    )

    return pdf


def main() -> None:
    pdf = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
