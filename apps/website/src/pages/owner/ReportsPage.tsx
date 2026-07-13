import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchCustomerSegments,
  fetchPeakHours,
  fetchRevenueSummary,
  fetchRevenueTimeseries,
  fetchTopDishes,
  type CustomerSegments,
  type PeakHours,
  type RevenueSummary,
  type RevenueTimeseries,
  type TopDishes,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const RANGES = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function chartDayLabel(isoDate: string): string {
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-IN", { weekday: "short" });
}

function ReportsSkeleton() {
  return (
    <div className="od-reports__loading">
      <div className="od-board__kpi-grid">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="od-skeleton od-skeleton--card" />
        ))}
      </div>
      <div className="od-skeleton od-skeleton--wide" />
      <div className="report-grid">
        <div className="od-skeleton od-skeleton--chart" />
        <div className="od-skeleton od-skeleton--chart" />
      </div>
    </div>
  );
}

export function ReportsPage() {
  const { kitchen } = useKitchen();
  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<RevenueSummary | null>(null);
  const [series, setSeries] = useState<RevenueTimeseries | null>(null);
  const [dishes, setDishes] = useState<TopDishes | null>(null);
  const [peak, setPeak] = useState<PeakHours | null>(null);
  const [customers, setCustomers] = useState<CustomerSegments | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const hasLoaded = useRef(false);

  useEffect(() => {
    if (!kitchen) return;
    if (hasLoaded.current) setRefreshing(true);
    else setLoading(true);
    setError("");
    Promise.all([
      fetchRevenueSummary(kitchen.id, days),
      fetchRevenueTimeseries(kitchen.id, days),
      fetchTopDishes(kitchen.id, days, 8),
      fetchPeakHours(kitchen.id, days),
      fetchCustomerSegments(kitchen.id, Math.max(days, 90), 8),
    ])
      .then(([s, t, d, p, c]) => {
        setSummary(s);
        setSeries(t);
        setDishes(d);
        setPeak(p);
        setCustomers(c);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load reports"))
      .finally(() => {
        hasLoaded.current = true;
        setLoading(false);
        setRefreshing(false);
      });
  }, [kitchen, days]);

  const maxRevenue = useMemo(
    () => Math.max(1, ...(series?.points.map((p) => p.revenue) ?? [1])),
    [series],
  );
  const maxHour = useMemo(
    () => Math.max(1, ...(peak?.hours.map((h) => h.orders) ?? [1])),
    [peak],
  );
  const maxDishRevenue = useMemo(
    () => Math.max(1, ...(dishes?.dishes.map((d) => d.revenue) ?? [1])),
    [dishes],
  );

  if (!kitchen) return null;

  return (
    <div className="owner-screen od-board od-reports">
      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">Growth intelligence</p>
          <h1>Reports</h1>
          <p className="od-board__meta">
            Revenue trends · best sellers · peak hours · customer retention
          </p>
        </div>
        <div className="od-board__hero-actions od-board__hero-actions--tools">
          <div className="owner-tabs od-reports__range">
            {RANGES.map((r) => (
              <button
                key={r.days}
                type="button"
                className={days === r.days ? "active" : ""}
                onClick={() => setDays(r.days)}
                disabled={loading}
              >
                {r.label}
              </button>
            ))}
          </div>
          <Link to="/dashboard/crm" className="btn btn--ghost btn--sm">Open CRM →</Link>
        </div>
      </section>

      {error && <div className="auth-card__error">{error}</div>}

      {loading ? (
        <ReportsSkeleton />
      ) : summary ? (
        <div className={refreshing ? "od-reports__body od-reports__body--refreshing" : "od-reports__body"}>
          {refreshing && <p className="od-reports__refresh-hint">Updating {days}-day window…</p>}
          <div className="od-board__kpi-grid od-reports__kpis">
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--revenue" aria-hidden="true" />
              <div>
                <strong>{inr(summary.gross_revenue)}</strong>
                <span>Revenue ({summary.window_days}d)</span>
                <em>{summary.completed_orders} completed orders</em>
              </div>
            </div>
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--orders" aria-hidden="true" />
              <div>
                <strong>{summary.completed_orders}</strong>
                <span>Orders</span>
                <em>{summary.active_orders} still active</em>
              </div>
            </div>
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--menu" aria-hidden="true" />
              <div>
                <strong>{inr(summary.avg_order_value)}</strong>
                <span>Avg order value</span>
                <em>Per completed order</em>
              </div>
            </div>
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--drafts" aria-hidden="true" />
              <div>
                <strong>{pct(summary.repeat_rate)}</strong>
                <span>Repeat rate</span>
                <em>{summary.repeat_customers} returning customers</em>
              </div>
            </div>
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--orders" aria-hidden="true" />
              <div>
                <strong>{summary.unique_customers}</strong>
                <span>Unique customers</span>
                <em>In this window</em>
              </div>
            </div>
            <div className="od-kpi dash-card">
              <span className="od-kpi__icon od-kpi__icon--drafts" aria-hidden="true" />
              <div>
                <strong>{pct(summary.cancellation_rate)}</strong>
                <span>Cancellation rate</span>
                <em>{summary.cancelled_orders} cancelled</em>
              </div>
            </div>
          </div>

          <section className="dash-card od-panel report-card">
            <header className="od-panel__head">
              <div>
                <h2>Revenue trend</h2>
                <p>Daily gross revenue over the selected period</p>
              </div>
            </header>
            {series && series.points.every((p) => p.revenue === 0) ? (
              <p className="od-panel__empty">No revenue in this period yet — share your menu link to get started.</p>
            ) : (
              <div className="report-bars od-reports__bars">
                {series?.points.map((p) => (
                  <div key={p.date} className="report-bars__col" title={`${p.date}: ${inr(p.revenue)} · ${p.orders} orders`}>
                    <div
                      className="report-bars__fill"
                      style={{ height: `${(p.revenue / maxRevenue) * 100}%` }}
                    />
                    <span className="report-bars__label">{chartDayLabel(p.date)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="report-grid">
            <section className="dash-card od-panel report-card">
              <header className="od-panel__head">
                <div>
                  <h2>Top dishes</h2>
                  <p>Best sellers by revenue</p>
                </div>
              </header>
              {dishes && dishes.dishes.length > 0 ? (
                <ul className="report-rank">
                  {dishes.dishes.map((d, idx) => (
                    <li key={d.dish_id}>
                      <div className="report-rank__row">
                        <span><em className="od-reports__rank">{idx + 1}</em> {d.dish_name}</span>
                        <strong>{inr(d.revenue)}</strong>
                      </div>
                      <div className="report-rank__track">
                        <div
                          className="report-rank__bar"
                          style={{ width: `${(d.revenue / maxDishRevenue) * 100}%` }}
                        />
                      </div>
                      <span className="report-rank__meta">{d.quantity} sold · {d.order_count} orders</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="od-panel__empty">No dish sales yet.</p>
              )}
            </section>

            <section className="dash-card od-panel report-card">
              <header className="od-panel__head">
                <div>
                  <h2>Busy hours (IST)</h2>
                  <p>When customers order most</p>
                </div>
              </header>
              <div className="report-hours od-reports__hours">
                {peak?.hours.map((h) => (
                  <div key={h.hour} className="report-hours__col" title={`${h.hour}:00 — ${h.orders} orders`}>
                    <div
                      className="report-hours__fill"
                      style={{ height: `${(h.orders / maxHour) * 100}%` }}
                    />
                    {h.hour % 6 === 0 && <span>{h.hour}</span>}
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="report-grid">
            <section className="dash-card od-panel report-card">
              <header className="od-panel__head">
                <div>
                  <h2>Best customers</h2>
                  <p>Highest spend in the lookback window</p>
                </div>
              </header>
              <div className="report-seg">
                <span>{customers?.new_customers ?? 0} new</span>
                <span>{customers?.repeat_customers ?? 0} repeat</span>
                <span>{customers?.vip_customers ?? 0} VIP</span>
              </div>
              {customers && customers.top_customers.length > 0 ? (
                <table className="report-table">
                  <tbody>
                    {customers.top_customers.map((c) => (
                      <tr key={c.customer_phone}>
                        <td>{c.customer_name ?? c.customer_phone}</td>
                        <td>{c.orders} orders</td>
                        <td>{inr(c.total_spent)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="od-panel__empty">No customer data yet.</p>
              )}
            </section>

            <section className="dash-card od-panel report-card">
              <header className="od-panel__head">
                <div>
                  <h2>Win-back list</h2>
                  <p>Loyal customers who haven&apos;t ordered in 3+ weeks</p>
                </div>
              </header>
              <p className="report-hint">Send them a coupon from the Coupons page to re-engage.</p>
              {customers && customers.churn_risk.length > 0 ? (
                <table className="report-table">
                  <tbody>
                    {customers.churn_risk.map((c) => (
                      <tr key={c.customer_phone}>
                        <td>{c.customer_name ?? c.customer_phone}</td>
                        <td>{c.orders} orders</td>
                        <td>last {new Date(c.last_order_at).toLocaleDateString("en-IN")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="od-panel__empty">No customers at risk — great retention!</p>
              )}
            </section>
          </div>
        </div>
      ) : null}
    </div>
  );
}
