import { useEffect, useMemo, useState } from "react";
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

  useEffect(() => {
    if (!kitchen) return;
    setLoading(true);
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
      .finally(() => setLoading(false));
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
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Growth reports</h1>
          <p className="owner-page__code">Revenue, best sellers, busy hours & customer retention</p>
        </div>
        <div className="owner-tabs">
          {RANGES.map((r) => (
            <button
              key={r.days}
              type="button"
              className={days === r.days ? "active" : ""}
              onClick={() => setDays(r.days)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </header>

      {error && <div className="auth-card__error">{error}</div>}
      {loading && <p className="owner-empty">Crunching numbers...</p>}

      {!loading && summary && (
        <>
          <div className="owner-stats report-kpis">
            <div className="owner-stat glass">
              <strong>{inr(summary.gross_revenue)}</strong>
              <span>Revenue ({summary.window_days}d)</span>
            </div>
            <div className="owner-stat glass">
              <strong>{summary.completed_orders}</strong>
              <span>Orders</span>
            </div>
            <div className="owner-stat glass">
              <strong>{inr(summary.avg_order_value)}</strong>
              <span>Avg order value</span>
            </div>
            <div className="owner-stat glass">
              <strong>{pct(summary.repeat_rate)}</strong>
              <span>Repeat customers</span>
            </div>
            <div className="owner-stat glass">
              <strong>{summary.unique_customers}</strong>
              <span>Unique customers</span>
            </div>
            <div className="owner-stat glass">
              <strong>{pct(summary.cancellation_rate)}</strong>
              <span>Cancellation rate</span>
            </div>
          </div>

          <section className="glass report-card">
            <h2>Revenue trend</h2>
            {series && series.points.every((p) => p.revenue === 0) ? (
              <p className="owner-empty">No revenue in this period yet.</p>
            ) : (
              <div className="report-bars">
                {series?.points.map((p) => (
                  <div key={p.date} className="report-bars__col" title={`${p.date}: ${inr(p.revenue)} · ${p.orders} orders`}>
                    <div
                      className="report-bars__fill"
                      style={{ height: `${(p.revenue / maxRevenue) * 100}%` }}
                    />
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="report-grid">
            <section className="glass report-card">
              <h2>Top dishes</h2>
              {dishes && dishes.dishes.length > 0 ? (
                <ul className="report-rank">
                  {dishes.dishes.map((d) => (
                    <li key={d.dish_id}>
                      <div className="report-rank__row">
                        <span>{d.dish_name}</span>
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
                <p className="owner-empty">No dish sales yet.</p>
              )}
            </section>

            <section className="glass report-card">
              <h2>Busy hours (IST)</h2>
              <div className="report-hours">
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
            <section className="glass report-card">
              <h2>Best customers</h2>
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
                <p className="owner-empty">No customer data yet.</p>
              )}
            </section>

            <section className="glass report-card">
              <h2>Win-back list (churn risk)</h2>
              <p className="report-hint">Loyal customers who haven't ordered in 3+ weeks — send them an offer.</p>
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
                <p className="owner-empty">No customers at risk. Great retention!</p>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
