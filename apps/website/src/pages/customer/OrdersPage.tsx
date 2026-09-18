import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { OrderDishRatings } from "../../components/OrderDishRatings";
import type { DishHealthSnapshot, Order } from "../../shared/api";
import { getCustomerToken } from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";
import { addItemsToCart, kitchenFromOrderCode } from "../../shared/customerCart";
import { fetchMyOrders } from "../../shared/customerCheckoutApi";
import type { HealthNudge } from "../../shared/customerRatingsApi";
import { fetchDishesHealth } from "../../shared/publicApi";
import { customerStatusTone, humanStatus } from "../../shared/customerUi";

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
  const [searchParams] = useSearchParams();
  const focusOrderId = searchParams.get("rate");
  const [orders, setOrders] = useState<Order[]>([]);
  const [dishHealth, setDishHealth] = useState<Record<string, DishHealthSnapshot>>({});
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [repeatingId, setRepeatingId] = useState<string | null>(null);
  const [nudges, setNudges] = useState<Record<string, HealthNudge>>({});

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

  useEffect(() => {
    if (!focusOrderId || fetching) return;
    const el = document.getElementById(`order-${focusOrderId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [focusOrderId, fetching, orders.length]);

  useEffect(() => {
    const ids = orders.flatMap((order) => order.items.map((item) => item.dish_id));
    if (!ids.length) {
      setDishHealth({});
      return;
    }
    let cancelled = false;
    void fetchDishesHealth(ids)
      .then((res) => {
        if (cancelled) return;
        const map: Record<string, DishHealthSnapshot> = {};
        for (const snap of res.dishes) {
          if (snap.dish_id) map[String(snap.dish_id)] = snap;
        }
        setDishHealth(map);
      })
      .catch(() => {
        if (!cancelled) setDishHealth({});
      });
    return () => {
      cancelled = true;
    };
  }, [orders]);

  if (!loading && !token) {
    return <Navigate to="/login?next=/orders" replace />;
  }

  const groups = useMemo(() => {
    const result: { key: string; masterOrderId: string | null; orders: Order[] }[] = [];
    const byMaster = new Map<string, { key: string; masterOrderId: string; orders: Order[] }>();
    for (const order of orders) {
      if (order.master_order_id) {
        const existing = byMaster.get(order.master_order_id);
        if (existing) {
          existing.orders.push(order);
        } else {
          const group = {
            key: order.master_order_id,
            masterOrderId: order.master_order_id,
            orders: [order],
          };
          byMaster.set(order.master_order_id, group);
          result.push(group);
        }
      } else {
        result.push({ key: order.id, masterOrderId: null, orders: [order] });
      }
    }
    return result;
  }, [orders]);

  const onRepeat = (order: Order) => {
    setRepeatingId(order.id);
    setError("");
    try {
      if (!order.items.length) {
        setError("This order has no items to repeat");
        return;
      }
      addItemsToCart(
        kitchenFromOrderCode(order.kitchen_id, order.order_code),
        order.items.map((item) => ({
          dish_id: item.dish_id,
          dish_name: item.dish_name,
          quantity: item.quantity,
          unit_price: item.unit_price,
          prep_time_min: item.prep_time_min,
          special_instructions: item.special_instructions,
        })),
      );
      navigate("/checkout");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add items to cart");
    } finally {
      setRepeatingId(null);
    }
  };

  return (
    <div className="container customer-dash">
      <header className="customer-space__hero">
        <div>
          <p className="customer-dash__eyebrow">{t("customer.orders.history")}</p>
          <h1>{t("customer.orders.title")}</h1>
          <p className="customer-space__meta">{t("customer.orders.lede")}</p>
        </div>
        <div className="customer-dash__hero-actions">
          <Link to="/#near-you" className="btn btn--primary btn--sm">
            {t("customer.discovery.title")}
          </Link>
          <Link to="/dashboard" className="btn btn--ghost btn--sm">
            {t("customer.nav.dashboard")}
          </Link>
        </div>
      </header>

      {error && <div className="auth-card__error">{error}</div>}

      {loading || fetching ? (
        <p className="app-loading">{t("common.loading")}</p>
      ) : orders.length === 0 ? (
        <section className="glass empty-state">
          <p className="empty-state__title">{t("customer.orders.empty")}</p>
          <p className="empty-state__hint">{t("customer.orders.emptyHint")}</p>
          <Link to="/#near-you" className="btn btn--primary">
            {t("customer.discovery.title")}
          </Link>
        </section>
      ) : (
        <ul className="customer-dash__orders">
          {groups.map((group) => (
            <li key={group.key} className="customer-order-group">
              {group.masterOrderId && (
                <div className="customer-order-group__head">
                  <Link
                    to={`/master-orders/${group.masterOrderId}/confirm`}
                    className="btn btn--ghost btn--sm"
                  >
                    {t("customer.orders.masterReceipt", { count: group.orders.length })}
                  </Link>
                </div>
              )}
              {group.orders.map((order) => (
                <article
                  key={order.id}
                  id={`order-${order.id}`}
                  className={`glass customer-dash__order${focusOrderId === order.id ? " customer-dash__order--focus" : ""}`}
                >
                  <div className="customer-dash__order-head">
                    <div>
                      <div className="customer-dash__order-title">
                        <strong>{order.order_code}</strong>
                        <span className={`customer-status customer-status--${customerStatusTone(order.status)}`}>
                          {t(`status.${order.status}`, { defaultValue: humanStatus(order.status) })}
                        </span>
                      </div>
                      <span>
                        {formatWhen(order.created_at, i18n.language || "en")} ·{" "}
                        {t("customer.orders.itemsCount", { count: order.items.length })} · ₹
                        {order.total.toFixed(0)}
                      </span>
                    </div>
                    <div className="customer-dash__order-actions">
                      {order.tracking_token && (
                        <Link to={`/t/${order.tracking_token}`} className="btn btn--ghost btn--sm">
                          {t("customer.orders.track")}
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
                    </div>
                  </div>
                  <ul className="customer-dash__order-items">
                    {(order.status === "delivered" ? order.items : order.items.slice(0, 4)).map((item) => (
                      <li key={item.id} className="customer-dash__order-item">
                        <div>
                          {item.quantity}× {item.dish_name}
                          {dishHealth[item.dish_id]?.score != null
                            ? ` · health ${dishHealth[item.dish_id].score}`
                            : ""}
                        </div>
                        {order.status === "delivered" && (
                          <OrderDishRatings
                            orderId={order.id}
                            item={item}
                            canRate
                            onError={setError}
                            onRated={({ dishId, home_taste, quality, health_nudge }) => {
                              setError("");
                              setNudges((prev) => ({ ...prev, [order.id]: health_nudge }));
                              setOrders((prev) =>
                                prev.map((row) => {
                                  if (row.id !== order.id) return row;
                                  const items = row.items.map((line) =>
                                    line.dish_id === dishId
                                      ? {
                                          ...line,
                                          rating_home_taste: home_taste,
                                          rating_quality: quality,
                                        }
                                      : line,
                                  );
                                  const scored = items.filter((line) => line.rating_home_taste != null);
                                  const avgTaste =
                                    scored.length > 0
                                      ? scored.reduce((sum, line) => sum + (line.rating_home_taste ?? 0), 0) /
                                        scored.length
                                      : null;
                                  const avgQuality =
                                    scored.length > 0
                                      ? scored.reduce((sum, line) => sum + (line.rating_quality ?? 0), 0) /
                                        scored.length
                                      : null;
                                  return {
                                    ...row,
                                    items,
                                    is_rated: scored.length > 0,
                                    rating_home_taste: avgTaste,
                                    rating_quality: avgQuality,
                                  };
                                }),
                              );
                            }}
                          />
                        )}
                      </li>
                    ))}
                    {order.status !== "delivered" && order.items.length > 4 && (
                      <li>+{order.items.length - 4} more</li>
                    )}
                  </ul>
                  {nudges[order.id] && (
                    <p className="customer-wellness-nudge" role="status">
                      {nudges[order.id].message}{" "}
                      <span className="customer-wellness-nudge__meta">
                        (~{nudges[order.id].walk_minutes} min walk · ~{nudges[order.id].water_ml} ml water)
                      </span>
                    </p>
                  )}
                </article>
              ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
