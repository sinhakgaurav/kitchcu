import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchTracking, type TrackingInfo } from "../../shared/api";
import { STATUS_LABELS } from "../../lib/api";
import { googleMapsDirectionsEmbedUrl, googleMapsRouteUrl } from "../../lib/locationMaps";

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

  const hasRoute =
    info?.kitchen_latitude != null &&
    info.kitchen_longitude != null &&
    info.customer_latitude != null &&
    info.customer_longitude != null;

  return (
    <div className="container customer-checkout">
      <Link to="/" className="owner-back">← Back to kitchCU</Link>
      <header className="owner-page__head">
        <div>
          <h1>Order tracking</h1>
          <p>Live status + Google Maps route from kitchen to you.</p>
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

          {hasRoute && (
            <div className="track-map">
              <iframe
                title="Delivery route on Google Maps"
                className="track-map__frame"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                src={googleMapsDirectionsEmbedUrl(
                  info.kitchen_latitude!,
                  info.kitchen_longitude!,
                  info.customer_latitude!,
                  info.customer_longitude!,
                )}
              />
              <a
                className="btn btn--ghost btn--sm"
                href={
                  info.map_directions_url ||
                  googleMapsRouteUrl(
                    info.kitchen_latitude!,
                    info.kitchen_longitude!,
                    info.customer_latitude!,
                    info.customer_longitude!,
                  )
                }
                target="_blank"
                rel="noreferrer"
              >
                Open in Google Maps
              </a>
            </div>
          )}

          {(info.estimated_prep_min != null || info.estimated_delivery_min != null) && (
            <p className="report-hint">
              Timing: prep {info.estimated_prep_min ?? "—"} min
              {info.delivery_type === "delivery" && (
                <> + delivery {info.estimated_delivery_min ?? "—"} min
                  {info.estimated_prep_min != null && info.estimated_delivery_min != null && (
                    <> = ~{info.estimated_prep_min + info.estimated_delivery_min} min total</>
                  )}
                </>
              )}
            </p>
          )}
          {info.estimated_ready_at && (
            <p className="report-hint">
              Food ready around{" "}
              {new Date(info.estimated_ready_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
            </p>
          )}
          {info.estimated_delivery_at && info.delivery_type === "delivery" && (
            <p className="report-hint">
              Estimated delivery around{" "}
              {new Date(info.estimated_delivery_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
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
