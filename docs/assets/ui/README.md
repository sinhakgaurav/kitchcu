# UI reference screenshots

Referenced by [`CKAC-COMPLETE-GUIDE.md`](../../CKAC-COMPLETE-GUIDE.md) §18 (UI Catalog), the Complete Guide PDF, Userflows PDF, and the CPO Pitch Deck PDF.

Captures are desktop ≥1440px against local PWAs. JPEG `*-pdf.jpg` variants are compressed for PDF embedding.

| File | Surface / context |
|------|-------------------|
| `01-portal-home.png` (+ `-pdf.jpg`) | Portal home (`kitchcu.in` :13000) — marketing landing |
| `02-customer-home.png` (+ `-pdf.jpg`) | Customer home (`customer.kitchcu.in` :13001) — discovery |
| `03-kitchen-login.png` (+ `-pdf.jpg`) | Kitchen login — owner OTP + **AuthLoginHighlights** (zero commission, timing, delivery payer, Maps) |
| `04-owner-dashboard.png` (+ `-pdf.jpg`) | Owner dashboard — dark ops + commission advantage panel |
| `05-admin-overview.png` (+ `-pdf.jpg`) | Admin overview — Customers / Refunds / Control nav |
| `06-customer-login.png` (+ `-pdf.jpg`) | Customer login — WhatsApp OTP + highlights (ready-within, Maps, dashboard, in-range fee) |
| `07-admin-login.png` (+ `-pdf.jpg`) | Admin login — platform-control highlights |
| `08-admin-control.png` (+ `-pdf.jpg`) | Admin **Control** — feature flags, application data journeys, subscriptions |

## Regeneration notes

1. Run seed: `python scripts/seed-dev-data.py` (owners/kitchens for kitchen login demos).
2. Capture against built containers or Vite preview on ports 13000–13003.
3. Compress: open PNG → max width 1400 → JPEG quality ~72 → `*-pdf.jpg`.
4. Re-run `python scripts/generate_complete_guide_pdf.py` (and pitch / userflows generators).
