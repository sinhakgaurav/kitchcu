/**
 * Static UI reachability check — verifies nav → route → API → customer surface
 * wiring for Brand page, admin kitchen Brand tab, and DataTable list screens.
 *
 * Run: node scripts/check-ui-reach.mjs
 * Exit 1 on any FAIL.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fail = [];
const warn = [];
const pass = [];

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function assert(cond, msg) {
  if (cond) pass.push(msg);
  else fail.push(msg);
}

function assertWarn(cond, msg) {
  if (cond) pass.push(msg);
  else warn.push(msg);
}

function includesAll(src, needles, label) {
  for (const n of needles) {
    assert(src.includes(n), `${label} contains ${JSON.stringify(n)}`);
  }
}

// ── Owner Brand page ──────────────────────────────────────────────
const ownerLayout = read("apps/website/src/layouts/OwnerLayout.tsx");
const kitchenApp = read("apps/website/src/kitchen/App.tsx");
const brandPage = read("apps/website/src/pages/owner/BrandPage.tsx");
const ownerHome = read("apps/website/src/pages/owner/OwnerHomePage.tsx");
const ownerApi = read("apps/website/src/shared/api.ts");
const kitchenSetup = read("apps/website/src/pages/owner/KitchenSetupPage.tsx");

assert(exists("apps/website/src/pages/owner/BrandPage.tsx"), "BrandPage.tsx exists");
assert(ownerLayout.includes('to: "/dashboard/brand"'), "Owner nav → /dashboard/brand");
assert(ownerLayout.includes('label: "Brand page"'), "Owner nav label Brand page");
assert(kitchenApp.includes('path="brand"'), "Kitchen router registers brand route");
assert(kitchenApp.includes("BrandPage"), "Kitchen router imports BrandPage");
assert(brandPage.includes("updateKitchenBrandedPage"), "BrandPage calls updateKitchenBrandedPage");
assert(brandPage.includes("uploadKitchenMedia"), "BrandPage uploads logo/background via media API");
assert(brandPage.includes("brand_logo"), "BrandPage uses brand_logo context");
assert(brandPage.includes("brand_background"), "BrandPage uses brand_background context");
assert(brandPage.includes("/dashboard/templates"), "BrandPage links to message templates");
assert(ownerApi.includes("/branded-page"), "shared/api has owner branded-page PATCH");
assert(ownerApi.includes("logo_url"), "shared/api branded page includes logo_url");
assert(ownerHome.includes("/dashboard/brand"), "Overview links to Brand page");
assert(ownerHome.includes("od-branded--teaser") || ownerHome.includes("Manage brand page"), "Overview shows brand teaser");
assertWarn(
  kitchenSetup.includes("/dashboard/brand") || kitchenSetup.includes("Brand page"),
  "Kitchen setup links day-1 owners to Brand page",
);

// ── Customer storefront ───────────────────────────────────────────
const customerApp = read("apps/website/src/customer/App.tsx");
const brandedStore = read("apps/website/src/customer/BrandedStorefront.tsx");
assert(customerApp.includes('path="/k/:code"'), "Customer app has /k/:code route");
assert(brandedStore.includes("fetchKitchenByCode"), "BrandedStorefront loads kitchen by code");
assert(brandedStore.includes("branded_page"), "BrandedStorefront reads branded_page settings");
assert(brandedStore.includes("logo_url") || brandedStore.includes("logoUrl"), "BrandedStorefront renders logo");
assert(
  brandedStore.includes("background_url") || brandedStore.includes("backgroundUrl"),
  "BrandedStorefront uses background image",
);
assert(ownerApi.includes("public/by-code"), "Public by-code API client exists");

// ── Admin Brand workspace ─────────────────────────────────────────
const adminApp = read("apps/website/src/admin/App.tsx");
const adminApi = read("apps/website/src/admin/adminApi.ts");
const adminRoutes = read("services/identity/app/admin_routes.py");
const identityRoutes = read("services/identity/app/routes.py");
const gateway = read("services/gateway/app/main.py");

assert(adminApi.includes("updateAdminKitchenBrandedPage"), "adminApi has updateAdminKitchenBrandedPage");
assert(adminApi.includes("uploadAdminKitchenBrandMedia"), "adminApi uploads brand media");
assert(adminApi.includes("branded_page_enabled"), "adminApi types branded_page_enabled");
assert(adminApi.includes("/branded-page"), "adminApi PATCH path branded-page");
assert(adminApp.includes('"brand"'), "Admin kitchen panelTab includes brand");
assert(adminApp.includes("saveBrandedPage") || adminApp.includes("updateAdminKitchenBrandedPage"), "Admin UI calls brand save");
assert(adminApp.includes("uploadBrandMedia") || adminApp.includes("uploadAdminKitchenBrandMedia"), "Admin UI uploads brand media");
assert(adminApp.includes('header: "Brand"'), "Admin kitchens DataTable has Brand column");
assert(adminRoutes.includes('"/kitchens/{kitchen_id}/branded-page"'), "Identity admin route branded-page");
assert(adminRoutes.includes("branded-page/media"), "Identity admin brand media upload route");
assert(adminRoutes.includes("branded_page_enabled"), "AdminKitchenRow exposes branded_page_enabled");
assert(identityRoutes.includes('"/kitchens/{kitchen_id}/branded-page"'), "Owner identity route branded-page");
assert(gateway.includes('"/api/v1/admin"'), "Gateway IDENTITY_PREFIXES includes /api/v1/admin");
assert(
  gateway.includes('"/api/v1/kitchens"'),
  "Gateway routes /api/v1/kitchens (owner branded-page → identity)",
);

// ── DataTable list screens ────────────────────────────────────────
const dataTable = read("apps/website/src/components/DataTable.tsx");
const adminPanels = read("apps/website/src/admin/AdminPanels.tsx");
assert(dataTable.includes("ListingToolbar"), "DataTable composes ListingToolbar");
assert(dataTable.includes("paginateRows"), "DataTable paginates");
assert(adminApp.includes("<DataTable"), "Admin App uses DataTable");
assert(adminPanels.includes("<DataTable"), "AdminPanels uses DataTable (customers)");

const listScreens = [
  ["AdminKitchens", adminApp.includes("function AdminKitchens") && adminApp.includes("<DataTable")],
  ["AdminOwners", adminApp.includes("function AdminOwners") && /function AdminOwners[\s\S]*?<DataTable/.test(adminApp)],
  ["AdminOrders", adminApp.includes("function AdminOrders") && /function AdminOrders[\s\S]*?<DataTable/.test(adminApp)],
  ["AdminCustomers", adminPanels.includes("function AdminCustomers") && /function AdminCustomers[\s\S]*?<DataTable/.test(adminPanels)],
  ["AdminRefunds", /function AdminRefunds[\s\S]*?<DataTable/.test(adminPanels)],
  ["AdminTickets", /function AdminTickets[\s\S]*?<DataTable/.test(adminApp)],
  ["AdminEmployeesPanel", /function AdminEmployeesPanel[\s\S]*?<DataTable/.test(adminPanels)],
];

for (const [name, ok] of listScreens) {
  assertWarn(ok, `${name} uses DataTable (search/sort/filter/pagination)`);
}

// ── CSS surface ───────────────────────────────────────────────────
const indexCss = read("apps/website/src/index.css");
const ownerCss = read("apps/website/src/owner-app.css");
assert(indexCss.includes(".data-table"), "index.css has .data-table styles");
assert(indexCss.includes(".listing-toolbar"), "index.css has .listing-toolbar styles");
assert(ownerCss.includes(".od-branded"), "owner-app.css has brand page styles");
assert(adminApp.includes('../index.css') || read("apps/website/src/admin/main.tsx").includes("index.css"), "Admin loads index.css");
assert(read("apps/website/src/kitchen/main.tsx").includes("owner-app.css"), "Kitchen loads owner-app.css");

// ── Report ────────────────────────────────────────────────────────
console.log("\n=== UI reach check ===\n");
for (const m of pass) console.log(`PASS  ${m}`);
for (const m of warn) console.log(`WARN  ${m}`);
for (const m of fail) console.log(`FAIL  ${m}`);
console.log(`\n${pass.length} pass · ${warn.length} warn · ${fail.length} fail\n`);

if (fail.length) {
  process.exit(1);
}
if (warn.length) {
  console.log("Warnings are incomplete UI mappings — fix before calling the surface done.\n");
  process.exit(2);
}
console.log("All reach checks passed.\n");
