import { Link, Navigate, useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Order } from "../../shared/api";
import { getCustomerToken } from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";
import { fetchMyOrders, repeatCustomerOrder } from "../../shared/customerCheckoutApi";

function formatWhen(iso: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale.startsWith("en") ? "en-IN" : locale, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function OrdersPage() {
  const { t, i18n } = useTranslation();
  const { loading } = useCustomerAuth();
  const token = getCustomerToken();
  const navigate = useNavigate();
  const [orders, setOrders] = useState<Order[]>([]);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [repeatingId, setRepeatingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setFetching(true);
    setError("");
    try {
      const data = await fetchMyOrders();
      setOrders(data.orders);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load orders");
      setOrders([]);
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!loading && !token) {
    return <Navigate to="/login?next=/orders" replace />;
  }

  const onRepeat = async (order: Order) => {
    setRepeatingId(order.id);
    setError("");
    try {
      const newOrder = await repeatCustomerOrder(order.id);
      navigate(`/orders/${newOrder.id}/confirm`, {
        state: { order: newOrder, paymentMethod: newOrder.payment_method },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not repeat order");
    } finally {
      setRepeatingId(null);
    }
  };

  return (
    <div className="container customer-checkout">
      <header className="owner-page__head">
        <div>
          <h1>{t("customer.orders.title")}</h1>
          <p>{t("customer.orders.history")}</p>
        </div>
        <Link to="/#near-you" className="btn btn--ghost btn--sm">{t("customer.discovery.title")}</Link>
      </header>

      {error && <div className="auth-card__error">{error}</div>}

      {fetching ? (
        <p className="app-loading">{t("common.loading")}</p>
      ) : orders.length === 0 ? (
        <section className="glass">
          <p>{t("customer.orders.empty")}</p>
          <Link to="/#near-you" className="btn btn--primary">{t("customer.discovery.title")}</Link>
        </section>
      ) : (
        <ul className="nearby-kitchens__list">
          {orders.map((order) => (
            <li key={order.id}>
              <article className="glass nearby-kitchens__card" style={{ cursor: "default" }}>
                <div className="nearby-kitchens__card-body">
                  <strong>{order.order_code}</strong>
                  <span className="nearby-kitchens__meta">
                    {formatWhen(order.created_at, i18n.language || "en")} ·{" "}
                    {t(`status.${order.status}`, { defaultValue: order.status.replace(/_/g, " ") })}
                  </span>
                  <span className="nearby-kitchens__meta">
                    {order.items.length} item{order.items.length === 1 ? "" : "s"} · ₹{order.total.toFixed(0)}
                  </span>
                  <ul className="owner-detail-items">
                    {order.items.slice(0, 4).map((item) => (
                      <li key={item.id}>
                        <span>{item.quantity}× {item.dish_name}</span>
                      </li>
                    ))}
                    {order.items.length > 4 && (
                      <li><span>+{order.items.length - 4} more</span></li>
                    )}
                  </ul>
                </div>
                <div className="owner-actions">
                  {order.tracking_token && (
                    <Link to={`/t/${order.tracking_token}`} className="btn btn--ghost btn--sm">
                      Track
                    </Link>
                  )}
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    disabled={repeatingId === order.id || order.status === "cancelled"}
                    onClick={() => onRepeat(order)}
                  >
                    {repeatingId === order.id ? t("common.loading") : t("customer.orders.repeat")}
                  </button>
                  {order.status === "delivered" && (
                    <Link to={`/orders/${order.id}/rate`} className="btn btn--ghost btn--sm">
                      Rate meal
                    </Link>
                  )}
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
