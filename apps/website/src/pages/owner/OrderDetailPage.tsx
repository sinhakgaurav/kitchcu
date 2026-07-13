import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { DishRecipeGuide } from "../../components/DishRecipeGuide";
import {
  capturePayment,
  createPayment,
  createUpiIntent,
  downloadOwnerOrderBillPdf,
  fetchOrder,
  fetchOrderStockWarnings,
  ORDER_NEXT,
  STATUS_LABELS,
  updateOrderStatus,
  type Order,
  type OrderStockWarnings,
  type Payment,
  type UpiIntent,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function OrderDetailSkeleton() {
  return (
    <div className="od-order-detail__loading">
      <div className="od-skeleton od-skeleton--wide" />
      <div className="od-order-detail__grid">
        <div className="od-skeleton od-skeleton--chart" />
        <div className="od-skeleton od-skeleton--chart" />
      </div>
    </div>
  );
}

export function OrderDetailPage() {
  const { kitchen } = useKitchen();
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [payment, setPayment] = useState<Payment | null>(null);
  const [upiIntent, setUpiIntent] = useState<UpiIntent | null>(null);
  const [payError, setPayError] = useState("");
  const [payBusy, setPayBusy] = useState(false);
  const [stockWarnings, setStockWarnings] = useState<OrderStockWarnings | null>(null);

  useEffect(() => {
    if (!orderId) return;
    setLoading(true);
    fetchOrder(orderId)
      .then(setOrder)
      .catch(() => setError("Order not found"))
      .finally(() => setLoading(false));
  }, [orderId]);

  useEffect(() => {
    if (!orderId || !order || order.status !== "received") {
      setStockWarnings(null);
      return;
    }
    fetchOrderStockWarnings(orderId)
      .then(setStockWarnings)
      .catch(() => setStockWarnings(null));
  }, [orderId, order?.status, order?.id]);

  const advance = async (status: string) => {
    if (!order) return;
    setError("");
    setBusy(true);
    try {
      const updated = await updateOrderStatus(order.id, {
        status,
        cancel_reason: status === "cancelled" ? cancelReason || "Cancelled by owner" : undefined,
      });
      setOrder(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const startUpiPayment = async () => {
    if (!order) return;
    setPayError("");
    setPayBusy(true);
    try {
      const intent = await createUpiIntent(order.id);
      setUpiIntent(intent);
      setPayment(null);
    } catch (err) {
      setPayError(err instanceof Error ? err.message : "UPI intent failed");
    } finally {
      setPayBusy(false);
    }
  };

  const collectOnlinePayment = async () => {
    if (!order) return;
    setPayError("");
    setPayBusy(true);
    try {
      const created = await createPayment({ order_id: order.id, method: "online" });
      const captured = await capturePayment(created.id);
      setPayment(captured);
      setUpiIntent(null);
    } catch (err) {
      setPayError(err instanceof Error ? err.message : "Payment failed");
    } finally {
      setPayBusy(false);
    }
  };

  const markUpiPaid = async () => {
    if (!upiIntent) return;
    setPayError("");
    setPayBusy(true);
    try {
      const captured = await capturePayment(upiIntent.payment_id);
      setPayment(captured);
    } catch (err) {
      setPayError(err instanceof Error ? err.message : "Capture failed");
    } finally {
      setPayBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="owner-screen od-board od-order-detail">
        <Link to="/dashboard/orders" className="owner-back">← Back to orders</Link>
        <OrderDetailSkeleton />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="owner-screen od-board od-order-detail">
        <Link to="/dashboard/orders" className="owner-back">← Back to orders</Link>
        <p className="od-panel__empty dash-card od-panel">{error || "Order not found"}</p>
      </div>
    );
  }

  const next = ORDER_NEXT[order.status] ?? [];
  const needsPayment = ["online", "upi"].includes(order.payment_method);
  const paymentCaptured = payment?.status === "captured";

  return (
    <div className="owner-screen od-board od-order-detail">
      <Link to="/dashboard/orders" className="owner-back">← Back to orders</Link>

      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">Order detail</p>
          <h1>{order.order_code}</h1>
          <p className="od-board__meta">
            <span className="od-board__code">{order.bill_id}</span>
            <span>{new Date(order.created_at).toLocaleString("en-IN")}</span>
            <span>{order.source} · {order.delivery_type}</span>
          </p>
          <div className="od-board__pills">
            <span className={`status-badge status-badge--${order.status} status-badge--lg`}>
              {STATUS_LABELS[order.status]}
            </span>
            <span className="od-pill od-pill--sub">{order.payment_method.toUpperCase()}</span>
            {paymentCaptured && <span className="od-pill od-pill--active">Paid</span>}
          </div>
        </div>
        <div className="od-board__hero-actions">
          <strong className="od-order-detail__total">{inr(order.total)}</strong>
          <span className="od-order-detail__total-label">Order total</span>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            style={{ marginTop: "0.75rem" }}
            onClick={() => {
              downloadOwnerOrderBillPdf(order.id, order.order_code).catch((err) =>
                setError(err instanceof Error ? err.message : "Download failed"),
              );
            }}
          >
            Download PDF bill
          </button>
        </div>
      </section>

      <div className="od-order-detail__grid">
        <section className="dash-card od-panel">
          <header className="od-panel__head">
            <div>
              <h2>Line items</h2>
              <p>{order.items.length} dish{order.items.length !== 1 ? "es" : ""}</p>
            </div>
          </header>
          <ul className="owner-detail-items">
            {order.items.map((i) => (
              <li key={i.id}>
                <span>{i.quantity}× {i.dish_name}</span>
                <span>{inr(i.unit_price * i.quantity)}</span>
              </li>
            ))}
          </ul>
          <div className="owner-detail-total">
            <span>Total</span>
            <strong>{inr(order.total)}</strong>
          </div>
          {(order.customer_name || order.customer_phone) && (
            <p className="od-order-detail__customer">
              <strong>Customer:</strong> {order.customer_name ?? "—"} {order.customer_phone ?? ""}
            </p>
          )}
          {kitchen && order.status !== "cancelled" && order.status !== "delivered" && (
            <div className="owner-recipe-guide-list">
              <h3>Prep guides</h3>
              {order.items.map((item) => (
                <DishRecipeGuide
                  key={item.id}
                  kitchenId={kitchen.id}
                  dishId={item.dish_id}
                  dishName={item.dish_name}
                  quantity={item.quantity}
                  defaultOpen={order.items.length === 1}
                />
              ))}
            </div>
          )}
        </section>

        <div className="od-order-detail__side">
          {needsPayment && !paymentCaptured && order.status !== "cancelled" && (
            <section className="dash-card od-panel owner-pay-panel">
              <header className="od-panel__head">
                <div>
                  <h2>Collect payment</h2>
                  <p>{order.payment_method === "upi" ? "UPI link or QR" : "Online checkout"}</p>
                </div>
              </header>
              {payError && <div className="auth-card__error">{payError}</div>}
              {order.payment_method === "upi" && (
                <>
                  <p className="od-panel__empty">Show UPI link to customer, then confirm when paid.</p>
                  <button type="button" className="btn btn--primary" disabled={payBusy} onClick={startUpiPayment}>
                    Generate UPI link
                  </button>
                  {upiIntent && (
                    <div className="owner-upi-box">
                      <code>{upiIntent.upi_uri}</code>
                      <div className="owner-upi-actions">
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => navigator.clipboard.writeText(upiIntent.upi_uri)}
                        >
                          Copy link
                        </button>
                        <button type="button" className="btn btn--primary btn--sm" disabled={payBusy} onClick={markUpiPaid}>
                          Mark as paid
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
              {order.payment_method === "online" && (
                <>
                  <p className="od-panel__empty">Collect via Razorpay (dev: instant capture).</p>
                  <button type="button" className="btn btn--primary" disabled={payBusy} onClick={collectOnlinePayment}>
                    Collect {inr(order.total)}
                  </button>
                </>
              )}
            </section>
          )}

          {stockWarnings && stockWarnings.warnings.length > 0 && (
            <section className="dash-card od-panel owner-stock-warnings">
              <header className="od-panel__head">
                <div>
                  <h2>Ingredient stock</h2>
                  <p>Review before accepting</p>
                </div>
              </header>
              <p className="od-order-detail__stock-hint">
                {stockWarnings.has_shortfall
                  ? "Some ingredients may run short."
                  : "Some items are below low-stock threshold."}
              </p>
              <ul className="owner-detail-items">
                {stockWarnings.warnings.map((w) => (
                  <li key={w.ingredient_id}>
                    <span>
                      {w.ingredient_name}: need {w.required}{w.unit}, have {w.available}{w.unit}
                      {w.shortfall > 0 ? ` (short ${w.shortfall}${w.unit})` : ""}
                    </span>
                    {w.is_low && <span className="status-badge status-badge--cancelled">Low</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="dash-card od-panel">
            <header className="od-panel__head">
              <div>
                <h2>Update status</h2>
                <p>Move order through the kitchen pipeline</p>
              </div>
            </header>
            {error && <div className="auth-card__error">{error}</div>}
            <div className="owner-status-actions">
              {next.filter((s) => s !== "cancelled").map((s) => (
                <button key={s} type="button" className="btn btn--primary" disabled={busy} onClick={() => advance(s)}>
                  Mark {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
            {next.includes("cancelled") && (
              <div className="owner-cancel">
                <label className="kc-field owner-cancel__field">
                  <span className="kc-field__label">Cancel reason</span>
                  <input
                    className="kc-input"
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    placeholder="e.g. Out of stock, customer request"
                  />
                </label>
                <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => advance("cancelled")}>
                  Cancel order
                </button>
              </div>
            )}
          </section>

          <section className="dash-card od-panel owner-timeline">
            <header className="od-panel__head">
              <div>
                <h2>Timeline</h2>
                <p>Status history</p>
              </div>
            </header>
            {order.status_events.map((e) => (
              <div key={e.id} className="owner-timeline__item">
                <time>{new Date(e.created_at).toLocaleString("en-IN")}</time>
                <span className={`status-badge status-badge--${e.to_status}`}>
                  {STATUS_LABELS[e.to_status] ?? e.to_status}
                </span>
                {e.note && <small>{e.note}</small>}
              </div>
            ))}
          </section>
        </div>
      </div>
    </div>
  );
}
