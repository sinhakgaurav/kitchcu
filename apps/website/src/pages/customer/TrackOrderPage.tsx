import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTracking, type TrackingInfo } from "../../shared/api";
import { STATUS_LABELS } from "../../lib/api";

export function TrackOrderPage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<TrackingInfo | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetchTracking(token)
      .then(setInfo)
      .catch((err) => setError(err instanceof Error ? err.message : "Tracking not found"))
      .finally(() => setLoading(false));
    const timer = window.setInterval(() => {
      fetchTracking(token).then(setInfo).catch(() => undefined);
    }, 30000);
    return () => window.clearInterval(timer);
  }, [token]);

  if (!token) {
    return (
      <div className="container customer-checkout">
        <p className="owner-empty">Invalid tracking link.</p>
      </div>
    );
  }

  return (
    <div className="container customer-checkout">
      <Link to="/" className="owner-back">← Back to kitchCU</Link>
      <header className="owner-page__head">
        <div>
          <h1>Order tracking</h1>
          <p>Live status from your kitchen — quality-first ETA, not a speed race.</p>
        </div>
      </header>

      {loading && <p className="owner-empty">Loading tracking…</p>}
      {error && <div className="auth-card__error">{error}</div>}

      {info && (
        <section className="glass report-card">
          <h2>{info.kitchen_name ?? "Kitchen"}</h2>
          <p className="owner-page__code">{info.order_code}</p>
          <div className="owner-stats report-kpis">
            <div className="owner-stat glass">
              <strong>{STATUS_LABELS[info.status] ?? info.status}</strong>
              <span>Status</span>
            </div>
            {info.distance_km != null && (
              <div className="owner-stat glass">
                <strong>{info.distance_km.toFixed(1)} km</strong>
                <span>Distance</span>
              </div>
            )}
            <div className="owner-stat glass">
              <strong>₹{Math.round(info.delivery_fee)}</strong>
              <span>Delivery fee</span>
            </div>
          </div>
          {info.estimated_ready_at && (
            <p className="report-hint">
              Estimated ready around{" "}
              {new Date(info.estimated_ready_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
            </p>
          )}
          <p className="report-hint">
            Progress updates every {info.tracking_notify_interval_min} minutes while your order is preparing.
          </p>
        </section>
      )}
    </div>
  );
}
