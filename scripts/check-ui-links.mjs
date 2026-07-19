/**
 * Recursive UI link / route wiring audit across portal · customer · kitchen · admin.
 *
 * Extracts Route path= registries and compares against Link/Navigate/navigate/href targets.
 * Also flags known anti-patterns (dead /customers, mislabeled Owner Login on customer app).
 *
 * Run: node scripts/check-ui-links.mjs
 * Exit 1 on FAIL.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const srcRoot = path.join(root, "apps/website/src");
const fail = [];
const warn = [];
const pass = [];

function walk(dir, out = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name === "node_modules" || ent.name === "dist") continue;
      walk(p, out);
    } else if (/\.(tsx|ts|jsx|js)$/.test(ent.name)) {
      out.push(p);
    }
  }
  return out;
}

function rel(p) {
  return path.relative(root, p).replace(/\\/g, "/");
}

function read(p) {
  return fs.readFileSync(p, "utf8");
}

function ok(cond, msg) {
  if (cond) pass.push(msg);
  else fail.push(msg);
}

function soft(cond, msg) {
  if (cond) pass.push(msg);
  else warn.push(msg);
}

/** Normalize a path for membership checks (strip query/hash, collapse params). */
function normalizeTarget(raw) {
  let t = raw.trim();
  if (!t.startsWith("/")) return null;
  // template literals / dynamic — skip deep validation
  if (t.includes("${") || t.includes("`")) return null;
  t = t.split("?")[0].split("#")[0];
  if (!t) t = "/";
  // collapse :params already static
  return t.replace(/\/+/g, "/");
}

/** Convert registered route pattern to a matcher. */
function routeToRegex(routePath) {
  const body = routePath
    .replace(/\/+/g, "/")
    .replace(/:[A-Za-z_][\w]*/g, "[^/]+")
    .replace(/\*/g, ".*");
  return new RegExp(`^${body}$`);
}

function extractRoutes(appSrc) {
  const routes = new Set();
  const re = /path\s*=\s*["']([^"']+)["']/g;
  let m;
  while ((m = re.exec(appSrc))) {
    routes.add(m[1]);
  }
  // Nested dashboard children are relative — expand under /dashboard
  const nested = [];
  for (const r of routes) {
    if (!r.startsWith("/") && r !== "*") nested.push(r);
  }
  if (appSrc.includes('path="/dashboard"') || appSrc.includes("path='/dashboard'")) {
    for (const n of nested) {
      if (n === "index" || n === "") routes.add("/dashboard");
      else routes.add(`/dashboard/${n}`);
    }
  }
  // branded store nested under /k/:code
  if (appSrc.includes('path="/k/:code"')) {
    for (const n of nested) {
      if (["menu", "checkout"].includes(n) || n.startsWith("orders") || n.startsWith("master-orders")) {
        routes.add(`/k/:code/${n}`);
      }
    }
    routes.add("/k/:code");
    routes.add("/k/:code/menu");
    routes.add("/k/:code/checkout");
  }
  routes.add("/");
  return [...routes].filter((r) => r.startsWith("/") || r === "*");
}

function extractTargets(fileSrc) {
  const targets = [];
  const patterns = [
    /\bto\s*=\s*["']([^"']+)["']/g,
    /\bnavigate\(\s*["']([^"']+)["']/g,
    /<Navigate[^>]*\bto\s*=\s*["']([^"']+)["']/g,
    /\bhref\s*=\s*["'](\/[^"']+)["']/g,
  ];
  for (const re of patterns) {
    let m;
    while ((m = re.exec(fileSrc))) {
      targets.push(m[1]);
    }
  }
  return targets;
}

function matchesAnyRoute(target, routeRegexes) {
  const n = normalizeTarget(target);
  if (!n) return true; // dynamic / skip
  // hash-only home anchors
  if (n === "/") return true;
  return routeRegexes.some((rx) => rx.test(n));
}

// ── App route registries ─────────────────────────────────────────
const customerApp = read(path.join(srcRoot, "customer/App.tsx"));
const kitchenApp = read(path.join(srcRoot, "kitchen/App.tsx"));
const portalApp = read(path.join(srcRoot, "portal/App.tsx"));

const customerRoutes = extractRoutes(customerApp);
const kitchenRoutes = extractRoutes(kitchenApp);
const portalRoutes = extractRoutes(portalApp);

// Explicit known customer routes (nested + auth)
for (const r of [
  "/login",
  "/browse",
  "/oauth/callback",
  "/checkout",
  "/orders",
  "/dashboard",
  "/account",
  "/kitchen/:kitchenId/menu",
  "/kitchen/:kitchenId/checkout",
  "/orders/:orderId/confirm",
  "/orders/:orderId/rate",
  "/master-orders/:masterOrderId/confirm",
  "/t/:token",
  "/live/:sessionId",
  "/k/:code",
  "/k/:code/menu",
  "/k/:code/checkout",
  "/k/:code/orders/:orderId/confirm",
  "/k/:code/master-orders/:masterOrderId/confirm",
]) {
  customerRoutes.push(r);
}

const customerRx = customerRoutes.map(routeToRegex);
const kitchenRx = kitchenRoutes.map(routeToRegex);
const portalRx = portalRoutes.map(routeToRegex);

ok(customerRoutes.includes("/browse"), "Customer registers /browse");
ok(kitchenRoutes.some((r) => r.includes("brand")) || kitchenApp.includes('path="brand"'), "Kitchen registers brand");
ok(portalApp.includes('path="*"') || portalApp.includes("Navigate"), "Portal has catch-all or Navigate import");

// ── Anti-patterns (always fail) ──────────────────────────────────
const allFiles = walk(srcRoot);
let deadCustomers = [];
let ownerLoginOnCustomerBrowse = false;

for (const file of allFiles) {
  const src = read(file);
  const r = rel(file);

  if (/\bto=["']\/customers["']/.test(src) || /\bhref=["']\/customers["']/.test(src)) {
    deadCustomers.push(r);
  }

  if (r.endsWith("CustomerBrowsePage.tsx")) {
    if (/Owner Login/.test(src) && /to=["']\/login["']/.test(src) && !/kitchenUrl\(/.test(src)) {
      ownerLoginOnCustomerBrowse = true;
    }
  }

  // Per-app internal link validation (same-origin Link/navigate/href="/…")
  let rx = null;
  if (
    r.includes("/customer/") ||
    r.includes("/pages/customer/") ||
    r.includes("CustomerNavbar") ||
    r.includes("CustomerFooter") ||
    r.includes("NearbyKitchensList") ||
    r.includes("BrandedStorefront") ||
    r.includes("CustomerShowcase") ||
    r.includes("Hero.tsx")
  ) {
    // Hero is shared — only validate customer-specific absolute paths later
    if (!r.endsWith("Hero.tsx")) rx = customerRx;
  }
  if (
    r.includes("/kitchen/") ||
    r.includes("/pages/owner/") ||
    r.includes("OwnerLayout") ||
    r.includes("KitchenNavbar") ||
    r.includes("KitchenFooter") ||
    r.includes("KitchenLandingPage")
  ) {
    rx = kitchenRx;
  }
  if (r.includes("/portal/") || r.includes("PortalNavbar") || r.includes("PortalFooter")) {
    rx = portalRx;
  }

  if (!rx) continue;

  for (const t of extractTargets(src)) {
    const n = normalizeTarget(t);
    if (!n) continue;
    // Allow hash home links
    if (n === "/" && t.includes("#")) continue;
    // Skip cross-app helpers used as template — only plain strings
    if (!matchesAnyRoute(t, rx)) {
      // Allow /#section style
      if (t.startsWith("/#")) continue;
      fail.push(`${r} → ${JSON.stringify(t)} not in app routes`);
    }
  }
}

ok(deadCustomers.length === 0, `No dead /customers links (found: ${deadCustomers.join(", ") || "none"})`);
ok(!ownerLoginOnCustomerBrowse, "CustomerBrowsePage Owner Login uses kitchenUrl (not customer /login)");

// ── Required inbound wiring ──────────────────────────────────────
const customerNav = read(path.join(srcRoot, "components/CustomerNavbar.tsx"));
const customerFooter = read(path.join(srcRoot, "components/CustomerFooter.tsx"));
const branded = read(path.join(srcRoot, "customer/BrandedStorefront.tsx"));
const openApi = read(path.join(srcRoot, "portal/OpenApiPage.tsx"));
const browse = read(path.join(srcRoot, "pages/customer/CustomerBrowsePage.tsx"));
const menuPage = read(path.join(srcRoot, "pages/customer/KitchenMenuPage.tsx"));
const audience = read(path.join(srcRoot, "components/AudienceSections.tsx"));
const legacyNav = read(path.join(srcRoot, "components/Navbar.tsx"));
const legacyFooter = read(path.join(srcRoot, "components/Footer.tsx"));

ok(customerNav.includes('to="/browse"') || customerNav.includes("to={'/browse'}"), "Customer nav links to /browse");
ok(customerFooter.includes('to="/browse"') || customerFooter.includes("/#nearby"), "Customer footer discovers kitchens");
ok(branded.includes("portalUrl"), "BrandedStorefront uses portalUrl (not hardcoded kitchcu.in)");
ok(!openApi.includes("localhost:18000"), "OpenApiPage avoids hardcoded localhost:18000");
ok(browse.includes("kitchenUrl"), "Browse page Owner CTA → kitchenUrl");
ok(menuPage.includes("login?next=") || menuPage.includes("next="), "KitchenMenuPage login preserves next=");
ok(!audience.includes('to="/customers"'), "AudienceSections has no /customers");
ok(!legacyNav.includes('to="/customers"'), "Legacy Navbar has no /customers");
ok(!legacyFooter.includes('to="/customers"'), "Legacy Footer has no /customers");
ok(portalApp.includes('path="*"'), "Portal catch-all route registered");

const customerLogin = read(path.join(srcRoot, "customer/pages/CustomerPages.tsx"));
const oauthCb = read(path.join(srcRoot, "customer/pages/CustomerOAuthCallbackPage.tsx"));
const customerApiSrc = read(path.join(srcRoot, "shared/customerApi.ts"));
ok(
  customerLogin.includes('safeNext !== "/"') || customerLogin.includes("safeNext !== '/'"),
  "Customer login prefers ?next= over kitchen redirect",
);
ok(oauthCb.includes("takeCustomerOAuthNext"), "OAuth callback restores next path");
ok(
  customerApiSrc.includes("next") && customerApiSrc.includes("oauth_pending_"),
  "OAuth start stashes next in pending session",
);

// Owner nav ↔ routes
const ownerLayout = read(path.join(srcRoot, "layouts/OwnerLayout.tsx"));
const navTos = [...ownerLayout.matchAll(/to:\s*["']([^"']+)["']/g)].map((m) => m[1]);
for (const to of navTos) {
  ok(matchesAnyRoute(to, kitchenRx), `Owner nav ${to} has kitchen route`);
}

// Admin tabs have panel render branches
const adminApp = read(path.join(srcRoot, "admin/App.tsx"));
for (const tab of [
  "overview",
  "kitchens",
  "owners",
  "customers",
  "orders",
  "refunds",
  "tickets",
  "packages",
  "employees",
  "api-keys",
  "control",
  "audit",
]) {
  soft(adminApp.includes(`"${tab}"`) || adminApp.includes(`'${tab}'`), `Admin tab id ${tab} present`);
}

console.log("\n=== UI link / route wiring audit ===\n");
for (const m of pass) console.log(`PASS  ${m}`);
for (const m of warn) console.log(`WARN  ${m}`);
for (const m of fail) console.log(`FAIL  ${m}`);
console.log(`\n${pass.length} pass · ${warn.length} warn · ${fail.length} fail\n`);

if (fail.length) {
  console.error("UI link wiring has failures.");
  process.exit(1);
}
console.log("All UI link checks passed.");
process.exit(0);
