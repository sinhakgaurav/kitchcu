import { FormEvent, useEffect, useMemo, useState } from "react";
import { DataTable, type DataColumn } from "../components/DataTable";
import {
  adminLogin,
  clearAdminKitchenPaymentGateway,
  clearAdminToken,
  fetchAdminLoginHint,
  fetchAdminKitchen,
  fetchAdminKitchenModuleFlags,
  fetchAdminKitchenPaymentGateway,
  fetchAdminKitchens,
  fetchAdminKitchenPackage,
  fetchAdminKitchenTemplates,
  fetchAdminKitchenTiffinSummary,
  fetchAdminKitchenGstMonthly,
  fetchAdminKitchenGstProfile,
  downloadAdminKitchenGstExcel,
  downloadAdminKitchenGstPdf,
  fetchAdminKitchenWhatsApp,
  updateAdminKitchenDeliverySettings,
  updateAdminKitchenBrandedPage,
  uploadAdminKitchenBrandMedia,
  fetchAdminMe,
  fetchAdminEmployees,
  fetchAdminOrders,
  fetchAdminOwners,
  fetchAdminPackages,
  fetchAdminStats,
  fetchAdminTicket,
  fetchAdminTickets,
  fetchReferralLeads,
  fetchReferralSettings,
  grantReferralLead,
  patchReferralSettings,
  rejectReferralLead,
  getAdminToken,
  type AdminNavDetail,
  type AdminOrder,
  type AdminEmployee,
  type AdminTicket,
  adminNavigate,
  replyAdminTicket,
  setAdminToken,
  assignAdminKitchenPackage,
  updateAdminKitchenModuleFlag,
  updateAdminTicket,
  updateAdminOwnerSubscription,
  updateKitchenStatus,
  upsertAdminKitchenPaymentGateway,
  upsertAdminKitchenWhatsApp,
  type AdminKitchen,
  type AdminKitchenDetail,
  type AdminKitchenModuleFlags,
  type AdminKitchenPackage,
  type AdminKitchenPaymentGateway,
  type AdminKitchenWhatsApp,
  type AdminPackage,
  type AdminMe,
  type AdminGstMonthlyReport,
  type AdminGstProfile,
  type AdminReferralLead,
  type AdminReferralSettings,
  type AdminTiffinSummary,
  type PlatformStats,
} from "./adminApi";
import {
  AdminApiKeysPanel,
  AdminAuditPanel,
  AdminControlPlane,
  AdminCustomers,
  AdminEmployeesPanel,
  AdminPackagesPanel,
  AdminRefunds,
} from "./AdminPanels";
import {
  buildOrderTimeline,
  buildStatusBreakdown,
  buildTierBreakdown,
  buildTopKitchens,
} from "./adminCharts";
import { ADMIN_DEV_EMAIL, ADMIN_HOST, CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { DEMO_OWNERS, adminLoginDefaults } from "../shared/demo";
import { AuthLoginHighlights } from "../components/AuthLoginHighlights";
import { BrandAuthArt, BrandLogo } from "../components/BrandLogo";
import { BrandNavMark } from "../components/BrandNavMark";
import { customerUrl, kitchenUrl } from "../shared/urls";
import "../owner-app.css";

type Tab =
  | "overview"
  | "kitchens"
  | "owners"
  | "customers"
  | "orders"
  | "refunds"
  | "tickets"
  | "packages"
  | "employees"
  | "api-keys"
  | "control"
  | "audit"
  | "referrals";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "kitchens", label: "Kitchens" },
  { id: "owners", label: "Owners" },
  { id: "customers", label: "Customers" },
  { id: "orders", label: "Orders" },
  { id: "refunds", label: "Refunds" },
  { id: "tickets", label: "Tickets" },
  { id: "packages", label: "Packages" },
  { id: "employees", label: "Employees" },
  { id: "api-keys", label: "API Keys" },
  { id: "referrals", label: "Referrals" },
  { id: "control", label: "Control" },
  { id: "audit", label: "Audit" },
];

function chartDayLabel(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", { weekday: "short" });
}

const TAB_META: Record<Tab, { title: string; desc: string }> = {
  overview: {
    title: "Platform overview",
    desc: "Health snapshot across kitchens, customers, money, and support",
  },
  kitchens: {
    title: "Kitchens",
    desc: "Kitchen workspace — brand, WhatsApp, payments, GST, package, marketing, modules, streaming",
  },
  owners: { title: "Owners", desc: "Subscription tiers and kitchen counts — force plan changes" },
  customers: {
    title: "Customers",
    desc: "Full customer control — status, payout profile, addresses, password reset",
  },
  orders: { title: "Orders", desc: "Cross-kitchen order feed" },
  refunds: {
    title: "Refunds & money",
    desc: "Gateway and direct-transfer refunds — escalate, complete, or fail",
  },
  tickets: { title: "Support tickets", desc: "Customer and owner escalations from AI chat" },
  packages: {
    title: "Package mapper",
    desc: "Features → packages → owner/customer plans — assign on kitchen workspace",
  },
  employees: {
    title: "Employees",
    desc: "kitchCU staff CRUD with RBAC roles (superadmin, ops, support, finance)",
  },
  "api-keys": {
    title: "Platform API keys",
    desc: "Meta App Secret / Verify Token, platform Razorpay (SaaS), LiveKit, Maps, OAuth — not per-kitchen keys",
  },
  control: {
    title: "Control plane",
    desc: "Feature flags, data journeys, payments, and SaaS subscription overrides",
  },
  audit: {
    title: "Audit log",
    desc: "Who changed kitchens, flags, API keys, employees, and subscriptions",
  },
  referrals: {
    title: "Referrals",
    desc: "Configure dual referral rewards and manage kitchen / customer leads",
  },
};

const STAT_CARDS: {
  key: keyof PlatformStats;
  label: string;
  desc: string;
  accent: string;
}[] = [
  { key: "owners", label: "Registered owners", desc: "Kitchen operators on the platform", accent: "teal" },
  { key: "kitchens", label: "Total kitchens", desc: "All kitchen profiles created", accent: "orange" },
  { key: "active_kitchens", label: "Active kitchens", desc: "Currently accepting orders", accent: "green" },
  { key: "customers", label: "Customers", desc: "Registered diner accounts", accent: "blue" },
  { key: "orders", label: "Platform orders", desc: "Lifetime order count", accent: "blue" },
  { key: "dishes", label: "Menu dishes", desc: "Live-capture items across kitchens", accent: "purple" },
  { key: "refunds_open", label: "Open refunds", desc: "Needs owner or admin action", accent: "orange" },
  { key: "payments_captured", label: "Captured payments", desc: "Successful customer payments", accent: "green" },
];

export default function AdminApp() {
  const [token, setToken] = useState(getAdminToken());
  const [tab, setTab] = useState<Tab>("overview");
  const [me, setMe] = useState<AdminMe | null>(null);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [allOrders, setAllOrders] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
  const [owners, setOwners] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  const [kitchens, setKitchens] = useState<Awaited<ReturnType<typeof fetchAdminKitchens>>>([]);
  const [recentOrders, setRecentOrders] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
  const [openTickets, setOpenTickets] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [focusKitchenId, setFocusKitchenId] = useState<string | null>(null);
  const [refundSearch, setRefundSearch] = useState("");

  const visibleTabs =
    me?.allowed_tabs?.length
      ? TABS.filter((t) => me.allowed_tabs.includes(t.id))
      : me
        ? TABS
        : [];

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      let profile: AdminMe | null = null;
      try {
        profile = await fetchAdminMe();
        if (cancelled) return;
        setMe(profile);
        if (profile.allowed_tabs?.length) {
          setTab((prev) =>
            profile!.allowed_tabs.includes(prev)
              ? prev
              : ((profile!.allowed_tabs[0] as Tab) || "overview"),
          );
        }
      } catch {
        if (!cancelled) setMe(null);
      }

      const results = await Promise.allSettled([
        fetchAdminStats(),
        fetchAdminOrders(500),
        fetchAdminOwners(),
        fetchAdminKitchens(),
        fetchAdminTickets({ status: "open" }),
      ]);
      if (cancelled) return;
      const [s, orders, ownerRows, kitchenRows, tickets] = results;
      if (s.status === "fulfilled") setStats(s.value);
      if (orders.status === "fulfilled") {
        setAllOrders(orders.value);
        setRecentOrders(orders.value.slice(0, 6));
      }
      if (ownerRows.status === "fulfilled") setOwners(ownerRows.value);
      if (kitchenRows.status === "fulfilled") setKitchens(kitchenRows.value);
      if (tickets.status === "fulfilled") setOpenTickets(tickets.value.total);
      const firstErr = results.find((r) => r.status === "rejected") as PromiseRejectedResult | undefined;
      if (firstErr && results.every((r) => r.status === "rejected")) {
        setError(String(firstErr.reason?.message || firstErr.reason || "Failed to load"));
      } else {
        setError("");
      }
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const onNav = (ev: Event) => {
      const detail = (ev as CustomEvent<AdminNavDetail>).detail;
      if (!detail?.tab) return;
      setTab(detail.tab as Tab);
      if (detail.kitchenId) setFocusKitchenId(detail.kitchenId);
      if (detail.refundSearch) setRefundSearch(detail.refundSearch);
    };
    window.addEventListener("kitchcu-admin-nav", onNav);
    return () => window.removeEventListener("kitchcu-admin-nav", onNav);
  }, []);

  if (!token) {
    return <AdminLogin onSuccess={(t) => setToken(t)} />;
  }

  return (
    <div className="admin-shell">
      <aside className="admin-shell__sidebar">
        <div className="admin-shell__brand">
          <BrandNavMark subtitle={ADMIN_HOST} height={40} />
          <p className="admin-shell__tagline">Super admin · platform control center</p>
        </div>

        <nav className="admin-shell__nav" aria-label="Admin navigation">
          {visibleTabs.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "active" : ""}
              onClick={() => setTab(t.id)}
            >
              {t.id === "tickets" && openTickets > 0 ? `${t.label} (${openTickets})` : t.label}
            </button>
          ))}
        </nav>

        <div className="admin-shell__foot">
          <a href={customerUrl("/")} className="admin-app__ext-link" title={CUSTOMER_HOST} target="_blank" rel="noopener noreferrer">
            Customer app
          </a>
          <a href={kitchenUrl("/")} className="admin-app__ext-link" title={KITCHEN_HOST} target="_blank" rel="noopener noreferrer">
            Kitchen app
          </a>
        </div>
      </aside>

      <div className="admin-shell__main">
        <header className="admin-shell__topbar">
          {me && (
            <span className="owner-muted" style={{ marginRight: "auto" }}>
              {me.name} · <strong>{me.role}</strong>
            </span>
          )}
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              clearAdminToken();
              setToken(null);
              setMe(null);
            }}
          >
            Sign out
          </button>
        </header>

        <div className="admin-main">
          <header className="admin-section-head">
            <h1>{TAB_META[tab]?.title || "Admin"}</h1>
            <p>{TAB_META[tab]?.desc || ""}</p>
          </header>

          {error && <p className="auth-card__error">{error}</p>}

          {tab === "overview" && (
            <AdminOverview
              stats={stats}
              allOrders={allOrders}
              owners={owners}
              kitchens={kitchens}
              recentOrders={recentOrders}
              openTickets={openTickets}
              loading={loading}
              onNavigate={setTab}
            />
          )}

          {tab === "kitchens" && (
            <AdminKitchens
              focusKitchenId={focusKitchenId}
              onFocusConsumed={() => setFocusKitchenId(null)}
            />
          )}
          {tab === "owners" && <AdminOwners />}
          {tab === "customers" && <AdminCustomers />}
          {tab === "orders" && <AdminOrders />}
          {tab === "refunds" && <AdminRefunds initialSearch={refundSearch} />}
          {tab === "tickets" && <AdminTickets />}
          {tab === "packages" && <AdminPackagesPanel />}
          {tab === "employees" && <AdminEmployeesPanel />}
          {tab === "api-keys" && <AdminApiKeysPanel />}
          {tab === "referrals" && <AdminReferralsPanel />}
          {tab === "control" && <AdminControlPlane />}
          {tab === "audit" && <AdminAuditPanel />}
        </div>
      </div>
    </div>
  );
}

function AdminOverview({
  stats,
  allOrders,
  owners,
  kitchens,
  recentOrders,
  openTickets,
  loading,
  onNavigate,
}: {
  stats: PlatformStats | null;
  allOrders: Awaited<ReturnType<typeof fetchAdminOrders>>;
  owners: Awaited<ReturnType<typeof fetchAdminOwners>>;
  kitchens: Awaited<ReturnType<typeof fetchAdminKitchens>>;
  recentOrders: Awaited<ReturnType<typeof fetchAdminOrders>>;
  openTickets: number;
  loading: boolean;
  onNavigate: (tab: Tab) => void;
}) {
  const timeline = buildOrderTimeline(allOrders, 14);
  const statusBreakdown = buildStatusBreakdown(allOrders);
  const topKitchens = buildTopKitchens(allOrders, 6);
  const tierBreakdown = buildTierBreakdown(owners);
  const maxTimeline = Math.max(1, ...timeline.map((p) => p.count));
  const maxStatus = Math.max(1, ...statusBreakdown.map((s) => s.count));
  const maxKitchen = Math.max(1, ...topKitchens.map((k) => k.count));
  const maxTier = Math.max(1, ...tierBreakdown.map((t) => t.count));
  const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;
  if (loading) {
    return (
      <div className="admin-overview__loading">
        <div className="od-skeleton od-skeleton--wide" />
        <div className="admin-stats admin-stats--rich">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="od-skeleton od-skeleton--card" />
          ))}
        </div>
        <div className="admin-charts">
          <div className="od-skeleton od-skeleton--chart" />
          <div className="od-skeleton od-skeleton--chart" />
        </div>
        <div className="admin-charts">
          <div className="od-skeleton od-skeleton--chart" />
          <div className="od-skeleton od-skeleton--chart" />
        </div>
      </div>
    );
  }

  if (!stats) return <p className="owner-empty">Could not load platform stats.</p>;

  const activationRate = stats.kitchens > 0
    ? Math.round((stats.active_kitchens / stats.kitchens) * 100)
    : 0;

  const suspendedKitchens = kitchens.filter((k) => k.status === "suspended").length;
  const trialOwners = owners.filter((o) => o.subscription_tier === "trial").length;
  const inactiveOwners = owners.filter((o) => o.subscription_status !== "active").length;
  const openRefunds = stats.refunds_open ?? 0;
  const attentionItems = [
    {
      key: "tickets",
      count: openTickets,
      label: "Open tickets",
      hint: openTickets > 0 ? "Support queue needs replies" : "Queue clear",
      tab: "tickets" as Tab,
      tone: openTickets > 0 ? "alert" : "ok",
    },
    {
      key: "refunds",
      count: openRefunds,
      label: "Open refunds",
      hint: openRefunds > 0 ? "Escalate or complete refunds" : "No pending refunds",
      tab: "refunds" as Tab,
      tone: openRefunds > 0 ? "alert" : "ok",
    },
    {
      key: "suspended",
      count: suspendedKitchens,
      label: "Suspended kitchens",
      hint: suspendedKitchens > 0 ? "Review moderation list" : "All kitchens active",
      tab: "kitchens" as Tab,
      tone: suspendedKitchens > 0 ? "warn" : "ok",
    },
    {
      key: "trial",
      count: trialOwners,
      label: "Trial owners",
      hint: "Convert to paid subscription",
      tab: "owners" as Tab,
      tone: trialOwners > 0 ? "warn" : "ok",
    },
    {
      key: "billing",
      count: inactiveOwners,
      label: "Billing issues",
      hint: inactiveOwners > 0 ? "Non-active subscriptions" : "All subscriptions active",
      tab: "owners" as Tab,
      tone: inactiveOwners > 0 ? "alert" : "ok",
    },
  ];

  return (
    <>
      <div className="admin-attention">
        {attentionItems.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`dash-card admin-attention__item admin-attention__item--${item.tone}`}
            onClick={() => onNavigate(item.tab)}
          >
            <strong>{item.count}</strong>
            <span>{item.label}</span>
            <em>{item.hint}</em>
          </button>
        ))}
      </div>

      <section className="dash-card admin-hero">
        <div>
          <p className="admin-hero__eyebrow">Platform health</p>
          <h2>{stats.active_kitchens} kitchens live</h2>
          <p>
            {activationRate}% activation rate · {stats.owners} owner{stats.owners !== 1 ? "s" : ""} ·{" "}
            {stats.orders.toLocaleString("en-IN")} orders processed
          </p>
        </div>
        <div className="admin-hero__actions">
          <button type="button" className="btn btn--primary btn--sm" onClick={() => onNavigate("control")}>
            Open control plane
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => onNavigate("kitchens")}>
            Manage kitchens
          </button>
          {openTickets > 0 && (
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => onNavigate("tickets")}>
              {openTickets} open ticket{openTickets !== 1 ? "s" : ""}
            </button>
          )}
        </div>
      </section>

      <div className="admin-stats admin-stats--rich">
        {STAT_CARDS.map((card) => {
          const value = stats[card.key] ?? 0;
          return (
            <div key={card.key} className={`dash-card admin-stat-card admin-stat-card--${card.accent}`}>
              <strong>{Number(value).toLocaleString("en-IN")}</strong>
              <span>{card.label}</span>
              <em>{card.desc}</em>
            </div>
          );
        })}
      </div>

      <div className="admin-charts">
        <section className="dash-card admin-panel admin-chart-panel">
          <header className="admin-panel__head">
            <h3>Orders · last 14 days</h3>
            <span className="admin-chart-panel__sub">From recent platform activity</span>
          </header>
          {timeline.every((p) => p.count === 0) ? (
            <p className="admin-panel__empty">No orders in the last two weeks.</p>
          ) : (
            <div className="report-bars admin-chart-bars">
              {timeline.map((p) => (
                <div
                  key={p.date}
                  className="report-bars__col"
                  title={`${p.date}: ${p.count} orders · ${inr(p.revenue)}`}
                >
                  <div
                    className="report-bars__fill admin-chart-bars__fill--orders"
                    style={{ height: `${(p.count / maxTimeline) * 100}%` }}
                  />
                  <span className="report-bars__label">{chartDayLabel(p.date)}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="dash-card admin-panel admin-chart-panel">
          <header className="admin-panel__head">
            <h3>Order status mix</h3>
            <span className="admin-chart-panel__sub">Current pipeline distribution</span>
          </header>
          {statusBreakdown.length === 0 ? (
            <p className="admin-panel__empty">No status data yet.</p>
          ) : (
            <ul className="admin-breakdown">
              {statusBreakdown.map((s) => (
                <li key={s.status}>
                  <div className="admin-breakdown__row">
                    <span className={`status-badge status-badge--${s.status}`}>{s.status}</span>
                    <strong>{s.count}</strong>
                  </div>
                  <div className="report-rank__track">
                    <div
                      className={`report-rank__bar admin-breakdown__bar admin-breakdown__bar--${s.status}`}
                      style={{ width: `${(s.count / maxStatus) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="admin-charts">
        <section className="dash-card admin-panel admin-chart-panel">
          <header className="admin-panel__head">
            <h3>Top kitchens</h3>
            <span className="admin-chart-panel__sub">By order volume (recent sample)</span>
          </header>
          {topKitchens.length === 0 ? (
            <p className="admin-panel__empty">No kitchen activity yet.</p>
          ) : (
            <ul className="admin-breakdown">
              {topKitchens.map((k) => (
                <li key={k.name}>
                  <div className="admin-breakdown__row">
                    <span>{k.name}</span>
                    <strong>{k.count} · {inr(k.revenue)}</strong>
                  </div>
                  <div className="report-rank__track">
                    <div
                      className="report-rank__bar admin-breakdown__bar--teal"
                      style={{ width: `${(k.count / maxKitchen) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dash-card admin-panel admin-chart-panel">
          <header className="admin-panel__head">
            <h3>Owner subscription tiers</h3>
            <span className="admin-chart-panel__sub">SaaS plan distribution</span>
          </header>
          {tierBreakdown.length === 0 ? (
            <p className="admin-panel__empty">No owners registered yet.</p>
          ) : (
            <ul className="admin-breakdown">
              {tierBreakdown.map((t) => (
                <li key={t.tier}>
                  <div className="admin-breakdown__row">
                    <span className="od-pill od-pill--sub">{t.tier}</span>
                    <strong>{t.count} owner{t.count !== 1 ? "s" : ""}</strong>
                  </div>
                  <div className="report-rank__track">
                    <div
                      className="report-rank__bar admin-breakdown__bar--purple"
                      style={{ width: `${(t.count / maxTier) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="admin-overview__grid">
        <section className="dash-card admin-panel">
          <header className="admin-panel__head">
            <h3>Recent orders</h3>
            <button type="button" className="admin-panel__link" onClick={() => onNavigate("orders")}>
              View all →
            </button>
          </header>
          {recentOrders.length === 0 ? (
            <p className="admin-panel__empty">No orders on the platform yet.</p>
          ) : (
            <table className="admin-table admin-table--compact">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Kitchen</th>
                  <th>Status</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((o) => (
                  <tr key={o.id}>
                    <td><code className="admin-code">{o.order_code}</code></td>
                    <td>{o.kitchen_name}</td>
                    <td><span className={`status-badge status-badge--${o.status}`}>{o.status}</span></td>
                    <td>₹{o.total.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="dash-card admin-panel">
          <header className="admin-panel__head">
            <h3>Quick actions</h3>
          </header>
          <div className="admin-quick">
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("customers")}>
              <strong>Customer control</strong>
              <span>Suspend accounts, reset passwords, view payouts</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("refunds")}>
              <strong>Refund oversight</strong>
              <span>Escalate gateway and direct transfers</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("api-keys")}>
              <strong>API keys</strong>
              <span>Add / update Razorpay, LiveKit, WhatsApp secrets</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("control")}>
              <strong>Feature flags & journeys</strong>
              <span>Kill-switches across app data journeys</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("tickets")}>
              <strong>Support queue</strong>
              <span>{openTickets} open tickets need attention</span>
            </button>
          </div>
          <div className="admin-panel__note">
            <p>
              <strong>Access:</strong>{" "}
              {adminLoginDefaults().isProductionHost
                ? "admin@kitchcu.com (VM ADMIN_PASSWORD)"
                : `${ADMIN_DEV_EMAIL} / admin123456`}
            </p>
            <p>Gateway API: <code>/api/v1/admin/*</code> · Port <code>13003</code> locally</p>
          </div>
        </section>
      </div>
    </>
  );
}

function AdminLogin({ onSuccess }: { onSuccess: (token: string) => void }) {
  const defaults = adminLoginDefaults();
  const [email, setEmail] = useState(defaults.email);
  const [password, setPassword] = useState(defaults.password);
  const [revealedPassword, setRevealedPassword] = useState<string | null>(
    defaults.isProductionHost ? null : defaults.password || null,
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const hint = await fetchAdminLoginHint();
        if (cancelled) return;
        if (hint.email) setEmail(hint.email);
        if (hint.revealed && hint.password) {
          setPassword(hint.password);
          setRevealedPassword(hint.password);
        }
      } catch {
        /* identity down — keep hostname defaults */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await adminLogin(email, password);
      setAdminToken(res.access_token);
      onSuccess(res.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page admin-login">
      <div className="auth-page__visual admin-login__visual">
        <div className="auth-page__overlay" />
        <div className="auth-page__brand-stack">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <h1>Platform control</h1>
          <p>Full visibility over kitchens, owners, orders, and support.</p>
          <AuthLoginHighlights surface="admin" />
          <BrandAuthArt surface="admin" />
        </div>
      </div>
      <div className="auth-page__form-wrap">
        <div className="auth-page__mobile-brand">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <p>Platform control · {ADMIN_HOST}</p>
        </div>
        <form className="auth-card admin-login__card" onSubmit={submit}>
          <p className="admin-login__eyebrow">Super admin</p>
          <h1>Sign in</h1>
          <p>Use the platform admin credentials for {ADMIN_HOST}.</p>
          {error && <div className="auth-card__error">{error}</div>}
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input
              type={revealedPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
          <p className="auth-card__hint">
            {revealedPassword ? (
              <>
                Admin: <strong>{email}</strong> · password: <code>{revealedPassword}</code>
                {defaults.isProductionHost ? (
                  <>
                    {" "}
                    (from VM <code>ADMIN_PASSWORD</code> / GCE <code>admin-password</code>; synced on login)
                  </>
                ) : null}
              </>
            ) : defaults.isProductionHost ? (
              <>
                Production admin: <strong>admin@kitchcu.com</strong> — password from VM{" "}
                <code>ADMIN_PASSWORD</code> / GCE metadata <code>admin-password</code> (synced on login).
                Do not use <code>admin@kitchcu.dev</code> here.
              </>
            ) : (
              <>
                Dev admin: {defaults.email} / {defaults.password}
              </>
            )}
            <br />
            Owner demos: {DEMO_OWNERS.map((o) => o.phone).join(", ")} (OTP 123456)
            {" · "}
            <a href={kitchenUrl("/login")} target="_blank" rel="noopener noreferrer">Owner app</a>
          </p>
        </form>
      </div>
    </div>
  );
}

function AdminKitchens({
  focusKitchenId,
  onFocusConsumed,
}: {
  focusKitchenId?: string | null;
  onFocusConsumed?: () => void;
} = {}) {
  const [rows, setRows] = useState<AdminKitchen[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [kitchenOrders, setKitchenOrders] = useState<AdminOrder[]>([]);
  const [detail, setDetail] = useState<AdminKitchenDetail | null>(null);
  const [wa, setWa] = useState<AdminKitchenWhatsApp | null>(null);
  const [pgw, setPgw] = useState<AdminKitchenPaymentGateway | null>(null);
  const [modules, setModules] = useState<AdminKitchenModuleFlags | null>(null);
  const [kitchenPkg, setKitchenPkg] = useState<AdminKitchenPackage | null>(null);
  const [allPackages, setAllPackages] = useState<AdminPackage[]>([]);
  const [templates, setTemplates] = useState<{ id: string; channel: string; name: string; is_active: boolean; body: string }[]>([]);
  const [panelTab, setPanelTab] = useState<
    | "profile"
    | "brand"
    | "whatsapp"
    | "payments"
    | "package"
    | "marketing"
    | "modules"
    | "streaming"
    | "delivery"
    | "tiffin"
    | "gst"
    | "orders"
  >("profile");
  const [porterAutoBook, setPorterAutoBook] = useState(true);
  const [porterDelayMin, setPorterDelayMin] = useState(15);
  const [tiffinSummary, setTiffinSummary] = useState<AdminTiffinSummary | null>(null);
  const [gstProfile, setGstProfile] = useState<AdminGstProfile | null>(null);
  const [gstReport, setGstReport] = useState<AdminGstMonthlyReport | null>(null);
  const gstNow = useMemo(() => new Date(), []);
  const [gstYear, setGstYear] = useState(gstNow.getFullYear());
  const [gstMonth, setGstMonth] = useState(gstNow.getMonth() + 1);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [phoneId, setPhoneId] = useState("");
  const [displayPhone, setDisplayPhone] = useState("");
  const [brandTagline, setBrandTagline] = useState("");
  const [brandAccent, setBrandAccent] = useState("#0F766E");
  const [brandLogoUrl, setBrandLogoUrl] = useState<string | null>(null);
  const [brandBackgroundUrl, setBrandBackgroundUrl] = useState<string | null>(null);
  const [brandUploading, setBrandUploading] = useState<"logo" | "background" | null>(null);
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [linkedAccountId, setLinkedAccountId] = useState("");
  const [pgwActive, setPgwActive] = useState(true);
  const [assignPackageId, setAssignPackageId] = useState("");

  const reloadList = async () => {
    setRows(await fetchAdminKitchens());
  };

  const openKitchen = async (id: string) => {
    setSelectedId(id);
    setError("");
    setOk("");
    setPanelTab("profile");
    try {
      const [d, w, p, m, pkg, pkgs, tmpl, tf] = await Promise.all([
        fetchAdminKitchen(id),
        fetchAdminKitchenWhatsApp(id),
        fetchAdminKitchenPaymentGateway(id),
        fetchAdminKitchenModuleFlags(id),
        fetchAdminKitchenPackage(id).catch(() => null),
        fetchAdminPackages("owner").catch(() => [] as AdminPackage[]),
        fetchAdminKitchenTemplates(id).catch(() => []),
        fetchAdminKitchenTiffinSummary(id).catch(() => null),
      ]);
      setDetail(d);
      setWa(w);
      setKitchenPkg(pkg);
      setAllPackages(pkgs);
      setTemplates(tmpl);
      setTiffinSummary(tf);
      setGstProfile(null);
      setGstReport(null);
      setKitchenOrders([]);
      setAssignPackageId(pkg?.package?.id ?? pkgs[0]?.id ?? "");
      void fetchAdminOrders(50, { kitchen_id: id })
        .then(setKitchenOrders)
        .catch(() => setKitchenOrders([]));
      setPgw(p);
      setModules(m);
      setPorterAutoBook(d.porter_auto_book_enabled !== false);
      setPorterDelayMin(d.porter_auto_book_delay_min ?? 15);
      setPhoneId(w.whatsapp_phone_id ?? "");
      setDisplayPhone(w.whatsapp_display_phone ?? "");
      setBrandTagline(d.branded_page?.tagline ?? "");
      setBrandAccent(d.branded_page?.accent_color ?? "#0F766E");
      setBrandLogoUrl(d.branded_page?.logo_url ?? null);
      setBrandBackgroundUrl(d.branded_page?.background_url ?? null);
      setKeyId(p.key_id ?? "");
      setLinkedAccountId(p.linked_account_id ?? "");
      setPgwActive(p.is_active);
      setKeySecret("");
      setWebhookSecret("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load kitchen workspace");
    }
  };

  useEffect(() => {
    reloadList()
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (focusKitchenId) {
      void openKitchen(focusKitchenId).finally(() => onFocusConsumed?.());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- open on focus prop only
  }, [focusKitchenId]);

  const active = rows.filter((k) => k.status === "active").length;
  const suspended = rows.filter((k) => k.status === "suspended").length;
  const waLinked = rows.filter((k) => k.whatsapp_connected).length;
  const pgwReady = rows.filter((k) => k.payment_gateway_configured).length;

  const kitchenColumns = useMemo<DataColumn<AdminKitchen>[]>(
    () => [
      {
        id: "code",
        header: "Code",
        sortable: true,
        sortValue: (k) => k.code,
        cell: (k) => <code className="admin-code">{k.code}</code>,
      },
      {
        id: "name",
        header: "Name",
        sortable: true,
        sortValue: (k) => k.name,
        cell: (k) => k.name,
      },
      {
        id: "owner",
        header: "Owner",
        sortable: true,
        sortValue: (k) => k.owner_name,
        cell: (k) => k.owner_name,
      },
      {
        id: "wa",
        header: "WA",
        sortable: true,
        sortValue: (k) => (k.whatsapp_connected ? 1 : 0),
        cell: (k) => (k.whatsapp_connected ? "●" : "○"),
      },
      {
        id: "pay",
        header: "Pay",
        sortable: true,
        sortValue: (k) => (k.payment_gateway_configured ? 1 : 0),
        cell: (k) => (k.payment_gateway_configured ? "●" : "○"),
      },
      {
        id: "brand",
        header: "Brand",
        sortable: true,
        sortValue: (k) => (k.branded_page_enabled ? 1 : 0),
        cell: (k) => (k.branded_page_enabled ? "●" : "○"),
      },
      {
        id: "health",
        header: "Care",
        sortable: true,
        sortValue: (k) => (k.open_ticket_count ?? 0) + (k.open_refund_count ?? 0),
        cell: (k) => {
          const t = k.open_ticket_count ?? 0;
          const r = k.open_refund_count ?? 0;
          if (!t && !r) return "—";
          return (
            <span title="Open tickets / open refunds">
              {t ? `${t} tix` : ""}
              {t && r ? " · " : ""}
              {r ? `${r} ref` : ""}
            </span>
          );
        },
      },
      {
        id: "last_order",
        header: "Last order",
        sortable: true,
        sortValue: (k) => k.last_order_at ?? "",
        cell: (k) =>
          k.last_order_at ? new Date(k.last_order_at).toLocaleDateString("en-IN") : "—",
      },
      {
        id: "status",
        header: "Status",
        sortable: true,
        sortValue: (k) => k.status,
        cell: (k) => <span className={`status-badge status-badge--${k.status}`}>{k.status}</span>,
      },
      {
        id: "workspace",
        header: "Workspace",
        cell: (k) => (
          <button type="button" className="btn btn--sm btn--primary" onClick={() => openKitchen(k.id)}>
            Open
          </button>
        ),
      },
    ],
    // openKitchen closes over setters only — stable enough for column defs
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const saveBrandedPage = async (enabled?: boolean) => {
    if (!selectedId) return;
    setBusy(true);
    setError("");
    try {
      const next = await updateAdminKitchenBrandedPage(selectedId, {
        enabled,
        tagline: brandTagline.trim() || null,
        accent_color: brandAccent.trim() || null,
        logo_url: brandLogoUrl,
        background_url: brandBackgroundUrl,
      });
      setDetail(next);
      setBrandTagline(next.branded_page?.tagline ?? "");
      setBrandAccent(next.branded_page?.accent_color ?? "#0F766E");
      setBrandLogoUrl(next.branded_page?.logo_url ?? null);
      setBrandBackgroundUrl(next.branded_page?.background_url ?? null);
      await reloadList();
      setOk(
        enabled === true
          ? "Branded page published."
          : enabled === false
            ? "Branded page unpublished."
            : "Brand page saved.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Brand page update failed");
    } finally {
      setBusy(false);
    }
  };

  const uploadBrandMedia = async (slot: "logo" | "background", file: File | null) => {
    if (!selectedId || !file) return;
    setBrandUploading(slot);
    setError("");
    try {
      const next = await uploadAdminKitchenBrandMedia(selectedId, file, slot, file.name || `${slot}.jpg`);
      setDetail(next);
      setBrandLogoUrl(next.branded_page?.logo_url ?? null);
      setBrandBackgroundUrl(next.branded_page?.background_url ?? null);
      setOk(slot === "logo" ? "Logo uploaded." : "Background uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Brand media upload failed");
    } finally {
      setBrandUploading(null);
    }
  };

  const setStatus = async (id: string, status: string) => {
    setBusy(true);
    try {
      await updateKitchenStatus(id, status);
      await reloadList();
      if (selectedId === id) await openKitchen(id);
      setOk(`Kitchen marked ${status}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Status update failed");
    } finally {
      setBusy(false);
    }
  };

  const saveWhatsApp = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    setBusy(true);
    setError("");
    try {
      const next = await upsertAdminKitchenWhatsApp(selectedId, {
        whatsapp_phone_id: phoneId.trim() || null,
        whatsapp_display_phone: displayPhone.trim() || null,
      });
      setWa(next);
      await reloadList();
      setOk("WhatsApp phone ID saved for this kitchen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "WhatsApp save failed");
    } finally {
      setBusy(false);
    }
  };

  const clearWhatsApp = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      const next = await upsertAdminKitchenWhatsApp(selectedId, { clear: true });
      setWa(next);
      setPhoneId("");
      setDisplayPhone("");
      await reloadList();
      setOk("WhatsApp disconnected for this kitchen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setBusy(false);
    }
  };

  const savePayments = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    setBusy(true);
    setError("");
    try {
      const next = await upsertAdminKitchenPaymentGateway(selectedId, {
        key_id: keyId,
        key_secret: keySecret || undefined,
        webhook_secret: webhookSecret || undefined,
        linked_account_id: linkedAccountId,
        is_active: pgwActive,
      });
      setPgw(next);
      setKeySecret("");
      setWebhookSecret("");
      await reloadList();
      setOk("Kitchen Razorpay credentials saved (secrets encrypted).");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment gateway save failed");
    } finally {
      setBusy(false);
    }
  };

  const clearPayments = async () => {
    if (!selectedId) return;
    if (!window.confirm("Clear Razorpay credentials for this kitchen?")) return;
    setBusy(true);
    try {
      const next = await clearAdminKitchenPaymentGateway(selectedId);
      setPgw(next);
      setKeyId("");
      setLinkedAccountId("");
      await reloadList();
      setOk("Kitchen payment gateway cleared.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clear failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleModule = async (moduleKey: string, enabled: boolean) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminKitchenModuleFlag(selectedId, moduleKey, enabled);
      setModules(await fetchAdminKitchenModuleFlags(selectedId));
      setOk(`${moduleKey} ${enabled ? "enabled" : "disabled"}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Module update failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="admin-tab-kpis">
        <div className="dash-card admin-stat-card admin-stat-card--teal">
          <strong>{rows.length}</strong>
          <span>Total kitchens</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--green">
          <strong>{active}</strong>
          <span>Active</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--orange">
          <strong>{suspended}</strong>
          <span>Suspended</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--purple">
          <strong>{waLinked}/{pgwReady}</strong>
          <span>WA / payments linked</span>
        </div>
      </div>

      {error && <p className="auth-card__error">{error}</p>}
      {ok && <p className="auth-card__success">{ok}</p>}

      <div
        className={`admin-kitchen-workspace${detail && selectedId ? "" : " admin-kitchen-workspace--list-only"}`}
      >
        <DataTable
          rows={rows}
          loading={loading}
          emptyMessage="No kitchens yet."
          searchPlaceholder="Search code, name, owner…"
          getSearchText={(k) => `${k.code} ${k.name} ${k.owner_name} ${k.status}`}
          filterChips={[
            { id: "", label: "All" },
            { id: "active", label: "Active" },
            { id: "suspended", label: "Suspended" },
          ]}
          getFilterValue={(k) => k.status}
          rowKey={(k) => k.id}
          rowClassName={(k) => (selectedId === k.id ? "admin-table__row--active" : undefined)}
          columns={kitchenColumns}
        />

        {detail && selectedId && (
          <section className="dash-card admin-kitchen-panel">
            <header className="admin-kitchen-panel__head">
              <div>
                <h2>{detail.name}</h2>
                <p>
                  <code className="admin-code">{detail.code}</code>
                  {" · "}
                  {detail.owner_name} · {detail.city ?? "—"}
                </p>
              </div>
              <div className="admin-kitchen-panel__status">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => {
                    setSelectedId(null);
                    setDetail(null);
                  }}
                >
                  Close
                </button>
                {detail.status !== "active" && (
                  <button type="button" className="btn btn--sm btn--primary" disabled={busy} onClick={() => setStatus(selectedId, "active")}>
                    Activate
                  </button>
                )}
                {detail.status === "active" && (
                  <button type="button" className="btn btn--sm btn--ghost" disabled={busy} onClick={() => setStatus(selectedId, "suspended")}>
                    Suspend
                  </button>
                )}
              </div>
            </header>

            <div className="admin-kitchen-panel__tabs">
              {(
                [
                  "profile",
                  "brand",
                  "whatsapp",
                  "payments",
                  "package",
                  "marketing",
                  "modules",
                  "orders",
                  "streaming",
                  "delivery",
                  "tiffin",
                  "gst",
                ] as const
              ).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={panelTab === t ? "active" : ""}
                  onClick={() => {
                    setPanelTab(t);
                    if (t === "orders" && selectedId) {
                      void fetchAdminOrders(50, { kitchen_id: selectedId })
                        .then(setKitchenOrders)
                        .catch(() => setKitchenOrders([]));
                    }
                    if (t === "gst" && selectedId) {
                      void (async () => {
                        setError("");
                        try {
                          const [prof, rep] = await Promise.all([
                            fetchAdminKitchenGstProfile(selectedId).catch(() => null),
                            fetchAdminKitchenGstMonthly(selectedId, gstYear, gstMonth).catch(
                              () => null,
                            ),
                          ]);
                          setGstProfile(prof);
                          setGstReport(rep);
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "GST load failed");
                        }
                      })();
                    }
                  }}
                >
                  {t === "whatsapp"
                    ? "WhatsApp"
                    : t === "payments"
                      ? "Payments"
                      : t === "gst"
                        ? "GST"
                        : t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {panelTab === "orders" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Last {kitchenOrders.length} orders for this kitchen (platform read). Open Tickets /
                  Refunds tabs for care actions.
                </p>
                {kitchenOrders.length === 0 ? (
                  <p className="admin-panel__empty">No orders yet for this kitchen.</p>
                ) : (
                  <div className="owner-table-wrap">
                    <table className="owner-table">
                      <thead>
                        <tr>
                          <th>Order</th>
                          <th>Status</th>
                          <th>Customer</th>
                          <th>Total</th>
                          <th>When</th>
                        </tr>
                      </thead>
                      <tbody>
                        {kitchenOrders.map((o) => (
                          <tr key={o.id}>
                            <td><code>{o.order_code}</code></td>
                            <td>
                              <span className={`status-badge status-badge--${o.status}`}>{o.status}</span>
                            </td>
                            <td>{o.customer_name || o.customer_phone || "—"}</td>
                            <td>₹{o.total.toFixed(0)}</td>
                            <td>{new Date(o.created_at).toLocaleString("en-IN")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {panelTab === "profile" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">{detail.platform_secrets_note}</p>
                <dl className="admin-kv">
                  <div><dt>Owner phone</dt><dd>{detail.owner_phone}</dd></div>
                  <div><dt>Address</dt><dd>{detail.address_line ?? "—"}</dd></div>
                  <div><dt>State / PIN</dt><dd>{detail.state ?? "—"} / {detail.pincode ?? "—"}</dd></div>
                  <div><dt>WhatsApp</dt><dd>{detail.whatsapp_connected ? "Linked" : "Not linked"}</dd></div>
                  <div><dt>Payment gateway</dt><dd>{detail.payment_gateway_configured ? "Configured" : "Not set"}</dd></div>
                  <div>
                    <dt>Brand page</dt>
                    <dd>{detail.branded_page?.enabled || detail.branded_page_enabled ? "Published" : "Not published"}</dd>
                  </div>
                  <div>
                    <dt>Last order</dt>
                    <dd>
                      {detail.last_order_at
                        ? new Date(detail.last_order_at).toLocaleString("en-IN")
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>Open tickets</dt>
                    <dd>{detail.open_ticket_count ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Open refunds</dt>
                    <dd>{detail.open_refund_count ?? 0}</dd>
                  </div>
                </dl>
              </div>
            )}

            {panelTab === "brand" && (
              <div className="admin-kitchen-panel__body owner-forms">
                <p className="report-hint">
                  Customer storefront at <code>/k/{detail.code}</code>. Same fields as owner Brand page — logo,
                  background, tagline, accent. Message templates use <code>{"{{storefront_url}}"}</code>.
                </p>
                <dl className="admin-kv">
                  <div>
                    <dt>Public link</dt>
                    <dd>
                      <a
                        href={customerUrl(`/k/${detail.code}`)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {customerUrl(`/k/${detail.code}`)}
                      </a>
                    </dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{detail.branded_page?.enabled ? "Published" : "Not published"}</dd>
                  </div>
                </dl>
                <div className="od-brand-media" style={{ marginBottom: "1rem" }}>
                  <div className="od-brand-media__slot">
                    <span>Logo</span>
                    {brandLogoUrl ? (
                      <img src={brandLogoUrl} alt="" className="od-brand-media__preview od-brand-media__preview--logo" />
                    ) : (
                      <div className="od-brand-media__empty">No logo</div>
                    )}
                    <label className="btn btn--ghost btn--sm">
                      {brandUploading === "logo" ? "Uploading…" : "Upload logo"}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        hidden
                        disabled={!!brandUploading || busy}
                        onChange={(e) => {
                          void uploadBrandMedia("logo", e.target.files?.[0] ?? null);
                          e.target.value = "";
                        }}
                      />
                    </label>
                    {brandLogoUrl && (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={() => {
                          setBrandLogoUrl(null);
                          void updateAdminKitchenBrandedPage(selectedId!, { logo_url: "" }).then((next) => {
                            setDetail(next);
                            setBrandLogoUrl(next.branded_page?.logo_url ?? null);
                          });
                        }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="od-brand-media__slot">
                    <span>Background</span>
                    {brandBackgroundUrl ? (
                      <img
                        src={brandBackgroundUrl}
                        alt=""
                        className="od-brand-media__preview od-brand-media__preview--bg"
                      />
                    ) : (
                      <div className="od-brand-media__empty">No background</div>
                    )}
                    <label className="btn btn--ghost btn--sm">
                      {brandUploading === "background" ? "Uploading…" : "Upload background"}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        hidden
                        disabled={!!brandUploading || busy}
                        onChange={(e) => {
                          void uploadBrandMedia("background", e.target.files?.[0] ?? null);
                          e.target.value = "";
                        }}
                      />
                    </label>
                    {brandBackgroundUrl && (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={() => {
                          setBrandBackgroundUrl(null);
                          void updateAdminKitchenBrandedPage(selectedId!, { background_url: "" }).then((next) => {
                            setDetail(next);
                            setBrandBackgroundUrl(next.branded_page?.background_url ?? null);
                          });
                        }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
                <label>
                  Tagline
                  <input
                    value={brandTagline}
                    onChange={(e) => setBrandTagline(e.target.value)}
                    maxLength={160}
                    placeholder="Home-style thalis · live-capture menu"
                  />
                </label>
                <label>
                  Accent colour
                  <input
                    value={brandAccent}
                    onChange={(e) => setBrandAccent(e.target.value.toUpperCase())}
                    maxLength={7}
                    placeholder="#0F766E"
                  />
                </label>
                <div className="owner-forms__actions">
                  <button
                    type="button"
                    className="btn btn--primary"
                    disabled={busy}
                    onClick={() => saveBrandedPage(true)}
                  >
                    Publish
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={busy}
                    onClick={() => saveBrandedPage()}
                  >
                    Save content
                  </button>
                  {detail.branded_page?.enabled && (
                    <button
                      type="button"
                      className="btn btn--ghost"
                      disabled={busy}
                      onClick={() => saveBrandedPage(false)}
                    >
                      Unpublish
                    </button>
                  )}
                </div>
              </div>
            )}

            {panelTab === "whatsapp" && !wa && (
              <p className="admin-kitchen-panel__body report-hint">
                WhatsApp settings unavailable. Close and reopen this kitchen, or check the gateway.
              </p>
            )}
            {panelTab === "whatsapp" && wa && (
              <form className="admin-kitchen-panel__body owner-forms" onSubmit={saveWhatsApp}>
                <p className="report-hint">{wa.platform_secrets_note}</p>
                <label>
                  Meta phone_number_id
                  <input value={phoneId} onChange={(e) => setPhoneId(e.target.value)} placeholder="1099…" autoComplete="off" />
                </label>
                <label>
                  Display phone (E.164)
                  <input value={displayPhone} onChange={(e) => setDisplayPhone(e.target.value)} placeholder="+91…" autoComplete="off" />
                </label>
                <div className="owner-forms__actions">
                  <button type="submit" className="btn btn--primary" disabled={busy}>Save WhatsApp</button>
                  {wa.connected && (
                    <button type="button" className="btn btn--ghost" disabled={busy} onClick={clearWhatsApp}>
                      Disconnect
                    </button>
                  )}
                </div>
              </form>
            )}

            {panelTab === "payments" && !pgw && (
              <p className="admin-kitchen-panel__body report-hint">
                Payment gateway settings unavailable. Close and reopen this kitchen, or check the gateway.
              </p>
            )}
            {panelTab === "payments" && pgw && (
              <form className="admin-kitchen-panel__body owner-forms" onSubmit={savePayments}>
                <p className="report-hint">
                  Kitchen Razorpay keys for checkout / Route. Platform SaaS Razorpay stays under API Keys.
                </p>
                <label>
                  Key ID
                  <input value={keyId} onChange={(e) => setKeyId(e.target.value)} placeholder="rzp_live_…" autoComplete="off" />
                </label>
                <label>
                  Key secret
                  <input
                    type="password"
                    value={keySecret}
                    onChange={(e) => setKeySecret(e.target.value)}
                    placeholder={
                      pgw.key_secret_configured
                        ? `Configured (${pgw.key_secret_masked ?? "••••"}) — blank to keep`
                        : "Enter secret"
                    }
                    autoComplete="new-password"
                  />
                </label>
                <label>
                  Webhook secret
                  <input
                    type="password"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                    placeholder={
                      pgw.webhook_secret_configured
                        ? `Configured (${pgw.webhook_secret_masked ?? "••••"}) — blank to keep`
                        : "Optional"
                    }
                    autoComplete="new-password"
                  />
                </label>
                <label>
                  Route linked account
                  <input value={linkedAccountId} onChange={(e) => setLinkedAccountId(e.target.value)} placeholder="acc_…" autoComplete="off" />
                </label>
                <label className="owner-forms__check">
                  <input type="checkbox" checked={pgwActive} onChange={(e) => setPgwActive(e.target.checked)} />
                  Active for this kitchen
                </label>
                <div className="owner-forms__actions">
                  <button type="submit" className="btn btn--primary" disabled={busy}>Save payments</button>
                  {(pgw.key_id || pgw.key_secret_configured || pgw.linked_account_id) && (
                    <button type="button" className="btn btn--ghost" disabled={busy} onClick={clearPayments}>
                      Clear credentials
                    </button>
                  )}
                </div>
              </form>
            )}

            {panelTab === "package" && (
              <div className="admin-kitchen-panel__body owner-forms">
                <p className="report-hint">
                  Source: {kitchenPkg?.source ?? "none"}
                  {kitchenPkg?.owner_plan_tier ? ` · owner plan ${kitchenPkg.owner_plan_tier}` : ""}
                </p>
                {kitchenPkg?.package && (
                  <p>
                    Current: <strong>{kitchenPkg.package.name}</strong> ({kitchenPkg.package.code}) —{" "}
                    {kitchenPkg.package.feature_keys.join(", ")}
                  </p>
                )}
                <label>
                  Assign package
                  <select value={assignPackageId} onChange={(e) => setAssignPackageId(e.target.value)}>
                    {allPackages.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.code})
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={busy || !assignPackageId}
                  onClick={async () => {
                    if (!selectedId || !assignPackageId) return;
                    setBusy(true);
                    try {
                      const next = await assignAdminKitchenPackage(selectedId, {
                        package_id: assignPackageId,
                        sync_module_flags: true,
                      });
                      setKitchenPkg(next);
                      setModules(await fetchAdminKitchenModuleFlags(selectedId));
                      setOk("Package assigned and modules synced.");
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Package assign failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Assign & sync modules
                </button>
              </div>
            )}

            {panelTab === "marketing" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Owner WhatsApp/email templates for this kitchen ({templates.length}). Module: marketing_broadcast.
                </p>
                {templates.length === 0 ? (
                  <p className="admin-panel__empty">No templates yet.</p>
                ) : (
                  <ul className="report-rank">
                    {templates.map((t) => (
                      <li key={t.id}>
                        <div className="report-rank__row">
                          <span>
                            <strong>{t.name}</strong>
                            <span className="report-rank__meta">
                              {" "}
                              · {t.channel}
                              {!t.is_active ? " · inactive" : ""}
                            </span>
                          </span>
                        </div>
                        <p className="report-hint">{t.body.slice(0, 160)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {panelTab === "streaming" && !modules && (
              <p className="admin-kitchen-panel__body report-hint">
                Module flags unavailable. Close and reopen this kitchen, or check the gateway.
              </p>
            )}
            {panelTab === "streaming" && modules && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Per-dish go-live (ingredients → prep → prepared) lives on the owner Stream page.
                  Toggle streaming / livekit modules here for ops kill-switch.
                </p>
                <ul className="report-rank">
                  {modules.modules
                    .filter((m) => m.module_key === "streaming" || m.module_key === "livekit")
                    .map((m) => (
                      <li key={m.module_key}>
                        <div className="report-rank__row">
                          <span><strong>{m.module_key}</strong></span>
                          <button
                            type="button"
                            className={`btn btn--sm ${m.enabled ? "btn--ghost" : "btn--primary"}`}
                            disabled={busy}
                            onClick={() => toggleModule(m.module_key, !m.enabled)}
                          >
                            {m.enabled ? "Disable" : "Enable"}
                          </button>
                        </div>
                      </li>
                    ))}
                </ul>
              </div>
            )}

            {panelTab === "modules" && !modules && (
              <p className="admin-kitchen-panel__body report-hint">
                Module flags unavailable. Close and reopen this kitchen, or check the gateway.
              </p>
            )}
            {panelTab === "modules" && modules && (
              <ul className="admin-kitchen-panel__body report-rank">
                {modules.modules.map((m) => (
                  <li key={m.module_key}>
                    <div className="report-rank__row">
                      <span><strong>{m.module_key}</strong></span>
                      <button
                        type="button"
                        className={`btn btn--sm ${m.enabled ? "btn--ghost" : "btn--primary"}`}
                        disabled={busy}
                        onClick={() => toggleModule(m.module_key, !m.enabled)}
                      >
                        {m.enabled ? "Disable" : "Enable"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {panelTab === "tiffin" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Customer monthly thali/tiffin plans. Entitlement: Packages →{" "}
                  <code>tiffin_plans</code> · Modules → <code>tiffin_plans</code>.
                </p>
                {tiffinSummary ? (
                  <dl className="admin-kv">
                    <div><dt>Plans</dt><dd>{tiffinSummary.plans_active} active / {tiffinSummary.plans_total}</dd></div>
                    <div><dt>Pending</dt><dd>{tiffinSummary.pending}</dd></div>
                    <div><dt>Active subs</dt><dd>{tiffinSummary.active}</dd></div>
                    <div><dt>Paused</dt><dd>{tiffinSummary.paused}</dd></div>
                    <div><dt>MRR estimate</dt><dd>₹{Math.round(tiffinSummary.mrr_estimate).toLocaleString("en-IN")}</dd></div>
                  </dl>
                ) : (
                  <p className="admin-panel__empty">No tiffin summary (module off or empty).</p>
                )}
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  disabled={busy || !selectedId}
                  onClick={async () => {
                    if (!selectedId) return;
                    setBusy(true);
                    try {
                      setTiffinSummary(await fetchAdminKitchenTiffinSummary(selectedId));
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Refresh failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Refresh
                </button>
              </div>
            )}

            {panelTab === "gst" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Monthly GST calculation for this kitchen — same figures the owner closes for
                  accountant handoff. Download Excel / PDF exports below.
                </p>
                <div className="admin-toolbar" style={{ marginBottom: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                  <label>
                    Year{" "}
                    <select
                      value={gstYear}
                      onChange={async (e) => {
                        const y = Number(e.target.value);
                        setGstYear(y);
                        if (!selectedId) return;
                        const [prof, rep] = await Promise.all([
                          fetchAdminKitchenGstProfile(selectedId).catch(() => null),
                          fetchAdminKitchenGstMonthly(selectedId, y, gstMonth).catch(() => null),
                        ]);
                        setGstProfile(prof);
                        setGstReport(rep);
                      }}
                    >
                      {[gstYear - 1, gstYear, gstYear + 1].map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Month{" "}
                    <select
                      value={gstMonth}
                      onChange={async (e) => {
                        const m = Number(e.target.value);
                        setGstMonth(m);
                        if (!selectedId) return;
                        const rep = await fetchAdminKitchenGstMonthly(selectedId, gstYear, m).catch(
                          () => null,
                        );
                        setGstReport(rep);
                      }}
                    >
                      {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </label>
                  {gstReport && (
                    <>
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={busy}
                        onClick={async () => {
                          if (!selectedId) return;
                          setBusy(true);
                          setError("");
                          try {
                            await downloadAdminKitchenGstExcel(selectedId, gstYear, gstMonth);
                          } catch (e) {
                            setError(e instanceof Error ? e.message : "Excel download failed");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Download Excel
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={async () => {
                          if (!selectedId) return;
                          setBusy(true);
                          setError("");
                          try {
                            await downloadAdminKitchenGstPdf(selectedId, gstYear, gstMonth);
                          } catch (e) {
                            setError(e instanceof Error ? e.message : "PDF download failed");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Download PDF
                      </button>
                    </>
                  )}
                </div>
                {gstProfile ? (
                  <dl className="admin-kv">
                    <div><dt>GSTIN</dt><dd>{gstProfile.gstin}</dd></div>
                    <div><dt>Legal name</dt><dd>{gstProfile.legal_name}</dd></div>
                    <div><dt>State</dt><dd>{gstProfile.state_code}</dd></div>
                    <div><dt>Tax rate</dt><dd>{gstProfile.default_tax_rate}%</dd></div>
                    <div><dt>Active</dt><dd>{gstProfile.is_active ? "Yes" : "No"}</dd></div>
                  </dl>
                ) : (
                  <p className="admin-panel__empty">No GST profile registered for this kitchen.</p>
                )}
                {gstReport && (
                  <>
                    <dl className="admin-kv" style={{ marginTop: "1rem" }}>
                      <div><dt>Taxable</dt><dd>₹{gstReport.total_taxable.toLocaleString("en-IN")}</dd></div>
                      <div><dt>Output tax</dt><dd>₹{gstReport.total_tax.toLocaleString("en-IN")}</dd></div>
                      <div><dt>Gross sales</dt><dd>₹{gstReport.total_gross_sales.toLocaleString("en-IN")}</dd></div>
                      <div><dt>Invoices</dt><dd>{gstReport.invoice_count} · {gstReport.audit_status}</dd></div>
                    </dl>
                    <div className="owner-table-wrap" style={{ marginTop: "1rem" }}>
                      <table className="owner-table">
                        <thead>
                          <tr>
                            <th>Invoice</th>
                            <th>Order</th>
                            <th>Taxable</th>
                            <th>CGST</th>
                            <th>SGST</th>
                            <th>Gross</th>
                          </tr>
                        </thead>
                        <tbody>
                          {gstReport.invoices.length === 0 ? (
                            <tr><td colSpan={6}>No invoices in this period</td></tr>
                          ) : (
                            gstReport.invoices.map((inv) => (
                              <tr key={inv.id}>
                                <td>{inv.invoice_number}</td>
                                <td>{inv.order_code}</td>
                                <td>₹{inv.taxable_value.toFixed(2)}</td>
                                <td>₹{inv.cgst_amount.toFixed(2)}</td>
                                <td>₹{inv.sgst_amount.toFixed(2)}</td>
                                <td>₹{inv.gross_total.toFixed(2)}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            )}

            {panelTab === "delivery" && detail && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">
                  Porter auto-book: after accept, wait delay then book for food-ready pickup; retries
                  until booked. Also gate via Modules → <code>courier_porter_auto_book</code> and
                  Packages → feature <code>courier_porter_auto_book</code>.
                </p>
                <label className="owner-check">
                  <input
                    type="checkbox"
                    checked={porterAutoBook}
                    onChange={(e) => setPorterAutoBook(e.target.checked)}
                  />
                  Auto-book Porter enabled
                </label>
                <label>
                  Delay (minutes)
                  <input
                    type="number"
                    min={1}
                    max={120}
                    value={porterDelayMin}
                    onChange={(e) => setPorterDelayMin(Number(e.target.value) || 15)}
                  />
                </label>
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  disabled={busy}
                  onClick={async () => {
                    if (!selectedId) return;
                    setBusy(true);
                    setError("");
                    try {
                      const next = await updateAdminKitchenDeliverySettings(selectedId, {
                        porter_auto_book_enabled: porterAutoBook,
                        porter_auto_book_delay_min: porterDelayMin,
                      });
                      setDetail(next);
                      setOk("Delivery / Porter auto-book settings saved.");
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Save failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Save delivery settings
                </button>
              </div>
            )}
          </section>
        )}
      </div>
    </>
  );
}

function AdminOwners() {
  type OwnerRow = Awaited<ReturnType<typeof fetchAdminOwners>>[number];
  const [rows, setRows] = useState<OwnerRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    setRows(await fetchAdminOwners());
  };

  useEffect(() => {
    load()
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load owners"))
      .finally(() => setLoading(false));
  }, []);

  const tierCounts = rows.reduce<Record<string, number>>((acc, o) => {
    acc[o.subscription_tier] = (acc[o.subscription_tier] ?? 0) + 1;
    return acc;
  }, {});
  const topTier = Object.entries(tierCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  const ownerColumns = useMemo<DataColumn<OwnerRow>[]>(
    () => [
      {
        id: "name",
        header: "Name",
        sortable: true,
        sortValue: (o) => o.name,
        cell: (o) => o.name,
      },
      {
        id: "phone",
        header: "Phone",
        sortable: true,
        sortValue: (o) => o.phone,
        cell: (o) => o.phone,
      },
      {
        id: "tier",
        header: "Tier",
        sortable: true,
        sortValue: (o) => o.subscription_tier,
        cell: (o) => <span className="od-pill od-pill--sub">{o.subscription_tier}</span>,
      },
      {
        id: "status",
        header: "Status",
        sortable: true,
        sortValue: (o) => o.subscription_status,
        cell: (o) => o.subscription_status,
      },
      {
        id: "kitchens",
        header: "Kitchens",
        sortable: true,
        sortValue: (o) => o.kitchen_count,
        align: "right",
        cell: (o) => o.kitchen_count,
      },
      {
        id: "control",
        header: "Control",
        cell: (o) => (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={busyId === o.id}
            onClick={async () => {
              setBusyId(o.id);
              setError("");
              try {
                await updateAdminOwnerSubscription(o.id, {
                  subscription_tier: "growth",
                  subscription_status: "active",
                });
                await load();
              } catch (e) {
                setError(e instanceof Error ? e.message : "Update failed");
              } finally {
                setBusyId(null);
              }
            }}
          >
            Force growth/active
          </button>
        ),
      },
    ],
    [busyId],
  );

  return (
    <>
      {error && <p className="auth-card__error">{error}</p>}
      <div className="admin-tab-kpis">
        <div className="dash-card admin-stat-card admin-stat-card--teal">
          <strong>{rows.length}</strong>
          <span>Registered owners</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--purple">
          <strong>{rows.reduce((n, o) => n + o.kitchen_count, 0)}</strong>
          <span>Total kitchens</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--orange">
          <strong>{topTier}</strong>
          <span>Most common tier</span>
        </div>
      </div>
      <DataTable
        rows={rows}
        loading={loading}
        emptyMessage="No owners yet."
        searchPlaceholder="Search name, phone, tier…"
        getSearchText={(o) => `${o.name} ${o.phone} ${o.subscription_tier} ${o.subscription_status}`}
        filterChips={[
          { id: "", label: "All tiers" },
          ...Object.keys(tierCounts)
            .sort()
            .map((t) => ({ id: t, label: t })),
        ]}
        getFilterValue={(o) => o.subscription_tier}
        rowKey={(o) => o.id}
        columns={ownerColumns}
      />
    </>
  );
}

function AdminOrders() {
  type OrderRow = Awaited<ReturnType<typeof fetchAdminOrders>>[number];
  const [rows, setRows] = useState<OrderRow[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchAdminOrders(300)
      .then(setRows)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalRevenue = rows.reduce((sum, o) => sum + o.total, 0);
  const activeCount = rows.filter((o) => !["delivered", "cancelled"].includes(o.status)).length;
  const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

  const orderColumns = useMemo<DataColumn<OrderRow>[]>(
    () => [
      {
        id: "code",
        header: "Code",
        sortable: true,
        sortValue: (o) => o.order_code,
        cell: (o) => <code className="admin-code">{o.order_code}</code>,
      },
      {
        id: "kitchen",
        header: "Kitchen",
        sortable: true,
        sortValue: (o) => o.kitchen_name,
        cell: (o) => o.kitchen_name,
      },
      {
        id: "customer",
        header: "Customer",
        sortable: true,
        sortValue: (o) => o.customer_name ?? "",
        cell: (o) => o.customer_name ?? "—",
      },
      {
        id: "status",
        header: "Status",
        sortable: true,
        sortValue: (o) => o.status,
        cell: (o) => <span className={`status-badge status-badge--${o.status}`}>{o.status}</span>,
      },
      {
        id: "when",
        header: "When",
        sortable: true,
        sortValue: (o) => new Date(o.created_at).getTime(),
        cell: (o) => new Date(o.created_at).toLocaleDateString("en-IN"),
      },
      {
        id: "total",
        header: "Total",
        sortable: true,
        sortValue: (o) => o.total,
        align: "right",
        cell: (o) => inr(o.total),
      },
    ],
    [],
  );

  return (
    <>
      <div className="admin-tab-kpis">
        <div className="dash-card admin-stat-card admin-stat-card--blue">
          <strong>{rows.length}</strong>
          <span>Orders loaded</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--green">
          <strong>{activeCount}</strong>
          <span>Active pipeline</span>
        </div>
        <div className="dash-card admin-stat-card admin-stat-card--orange">
          <strong>{inr(totalRevenue)}</strong>
          <span>Sample revenue</span>
        </div>
      </div>
      <DataTable
        rows={rows}
        loading={loading}
        emptyMessage="No orders loaded."
        searchPlaceholder="Search code, kitchen, customer…"
        getSearchText={(o) =>
          `${o.order_code} ${o.kitchen_name} ${o.customer_name ?? ""} ${o.status}`
        }
        filterChips={[
          { id: "", label: "All" },
          { id: "received", label: "Received" },
          { id: "accepted", label: "Accepted" },
          { id: "preparing", label: "Preparing" },
          { id: "ready", label: "Ready" },
          { id: "out_for_delivery", label: "Out for delivery" },
          { id: "delivered", label: "Delivered" },
          { id: "cancelled", label: "Cancelled" },
        ]}
        getFilterValue={(o) => o.status}
        rowKey={(o) => o.id}
        columns={orderColumns}
        defaultPageSize={25}
      />
    </>
  );
}

function AdminTickets() {
  const [tickets, setTickets] = useState<AdminTicket[]>([]);
  const [employees, setEmployees] = useState<AdminEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminTicket | null>(null);
  const [reply, setReply] = useState("");
  const [resolutionNote, setResolutionNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [audienceFilter, setAudienceFilter] = useState("");

  const loadTickets = async () => {
    const res = await fetchAdminTickets({
      audience: audienceFilter || undefined,
    });
    setTickets(res.tickets);
  };

  useEffect(() => {
    Promise.all([loadTickets(), fetchAdminEmployees().catch(() => [] as AdminEmployee[])])
      .then(([, emps]) => setEmployees(emps.filter((e) => e.is_active)))
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void loadTickets().catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
  }, [audienceFilter]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    fetchAdminTicket(selectedId)
      .then((t) => {
        setDetail(t);
        setResolutionNote(t.resolution_note || "");
      })
      .catch((e) => setError(e.message));
  }, [selectedId]);

  const refreshDetail = async () => {
    if (!selectedId) return;
    const t = await fetchAdminTicket(selectedId);
    setDetail(t);
    setResolutionNote(t.resolution_note || "");
    await loadTickets();
  };

  const handleStatusChange = async (status: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminTicket(selectedId, {
        status,
        resolution_note:
          status === "resolved" || status === "closed"
            ? resolutionNote || undefined
            : undefined,
      });
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const handlePriorityChange = async (priority: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminTicket(selectedId, { priority });
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Priority update failed");
    } finally {
      setBusy(false);
    }
  };

  const handleAssigneeChange = async (adminId: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminTicket(selectedId, {
        assigned_admin_id: adminId || null,
      });
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Assign failed");
    } finally {
      setBusy(false);
    }
  };

  const handleReply = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedId || !reply.trim()) return;
    setBusy(true);
    try {
      await replyAdminTicket(selectedId, reply.trim());
      setReply("");
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reply failed");
    } finally {
      setBusy(false);
    }
  };

  const ticketColumns = useMemo<DataColumn<AdminTicket>[]>(
    () => [
      {
        id: "ticket",
        header: "Ticket",
        sortable: true,
        sortValue: (t) => t.ticket_number,
        cell: (t) => (
          <div>
            <strong>{t.ticket_number}</strong>
            <span className="admin-tickets__meta">
              {t.audience} · {t.category}
            </span>
          </div>
        ),
      },
      {
        id: "subject",
        header: "Subject",
        sortable: true,
        sortValue: (t) => t.subject,
        cell: (t) => t.subject,
      },
      {
        id: "status",
        header: "Status",
        sortable: true,
        sortValue: (t) => t.status,
        cell: (t) => <span className={`status-badge status-badge--${t.status}`}>{t.status}</span>,
      },
      {
        id: "priority",
        header: "Priority",
        sortable: true,
        sortValue: (t) => t.priority,
        cell: (t) => t.priority,
      },
      {
        id: "assignee",
        header: "Assignee",
        sortable: true,
        sortValue: (t) => t.assigned_admin_id ?? "",
        cell: (t) => {
          if (!t.assigned_admin_id) return "—";
          const emp = employees.find((e) => e.id === t.assigned_admin_id);
          return emp?.name ?? t.assigned_admin_id.slice(0, 8);
        },
      },
      {
        id: "open",
        header: "",
        cell: (t) => (
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelectedId(t.id)}>
            Open
          </button>
        ),
      },
    ],
    [employees],
  );

  return (
    <div className="admin-tickets">
      {error && <p className="auth-card__error">{error}</p>}

      <div className="admin-toolbar" style={{ marginBottom: "0.75rem" }}>
        <select value={audienceFilter} onChange={(e) => setAudienceFilter(e.target.value)}>
          <option value="">All audiences</option>
          <option value="customer">Customer</option>
          <option value="owner">Owner</option>
        </select>
      </div>

      <div className={`admin-tickets__grid${detail ? "" : " admin-tickets__grid--list-only"}`}>
        <DataTable
          rows={tickets}
          loading={loading}
          emptyMessage="No tickets yet — customers can raise them via AI chat on the portal."
          searchPlaceholder="Search ticket, subject, audience…"
          getSearchText={(t) =>
            `${t.ticket_number} ${t.subject} ${t.status} ${t.priority} ${t.audience} ${t.category} ${t.customer_name ?? ""} ${t.order_code ?? ""}`
          }
          filterChips={[
            { id: "", label: "All" },
            { id: "open", label: "Open" },
            { id: "in_progress", label: "In progress" },
            { id: "waiting_customer", label: "Waiting" },
            { id: "resolved", label: "Resolved" },
            { id: "closed", label: "Closed" },
          ]}
          getFilterValue={(t) => t.status}
          rowKey={(t) => t.id}
          rowClassName={(t) => (selectedId === t.id ? "admin-tickets__row--active" : undefined)}
          columns={ticketColumns}
        />

        {detail && (
          <div className="dash-card admin-tickets__detail">
            <header>
              <div>
                <h2>{detail.ticket_number}</h2>
                <p>{detail.subject}</p>
              </div>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelectedId(null)}>
                Close
              </button>
            </header>
            <dl className="admin-tickets__info">
              <div><dt>Status</dt><dd>{detail.status}</dd></div>
              <div><dt>Priority</dt><dd>{detail.priority}</dd></div>
              <div><dt>From</dt><dd>{detail.customer_name ?? "—"} ({detail.audience})</dd></div>
              <div><dt>Contact</dt><dd>{detail.customer_phone ?? detail.customer_email ?? "—"}</dd></div>
              {detail.order_code && <div><dt>Order</dt><dd>{detail.order_code}</dd></div>}
              {detail.kitchen_id && (
                <div>
                  <dt>Kitchen</dt>
                  <dd>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() =>
                        adminNavigate({ tab: "kitchens", kitchenId: detail.kitchen_id! })
                      }
                    >
                      Open kitchen workspace
                    </button>
                  </dd>
                </div>
              )}
            </dl>
            <p className="admin-tickets__desc">{detail.description}</p>

            <div className="admin-tickets__actions" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              <select
                value={detail.status}
                disabled={busy}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="waiting_customer">Waiting customer</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
              <select
                value={detail.priority}
                disabled={busy}
                onChange={(e) => handlePriorityChange(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
              <select
                value={detail.assigned_admin_id ?? ""}
                disabled={busy}
                onChange={(e) => handleAssigneeChange(e.target.value)}
              >
                <option value="">Unassigned</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.role})
                  </option>
                ))}
              </select>
              {detail.order_code && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() =>
                    adminNavigate({ tab: "refunds", refundSearch: detail.order_code || "" })
                  }
                >
                  Open refunds
                </button>
              )}
            </div>
            <label style={{ display: "block", marginTop: "0.75rem" }}>
              Resolution note
              <textarea
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                rows={2}
                disabled={busy}
                placeholder="Required when resolving…"
              />
            </label>

            <div className="admin-tickets__thread">
              {detail.messages.map((m) => (
                <div key={m.id} className={`admin-tickets__msg admin-tickets__msg--${m.author_type}`}>
                  <span>{m.author_type}</span>
                  <p>{m.message}</p>
                </div>
              ))}
            </div>

            <form className="admin-tickets__reply" onSubmit={handleReply}>
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Reply to customer..."
                rows={3}
                disabled={busy}
              />
              <button type="submit" className="btn btn--primary btn--sm" disabled={busy || !reply.trim()}>
                Send reply
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

function AdminReferralsPanel() {
  const [settings, setSettings] = useState<AdminReferralSettings | null>(null);
  const [leads, setLeads] = useState<AdminReferralLead[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filterDir, setFilterDir] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const reload = async () => {
    try {
      const [s, l] = await Promise.all([
        fetchReferralSettings(),
        fetchReferralLeads({
          direction: filterDir || undefined,
          status_filter: filterStatus || undefined,
        }),
      ]);
      setSettings(s);
      setLeads(l.leads);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load referrals");
    }
  };

  useEffect(() => {
    void reload();
  }, [filterDir, filterStatus]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setBusy(true);
    setError("");
    try {
      const next = await patchReferralSettings(settings);
      setSettings(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      {settings && (
        <form className="admin-form" onSubmit={save}>
          <h2>Reward configuration</h2>
          <label className="admin-check">
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
            />
            Program enabled
          </label>
          <label>
            Customer → kitchen reward (₹)
            <input
              type="number"
              min={0}
              step={1}
              value={settings.customer_to_kitchen_reward_inr}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  customer_to_kitchen_reward_inr: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Kitchen → customer reward (₹)
            <input
              type="number"
              min={0}
              step={1}
              value={settings.kitchen_to_customer_reward_inr}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  kitchen_to_customer_reward_inr: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Kitchen reward trigger
            <select
              value={settings.kitchen_reward_trigger}
              onChange={(e) =>
                setSettings({ ...settings, kitchen_reward_trigger: e.target.value })
              }
            >
              <option value="first_order_or_onboard">First order or onboard</option>
              <option value="onboard">Onboard only</option>
              <option value="first_order">First order only</option>
            </select>
          </label>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            Save settings
          </button>
        </form>
      )}

      <div className="admin-toolbar" style={{ marginTop: "1.5rem" }}>
        <select value={filterDir} onChange={(e) => setFilterDir(e.target.value)}>
          <option value="">All directions</option>
          <option value="customer_to_kitchen">Customer → kitchen</option>
          <option value="kitchen_to_customer">Kitchen → customer</option>
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="submitted">Submitted</option>
          <option value="converted">Converted</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <DataTable
        rows={leads}
        rowKey={(r) => r.id}
        emptyMessage="No referral leads yet"
        searchPlaceholder="Search contact, phone, kitchen, status…"
        getSearchText={(r) =>
          [
            r.direction,
            r.contact_name,
            r.contact_phone,
            r.contact_email,
            r.kitchen_name,
            r.status,
            r.city,
            r.notes,
          ]
            .filter(Boolean)
            .join(" ")
        }
        columns={[
          {
            id: "direction",
            header: "Direction",
            cell: (r) => r.direction.replaceAll("_", " "),
          },
          { id: "contact", header: "Contact", cell: (r) => r.contact_name || "—" },
          { id: "phone", header: "Phone", cell: (r) => r.contact_phone },
          { id: "kitchen", header: "Kitchen", cell: (r) => r.kitchen_name || "—" },
          { id: "status", header: "Status", cell: (r) => r.status },
          {
            id: "reward",
            header: "Reward",
            cell: (r) => (r.reward_inr != null ? `₹${r.reward_inr}` : "—"),
          },
          {
            id: "actions",
            header: "",
            cell: (r) =>
              r.status === "submitted" ? (
                <span style={{ display: "flex", gap: "0.35rem" }}>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={async () => {
                      await grantReferralLead(r.id);
                      await reload();
                    }}
                  >
                    Grant
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={async () => {
                      const reason = window.prompt("Rejection reason");
                      if (!reason) return;
                      await rejectReferralLead(r.id, reason);
                      await reload();
                    }}
                  >
                    Reject
                  </button>
                </span>
              ) : null,
          },
        ]}
      />
    </div>
  );
}
