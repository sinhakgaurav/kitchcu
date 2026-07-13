import { FormEvent, useEffect, useState } from "react";
import {
  adminLogin,
  clearAdminToken,
  fetchAdminKitchens,
  fetchAdminOrders,
  fetchAdminOwners,
  fetchAdminStats,
  fetchAdminTicket,
  fetchAdminTickets,
  getAdminToken,
  replyAdminTicket,
  setAdminToken,
  updateAdminTicket,
  updateKitchenStatus,
  type AdminTicket,
  type PlatformStats,
} from "./adminApi";
import {
  buildOrderTimeline,
  buildStatusBreakdown,
  buildTierBreakdown,
  buildTopKitchens,
} from "./adminCharts";
import { ADMIN_DEV_EMAIL, ADMIN_HOST, APP_NAME, CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";
import "../owner-app.css";

type Tab = "overview" | "kitchens" | "owners" | "orders" | "tickets";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "kitchens", label: "Kitchens" },
  { id: "owners", label: "Owners" },
  { id: "orders", label: "Orders" },
  { id: "tickets", label: "Tickets" },
];

function chartDayLabel(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", { weekday: "short" });
}

const TAB_META: Record<Tab, { title: string; desc: string }> = {
  overview: { title: "Platform overview", desc: "Health snapshot across all kitchens and owners" },
  kitchens: { title: "Kitchens", desc: "Activate, suspend, and monitor cloud kitchens" },
  owners: { title: "Owners", desc: "Subscription tiers and kitchen counts" },
  orders: { title: "Orders", desc: "Cross-kitchen order feed" },
  tickets: { title: "Support tickets", desc: "Customer and owner escalations from AI chat" },
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
  { key: "orders", label: "Platform orders", desc: "Lifetime order count", accent: "blue" },
  { key: "dishes", label: "Menu dishes", desc: "Live-capture items across kitchens", accent: "purple" },
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
          <span className="admin-shell__logo">{APP_NAME} Admin</span>
          <span className="admin-shell__host">{ADMIN_HOST}</span>
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
          <a href={customerUrl("/")} className="admin-app__ext-link" title={CUSTOMER_HOST}>
            Customer app
          </a>
          <a href={kitchenUrl("/")} className="admin-app__ext-link" title={KITCHEN_HOST}>
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
          {tab === "orders" && <AdminOrders />}
          {tab === "tickets" && <AdminTickets />}
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
          <button type="button" className="btn btn--primary btn--sm" onClick={() => onNavigate("kitchens")}>
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
        {STAT_CARDS.map((card) => (
          <div key={card.key} className={`dash-card admin-stat-card admin-stat-card--${card.accent}`}>
            <strong>{stats[card.key].toLocaleString("en-IN")}</strong>
            <span>{card.label}</span>
            <em>{card.desc}</em>
          </div>
        ))}
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
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("kitchens")}>
              <strong>Kitchen moderation</strong>
              <span>Activate or suspend kitchens</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("owners")}>
              <strong>Owner accounts</strong>
              <span>Review tiers and kitchen counts</span>
            </button>
            <button type="button" className="admin-quick__item" onClick={() => onNavigate("tickets")}>
              <strong>Support queue</strong>
              <span>{openTickets} open tickets need attention</span>
            </button>
          </div>
          <div className="admin-panel__note">
            <p><strong>Dev access:</strong> {ADMIN_DEV_EMAIL} / admin123456</p>
            <p>Gateway API: <code>/api/v1/admin/*</code> · Port <code>13003</code> locally</p>
          </div>
        </section>
      </div>
    </>
  );
}

function AdminLogin({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState(ADMIN_DEV_EMAIL);
  const [password, setPassword] = useState("admin123456");
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
      <form className="dash-card auth-card admin-login__card" onSubmit={submit}>
        <p className="admin-login__eyebrow">Super admin</p>
        <h1>Platform control</h1>
        <p>Full visibility over cloud kitchens, owners, orders, and support tickets.</p>
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
        <p className="auth-card__hint">Dev default: {ADMIN_DEV_EMAIL} / admin123456 · <a href={kitchenUrl("/")}>Owner app</a></p>
      </form>
    </div>
  );
}

function AdminKitchens() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminKitchens>>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchAdminKitchens()
      .then(setRows)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const active = rows.filter((k) => k.status === "active").length;
  const suspended = rows.filter((k) => k.status === "suspended").length;

  const setStatus = async (id: string, status: string) => {
    await updateKitchenStatus(id, status);
    setRows(await fetchAdminKitchens());
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
      </div>
    <div className="dash-card admin-table-wrap">
      {loading ? <p className="admin-panel__empty">Loading kitchens…</p> : (
      <table className="admin-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => (
            <tr key={k.id}>
              <td><code className="admin-code">{k.code}</code></td>
              <td>{k.name}</td>
              <td>{k.owner_name}</td>
              <td><span className={`status-badge status-badge--${k.status}`}>{k.status}</span></td>
              <td>
                {k.status !== "active" && (
                  <button type="button" className="btn btn--sm btn--primary" onClick={() => setStatus(k.id, "active")}>
                    Activate
                  </button>
                )}
                {k.status === "active" && (
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => setStatus(k.id, "suspended")}>
                    Suspend
                  </button>
                )}
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

function AdminOwners() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchAdminOwners()
      .then(setRows)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const tierCounts = rows.reduce<Record<string, number>>((acc, o) => {
    acc[o.subscription_tier] = (acc[o.subscription_tier] ?? 0) + 1;
    return acc;
  }, {});
  const topTier = Object.entries(tierCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

  return (
    <>
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
