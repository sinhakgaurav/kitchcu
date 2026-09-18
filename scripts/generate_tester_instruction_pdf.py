#!/usr/bin/env python3
"""Generate KitchCu Tester Instruction Pack PDF.

Source of truth: docs/TESTER-INSTRUCTION-PACK.md
Layout: scripts/pdf_guide.py (GuidePDF).
"""

from pathlib import Path

from pdf_guide import GuidePDF

GUIDE_VERSION = "1.2"
GUIDE_DATE = "September 2026"
OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "TESTER-INSTRUCTION-PACK.pdf"


def build() -> GuidePDF:
    pdf = GuidePDF(
        title="KitchCu Tester Instruction Pack",
        version=GUIDE_VERSION,
        date=GUIDE_DATE,
    )

    pdf.cover(
        subtitle="Tester Instruction Pack — Numbered UI and API steps",
        audience="Audience: QA testers, release sign-off, founders doing a full pass",
        lenses=[
            "UI — every click on portal, customer, kitchen, Super Admin, and Sales",
            "API — Swagger Authorize, public vs padlock, owner/customer/admin/sales calls",
            "QA — Must vs Should, defect template, Go / No-Go",
        ],
        bullets=[
            "Local Docker URLs and demo OTP 123456 (no SMS is sent)",
            "Production *.kitchcu.com extras — real OTP, admin@kitchcu.com only",
            "Six-month seed checks: Reports, Orders 90/180d, CRM, GST years",
            "Customer: discovery, first-run tips, cart, checkout, track, rate",
            "Owner: orders lifecycle, F19/F19b stock, tenant isolation, first-run tips",
            "Admin: every top tab + kitchen Train; Sales onboard 8-step playbook",
            "Store apps: kitchCU - customers / kitchen owner / admin (three ids)",
            "Swagger: OAuth2Password POST /api/v1/auth/token; sales 403 on /admin/stats",
            "Source markdown: docs/TESTER-INSTRUCTION-PACK.md",
        ],
    )

    pdf.toc(
        [
            (
                "PART 0 — How to test",
                [
                    "0. Session rules, Pass/Fail, out of scope",
                    "1. Lab setup, URLs, credentials, seed signals",
                    "2. Smoke (blocking, ~15 min)",
                ],
            ),
            (
                "PART I — UI testing",
                [
                    "3. Marketing portal :13000",
                    "4. Customer PWA :13001",
                    "5. Kitchen / owner PWA :13002",
                    "6. Super Admin :13003",
                    "6.4 Sales onboard + Train; 6.5 store apps",
                ],
            ),
            (
                "PART II — API testing",
                [
                    "7. Swagger contract, Authorize, padlocks",
                    "8. Public / owner / customer / admin call sequences",
                    "9. Negatives + audit-api-auth.py",
                ],
            ),
            (
                "PART III — Close",
                [
                    "10. Cross-cutting cases and production extras",
                    "11. Defect template + sign-off",
                ],
            ),
        ]
    )

    # ── How to test ──────────────────────────────────────────────────────
    pdf.lens_part("SETUP", 0, "How to run a test session")

    pdf.chapter("Session rules")
    pdf.body(
        "This pack is the how-to-click / how-to-call book. The short Must/Should "
        "checklist lives in QA-INSTRUCTION-PACK.md. Use this document when you "
        "need every numbered step."
    )
    pdf.bullets(
        [
            "Pick one environment (local Docker OR production). Never mix credentials.",
            "Confirm the stack (section 1). If smoke fails, stop — do not deep-test.",
            "Work persona by persona: Portal -> Customer -> Kitchen -> Admin -> Sales -> store shells -> Swagger.",
            "Mark every case Pass / Fail / Blocked. Write the URL, what you typed, what you saw.",
            "On Fail use the defect template. Include screenshot and X-Correlation-ID.",
            "Pass rule: every Must case Pass. Should may Fail only with a written waiver.",
            "Chrome or Edge. After a frontend rebuild, Ctrl+Shift+R or unregister the PWA worker.",
        ]
    )
    pdf.section("Product rules testers must not fail")
    pdf.bullets(
        [
            "KitchCu is owner-subscription SaaS. There is NO per-order food commission. "
            "Do not file missing commission % as a bug.",
            "Out of scope: restaurant POS, dine-in, tables, waiters, KDS, bar, hotel.",
        ]
    )

    pdf.chapter("Lab URLs")
    pdf.table(
        ["Surface", "Local URL"],
        [
            ["Marketing portal", "http://localhost:13000"],
            ["Customer PWA", "http://localhost:13001"],
            ["Kitchen (owner) PWA", "http://localhost:13002"],
            ["Super Admin", "http://localhost:13003"],
            ["kitchCU - customers (store)", "in.kitchcu.customer -> :13001"],
            ["kitchCU - kitchen owner (store)", "in.kitchcu.kitchen -> :13002"],
            ["kitchCU - admin (store)", "in.kitchcu.admin -> :13003"],
            ["API gateway", "http://localhost:18000"],
            ["Swagger", "http://localhost:18000/docs"],
            ["ReDoc", "http://localhost:18000/redoc"],
            ["Portal OpenAPI", "http://localhost:13000/openapi"],
        ],
        widths=[55, 115],
    )
    pdf.body(
        "Production substitutes: https://kitchcu.com, customer/kitchen/admin.kitchcu.com, "
        "https://api.kitchcu.com/docs. Testers never call service ports 18001-18012."
    )

    pdf.chapter("Confirm the stack")
    pdf.bullets(
        [
            "1. Open /health/live on the gateway — HTTP 200.",
            "2. Open /health/ready — HTTP 200. If this fails, do not test UI.",
            "3. Open each PWA URL. Each must render (not blank/black, not connection refused).",
            "4. If a PWA is down, ask engineering to start Vite / docker compose up -d.",
        ]
    )

    pdf.chapter("Demo credentials (local / demo only)")
    pdf.table(
        ["Persona", "Login", "Land on"],
        [
            ["Owner primary", "9876543210 / OTP 123456", "CKPNQ001 Sharma Home Kitchen"],
            ["Owner alt", "9876543211-13 / 123456", "Tenant-isolation kitchens"],
            ["Customer primary", "9123456789 / 123456", "Priya — discovery home"],
            ["Customer repeat", "9123456780 / 123456", "Rahul — richer history"],
            ["Customer guest", "9988776655 / 123456", "Ananya"],
            ["Super Admin", "admin@kitchcu.dev / admin123456", "Admin Overview"],
            ["Sales (field)", "sales@kitchcu.dev / sales123456", "Admin Sales (extras seed)"],
        ],
        widths=[40, 65, 65],
    )
    pdf.body(
        "Production: admin@kitchcu.com + live ADMIN_PASSWORD. OTP 123456 is refused "
        "when APP_ENV=production. Never use the .dev email on *.kitchcu.com."
    )
    pdf.body(
        "Demo OTP banner: sign-in must say demo mode does NOT send SMS/WhatsApp — "
        "enter 123456. If the UI claims OTP sent and you wait for a phone message, "
        "that is a fail (ID-08 regression)."
    )

    pdf.chapter("Seeded data you should already see")
    pdf.body(
        "After .\\scripts\\seed-all.ps1 or $env:CKAC_BULK_MONTHS=6; python scripts/seed-bulk-data.py:"
    )
    pdf.bullets(
        [
            "CKPNQ001 has months of orders, not only today.",
            "Owner Reports offers a 6-month range; 90/180-day charts roll up to weeks/months.",
            "Owner Orders can filter 90 / 180 days and still show rows.",
            "Owner GST year options match dated invoices.",
            "CRM has more than a handful of contacts on CKPNQ001.",
            "Public dish heroes are live-capture. Drinks without a hero stay inactive.",
        ]
    )
    pdf.body(
        "If Reports look empty or CRM shows 0-2 profiles against hundreds of orders, "
        "the six-month seed was not applied — mark Blocked, not product empty state."
    )

    pdf.chapter("Smoke (Must — about 15 minutes)")
    pdf.body("Fail on S1-S4 -> stop the session.")
    pdf.table(
        ["ID", "Steps", "Expected"],
        [
            ["S1", "Gateway /health/live then /ready", "Both 200"],
            ["S2", "Kitchen login 9876543210 / 123456", "Overview; name + CKPNQ001"],
            ["S3", "Customer login 9123456789 / 123456", "Discovery home loads"],
            ["S4", "Admin admin@kitchcu.dev / admin123456", "Overview KPIs; login-hint if reveal on"],
            ["S5", "Portal :13000", "Brand hero; cities; no crash"],
            ["S6", "Gateway /docs Authorize OAuth2Password", "Public no padlock; three demo logins work"],
            ["S7", "Sales sales@kitchcu.dev / sales123456", "Nav Sales + Kitchens only; no Overview"],
            ["S8", "First-run tips C / Kitchen / Admin", "Skip / Next / Show tips; page still usable"],
        ],
        widths=[16, 78, 76],
    )

    # ── UI ───────────────────────────────────────────────────────────────
    pdf.lens_part("UI", 1, "Persona screens — click by click")

    pdf.chapter("Marketing portal (:13000) — Must")
    pdf.bullets(
        [
            "1. Open http://localhost:13000.",
            "2. Confirm the Kitchcu brand hero (cream / teal / orange — not a generic purple splash).",
            "3. Scroll Features, How it works, cities (#cities), pricing, contact / support.",
            "4. Cities Live: Pune, Mumbai, Delhi, Gurugram, Noida, Lucknow, Kanpur, "
            "Prayagraj, Varanasi, Jhansi, Dehradun. Coming soon: Bengaluru, Hyderabad, "
            "Chennai, Kolkata.",
            "5. Language switcher: English -> Hindi -> English. Nav, hero CTA, footer change then restore.",
            "6. Open /openapi (or /api-docs). Explorer loads the aggregated spec without a token.",
            "7. Open /terms, /privacy, /refund-policy, /platform-refund-policy — each has text, not 404.",
            "8. Footer / tiles to customer and kitchen hosts resolve (new tab OK).",
            "9. Support chat (if visible): options-first; raising a ticket must not crash.",
        ]
    )
    pdf.body(
        "Fail if: blank page, cities missing, Hindi does nothing, /openapi empty, legal 404."
    )

    pdf.chapter("Customer login (:13001/login)")
    pdf.bullets(
        [
            "1. Open http://localhost:13001/login.",
            "2. Confirm the demo strip: enter 123456 — no SMS is sent.",
            "3. Type 9123456789. Invalid phones (12345, 987654321011) are rejected before success.",
            "4. Request OTP. Banner still says demo — do not wait for WhatsApp.",
            "5. Enter 123456 and submit. Land on discovery home (/). Navbar shows the diner.",
            "6. Wrong OTP 000000 -> error, stay on login.",
            "7. Logout. New login must not keep another diner's cart.",
            "8. First-run tour: Skip / Next / Done. Show tips restarts it. Does not hide kitchens.",
        ]
    )

    pdf.chapter("Customer discovery, menu, cart")
    pdf.bullets(
        [
            "1. On / confirm nearby / featured kitchens and the cities strip.",
            "2. Search a dish or cuisine (paneer or thali). Wait ~1s. Results include kitchens that serve it.",
            "3. Use my location (allow permission). Far from Pune: nearest fallback with visible cards, "
            "not a blank No kitchens list.",
            "4. Open Sharma Home Kitchen / CKPNQ001 -> /kitchen/{id}/menu or /k/CKPNQ001/menu.",
            "5. Menu lists active dishes only. Drafts / no-hero drinks stay off the diner menu.",
            "6. Heroes match the dish (not a dining-room photo, not one salad on every curry).",
            "7. Add one dish, qty 1. Cart badge increments. Change qty, remove, totals update.",
            "8. Empty cart has a clear empty state. Add again and open checkout.",
        ]
    )

    pdf.chapter("Customer checkout, orders, track, rate")
    pdf.bullets(
        [
            "1. Address: Pune-area or seeded default.",
            "2. Delivery quote appears (fee >= 0). Out-of-radius denies or explains — not a silent forever-zero.",
            "3. Optional coupon: valid seeded code applies; invalid code errors, no crash.",
            "4. Choose the pay path the demo offers (dev capture / COD / UPI intent).",
            "5. Submit. Land on /orders/{id}/confirm or master-order confirm. Note the order id.",
            "6. Should (F06): add from two kitchens -> master receipt MORD-... plus sub-orders.",
            "7. My orders (/orders): loader while fetching — never a false empty page.",
            "8. True empty state has title + hint + discovery CTA.",
            "9. Open a delivered seeded order. Track /t/{token} matches owner status.",
            "10. Rate a delivered order (home-taste + quality 1-5). Undelivered cannot silently rate.",
            "11. Reorder (if present) fills the cart.",
        ]
    )

    pdf.chapter("Customer account, brand page, live, i18n")
    pdf.bullets(
        [
            "1. /account — profile / addresses / UPI payout load; save persists after reload.",
            "2. /dashboard — diner My space loads without a crash.",
            "3. Open /k/CKPNQ001 or /k/CKPNQ001/menu. Brand name matches. Public menu only.",
            "4. Should — live: /live/{sessionId} plays or honest not-live empty (no fake countdown).",
            "5. Should — i18n: switch hi. Nav and discovery headings change. Admin stays English.",
        ]
    )

    pdf.chapter("Owner landing + Overview")
    pdf.bullets(
        [
            "1. Open http://localhost:13002 — landing, not a crash.",
            "2. /login demo strip lists owner phones. OTP story matches (no fake SMS).",
            "3. Login 9876543210 / 123456. Land on /dashboard Today OS — never black.",
            "4. Kitchen context prefers CKPNQ001.",
            "5. Hero: name + code on the left; Do this now CTA + New order same row top-right.",
            "6. First-run tips: Skip / Next / Show tips. Must not block Orders.",
            "7. Do this now matches highest-priority open work. Live board = in-flight only (no 6-month dump).",
            "8. Open a live-board row -> /dashboard/orders/{id}. View all -> Orders inbox.",
        ]
    )

    pdf.chapter("Owner Orders (Must)")
    pdf.bullets(
        [
            "1. /dashboard/orders — toolbar visible: search, sort, tabs, filters.",
            "2. Search customer name or bill fragment — list shrinks; count updates.",
            "3. Sort Newest, Customer A-Z, Z-A. Drafts tab also sorts.",
            "4. Tabs Active / All / Drafts. Drafts are unconfirmed intake, not live tickets.",
            "5. Filters status / source / date. 90 days and 180 days still show CKPNQ001 history.",
            "6. Open a received or accepted order.",
            "7. Advance accepted -> preparing -> ready -> out_for_delivery -> delivered. No skip back except cancel.",
            "8. Cancel: leaves Active; appears under All / cancelled.",
            "9. New order: add a live dish + phone, place. Appears Active as received.",
            "10. Draft remap stays disabled until a matched item is chosen.",
        ]
    )

    pdf.chapter("Owner Menu + Add dish")
    pdf.bullets(
        [
            "1. Search, sort, highlight + diet chips work; count updates.",
            "2. Live dishes show a live-capture hero. No-hero drafts stay off the public menu.",
            "3. Add dish: you cannot set a gallery/stock photo as the hero without live-capture.",
            "4. Save. Appears in the owner list. Without a live hero it stays inactive.",
        ]
    )

    pdf.chapter("Owner Ingredients + Bulk prep (F19 / F19b) — Must")
    pdf.bullets(
        [
            "1. /dashboard/ingredients — pantry 4-column. Add one ingredient.",
            "2. Adjust stock +100 then -10. Number updates; no 404.",
            "3. Low stock chip hides healthy rows.",
            "4. Select a dish -> edit recipe (ingredient / qty / unit labels ABOVE controls) -> save -> reload persists.",
            "5. /dashboard/prep — modes Order Ready and Bulk prep only. No Not Found.",
            "6. Order Ready helper: orders deduct when marked Ready.",
            "7. Create combo batch (>=2 dishes, portions > 0). Table shows ingredient lines.",
            "8. Edit qty -> save. Totals persist.",
            "9. Mark prepared -> status prepared; pantry stock decreases.",
            "10. Bulk prep only: new order Ready must NOT drop stock. Only Mark prepared deducts.",
            "11. Order Ready: first Ready deducts once. Repeat Ready does not double-deduct. Accept does not deduct.",
        ]
    )

    pdf.chapter("Owner Reports, ratings, GST, payments")
    pdf.bullets(
        [
            "1. /dashboard/reports — choose 6 months. Revenue / top dishes / peak hours are not a flat zero.",
            "2. 90/180-day views roll up (not 180 unreadable daily bars). Period-over-period hides if prior window empty.",
            "3. /dashboard/ratings — aggregates or an honest empty state.",
            "4. /dashboard/gst — year selector includes seeded invoice years. Excel/PDF Should download, not 500.",
            "5. /dashboard/payment-gateway — kitchen Razorpay / Route only (not platform SaaS secrets).",
        ]
    )

    pdf.chapter("Owner CRM, coupons, tiffin, brand, other nav")
    pdf.bullets(
        [
            "1. /dashboard/crm — search; sort Spend/Orders/Name; VIP/Repeat/Tagged. CKPNQ001 must not be empty after 6-month seed.",
            "2. /dashboard/coupons — create a test code, active, save. Search + Active/Inactive chips.",
            "3. /dashboard/tiffin — combo plans need >=2 dishes; single-dish = 1.",
            "4. /dashboard/templates — themed chevron dropdowns, not a raw system control.",
            "5. /dashboard/brand — save; customer /k/CKPNQ001 matches.",
            "6. /dashboard/setup — name/address/pin stay editable. Kitchen CODE does not change.",
            "7. Growth / learning / community load (locked/empty OK; crash is a fail).",
            "8. /dashboard/stream — no publisher token dumped on screen.",
            "9. Referrals + WhatsApp kitchen phone_number_id (not Meta app secret).",
            "10. /dashboard/subscription — SaaS plan. No per-order commission line.",
        ]
    )

    pdf.chapter("Owner tenant isolation + layout (Must)")
    pdf.bullets(
        [
            "1. Log out. Log in as 9876543211.",
            "2. Orders, CRM, ingredients, prep, GST belong to THAT kitchen only — never CKPNQ001 bills.",
            "3. Log back in as 9876543210 and confirm the reverse.",
            "4. Owner panels use the full board width (not a ~560px stub).",
            "5. Sort dropdowns show chevron + theme fill.",
            "6. Table headers align. No nested card-in-card double shadow on CRM / Ingredients.",
        ]
    )

    pdf.chapter("Super Admin sign-in")
    pdf.bullets(
        [
            "1. Open http://localhost:13003.",
            "2. Username + password print / prefill only when APP_ENV is development/test "
            "OR ADMIN_LOGIN_REVEAL_PASSWORD=1. Local Docker should show them.",
            "3. Confirm links to Swagger, ReDoc, portal /openapi.",
            "4. Sign in admin@kitchcu.dev / admin123456. Overview KPIs load.",
            "5. Cleared / expired token returns to Sign in, not a broken shell.",
            "6. Admin UI stays English.",
        ]
    )

    pdf.chapter("Super Admin — walk every top tab")
    pdf.body("Open each tab, wait for load, no white-crash, then the action.")
    pdf.table(
        ["Tab", "Do this", "Expected"],
        [
            ["Overview", "Read tiles; click one", "Jumps to the matching tab"],
            ["Kitchens", "Search CKPNQ001; open workspace", "Name + immutable code"],
            ["Owners", "Search 9876543210", "Raj Sharma / CKPNQ001"],
            ["Customers", "Search 9123456789", "Profile, orders, tickets"],
            ["Orders", "Filter kitchen or customer", "Platform list; no cook-line mutate"],
            ["Refunds", "Open list + settlements", "Status chips; no 500"],
            ["Tickets", "Open one", "Assignee / priority / reply"],
            ["Packages", "View mapper", "Read-only without packages:write"],
            ["Employees", "List staff", "Write hidden without employees:write; role includes sales"],
            ["Sales", "Onboard + Train", "Kitchen code; 8-step playbook; other sales 403"],
            ["API Keys", "Open a key", "Masked after save — never full secret"],
            ["Referrals", "Settings + leads", "Loads"],
            ["Control", "Flags / journeys / calories", "Toggles persist; kcal cap; no raw secrets"],
            ["Audit", "Recent actions", "Writes appear; no OTP/token text"],
        ],
        widths=[32, 62, 76],
    )

    pdf.chapter("Super Admin — kitchen workspace (CKPNQ001)")
    pdf.table(
        ["Tab", "Check"],
        [
            ["Profile", "Address / branded summary; code cannot be edited"],
            ["Train", "8-step owner playbook; sales tick kitchens they onboarded"],
            ["WhatsApp", "Kitchen phone number id only — not Meta app secret"],
            ["Payments", "Kitchen Razorpay / Route — not platform SaaS keys"],
            ["Modules", "Per-kitchen module flags"],
            ["Package", "Assigned package + feature checklist"],
            ["Marketing", "Template / broadcast summary"],
            ["Streaming", "Session summary — no publisher token"],
            ["Orders / Care", "Recent orders + open tickets / refunds strip"],
            ["GST", "Profile / report / export paths load"],
        ],
        widths=[40, 130],
    )
    pdf.body(
        "Admin must not mutate owner menu items or cook-line status from this console."
    )

    pdf.chapter("Sales onboard + Train (P55) — Must")
    pdf.bullets(
        [
            "1. Log out of Super Admin. Sign in sales@kitchcu.dev / sales123456.",
            "2. Nav is Sales + Kitchens only. Fail if Overview, Employees, API Keys, or Control appear.",
            "3. Sales form: owner name, unused phone (e.g. 9000012345), kitchen name, address, city, pin.",
            "4. Onboard -> kitchen code CK... issued; kitchen appears in this sales book.",
            "5. Open kitchen Train. Confirm 8 steps: profile, live hero, recipe, radius, KYC, "
            "test order, WhatsApp check, owner can login alone.",
            "6. Tick profile. Count 1/8. Reload persists. Training does not block going live.",
            "7. Super Admin Employees lists role sales. Other sales JWT -> 403 on this kitchen Train.",
        ]
    )

    pdf.chapter("Store apps (P55)")
    pdf.table(
        ["Listing name", "Package / bundle", "Host"],
        [
            ["kitchCU - customers", "in.kitchcu.customer", "customer.kitchcu.com / :13001"],
            ["kitchCU - kitchen owner", "in.kitchcu.kitchen", "kitchen.kitchcu.com / :13002"],
            ["kitchCU - admin", "in.kitchcu.admin", "admin.kitchcu.com / :13003"],
        ],
        widths=[50, 50, 70],
    )
    pdf.bullets(
        [
            "Three different downloads — installing customers must not replace kitchen owner.",
            "Product logic stays in the PWAs. Play steps: apps/android/README.md (three AABs).",
            "iOS WKWebView: apps/ios/README.md. Replace TEAMID in apple-app-site-association.",
        ]
    )

    # ── API ──────────────────────────────────────────────────────────────
    pdf.lens_part("API", 2, "Swagger and gateway calls")

    pdf.chapter("Open the contract")
    pdf.bullets(
        [
            "Public clients use the gateway only: http://localhost:18000.",
            "1. Open /docs. Confirm filter box and Authorize.",
            "2. Tags (Identity: Auth, Order, Billing) have summaries.",
            "3. Open /redoc — same spec, read-only.",
            "4. Open portal /openapi — same schema for non-technical browse.",
            "5. After a gateway restart, GET /openapi.json?refresh=true if a new route is missing.",
        ]
    )

    pdf.chapter("How padlocks work")
    pdf.table(
        ["What you see", "Meaning", "What you do"],
        [
            ["No padlock", "Public (security: [])", "Try it out WITHOUT Authorize. Leftover token must not be sent"],
            ["Padlock", "JWT required", "Authorize first, then Try it out"],
            ["Optional", "Token optional", "Works anonymous; richer with a token"],
        ],
        widths=[32, 48, 90],
    )

    pdf.chapter("Authorize (before protected calls)")
    pdf.bullets(
        [
            "1. Click Authorize.",
            "2. Prefer OAuth2Password (POST /api/v1/auth/token).",
            "3. Owner: 9876543210 / 123456. Customer: 9123456789 / 123456. "
            "Admin: admin@kitchcu.dev / admin123456.",
            "4. Or paste only the JWT into HTTPBearer (Swagger adds Bearer).",
            "5. Clear the token before switching persona.",
            "401 = missing / wrong / wrong type. 403 = valid JWT but not this kitchen or RBAC denied.",
        ]
    )

    pdf.chapter("Public API steps (no token)")
    pdf.bullets(
        [
            "1. Clear Authorize so you are anonymous.",
            "2. GET /health/live -> 200. Request has no Authorization header.",
            "3. GET /health/ready -> 200.",
            "4. Public discovery / kitchen / community reads -> 200, not 401.",
            "5. GET /api/v1/community/recipes -> 200 and a list or []. Must not 500 "
            "(orphan recipes are skipped).",
            "6. Dummy UUID on a public detail route -> 404, not 500.",
        ]
    )

    pdf.chapter("Owner API steps")
    pdf.bullets(
        [
            "1. Authorize as owner 9876543210 / 123456.",
            "2. GET /api/v1/owners/me -> 200. Repeat with a customer token -> 401.",
            "3. Copy the CKPNQ001 kitchen id.",
            "4. GET /kitchens/{id}/orders?open=true&limit=50 -> 200, in-flight + lane_counts. limit=500 -> 422. History is CSV.",
            "5. Analytics / reports path -> 200; 6-month series present if seeded.",
            "6. Menu / dishes -> 200.",
            "7. CRM contacts -> 200; not 0-2 rows on CKPNQ001 after 6-month seed.",
            "8. GET .../stock-settings -> 200 (not identity 404).",
            "9. GET .../prep-batches -> 200.",
            "10. GST report/export -> 200 or honest 404/422, not 500.",
            "11. Mutate status only on a NEW manual order — do not rewrite six-month history.",
            "12. Same orders URL with another kitchen id -> 403, not 200.",
        ]
    )

    pdf.chapter("Customer API steps")
    pdf.bullets(
        [
            "1. Authorize as customer 9123456789 / 123456.",
            "2. Customer me / dashboard / orders list -> 200.",
            "3. GET /api/v1/billing/refunds/customer/me -> 200 and a JSON list ([] OK). Must not 500.",
            "4. Owner-only route (GET /owners/me or kitchen CRM) -> 401.",
            "5. Random UUID on an owned resource -> 404.",
        ]
    )

    pdf.chapter("Admin API steps")
    pdf.bullets(
        [
            "1. Authorize as admin admin@kitchcu.dev / admin123456.",
            "2. GET /api/v1/admin/me -> 200 + allowed_tabs.",
            "3. GET /admin/stats -> 200.",
            "4. GET /admin/kitchens?q=CKPNQ001 -> Sharma Home Kitchen.",
            "5. GET /admin/customers?q=9123456789 -> 200.",
            "6. GET /admin/orders, /admin/refunds, /admin/tickets -> 200.",
            "7. GET /admin/auth/login-hint -> password present locally when reveal=1.",
            "8. Repeat one admin GET with the owner token -> 401.",
            "9. GET /api/v1/internal/anything via gateway -> 404 (never proxied).",
            "10. Sales: Authorize sales@kitchcu.dev / sales123456.",
            "11. GET /admin/me -> allowed_tabs sales + kitchens. GET /admin/stats -> 403.",
            "12. POST /admin/sales/onboard -> 201 kitchen code. GET/PATCH .../training 8 steps.",
        ]
    )

    pdf.chapter("Negative / security API (Must)")
    pdf.bullets(
        [
            "1. Protected route, no Authorize -> 401.",
            "2. Garbage Bearer abc -> 401.",
            "3. Customer token on owner route -> 401.",
            "4. Owner token on admin route -> 401.",
            "5. Owner token on another kitchen write -> 403.",
            "6. Do not send unsigned production-like webhooks. Local WhatsApp POST may "
            "accept unsigned bodies; production must fail closed.",
        ]
    )

    pdf.chapter("Automated auth audit (Should)")
    pdf.mono("python scripts/audit-api-auth.py")
    pdf.body(
        "Expect 0 FAIL. INFO rows on webhooks are allowed. Any FAIL is a release blocker."
    )
    pdf.body(
        "Do NOT run .\\scripts\\run-tests.ps1 or identity/community/billing pytest on a "
        "shared demo DB if you must keep the 6-month seed — those suites TRUNCATE "
        "kitchens, orders, and billing."
    )

    # ── Close ────────────────────────────────────────────────────────────
    pdf.lens_part("CLOSE", 3, "Cross-cutting, defects, sign-off")

    pdf.chapter("Cross-cutting cases")
    pdf.table(
        ["ID", "Steps", "Expected"],
        [
            ["X1", "Owner JWT vs /admin/stats", "401"],
            ["X2", "Logs during OTP login", "No OTP, token, or full phone dump"],
            ["X3", "Send X-Correlation-ID: qa-demo-1", "Same id on the response"],
            ["X4", "Owner A CRM vs owner B", "No shared rows"],
            ["X5", "Portal + customer en/hi", "Chrome changes; admin stays EN"],
            ["X6", "Cities on 3 PWAs", "Same live / coming-soon set"],
            ["X7", "Customer vs owner menu", "Public heroes match; drafts hidden"],
            ["X8", "Subscription + reports", "No platform food-commission %"],
            ["X9", "Sales JWT vs /admin/stats", "403"],
            ["X10", "C/O/A first-run overlay", "Skip or complete; Show tips restarts"],
        ],
        widths=[16, 78, 76],
    )

    pdf.chapter("Production extras (*.kitchcu.com)")
    pdf.bullets(
        [
            "1. GET https://api.kitchcu.com/health/ready -> 200.",
            "2. Open portal, www, customer, kitchen, admin hosts.",
            "3. Admin login is admin@kitchcu.com only.",
            "4. OTP 123456 is rejected.",
            "5. Do not paste production API secrets into tickets or chat.",
            "6. Prefer weekly QA cohort phones (7YYWW... owners, 8YYWW... customers) "
            "if ops provided them — PRODUCTION-PORTALS-CREDENTIALS-QA.md.",
            "7. Store listings (when published): three Play URLs for in.kitchcu.customer / "
            ".kitchen / .admin — not one combined APK.",
        ]
    )

    pdf.chapter("Defect template")
    pdf.mono(
        "Title:\n"
        "Environment: local | production\n"
        "Surface: portal | customer | kitchen | admin | Swagger | other API\n"
        "Case ID: (e.g. Owner Orders step 7)\n"
        "Severity: S1 blocker | S2 major | S3 minor | S4 polish\n"
        "Steps:\n1.\n2.\n3.\n"
        "Expected:\nActual:\nURL:\n"
        "Request (method + path):\nStatus / body:\n"
        "X-Correlation-ID:\nScreenshot:\nWorkaround:"
    )

    pdf.chapter("Sign-off")
    pdf.table(
        ["Role", "Verdict"],
        [
            ["Tester", "Pass / Fail"],
            ["QA Lead", "Go / No-Go"],
            ["Eng / CTO", "Notes"],
        ],
        widths=[50, 120],
    )
    pdf.body(
        "Go criteria: smoke Pass (incl. S7 sales + S8 tours); customer Must Pass; owner Must "
        "(orders, stock, isolation, reports seed) Pass; admin tabs + Sales/Train Pass; "
        "API public/owner/customer/admin/sales + negatives Pass; X1-X4 and X8-X10 Pass."
    )

    pdf.chapter("Cross-references")
    pdf.table(
        ["Need", "Doc"],
        [
            ["Short checklist", "docs/QA-INSTRUCTION-PACK.md"],
            ["Journeys + events", "docs/CKAC-USERFLOWS.md"],
            ["Auth / OpenAPI", "docs/API.md sections 1.1-1.2"],
            ["Prod URLs + matrix", "docs/PRODUCTION-PORTALS-CREDENTIALS-QA.md"],
            ["Seed + credentials", "docs/ADVANCEMENT-TRACKER.md"],
            ["Encyclopedia", "docs/CKAC-COMPLETE-GUIDE.md v3.2.8"],
            ["Store shells", "apps/android/README.md and apps/ios/README.md"],
        ],
        widths=[50, 120],
    )

    pdf.chapter("Document control")
    pdf.body(
        "v1.0 12 September 2026 — first tester pack: numbered UI steps for all "
        "four surfaces plus Swagger/API sequences, 6-month seed checks, and "
        "P47 Authorize / padlock rules."
    )
    pdf.quote(
        "KitchCu Tester Instruction Pack v1.0 — Confidential — September 2026."
    )

    return pdf


def main():
    pdf = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
