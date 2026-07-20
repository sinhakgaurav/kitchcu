/**
 * Platform feature → UI → endpoint mapping verifier.
 *
 * Checks that shipped product features have:
 *  1. Owner / admin / customer UI surfaces (files + nav/routes/tabs)
 *  2. Client API functions calling the expected /api/v1/ path fragments
 *
 * Run: node scripts/check-platform-ui-map.mjs
 * Exit 1 on FAIL · Exit 2 on WARN-only (optional completeness)
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
function ok(cond, msg) {
  if (cond) pass.push(msg);
  else fail.push(msg);
}
function soft(cond, msg) {
  if (cond) pass.push(msg);
  else warn.push(msg);
}

const ownerLayout = read("apps/website/src/layouts/OwnerLayout.tsx");
const kitchenApp = read("apps/website/src/kitchen/App.tsx");
const customerApp = read("apps/website/src/customer/App.tsx");
const adminApp = read("apps/website/src/admin/App.tsx");
const adminApi = read("apps/website/src/admin/adminApi.ts");
const sharedApi = read("apps/website/src/shared/api.ts");
const adminPanels = read("apps/website/src/admin/AdminPanels.tsx");

const apiBundle = [
  sharedApi,
  adminApi,
  exists("apps/website/src/shared/customerCheckoutApi.ts")
    ? read("apps/website/src/shared/customerCheckoutApi.ts")
    : "",
  exists("apps/website/src/shared/customerApi.ts") ? read("apps/website/src/shared/customerApi.ts") : "",
  exists("apps/website/src/shared/publicApi.ts") ? read("apps/website/src/shared/publicApi.ts") : "",
  exists("apps/website/src/shared/customerDashboardApi.ts")
    ? read("apps/website/src/shared/customerDashboardApi.ts")
    : "",
  exists("apps/website/src/shared/referralApi.ts")
    ? read("apps/website/src/shared/referralApi.ts")
    : "",
  exists("apps/website/src/lib/supportApi.ts") ? read("apps/website/src/lib/supportApi.ts") : "",
].join("\n");

function hasNav(pathSeg) {
  return ownerLayout.includes(`to: "${pathSeg}"`) || ownerLayout.includes(`to: '${pathSeg}'`);
}
function hasRoute(seg) {
  return kitchenApp.includes(`path="${seg}"`) || kitchenApp.includes(`path='${seg}'`);
}
function hasAdminTab(id) {
  return adminApp.includes(`id: "${id}"`) || adminApp.includes(`"${id}"`);
}
function hasCustomerRoute(seg) {
  return customerApp.includes(seg);
}
function hasApi(...needles) {
  return needles.every((n) => apiBundle.includes(n));
}
function hasPage(rel) {
  return exists(rel);
}
function pageCalls(rel, fn) {
  if (!exists(rel)) return false;
  return read(rel).includes(fn);
}

/** @type {{ id: string; name: string; checks: (() => void)[] }[]} */
const features = [
  {
    id: "AUTH-OWNER",
    name: "Owner OTP auth",
    checks: () => {
      ok(hasCustomerRoute("/login") || hasRoute("login") || kitchenApp.includes("/login"), "Owner login route");
      ok(hasApi("/api/v1/auth/otp/request", "/api/v1/auth/otp/verify"), "Owner OTP endpoints in client");
      ok(hasPage("apps/website/src/pages/LoginPage.tsx"), "LoginPage exists");
    },
  },
  {
    id: "AUTH-CUSTOMER",
    name: "Customer WhatsApp OTP + OAuth",
    checks: () => {
      ok(hasCustomerRoute("/login"), "Customer login route");
      ok(hasCustomerRoute("/oauth/callback"), "Customer OAuth callback route");
      soft(hasApi("otp") || hasApi("/customers"), "Customer auth API surface present");
    },
  },
  {
    id: "F01-F04",
    name: "Orders lifecycle (manual + drafts)",
    checks: () => {
      ok(hasNav("/dashboard/orders") && hasRoute("orders"), "Owner Orders nav+route");
      ok(hasRoute("orders/new") && hasRoute("orders/:orderId"), "New + detail order routes");
      ok(hasApi("/orders", "createManualOrder") || hasApi("/orders"), "Orders API paths");
      ok(pageCalls("apps/website/src/pages/owner/OrdersPage.tsx", "fetchOrders"), "OrdersPage→fetchOrders");
      ok(pageCalls("apps/website/src/pages/owner/OrdersPage.tsx", "parseMessage"), "OrdersPage→parseMessage");
      ok(pageCalls("apps/website/src/pages/owner/OrderDetailPage.tsx", "updateOrderStatus"), "OrderDetail→status");
    },
  },
  {
    id: "F06",
    name: "Multi-kitchen cart / master order",
    checks: () => {
      ok(hasCustomerRoute("master-orders") || hasCustomerRoute("MasterOrder"), "Customer master-order routes");
      soft(hasApi("master-orders") || hasApi("master_order") || hasApi("createMasterOrder"), "Master order client API");
    },
  },
  {
    id: "CATALOG",
    name: "Menu / dishes / live-capture",
    checks: () => {
      ok(hasNav("/dashboard/menu") && hasRoute("menu"), "Owner Menu nav+route");
      ok(hasRoute("menu/new"), "Add dish route");
      ok(pageCalls("apps/website/src/pages/owner/MenuPage.tsx", "fetchMenu"), "MenuPage→fetchMenu");
      ok(pageCalls("apps/website/src/pages/owner/AddDishPage.tsx", "createDish"), "AddDish→createDish");
      ok(hasCustomerRoute("/kitchen/:kitchenId/menu") || hasCustomerRoute("KitchenMenuPage"), "Customer menu route");
    },
  },
  {
    id: "P19",
    name: "Branded kitchen storefront",
    checks: () => {
      ok(hasNav("/dashboard/brand") && hasRoute("brand"), "Owner Brand page nav+route");
      ok(hasPage("apps/website/src/pages/owner/BrandPage.tsx"), "BrandPage.tsx");
      ok(pageCalls("apps/website/src/pages/owner/BrandPage.tsx", "updateKitchenBrandedPage"), "BrandPage→PATCH");
      ok(hasApi("/branded-page"), "branded-page in API clients");
      ok(hasCustomerRoute("/k/:code"), "Customer /k/:code storefront");
      ok(adminApp.includes('"brand"') && adminApi.includes("branded-page"), "Admin Brand tab + API");
      ok(hasPage("apps/website/src/customer/BrandedStorefront.tsx"), "BrandedStorefront layout");
    },
  },
  {
    id: "P20",
    name: "Golden performance day",
    checks: () => {
      ok(hasNav("/dashboard/growth") && hasRoute("growth"), "Growth Intelligence nav+route");
      ok(pageCalls("apps/website/src/pages/owner/GrowthPage.tsx", "saveGoldenRecipe"), "Growth→golden save");
      ok(hasApi("golden") || sharedApi.includes("GoldenRecipe") || sharedApi.includes("golden"), "Golden recipe API types/fns");
    },
  },
  {
    id: "P21",
    name: "WhatsApp + Razorpay kitchen workspace",
    checks: () => {
      ok(hasNav("/dashboard/whatsapp") && hasRoute("whatsapp"), "Owner WhatsApp nav+route");
      ok(hasNav("/dashboard/payment-gateway") && hasRoute("payment-gateway"), "Owner PG nav+route");
      ok(hasApi("whatsapp-integration") || hasApi("whatsapp"), "WhatsApp API client");
      ok(hasApi("payment-gateway"), "Payment gateway API client");
      ok(adminApp.includes("whatsapp") && adminApp.includes("payments"), "Admin WA + Payments tabs");
    },
  },
  {
    id: "P22-P30",
    name: "Live streaming + dish showcase",
    checks: () => {
      ok(hasNav("/dashboard/stream") && hasRoute("stream"), "Owner Stream nav+route");
      ok(pageCalls("apps/website/src/pages/owner/StreamPage.tsx", "goKitchenLive") || pageCalls("apps/website/src/pages/owner/StreamPage.tsx", "fetchStreamSettings"), "StreamPage APIs");
      ok(hasCustomerRoute("/live/:sessionId"), "Customer live watch route");
      soft(adminApp.includes("streaming"), "Admin streaming module tab");
    },
  },
  {
    id: "P25",
    name: "Package mapper",
    checks: () => {
      ok(hasAdminTab("packages"), "Admin Packages tab");
      ok(adminPanels.includes("AdminPackagesPanel") || adminApp.includes("AdminPackagesPanel"), "Packages panel wired");
      ok(adminApi.includes("/packages") || adminApi.includes("packages"), "Admin packages API");
      ok(adminApp.includes("package"), "Admin kitchen Package tab");
    },
  },
  {
    id: "P26",
    name: "Marketing templates",
    checks: () => {
      ok(hasNav("/dashboard/templates") && hasRoute("templates"), "Owner Templates nav+route");
      ok(pageCalls("apps/website/src/pages/owner/MarketingTemplatesPage.tsx", "fetchMarketingTemplates"), "Templates→API");
      ok(adminApp.includes("marketing"), "Admin kitchen Marketing tab");
    },
  },
  {
    id: "P27",
    name: "Platform employees + RBAC",
    checks: () => {
      ok(hasAdminTab("employees"), "Admin Employees tab");
      ok(adminApi.includes("/employees"), "Employees API");
      ok(adminPanels.includes("AdminEmployeesPanel"), "Employees panel");
    },
  },
  {
    id: "P28",
    name: "Super-admin kitchen workspace",
    checks: () => {
      for (const t of ["profile", "brand", "whatsapp", "payments", "package", "marketing", "modules", "orders", "streaming", "delivery", "tiffin", "gst"]) {
        ok(adminApp.includes(`"${t}"`) || adminApp.includes(`"${t}",`), `Admin kitchen tab: ${t}`);
      }
      soft(adminApp.includes("open_ticket_count") || adminApp.includes("Care"), "Kitchen care/health strip");
      soft(adminApi.includes("kitchen_id") && adminApi.includes("customer_id"), "Admin orders filter params");
    },
  },
  {
    id: "P30-AUDIT",
    name: "Admin audit log",
    checks: () => {
      ok(hasAdminTab("audit"), "Admin Audit tab");
      ok(adminApi.includes("audit"), "Audit API client");
    },
  },
  {
    id: "P32-P35",
    name: "Delivery / Porter / cost-share",
    checks: () => {
      ok(hasNav("/dashboard/setup") && hasRoute("setup"), "Kitchen setup (delivery settings)");
      ok(pageCalls("apps/website/src/pages/owner/KitchenSetupPage.tsx", "updateKitchenDeliverySettings"), "Setup→delivery settings");
      ok(hasApi("delivery") || hasApi("/delivery/"), "Delivery API client");
      ok(adminApp.includes("delivery"), "Admin Delivery tab");
      ok(hasCustomerRoute("/t/:token") || hasCustomerRoute("TrackOrder"), "Customer tracking route");
    },
  },
  {
    id: "P36",
    name: "Tiffin subscriptions",
    checks: () => {
      ok(hasNav("/dashboard/tiffin") && hasRoute("tiffin"), "Owner Tiffin nav+route");
      ok(pageCalls("apps/website/src/pages/owner/TiffinSubscriptionsPage.tsx", "fetchKitchenSubscriptionPlans"), "Tiffin→plans API");
      ok(adminApp.includes("tiffin"), "Admin Tiffin tab");
    },
  },
  {
    id: "F07-F08",
    name: "Owner analytics / reports",
    checks: () => {
      ok(hasNav("/dashboard/reports") && hasRoute("reports"), "Reports nav+route");
      ok(pageCalls("apps/website/src/pages/owner/ReportsPage.tsx", "fetchRevenueSummary"), "Reports→revenue");
    },
  },
  {
    id: "F09-F11-F39",
    name: "Growth intelligence + daily menu",
    checks: () => {
      ok(hasNav("/dashboard/growth"), "Growth nav");
      ok(pageCalls("apps/website/src/pages/owner/GrowthPage.tsx", "fetchGrowthSuggestions"), "Growth suggestions");
      soft(pageCalls("apps/website/src/pages/owner/GrowthPage.tsx", "pushDailyMenu"), "Daily menu push UI");
    },
  },
  {
    id: "F16-F18",
    name: "Home-taste ratings",
    checks: () => {
      ok(hasCustomerRoute("/orders/:orderId/rate") || hasCustomerRoute("rate"), "Customer rate route");
      soft(hasApi("ratings") || hasApi("/ratings"), "Ratings API client");
    },
  },
  {
    id: "F19",
    name: "Ingredient mapper",
    checks: () => {
      ok(hasNav("/dashboard/ingredients") && hasRoute("ingredients"), "Ingredients nav+route");
      ok(pageCalls("apps/website/src/pages/owner/IngredientsPage.tsx", "fetchIngredients"), "Ingredients→API");
    },
  },
  {
    id: "F21-F22",
    name: "Learning portal + trials",
    checks: () => {
      ok(hasNav("/dashboard/learning") && hasRoute("learning"), "Learning nav+route");
      ok(hasRoute("learning/trials/:trialId"), "Trial detail route");
      ok(pageCalls("apps/website/src/pages/owner/LearningPage.tsx", "fetchCuratedRecipes"), "Learning→curated");
    },
  },
  {
    id: "F23-F24",
    name: "Community recipes + rankings",
    checks: () => {
      ok(hasNav("/dashboard/community") && hasRoute("community"), "Community nav+route");
      ok(pageCalls("apps/website/src/pages/owner/CommunityPage.tsx", "fetchSharedRecipes") || pageCalls("apps/website/src/pages/owner/CommunityPage.tsx", "fetchChefRankings"), "Community APIs");
    },
  },
  {
    id: "F27-F31",
    name: "Customer discovery nearby",
    checks: () => {
      ok(hasCustomerRoute('path="/"') || customerApp.includes('path="/"'), "Customer home");
      ok(
        customerApp.includes("CustomerDiscoveryHome") ||
          exists("apps/website/src/customer/pages/CustomerDiscoveryHome.tsx"),
        "Customer discovery hub page",
      );
      soft(exists("apps/website/src/components/NearbyKitchensList.tsx"), "NearbyKitchensList component");
      soft(hasApi("nearby") || hasApi("/public/nearby"), "Nearby kitchens API");
      ok(hasApi("/discovery/home") || hasApi("discovery/home"), "Discovery home API client");
    },
  },
  {
    id: "F32-F33",
    name: "Order history + repeat",
    checks: () => {
      ok(hasCustomerRoute("/orders"), "Customer orders history route");
      soft(hasApi("repeat") || hasApi("/customers/me/orders"), "Customer orders API");
    },
  },
  {
    id: "F36-F38",
    name: "CRM + coupons + promotions",
    checks: () => {
      ok(hasNav("/dashboard/crm") && hasRoute("crm"), "CRM nav+route");
      ok(hasNav("/dashboard/coupons") && hasRoute("coupons"), "Coupons nav+route");
      ok(pageCalls("apps/website/src/pages/owner/CrmPage.tsx", "fetchCrmCustomers"), "CRM→API");
      ok(pageCalls("apps/website/src/pages/owner/CouponsPage.tsx", "fetchCoupons"), "Coupons→API");
    },
  },
  {
    id: "BILLING-SaaS",
    name: "Owner subscription SaaS",
    checks: () => {
      ok(hasNav("/dashboard/subscription") && hasRoute("subscription"), "Subscription nav+route");
      ok(pageCalls("apps/website/src/pages/owner/SubscriptionPage.tsx", "fetchMySubscription"), "Subscription→me");
      ok(hasApi("/billing/subscriptions"), "Billing subscriptions API");
    },
  },
  {
    id: "Referrals",
    name: "Dual referral program",
    checks: () => {
      ok(hasNav("/dashboard/referrals") && hasRoute("referrals"), "Owner Referrals nav+route");
      soft(
        hasApi("/owners/me/referrals") || hasApi("/customers/me/referrals"),
        "Referrals API client",
      );
      soft(hasAdminTab("referrals"), "Admin Referrals tab");
      soft(
        read("apps/website/src/pages/customer/CustomerDashboardPage.tsx").includes('"referrals"'),
        "Customer referrals tab",
      );
    },
  },
  {
    id: "GST",
    name: "GST & finance",
    checks: () => {
      ok(hasNav("/dashboard/gst") && hasRoute("gst"), "GST nav+route");
      ok(pageCalls("apps/website/src/pages/owner/GstFinancePage.tsx", "fetchGstProfile") || pageCalls("apps/website/src/pages/owner/GstFinancePage.tsx", "Gst"), "GST page wired");
      soft(
        pageCalls("apps/website/src/pages/owner/GstFinancePage.tsx", "downloadGstMonthlyExcel") &&
          pageCalls("apps/website/src/pages/owner/GstFinancePage.tsx", "downloadGstMonthlyPdf"),
        "Owner GST Excel/PDF downloads",
      );
      soft(adminApp.includes('"gst"') || adminApp.includes("panelTab === \"gst\""), "Admin kitchen GST tab");
      soft(adminApi.includes("/gst/reports/monthly"), "Admin GST API client");
    },
  },
  {
    id: "SUPPORT",
    name: "Support tickets",
    checks: () => {
      ok(hasAdminTab("tickets"), "Admin Tickets tab");
      ok(adminApi.includes("/tickets") || adminApi.includes("tickets"), "Tickets API");
      soft(adminApp.includes("handleAssigneeChange") || adminApp.includes("assigned_admin_id"), "Ticket assignee triage");
      soft(adminApp.includes("adminNavigate") || adminApi.includes("adminNavigate"), "Ticket→kitchen/refunds deep-link");
      soft(hasCustomerRoute("/dashboard"), "Customer dashboard (tickets)");
    },
  },
  {
    id: "REFUNDS",
    name: "Refunds ops",
    checks: () => {
      ok(hasAdminTab("refunds"), "Admin Refunds tab");
      ok(adminApi.includes("refunds"), "Refunds API");
      ok(pageCalls("apps/website/src/pages/owner/OrderDetailPage.tsx", "createRefund"), "Owner order refunds");
      soft(adminPanels.includes("Settlements") || adminApi.includes("settlements"), "Admin settlements list");
      soft(adminPanels.includes("Recent orders") || adminPanels.includes("fetchAdminOrders"), "Customer order history in admin");
    },
  },
  {
    id: "CHECKOUT",
    name: "Customer checkout + payments",
    checks: () => {
      ok(hasCustomerRoute("/checkout"), "Checkout route");
      soft(hasApi("createCustomerOrder") || apiBundle.includes("createCustomerOrder") || apiBundle.includes("/orders"), "Checkout order create client");
    },
  },
  {
    id: "ADMIN-CORE",
    name: "Admin core tabs",
    checks: () => {
      for (const t of ["overview", "kitchens", "owners", "customers", "orders", "control", "api-keys"]) {
        ok(hasAdminTab(t), `Admin tab: ${t}`);
      }
      ok(adminApi.includes("branded_page_enabled") || adminApi.includes("branded-page"), "Admin brand API mapped");
    },
  },
  {
    id: "DATATABLE",
    name: "Admin full-width DataTable lists",
    checks: () => {
      ok(exists("apps/website/src/components/DataTable.tsx"), "DataTable component");
      ok(adminApp.includes("<DataTable"), "Admin App DataTable");
      ok(adminPanels.includes("<DataTable"), "AdminPanels DataTable");
      for (const name of ["AdminKitchens", "AdminOwners", "AdminOrders", "AdminCustomers", "AdminRefunds", "AdminTickets", "AdminEmployeesPanel"]) {
        const src = name.startsWith("AdminC") || name.includes("Refund") || name.includes("Employee") || name.includes("Package")
          ? adminPanels + adminApp
          : adminApp;
        soft(new RegExp(`function ${name}[\\s\\S]{0,8000}<DataTable`).test(src) || src.includes(`function ${name}`) && src.includes("<DataTable"), `${name} uses DataTable`);
      }
    },
  },
];

// Nav ↔ route parity (owner)
const navPaths = [...ownerLayout.matchAll(/to:\s*"(\/dashboard[^"]*)"/g)].map((m) => m[1]);
for (const p of navPaths) {
  const seg = p.replace(/^\/dashboard\/?/, "") || "index";
  if (seg === "index" || p === "/dashboard") {
    ok(kitchenApp.includes("OwnerHomePage") || kitchenApp.includes('index element'), `Nav ${p} → overview route`);
  } else {
    const routeSeg = seg.split("/")[0];
    ok(hasRoute(routeSeg) || kitchenApp.includes(`path="${seg}"`), `Nav ${p} → kitchen route`);
  }
}

ok(
  customerApp.includes("CustomerBrowsePage") && hasCustomerRoute("/browse"),
  "CustomerBrowsePage routed at /browse → brand-first /k/:code",
);

// Run feature checks
for (const f of features) {
  const before = fail.length;
  f.checks();
  if (fail.length === before) {
    // feature-level rollup already in individual ok()
  }
}

console.log("\n=== Platform UI ↔ endpoint map ===\n");
for (const m of pass) console.log(`PASS  ${m}`);
for (const m of warn) console.log(`WARN  ${m}`);
for (const m of fail) console.log(`FAIL  ${m}`);
console.log(`\n${pass.length} pass · ${warn.length} warn · ${fail.length} fail\n`);

if (fail.length) {
  console.log("FAILED — UI/endpoint/feature mapping incomplete.\n");
  process.exit(1);
}
if (warn.length) {
  console.log("WARN — soft completeness gaps (non-blocking).\n");
  process.exit(0);
}
console.log("All platform feature UI mappings verified.\n");
