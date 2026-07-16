import { Link, Navigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Order } from "../../shared/api";
import { getCustomerToken } from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";
import { fetchMyOrders } from "../../shared/customerCheckoutApi";
import { submitOrderRatings, type DishRatingInput } from "../../shared/customerRatingsApi";

type ItemRating = {
  dish_id: string;
  dish_name: string;
  home_taste_score: number;
  quality_score: number;
  media_url: string;
};

export function RateOrderPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { loading } = useCustomerAuth();
  const token = getCustomerToken();
  const [order, setOrder] = useState<Order | null>(null);
  const [ratings, setRatings] = useState<ItemRating[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [healthNudge, setHealthNudge] = useState<{ message: string; walk_minutes: number; water_ml: number } | null>(null);

  useEffect(() => {
    if (!token || !orderId) return;
    fetchMyOrders()
      .then(({ orders }) => {
        const found = orders.find((o) => o.id === orderId);
        if (!found) throw new Error("Order not found");
        if (found.status !== "delivered") throw new Error("Only delivered orders can be rated");
        setOrder(found);
        setRatings(
          found.items.map((item) => ({
            dish_id: item.dish_id,
            dish_name: item.dish_name,
            home_taste_score: 5,
            quality_score: 5,
            media_url: "",
          })),
        );
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load order"));
  }, [token, orderId]);

  if (!loading && !token) {
    return <Navigate to={`/login?next=/orders/${orderId}/rate`} replace />;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderId) return;
    setBusy(true);
    setError("");
    try {
      const payload: DishRatingInput[] = ratings.map((r) => ({
        dish_id: r.dish_id,
        home_taste_score: r.home_taste_score,
        quality_score: r.quality_score,
        ...(r.media_url.trim()
          ? { media_url: r.media_url.trim(), media_type: "video" as const }
          : {}),
      }));
      const result = await submitOrderRatings(orderId, payload);
      setHealthNudge(result.health_nudge);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit ratings");
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="container customer-checkout">
        <section className="glass">
          <h1>Thank you!</h1>
          <p>Your home-taste ratings help this kitchen grow with trust.</p>
          {healthNudge && (
            <p className="customer-wellness-nudge" role="status">
              {healthNudge.message}
              {" "}
              <span className="customer-wellness-nudge__meta">
                (~{healthNudge.walk_minutes} min walk · ~{healthNudge.water_ml} ml water)
              </span>
            </p>
          )}
          <Link to="/orders" className="btn btn--primary">Back to orders</Link>
        </section>
      </div>
    );
  }

  return (
    <div className="container customer-checkout">
      <Link to="/orders" className="owner-back">← Back to orders</Link>
      <header className="owner-page__head">
        <div>
          <h1>Rate your meal</h1>
          <p>Home taste vs restaurant — only verified delivered orders count.</p>
        </div>
      </header>

      {error && <div className="auth-card__error">{error}</div>}
      {!order && !error && <p className="app-loading">Loading order…</p>}

      {order && (
        <form className="owner-form" onSubmit={submit}>
          <p className="owner-page__code">{order.order_code}</p>
          {ratings.map((item, idx) => (
            <fieldset key={item.dish_id} className="owner-card">
              <legend>{item.dish_name}</legend>
              <label>
                Home taste (1–5)
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={item.home_taste_score}
                  onChange={(e) => {
                    const next = [...ratings];
                    next[idx] = { ...item, home_taste_score: Number(e.target.value) };
                    setRatings(next);
                  }}
                />
                <span>{item.home_taste_score}/5</span>
              </label>
              <label>
                Quality (1–5)
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={item.quality_score}
                  onChange={(e) => {
                    const next = [...ratings];
                    next[idx] = { ...item, quality_score: Number(e.target.value) };
                    setRatings(next);
                  }}
                />
                <span>{item.quality_score}/5</span>
              </label>
              <label>
                Optional review video URL (anonymous)
                <input
                  className="owner-input"
                  type="url"
                  placeholder="https://…"
                  value={item.media_url}
                  onChange={(e) => {
                    const next = [...ratings];
                    next[idx] = { ...item, media_url: e.target.value };
                    setRatings(next);
                  }}
                />
              </label>
            </fieldset>
          ))}
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? "Submitting…" : "Submit ratings"}
          </button>
        </form>
      )}
    </div>
  );
}
