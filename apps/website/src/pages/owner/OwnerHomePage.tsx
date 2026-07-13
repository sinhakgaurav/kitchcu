import { Link, Navigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useKitchen } from "../../lib/kitchen";
import { useKitchenAuth } from "../../shared/kitchenAuth";
import {
  fetchDrafts,
  fetchMenu,
  fetchOrders,
  fetchRevenueSummary,
  fetchRevenueTimeseries,
  fetchStreamSettings,
  fetchTopDishes,
  STATUS_LABELS,
  type Order,
  type RevenueSummary,
  type RevenueTimeseries,
  type StreamSettings,
} from "../../lib/api";
import { CUSTOMER_HOST } from "../../shared/brand";
import { customerUrl } from "../../shared/urls";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;
const pct = (n: number) => `${(n * 100).toFixed(0)}%`;

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) {
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function chartDayLabel(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", { weekday: "short" });
}

const QUICK_ACTIONS = [
  { to: "/dashboard/orders/new", title: "New order", desc: "Manual or walk-in", accent: "orange" },
  { to: "/dashboard/orders?tab=drafts", title: "WhatsApp drafts", desc: "Review parsed orders", accent: "teal" },
  { to: "/dashboard/menu/new", title: "Add dish", desc: "Live-capture photo", accent: "orange" },
  { to: "/dashboard/reports", title: "Growth reports", desc: "Revenue & retention", accent: "teal" },
  { to: "/dashboard/stream", title: "Live stream", desc: "Go live to customers", accent: "orange" },
  { to: "/dashboard/coupons", title: "Coupons", desc: "Run promotions", accent: "teal" },
] as const;

export function OwnerHomePage() {
  const { kitchen, kitchens, loading } = useKitchen();
  const { owner } = useKitchenAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [draftCount, setDraftCount] = useState(0);
  const [dishCount, setDishCount] = useState(0);
  const [summary, setSummary] = useState<RevenueSummary | null>(null);
  const [series, setSeries] = useState<RevenueTimeseries | null>(null);
  const [topDish, setTopDish] = useState<string | null>(null);
  const [stream, setStream] = useState<StreamSettings | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!kitchen) return;
    setPageLoading(true);
    Promise.allSettled([
      fetchOrders(kitchen.id),
      fetchDrafts(kitchen.id),
      fetchMenu(kitchen.id),
      fetchRevenueSummary(kitchen.id, 7),
      fetchRevenueTimeseries(kitchen.id, 7),
      fetchTopDishes(kitchen.id, 7, 1),
      fetchStreamSettings(kitchen.id),
    ])
      .then((results) => {
        const val = <T,>(i: number) =>
          results[i].status === "fulfilled" ? (results[i] as PromiseFulfilledResult<T>).value : null;
        const orderRes = val<Awaited<ReturnType<typeof fetchOrders>>>(0);
        const drafts = val<Awaited<ReturnType<typeof fetchDrafts>>>(1);
        const menu = val<Awaited<ReturnType<typeof fetchMenu>>>(2);
        const rev = val<Awaited<ReturnType<typeof fetchRevenueSummary>>>(3);
        const ts = val<Awaited<ReturnType<typeof fetchRevenueTimeseries>>>(4);
        const dishes = val<Awaited<ReturnType<typeof fetchTopDishes>>>(5);
        const streamSettings = val<Awaited<ReturnType<typeof fetchStreamSettings>>>(6);
        if (orderRes) setOrders(orderRes.orders);
        if (drafts) setDraftCount(drafts.total);
        if (menu) setDishCount(menu.dishes.length);
        if (rev) setSummary(rev);
        if (ts) setSeries(ts);
        if (dishes) setTopDish(dishes.dishes[0]?.dish_name ?? null);
        if (streamSettings) setStream(streamSettings);
      })
      .finally(() => setPageLoading(false));
  }, [kitchen]);

  const activeOrders = useMemo(
    () => orders.filter((o) => !["delivered", "cancelled"].includes(o.status)),
    [orders],
  );
  const recentOrders = useMemo(
    () => [...orders].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5),
    [orders],
  );
  const maxRevenue = useMemo(
    () => Math.max(1, ...(series?.points.map((p) => p.revenue) ?? [1])),
    [series],
  );

  if (!loading && kitchens.length === 0) {
    return <Navigate to="/dashboard/setup" replace />;
  }

  if (!kitchen) return null;

  const menuLink = customerUrl(`/kitchen/${kitchen.id}/menu`);
  const subTier = owner?.subscription_tier ?? "trial";
  const subStatus = owner?.subscription_status ?? "active";

  const copyLink = async () => {
    await navigator.clipboard.writeText(menuLink);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="owner-page od-board">
      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">{greeting()}, {owner?.name?.split(" ")[0] ?? "chef"}</p>
          <h1>{kitchen.name}</h1>
          <p className="od-board__meta">
            <span className="od-board__code">{kitchen.code}</span>
            <span>{kitchen.city}, {kitchen.state}</span>
          </p>
          <div className="od-board__pills">
            <span className={`od-pill od-pill--sub od-pill--${subStatus}`}>
              {subTier} · {subStatus}
            </span>
            {stream?.is_live && (
              <span className="od-pill od-pill--live">Live now</span>
            )}
            {draftCount > 0 && (
              <Link to="/dashboard/orders?tab=drafts" className="od-pill od-pill--alert">
                {draftCount} draft{draftCount !== 1 ? "s" : ""} waiting
              </Link>
            )}
          </div>
        </div>
        <div className="od-board__hero-actions">
          <Link to="/dashboard/orders/new" className="btn btn--primary">New order</Link>
          <Link to="/dashboard/reports" className="btn btn--ghost">View reports</Link>
        </div>
      </section>

      {pageLoading ? (
        <div className="od-board__loading">
          <div className="od-skeleton od-skeleton--wide" />
          <div className="od-board__kpi-grid">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="od-skeleton od-skeleton--card" />
            ))}
          </div>
        </div>
      ) : (
        <>
          <div className="od-board__kpi-grid">
            <Link to="/dashboard/reports" className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--revenue" aria-hidden="true" />
              <div>
                <strong>{summary ? inr(summary.gross_revenue) : "—"}</strong>
                <span>Revenue · last 7 days</span>
                {summary && summary.completed_orders > 0 && (
                  <em>{inr(summary.avg_order_value)} avg order</em>
                )}
              </div>
            </Link>
            <Link to="/dashboard/orders" className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--orders" aria-hidden="true" />
              <div>
                <strong>{activeOrders.length}</strong>
                <span>Active orders</span>
                <em>{summary?.completed_orders ?? 0} completed this week</em>
              </div>
            </Link>
            <Link to="/dashboard/orders?tab=drafts" className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--drafts" aria-hidden="true" />
              <div>
                <strong>{draftCount}</strong>
                <span>WhatsApp drafts</span>
                <em>Parse & confirm incoming</em>
              </div>
            </Link>
            <Link to="/dashboard/menu" className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--menu" aria-hidden="true" />
              <div>
                <strong>{dishCount}</strong>
                <span>Menu dishes</span>
                {topDish ? <em>Top: {topDish}</em> : <em>Add live-capture photos</em>}
              </div>
            </Link>
          </div>

          <div className="od-board__grid">
            <section className="dash-card od-panel">
              <header className="od-panel__head">
                <div>
                  <h2>Revenue pulse</h2>
                  <p>Last 7 days — tap Reports for full analytics</p>
                </div>
                <Link to="/dashboard/reports" className="od-panel__link">Full reports →</Link>
              </header>
              {series && series.points.some((p) => p.revenue > 0) ? (
                <div className="report-bars od-board__spark">
                  {series.points.map((p) => (
                    <div
                      key={p.date}
                      className="report-bars__col"
                      title={`${p.date}: ${inr(p.revenue)} · ${p.orders} orders`}
                    >
                      <div
                        className="report-bars__fill"
                        style={{ height: `${(p.revenue / maxRevenue) * 100}%` }}
                      />
                      <span className="report-bars__label">{chartDayLabel(p.date)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="od-panel__empty">No revenue yet — share your menu link and take your first order.</p>
              )}
              {summary && (
                <dl className="od-board__mini-stats">
                  <div><dt>Repeat rate</dt><dd>{pct(summary.repeat_rate)}</dd></div>
                  <div><dt>Customers</dt><dd>{summary.unique_customers}</dd></div>
                  <div><dt>Cancel rate</dt><dd>{pct(summary.cancellation_rate)}</dd></div>
                </dl>
              )}
            </section>

            <section className="dash-card od-panel">
              <header className="od-panel__head">
                <div>
                  <h2>Quick actions</h2>
                  <p>Common tasks for your kitchen</p>
                </div>
              </header>
              <div className="od-actions">
                {QUICK_ACTIONS.map((a) => (
                  <Link key={a.to} to={a.to} className={`od-action od-action--${a.accent}`}>
                    <strong>{a.title}</strong>
                    <span>{a.desc}</span>
                  </Link>
                ))}
              </div>
            </section>
          </div>

          <section className="dash-card od-panel">
            <header className="od-panel__head">
              <div>
                <h2>Recent orders</h2>
                <p>Latest activity across all channels</p>
              </div>
              <Link to="/dashboard/orders" className="od-panel__link">All orders →</Link>
            </header>
            {recentOrders.length === 0 ? (
              <p className="od-panel__empty">
                No orders yet. Create a <Link to="/dashboard/orders/new">manual order</Link> or paste a WhatsApp message on the Orders page.
              </p>
            ) : (
              <ul className="od-recent">
                {recentOrders.map((o) => (
                  <li key={o.id}>
                    <Link to={`/dashboard/orders/${o.id}`} className="od-recent__row">
                      <div>
                        <strong>{o.order_code}</strong>
                        <span>{o.customer_name ?? o.customer_phone ?? "Walk-in"}</span>
                      </div>
                      <div className="od-recent__end">
                        <span className={`status-badge status-badge--${o.status}`}>
                          {STATUS_LABELS[o.status] ?? o.status}
                        </span>
                        <span className="od-recent__meta">{inr(o.total)} · {formatWhen(o.created_at)}</span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="dash-card od-share">
            <div className="od-share__copy">
              <h2>Customer menu link</h2>
              <p>
                Share this link so customers browse your <strong>live-capture menu</strong> on{" "}
                <strong>{CUSTOMER_HOST}</strong>. They can also enter kitchen code{" "}
                <strong className="od-board__code">{kitchen.code}</strong>.
              </p>
              <div className="kc-copy-field owner-share__row">
                <code>{menuLink}</code>
                <button type="button" className="btn btn--ghost btn--sm" onClick={copyLink}>
                  {copied ? "Copied!" : "Copy link"}
                </button>
              </div>
            </div>
            <div className="od-share__aside">
              <p className="od-share__tip-title">Grow faster</p>
              <ul className="od-share__tips">
                <li>Post the link on WhatsApp status daily</li>
                <li>Enable live stream when cooking signature dishes</li>
                <li>Check Reports weekly for peak hours</li>
              </ul>
              <Link to="/dashboard/subscription" className="btn btn--ghost btn--sm">
                Manage subscription
              </Link>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
