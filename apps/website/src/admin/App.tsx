import { FormEvent, useEffect, useState } from "react";
import {
  adminLogin,
  clearAdminKitchenPaymentGateway,
  clearAdminToken,
  fetchAdminKitchen,
  fetchAdminKitchenModuleFlags,
  fetchAdminKitchenPaymentGateway,
  fetchAdminKitchens,
  fetchAdminKitchenWhatsApp,
  fetchAdminOrders,
  fetchAdminOwners,
  fetchAdminStats,
  fetchAdminTicket,
  fetchAdminTickets,
  getAdminToken,
  replyAdminTicket,
  setAdminToken,
  updateAdminKitchenModuleFlag,
  updateAdminTicket,
  updateAdminOwnerSubscription,
  updateKitchenStatus,
  upsertAdminKitchenPaymentGateway,
  upsertAdminKitchenWhatsApp,
  type AdminKitchen,
  type AdminKitchenDetail,
  type AdminKitchenModuleFlags,
  type AdminKitchenPaymentGateway,
  type AdminKitchenWhatsApp,
  type AdminTicket,
  type PlatformStats,
} from "./adminApi";
import { AdminApiKeysPanel, AdminControlPlane, AdminCustomers, AdminRefunds } from "./AdminPanels";
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
  | "api-keys"
  | "control";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "kitchens", label: "Kitchens" },
  { id: "owners", label: "Owners" },
  { id: "customers", label: "Customers" },
  { id: "orders", label: "Orders" },
  { id: "refunds", label: "Refunds" },
  { id: "tickets", label: "Tickets" },
  { id: "api-keys", label: "API Keys" },
  { id: "control", label: "Control" },
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
    desc: "Kitchen workspace — status, WhatsApp phone ID, Razorpay keys, module flags",
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
  "api-keys": {
    title: "Platform API keys",
    desc: "Meta App Secret / Verify Token, platform Razorpay (SaaS), LiveKit, Maps, OAuth — not per-kitchen keys",
  },
  control: {
    title: "Control plane",
    desc: "Feature flags, data journeys, payments, and SaaS subscription overrides",
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
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [allOrders, setAllOrders] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
  const [owners, setOwners] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  const [kitchens, setKitchens] = useState<Awaited<ReturnType<typeof fetchAdminKitchens>>>([]);
  const [recentOrders, setRecentOrders] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
  const [openTickets, setOpenTickets] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      fetchAdminStats(),
      fetchAdminOrders(500),
      fetchAdminOwners(),
      fetchAdminKitchens(),
      fetchAdminTickets({ status: "open" }),
    ])
      .then(([s, orders, ownerRows, kitchenRows, tickets]) => {
        setStats(s);
        setAllOrders(orders);
        setOwners(ownerRows);
        setKitchens(kitchenRows);
        setRecentOrders(orders.slice(0, 6));
        setOpenTickets(tickets.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

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
          {TABS.map((t) => (
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
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              clearAdminToken();
              setToken(null);
            }}
          >
            Sign out
          </button>
        </header>

        <div className="admin-main">
          <header className="admin-section-head">
            <h1>{TAB_META[tab].title}</h1>
            <p>{TAB_META[tab].desc}</p>
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

          {tab === "kitchens" && <AdminKitchens />}
          {tab === "owners" && <AdminOwners />}
          {tab === "customers" && <AdminCustomers />}
          {tab === "orders" && <AdminOrders />}
          {tab === "refunds" && <AdminRefunds />}
          {tab === "tickets" && <AdminTickets />}
          {tab === "api-keys" && <AdminApiKeysPanel />}
          {tab === "control" && <AdminControlPlane />}
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
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
          <p className="auth-card__hint">
            {defaults.isProductionHost ? (
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

function AdminKitchens() {
  const [rows, setRows] = useState<AdminKitchen[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminKitchenDetail | null>(null);
  const [wa, setWa] = useState<AdminKitchenWhatsApp | null>(null);
  const [pgw, setPgw] = useState<AdminKitchenPaymentGateway | null>(null);
  const [modules, setModules] = useState<AdminKitchenModuleFlags | null>(null);
  const [panelTab, setPanelTab] = useState<"profile" | "whatsapp" | "payments" | "modules">("profile");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [phoneId, setPhoneId] = useState("");
  const [displayPhone, setDisplayPhone] = useState("");
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [linkedAccountId, setLinkedAccountId] = useState("");
  const [pgwActive, setPgwActive] = useState(true);

  const reloadList = async () => {
    setRows(await fetchAdminKitchens());
  };

  useEffect(() => {
    reloadList()
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const openKitchen = async (id: string) => {
    setSelectedId(id);
    setError("");
    setOk("");
    setPanelTab("profile");
    try {
      const [d, w, p, m] = await Promise.all([
        fetchAdminKitchen(id),
        fetchAdminKitchenWhatsApp(id),
        fetchAdminKitchenPaymentGateway(id),
        fetchAdminKitchenModuleFlags(id),
      ]);
      setDetail(d);
      setWa(w);
      setPgw(p);
      setModules(m);
      setPhoneId(w.whatsapp_phone_id ?? "");
      setDisplayPhone(w.whatsapp_display_phone ?? "");
      setKeyId(p.key_id ?? "");
      setLinkedAccountId(p.linked_account_id ?? "");
      setPgwActive(p.is_active);
      setKeySecret("");
      setWebhookSecret("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load kitchen workspace");
    }
  };

  const active = rows.filter((k) => k.status === "active").length;
  const suspended = rows.filter((k) => k.status === "suspended").length;
  const waLinked = rows.filter((k) => k.whatsapp_connected).length;
  const pgwReady = rows.filter((k) => k.payment_gateway_configured).length;

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

      <div className="admin-kitchen-workspace">
        <div className="dash-card admin-table-wrap">
          {loading ? (
            <p className="admin-panel__empty">Loading kitchens…</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Owner</th>
                  <th>WA</th>
                  <th>Pay</th>
                  <th>Status</th>
                  <th>Workspace</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((k) => (
                  <tr key={k.id} className={selectedId === k.id ? "admin-table__row--active" : undefined}>
                    <td><code className="admin-code">{k.code}</code></td>
                    <td>{k.name}</td>
                    <td>{k.owner_name}</td>
                    <td>{k.whatsapp_connected ? "●" : "○"}</td>
                    <td>{k.payment_gateway_configured ? "●" : "○"}</td>
                    <td><span className={`status-badge status-badge--${k.status}`}>{k.status}</span></td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--sm btn--primary"
                        onClick={() => openKitchen(k.id)}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

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
              {(["profile", "whatsapp", "payments", "modules"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  className={panelTab === t ? "active" : ""}
                  onClick={() => setPanelTab(t)}
                >
                  {t === "whatsapp" ? "WhatsApp" : t === "payments" ? "Payments" : t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {panelTab === "profile" && (
              <div className="admin-kitchen-panel__body">
                <p className="report-hint">{detail.platform_secrets_note}</p>
                <dl className="admin-kv">
                  <div><dt>Owner phone</dt><dd>{detail.owner_phone}</dd></div>
                  <div><dt>Address</dt><dd>{detail.address_line ?? "—"}</dd></div>
                  <div><dt>State / PIN</dt><dd>{detail.state ?? "—"} / {detail.pincode ?? "—"}</dd></div>
                  <div><dt>WhatsApp</dt><dd>{detail.whatsapp_connected ? "Linked" : "Not linked"}</dd></div>
                  <div><dt>Payment gateway</dt><dd>{detail.payment_gateway_configured ? "Configured" : "Not set"}</dd></div>
                </dl>
              </div>
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
          </section>
        )}
      </div>
    </>
  );
}

function AdminOwners() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
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
    <div className="dash-card admin-table-wrap">
      {loading ? <p className="admin-panel__empty">Loading owners…</p> : (
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Tier</th>
            <th>Status</th>
            <th>Kitchens</th>
            <th>Control</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>{o.name}</td>
              <td>{o.phone}</td>
              <td><span className="od-pill od-pill--sub">{o.subscription_tier}</span></td>
              <td>{o.subscription_status}</td>
              <td>{o.kitchen_count}</td>
              <td>
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
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      )}
    </div>
    </>
  );
}

function AdminOrders() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
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
      <div className="dash-card admin-table-wrap">
      {loading ? <p className="admin-panel__empty">Loading orders…</p> : (
      <table className="admin-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Kitchen</th>
            <th>Customer</th>
            <th>Status</th>
            <th>When</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td><code className="admin-code">{o.order_code}</code></td>
              <td>{o.kitchen_name}</td>
              <td>{o.customer_name ?? "—"}</td>
              <td><span className={`status-badge status-badge--${o.status}`}>{o.status}</span></td>
              <td>{new Date(o.created_at).toLocaleDateString("en-IN")}</td>
              <td>{inr(o.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      )}
    </div>
    </>
  );
}

function AdminTickets() {
  const [tickets, setTickets] = useState<AdminTicket[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminTicket | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [audienceFilter, setAudienceFilter] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadTickets = async () => {
    const res = await fetchAdminTickets({
      status: statusFilter || undefined,
      audience: audienceFilter || undefined,
    });
    setTickets(res.tickets);
  };

  useEffect(() => {
    loadTickets().catch((e) => setError(e.message));
  }, [statusFilter, audienceFilter]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    fetchAdminTicket(selectedId)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [selectedId]);

  const refreshDetail = async () => {
    if (!selectedId) return;
    const t = await fetchAdminTicket(selectedId);
    setDetail(t);
    await loadTickets();
  };

  const handleStatusChange = async (status: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminTicket(selectedId, { status });
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
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

  return (
    <div className="admin-tickets">
      <div className="admin-tickets__filters">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In progress</option>
          <option value="waiting_customer">Waiting customer</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select value={audienceFilter} onChange={(e) => setAudienceFilter(e.target.value)}>
          <option value="">All audiences</option>
          <option value="customer">Customer</option>
          <option value="owner">Owner</option>
        </select>
      </div>

      {error && <p className="auth-card__error">{error}</p>}

      <div className="admin-tickets__grid">
        <div className="dash-card admin-tickets__list">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  className={selectedId === t.id ? "admin-tickets__row--active" : ""}
                  onClick={() => setSelectedId(t.id)}
                >
                  <td>
                    <strong>{t.ticket_number}</strong>
                    <span className="admin-tickets__meta">{t.audience} · {t.category}</span>
                  </td>
                  <td>{t.subject}</td>
                  <td><span className={`status-badge status-badge--${t.status}`}>{t.status}</span></td>
                  <td>{t.priority}</td>
                </tr>
              ))}
              {tickets.length === 0 && (
                <tr><td colSpan={4}>No tickets yet — customers can raise them via AI chat on the portal.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {detail && (
          <div className="dash-card admin-tickets__detail">
            <header>
              <h2>{detail.ticket_number}</h2>
              <p>{detail.subject}</p>
            </header>
            <dl className="admin-tickets__info">
              <div><dt>Status</dt><dd>{detail.status}</dd></div>
              <div><dt>Priority</dt><dd>{detail.priority}</dd></div>
              <div><dt>From</dt><dd>{detail.customer_name ?? "—"} ({detail.audience})</dd></div>
              <div><dt>Contact</dt><dd>{detail.customer_phone ?? detail.customer_email ?? "—"}</dd></div>
              {detail.order_code && <div><dt>Order</dt><dd>{detail.order_code}</dd></div>}
            </dl>
            <p className="admin-tickets__desc">{detail.description}</p>

            <div className="admin-tickets__actions">
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
            </div>

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
