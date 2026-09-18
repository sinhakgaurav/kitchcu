/** English how-to copy for Super Admin (ops UI stays English). */

export type AdminGuide = { title: string; steps: string[] };

export const ADMIN_TAB_GUIDES: Record<string, AdminGuide> = {
  overview: {
    title: "What you can do — Overview",
    steps: [
      "Read KPI tiles: owners, kitchens, diners, orders, open refunds, captured payments.",
      "Click an attention card (tickets, refunds, suspended kitchens, trials) to jump to that tab.",
      "This screen is pulse only — you never accept, mark-ready, or rewrite a cook-line ticket from here.",
      "Hire field staff under Employees (role sales) so they onboard kitchens without seeing API Keys or Control.",
      "Use Show tips (top right) to replay the full Super Admin walkthrough anytime.",
    ],
  },
  sales: {
    title: "What you can do — Sales",
    steps: [
      "Enter owner name, unused phone, kitchen name, street, city, and the map pin that matches the stall.",
      "Submit Onboard — a kitchen code (CK…) is issued. The owner logs in on the Kitchen app with that phone.",
      "Open the kitchen Train tab and tick the 8-step playbook while they do the work (live hero, recipe, radius, KYC, test order, WhatsApp, solo login).",
      "Training ticks do not block going live. You cannot open Control, API Keys, or another rep’s kitchens.",
    ],
  },
  kitchens: {
    title: "What you can do — Kitchens list",
    steps: [
      "Search by code (e.g. CKPNQ001) or name. Filter Active / Suspended. Open a row to enter that kitchen’s workspace.",
      "List chips: WA, Pay, Brand, KYC, Health — they are status, not buttons that mutate cook-line.",
      "Inside the workspace, each inner tab (Profile, Train, KYC, …) has its own What you can do list.",
      "The kitchen code is immutable. Never try to rename CKPNQ001 to another code.",
      "Sales logins only see kitchens they onboarded. Super Admin sees every tenant.",
    ],
  },
  owners: {
    title: "What you can do — Owners",
    steps: [
      "Search by phone (e.g. 9876543210). Open the owner to see linked kitchens.",
      "Force a subscription tier when billing glitches (permission owners:write).",
      "Do not use this list to change a kitchen’s public code.",
    ],
  },
  customers: {
    title: "What you can do — Customers",
    steps: [
      "Search by phone. Open a diner for addresses, recent orders, tickets, photos, payout profile.",
      "Suspend or clear password when support needs a lock. Diet-report flags show here — never the checkup file.",
      "Deep-link to Orders or Tickets for that diner. You do not impersonate their customer JWT.",
    ],
  },
  orders: {
    title: "What you can do — Platform orders",
    steps: [
      "Filter by kitchen or diner. This is a read/ops feed — not the owner cook board.",
      "You cannot mark ready, accept, or rewrite line items. Those stay on the Kitchen app.",
      "Use Care on the kitchen workspace for tickets/refunds tied to an order.",
    ],
  },
  refunds: {
    title: "What you can do — Refunds & money",
    steps: [
      "Open gateway vs direct-transfer refunds. Escalate, complete, or fail with a reason.",
      "Settlements list Route splits per kitchen. Status chips must load without a 500.",
      "Never paste production Razorpay secrets into this screen.",
    ],
  },
  tickets: {
    title: "What you can do — Tickets",
    steps: [
      "Triage: status, priority, assignee, resolution note.",
      "Use Open kitchen / Open refunds to jump to the related workspace.",
      "Replies notify the requester. Admin JWT still cannot mutate owner menu routes.",
    ],
  },
  packages: {
    title: "What you can do — Packages",
    steps: [
      "Map platform features → packages → owner/customer plans.",
      "Assign a package from the kitchen workspace Package tab (needs packages:write).",
      "Read-only staff can view the mapper but not save.",
    ],
  },
  employees: {
    title: "What you can do — Employees",
    steps: [
      "Create platform staff. Roles: superadmin, ops, support, finance, sales.",
      "Role sales grants Sales + Kitchens only — they never see Overview KPIs, API Keys, or Control.",
      "Deactivate rather than delete when someone leaves. Writes need employees:write.",
    ],
  },
  "api-keys": {
    title: "What you can do — API Keys",
    steps: [
      "Platform Meta / SaaS Razorpay / LiveKit / Maps / OAuth live here — not on kitchen forms.",
      "After save the value is masked. Opening a key must never show the full secret again.",
      "Kitchen WhatsApp phone_number_id and kitchen Razorpay stay on that kitchen’s workspace.",
    ],
  },
  referrals: {
    title: "What you can do — Referrals",
    steps: [
      "Set dual reward amounts (customer ↔ kitchen).",
      "Work the lead queue by direction and status.",
      "Settings save needs write permission; leads are platform-scoped.",
    ],
  },
  control: {
    title: "What you can do — Control",
    steps: [
      "Toggle platform feature flags (sales_onboarding, dish_calories, dish_healthy_tag, customer_diet_report, streaming, …).",
      "Dish calories & Healthy: turn Calories / Healthy tag on or off. Save max kcal cap (default 500) and health-score floor (default 65).",
      "A dish shows Healthy only when the recipe map is complete, plate kcal ≤ this cap, and score ≥ the floor — owners cannot pin it by hand.",
      "Journeys and subscription overrides live here. Kill a module globally, then use kitchen Modules for one tenant.",
      "No raw secrets on this tab — Meta / Razorpay / LiveKit keys stay under API Keys.",
    ],
  },
  audit: {
    title: "What you can do — Audit",
    steps: [
      "Filter who changed kitchens, flags, keys, employees, and subscriptions.",
      "Sensitive writes must appear. OTP, tokens, and full phones must not appear in the log text.",
    ],
  },
};

/** Per inner-tab copy when a kitchen workspace is open. */
export const ADMIN_KITCHEN_PANEL_GUIDES: Record<string, AdminGuide> = {
  profile: {
    title: "Workspace — Profile",
    steps: [
      "Read kitchen name, city, owner, and the immutable code (CK…). Activate or Suspend from the header — that is the live/offline switch.",
      "Edit street, city, pin, and map lat/lng so discovery distance is honest. Save. Do not invent a new kitchen code.",
      "Status chips (WA / Pay / Brand / KYC) on the list reflect this kitchen. Profile does not take orders or edit dishes.",
      "Sales can correct profile and pin on kitchens they onboarded. Super Admin can open any kitchen.",
    ],
  },
  train: {
    title: "Workspace — Train (8-step playbook)",
    steps: [
      "Tick while the owner does the work on the Kitchen app — ticks do not block going live.",
      "1 Profile is true · 2 Live-capture a dish hero (camera, not gallery) · 3 Map the first recipe (grams + pantry kcal).",
      "4 Set free/max delivery km they actually ride · 5 Owner KYC (live photo + Aadhaar + PAN) · 6 Place a test order and walk received → ready.",
      "7 Confirm kitchen WhatsApp phone_number_id (never the Meta app secret) · 8 Owner requests OTP alone.",
      "Reload must persist ticks. Another sales login cannot open this book. Super Admin can inspect any kitchen’s Train.",
    ],
  },
  brand: {
    title: "Workspace — Brand",
    steps: [
      "This is the public /k/{code} storefront: tagline, accent colour, logo, background.",
      "Upload brand media here when support is fixing a broken storefront. Open the customer link to confirm diners see it.",
      "Kitchen code stays display-only. Story copy belongs to the owner — do not replace it with stock-photo hero deception.",
    ],
  },
  kyc: {
    title: "Workspace — KYC",
    steps: [
      "Confirm live owner photo plus Aadhaar and PAN. Values must be masked in this console (never full numbers in the UI or logs).",
      "Incomplete KYC is a support flag — it does not auto-suspend the kitchen unless you choose Suspend on Profile.",
      "You cannot impersonate the owner JWT from this tab.",
    ],
  },
  whatsapp: {
    title: "Workspace — WhatsApp",
    steps: [
      "Save the kitchen phone_number_id (and display phone). This is tenant-scoped Cloud API identity.",
      "Never paste the Meta app secret, verify token, or platform WhatsApp token here — those live under API Keys.",
      "Disconnect clears this kitchen’s id only. Drafts from WhatsApp still confirm on the owner Orders → Drafts board.",
    ],
  },
  payments: {
    title: "Workspace — Payments",
    steps: [
      "Fill kitchen Razorpay key id / linked account (Route). Secrets encrypt after save and must not re-display in full.",
      "This is not SaaS Razorpay for kitchCU subscriptions — that key stays under API Keys.",
      "Clear credentials only when the owner rotates keys. Settlements and refunds are on Refunds / kitchen Orders, not a commission clawback.",
    ],
  },
  package: {
    title: "Workspace — Package",
    steps: [
      "Assign a package (starter / growth / pro). The feature checklist must match Packages mapper.",
      "Hard entitlements hide owner nav (Live stream, templates, CRM) when the plan does not include them — enforce is server-side.",
      "Needs packages:write. Read-only staff can view but not save. There is no per-order food commission line on any plan.",
    ],
  },
  modules: {
    title: "Workspace — Modules",
    steps: [
      "Toggle per-kitchen flags (whatsapp, razorpay, tiffin_plans, marketing_broadcast, streaming, dish_health, …).",
      "A global Control kill-switch still wins. Use this tab to enable one kitchen without opening the platform.",
      "Changing a flag does not rewrite the owner’s menu or cook-line tickets.",
    ],
  },
  marketing: {
    title: "Workspace — Marketing",
    steps: [
      "Read template counts and broadcast module state. This is a summary — owners author copy on Kitchen → Templates.",
      "You do not send a broadcast from Super Admin. CRM lists stay tenant-scoped to this kitchen.",
    ],
  },
  streaming: {
    title: "Workspace — Streaming",
    steps: [
      "Read live session summary and whether the streaming module is on.",
      "Never dump a LiveKit publisher token on this screen. Platform LiveKit keys stay under API Keys.",
      "Owners go live from Kitchen → Live stream with dish phases ingredients → prep → prepared.",
    ],
  },
  orders: {
    title: "Workspace — Orders / Care",
    steps: [
      "This is a platform read of recent tickets for this kitchen — not the owner cook board.",
      "You cannot accept, mark ready, or rewrite line items. Export CSV for ops; use Tickets / Refunds for care.",
      "Parse match rate (30d) shows WhatsApp draft mapping health. Unmatched drafts still confirm only on the Kitchen app.",
    ],
  },
  pantry: {
    title: "Workspace — Pantry",
    steps: [
      "Inspect SKUs, stock, and kcal per 100g (or per piece). This is the source for dish calories and Healthy.",
      "You do not edit recipes here — owners map grams on Kitchen → Ingredients. Low-stock chips are support context.",
      "Healthy on the diner menu still requires a complete map, kcal ≤ Control cap, and score ≥ Control floor.",
    ],
  },
  delivery: {
    title: "Workspace — Delivery",
    steps: [
      "Inspect free radius and max km. Porter auto-book / delay are kitchen settings, not fake 10-minute ETAs.",
      "Fees: owner pays in-range vs diner extended — honest distance, no aggregator race.",
      "Do not shrink radius from admin to ‘win’ discovery. Owners set what they actually ride on Setup.",
    ],
  },
  tiffin: {
    title: "Workspace — Tiffin",
    steps: [
      "Read combo vs single-dish plans and subscription rows for this kitchen.",
      "Combo plans need ≥2 dishes; single-dish = 1. You do not cook or bill a tiffin from this tab.",
      "Module-gated: if tiffin is off, the owner nav is hidden until Package / Modules allow it.",
    ],
  },
  gst: {
    title: "Workspace — GST",
    steps: [
      "Open the kitchen GST profile and pick year/month. Sync, then export Excel or PDF.",
      "Bill numbers are {code}-BILL-YYYYMMDD-SEQ. GST docs are {code}-GST-YYYYMM-SEQ.",
      "This is the ops export of the same books the owner closes on Kitchen → GST. No food-commission column.",
    ],
  },
};

export const ADMIN_TOUR_STEPS = [
  {
    title: "Overview is the pulse",
    body: "Start here for KPIs and attention tiles (tickets, refunds, suspended kitchens, trials). Click a tile to jump. You never cook or mark-ready an order from Super Admin.\n\nEach tab (and each kitchen workspace inner tab) has a collapsible What you can do list. Collapse it when you know the screen. Show tips replays this tour.",
  },
  {
    title: "Hire sales, then onboard",
    body: "Employees → create staff with role sales. They only see Sales + Kitchens.\n\nOn Sales: owner name, unused phone, kitchen name, street, city, stall map pin. Submit Onboard — a kitchen code (CK…) is issued. The owner logs in on kitchCU - kitchen owner with that phone. Demo sales: sales@kitchcu.dev / sales123456.",
  },
  {
    title: "Kitchens list → open a workspace",
    body: "Kitchens → search CKPNQ001 → open the row. The list is tenant inventory (WA / Pay / Brand / KYC chips). The workspace on the right is that kitchen’s ops desk.\n\nThe kitchen code never changes. Sales only see kitchens they onboarded. Super Admin sees every tenant.",
  },
  {
    title: "Workspace — Profile, Train, KYC, Brand",
    body: "Profile: address + pin; Activate / Suspend. Train: 8-step owner playbook (ticks do not block live). KYC: live photo + masked Aadhaar/PAN. Brand: public /k/{code} tagline, logo, accent.\n\nYou never impersonate the owner JWT or edit dish heroes from here.",
  },
  {
    title: "Workspace — WhatsApp, Payments, Package, Modules",
    body: "WhatsApp: kitchen phone_number_id only — never the Meta app secret. Payments: kitchen Razorpay / Route — never SaaS Razorpay. Package: assign plan + feature checklist (packages:write). Modules: per-kitchen flags; Control kill-switches still win.\n\nHard entitlements hide owner nav when the plan does not include Live stream or templates.",
  },
  {
    title: "Workspace — Orders, Pantry, Streaming, GST",
    body: "Orders / Care: platform read + CSV; you cannot mark ready. Pantry: inspect kcal — owners map recipes. Streaming: session summary, no publisher token. Delivery: honest radius. Tiffin: combo ≥2. GST: Excel/PDF {code}-GST-YYYYMM-SEQ.\n\nMarketing is a template count — owners send from Kitchen → Templates.",
  },
  {
    title: "Owners and customers",
    body: "Owners: search phone (9876543210), linked kitchens, force a subscription tier when billing glitches (owners:write).\n\nCustomers: search phone, addresses, orders, tickets, photos, payout, diet-report flags (not the checkup file). Suspend or clear password when support needs a lock. You do not impersonate a diner JWT.",
  },
  {
    title: "Orders, refunds, tickets",
    body: "Platform Orders is a feed — filter by kitchen or diner; do not advance cook-line status.\n\nRefunds: escalate gateway vs direct-transfer; complete or fail with a reason. Settlements list Route splits per kitchen. Tickets: status, priority, assignee, reply; Open kitchen / Open refunds to jump. Admin JWT still cannot mutate owner menu routes.",
  },
  {
    title: "Packages and entitlements",
    body: "Packages maps features → packages → owner/customer plans. Assign on the kitchen Package tab.\n\nkitchCU is owner-subscription SaaS — there is no per-order food commission on any plan. If a screen shows a commission % of food, that is a defect.",
  },
  {
    title: "API Keys vs kitchen keys",
    body: "API Keys hold platform Meta, SaaS Razorpay, LiveKit, Maps, OAuth. After save the value is masked — opening a key must never show the full secret again.\n\nKitchen WhatsApp id and kitchen Razorpay stay on that kitchen’s WhatsApp / Payments tabs. Sales never pastes SaaS secrets.",
  },
  {
    title: "Control — flags, calories, Healthy",
    body: "Toggle sales_onboarding, dish_calories, dish_healthy_tag, customer_diet_report, streaming.\n\nDish calories & Healthy: on/off plus max kcal cap (default 500) and score floor (default 65). Healthy on a diner menu is automatic (complete recipe map + cap + floor) — owners cannot pin it. Journeys and subscription overrides. No raw secrets here.",
  },
  {
    title: "Referrals, audit, store app",
    body: "Referrals: dual reward amounts (customer ↔ kitchen) and the lead queue.\n\nAudit: who changed kitchens, flags, keys, employees, subscriptions — OTP, tokens, and full phones must not appear in the log text.\n\nSame product in the kitchCU - admin store app. Use Show tips anytime. You are done — walk the left nav and the What you can do list on every tab.",
  },
];

export const SALES_TOUR_STEPS = [
  {
    title: "You only see Sales + Kitchens",
    body: "If Overview, Employees, API Keys, Control, Packages, Refunds, or Audit appear, stop — that is the wrong login. Demo: sales@kitchcu.dev / sales123456.",
  },
  {
    title: "Onboard on-site",
    body: "Open Sales. Fill owner name, a phone that is not already an owner, kitchen name, street, city, and drop the pin on the stall. Submit Onboard. Write down the kitchen code (CK…).",
  },
  {
    title: "Owner logs in on Kitchen",
    body: "They open kitchCU - kitchen owner (or kitchen.kitchcu.com). Phone + OTP. Local/demo OTP is 123456. Production sends WhatsApp OTP. Kitchen code does not change after save.",
  },
  {
    title: "Train — profile, live photo, recipe",
    body: "Open the kitchen Train tab. Tick while they do it: Setup name/street/pin; Add Dish with the camera (no gallery hero); Ingredients pantry SKU + recipe grams (this drives stock, health, calories).",
  },
  {
    title: "Train — radius, KYC, test order",
    body: "Setup delivery: free radius and max km they actually ride. Owner identity: live photo + Aadhaar + PAN. Place a test order and walk received → accepted → ready so they trust the board.",
  },
  {
    title: "Train — WhatsApp + solo login",
    body: "If they take WhatsApp orders, confirm kitchen phone_number_id with Super Admin — you never paste the Meta app secret. They request OTP alone. Training does not block going live.",
  },
  {
    title: "Your book only",
    body: "Kitchens lists kitchens you created. You can correct profile and pin. Another sales login cannot open this Train list. Super Admin can still inspect any kitchen.",
  },
];
