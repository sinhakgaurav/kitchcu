import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { DishRecipeGuide } from "../../components/DishRecipeGuide";
import {
  capturePayment,
  createPayment,
  createUpiIntent,
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

export function OrderDetailPage() {
  const { kitchen } = useKitchen();
  const { orderId } = useParams<{ orderId: string }>();
  const [order, setOrder] = useState<Order | null>(null);
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
    fetchOrder(orderId).then(setOrder).catch(() => setError("Order not found"));
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

  if (!order) return <div className="owner-page app-loading">{error || "Loading order..."}</div>;

  const next = ORDER_NEXT[order.status] ?? [];
  const needsPayment = ["online", "upi"].includes(order.payment_method);
  const paymentCaptured = payment?.status === "captured";

  return (
    <div className="owner-page">
      <Link to="/dashboard/orders" className="owner-back">← Back to orders</Link>

      <header className="owner-page__head">
        <div>
          <h1>{order.order_code}</h1>
          <p>{order.bill_id} · {new Date(order.created_at).toLocaleString()}</p>
        </div>
        <span className={`status-badge status-badge--${order.status} status-badge--lg`}>
          {STATUS_LABELS[order.status]}
        </span>
      </header>

      <div className="owner-detail-grid">
        <section className="glass">
          <h2>Items</h2>
          <ul className="owner-detail-items">
            {order.items.map((i) => (
              <li key={i.id}>
                <span>{i.quantity}× {i.dish_name}</span>
                <span>₹{(i.unit_price * i.quantity).toFixed(0)}</span>
              </li>
            ))}
          </ul>
          <div className="owner-detail-total">
            <span>Total</span>
            <strong>₹{order.total.toFixed(0)}</strong>
          </div>
          {order.customer_name && <p><strong>Customer:</strong> {order.customer_name} {order.customer_phone}</p>}
          <p><strong>Payment:</strong> {order.payment_method.toUpperCase()} · {order.delivery_type}</p>
          {paymentCaptured && (
            <p className="owner-pay-status owner-pay-status--ok">Payment captured · ₹{payment.amount.toFixed(0)}</p>
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

        {needsPayment && !paymentCaptured && order.status !== "cancelled" && (
          <section className="glass owner-pay-panel">
            <h2>Collect payment</h2>
            {payError && <div className="auth-card__error">{payError}</div>}
            {order.payment_method === "upi" && (
              <>
                <p>Show this UPI link or QR to the customer, then confirm when paid.</p>
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
                <p>Collect card/UPI/wallet payment via Razorpay (dev: instant capture).</p>
                <button type="button" className="btn btn--primary" disabled={payBusy} onClick={collectOnlinePayment}>
                  Collect ₹{order.total.toFixed(0)}
                </button>
              </>
            )}
          </section>
        )}

        {stockWarnings && stockWarnings.warnings.length > 0 && (
          <section className="glass owner-stock-warnings">
            <h2>Ingredient stock (before accept)</h2>
            <p className="owner-page__code">
              {stockWarnings.has_shortfall
                ? "Some ingredients may run short — review before accepting."
                : "Some items are below your low-stock threshold."}
            </p>
            <ul className="owner-detail-items">
              {stockWarnings.warnings.map((w) => (
                <li key={w.ingredient_id}>
                  <span>
                    {w.ingredient_name}: need {w.required}
                    {w.unit}, have {w.available}
                    {w.unit}
                    {w.shortfall > 0 ? ` (short ${w.shortfall}${w.unit})` : ""}
                  </span>
                  {w.is_low && <span className="status-badge status-badge--cancelled">Low</span>}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="glass">
          <h2>Update status</h2>
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
              <input
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Cancel reason"
              />
              <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => advance("cancelled")}>
                Cancel order
              </button>
            </div>
          )}
        </section>

        <section className="glass owner-timeline">
          <h2>Timeline</h2>
          {order.status_events.map((e) => (
            <div key={e.id} className="owner-timeline__item">
              <time>{new Date(e.created_at).toLocaleTimeString()}</time>
              <span>{STATUS_LABELS[e.to_status] ?? e.to_status}</span>
              {e.note && <small>{e.note}</small>}
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
