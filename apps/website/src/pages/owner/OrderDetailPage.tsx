import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { DishRecipeGuide } from "../../components/DishRecipeGuide";
import {
  capturePayment,
  completeDirectRefund,
  createPayment,
  createRefund,
  createUpiIntent,
  downloadOwnerOrderBillPdf,
  fetchOrder,
  fetchOrderStockWarnings,
  fetchRefunds,
  ORDER_NEXT,
  processGatewayRefund,
  setOrderDeliveryFulfillment,
  STATUS_LABELS,
  updateOrderStatus,
  uploadRefundEvidence,
  type Order,
  type OrderStockWarnings,
  type Payment,
  type Refund,
  type UpiIntent,
} from "../../lib/api";
import { googleMapsDirectionsEmbedUrl, googleMapsRouteUrl } from "../../lib/locationMaps";
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
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [refundKind, setRefundKind] = useState<"full" | "partial">("full");
  const [refundChannel, setRefundChannel] = useState<"gateway" | "direct_transfer">("gateway");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [refundError, setRefundError] = useState("");
  const [refundBusy, setRefundBusy] = useState(false);
  const [fulfillBusy, setFulfillBusy] = useState(false);
  const [fulfillError, setFulfillError] = useState("");

  useEffect(() => {
    if (!orderId) return;
    setLoading(true);
    fetchOrder(orderId)
      .then(setOrder)
      .catch(() => setError("Order not found"))
      .finally(() => setLoading(false));
  }, [orderId]);

  useEffect(() => {
    if (!orderId) return;
    fetchRefunds(orderId)
      .then(setRefunds)
      .catch(() => setRefunds([]));
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

  const refreshRefunds = async () => {
    if (!orderId) return;
    setRefunds(await fetchRefunds(orderId));
  };

  const submitRefund = async () => {
    if (!order) return;
    setRefundError("");
    setRefundBusy(true);
    try {
      const created = await createRefund({
        order_id: order.id,
        kind: refundKind,
        channel: refundKind === "full" ? refundChannel : "direct_transfer",
        amount: refundKind === "partial" ? Number(refundAmount) : undefined,
        reason: refundReason || undefined,
      });
      if (created.channel === "gateway") {
        await processGatewayRefund(created.id);
      }
      await refreshRefunds();
      setRefundAmount("");
      setRefundReason("");
    } catch (err) {
      setRefundError(err instanceof Error ? err.message : "Refund failed");
    } finally {
      setRefundBusy(false);
    }
  };

  const onRefundEvidence = async (refundId: string, file: File | null) => {
    if (!file) return;
    setRefundError("");
    setRefundBusy(true);
    try {
      await uploadRefundEvidence(refundId, file);
      await refreshRefunds();
    } catch (err) {
      setRefundError(err instanceof Error ? err.message : "Evidence upload failed");
    } finally {
      setRefundBusy(false);
    }
  };

  const markDirectRefundDone = async (refundId: string) => {
    setRefundError("");
    setRefundBusy(true);
    try {
      await completeDirectRefund(refundId);
      await refreshRefunds();
    } catch (err) {
      setRefundError(err instanceof Error ? err.message : "Could not complete refund");
    } finally {
      setRefundBusy(false);
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
  const paymentCaptured =
    payment?.status === "captured" ||
    payment?.status === "partially_refunded" ||
    payment?.status === "refunded" ||
    refunds.some((r) => r.status === "completed" || r.status === "requested" || r.status === "processing");
  const canRefund = needsPayment && order.status !== "cancelled";

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

      {order.delivery_type === "delivery" && (
        <section className="dash-card od-panel">
          <header className="od-panel__head">
            <div>
              <h2>Delivery fulfillment</h2>
              <p>
                {order.distance_km != null ? `${order.distance_km.toFixed(1)} km · ` : ""}
                {order.delivery_payer === "customer"
                  ? "Beyond range — customer pays full logistics"
                  : order.delivery_payer === "shared"
                    ? "Beyond range — kitchen subsidy + customer share"
                    : "In range — kitchen pays logistics (customer fee ₹0)"}
              </p>
            </div>
          </header>
          {fulfillError && <p className="auth-card__error">{fulfillError}</p>}
          <p className="report-hint">
            Mode: <strong>{order.delivery_mode ?? "not chosen"}</strong>
            {order.courier_partner ? ` · ${order.courier_partner}` : ""}
            {order.courier_job_id ? ` · job ${order.courier_job_id}` : ""}
            {order.courier_status ? ` · courier ${order.courier_status}` : ""}
            {order.delivery_fee_payment ? ` · fee ${order.delivery_fee_payment}` : ""}
            {order.owner_delivery_cost
              ? ` · kitchen cost ${inr(order.owner_delivery_cost)}`
              : ""}
            {order.delivery_fee > 0 ? ` · customer fee ${inr(order.delivery_fee)}` : ""}
          </p>
          {order.delivery_mode === "platform"
            && (order.delivery_payer === "shared" || order.delivery_fee_payment === "prepaid")
            && order.delivery_fee > 0
            && !order.courier_job_id && (
            <p className="report-hint" style={{ marginTop: "0.35rem" }}>
              Porter books after the customer’s prepaid delivery share is captured (UPI/online).
            </p>
          )}
          {order.status !== "delivered" && order.status !== "cancelled" && (
            <div className="od-board__hero-actions" style={{ flexDirection: "row", flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={fulfillBusy}
                onClick={async () => {
                  setFulfillBusy(true);
                  setFulfillError("");
                  try {
                    setOrder(await setOrderDeliveryFulfillment(order.id, { mode: "self" }));
                  } catch (e) {
                    setFulfillError(e instanceof Error ? e.message : "Failed");
                  } finally {
                    setFulfillBusy(false);
                  }
                }}
              >
                Self delivery
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={fulfillBusy}
                onClick={async () => {
                  setFulfillBusy(true);
                  setFulfillError("");
                  try {
                    setOrder(await setOrderDeliveryFulfillment(order.id, { mode: "platform" }));
                  } catch (e) {
                    setFulfillError(e instanceof Error ? e.message : "Failed");
                  } finally {
                    setFulfillBusy(false);
                  }
                }}
              >
                Book platform courier
              </button>
            </div>
          )}
          {order.customer_latitude != null &&
            order.customer_longitude != null &&
            kitchen?.latitude != null &&
            kitchen?.longitude != null && (
              <div className="track-map" style={{ marginTop: "1rem" }}>
                <iframe
                  title="Delivery map"
                  className="track-map__frame"
                  loading="lazy"
                  src={googleMapsDirectionsEmbedUrl(
                    kitchen.latitude,
                    kitchen.longitude,
                    order.customer_latitude,
                    order.customer_longitude,
                  )}
                />
                <a
                  className="btn btn--ghost btn--sm"
                  href={googleMapsRouteUrl(
                    kitchen.latitude,
                    kitchen.longitude,
                    order.customer_latitude,
                    order.customer_longitude,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open in Google Maps
                </a>
              </div>
            )}
        </section>
      )}

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
                <div className="owner-detail-items__row">
                  <span>{i.quantity}× {i.dish_name}</span>
                  <span>{inr(i.unit_price * i.quantity)}</span>
                </div>
                {i.special_instructions && (
                  <p className="owner-detail-items__note">
                    <strong>Note:</strong> {i.special_instructions}
                  </p>
                )}
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

          {canRefund && (
            <section className="dash-card od-panel owner-pay-panel">
              <header className="od-panel__head">
                <div>
                  <h2>Refund</h2>
                  <p>Full via gateway or direct UPI/bank · partial is always direct</p>
                </div>
              </header>
              {refundError && <div className="auth-card__error">{refundError}</div>}

              <label className="kc-field">
                <span className="kc-field__label">Type</span>
                <select
                  className="kc-input"
                  value={refundKind}
                  onChange={(e) => setRefundKind(e.target.value as "full" | "partial")}
                >
                  <option value="full">Full refund</option>
                  <option value="partial">Partial refund</option>
                </select>
              </label>

              {refundKind === "full" && (
                <label className="kc-field">
                  <span className="kc-field__label">Channel</span>
                  <select
                    className="kc-input"
                    value={refundChannel}
                    onChange={(e) => setRefundChannel(e.target.value as "gateway" | "direct_transfer")}
                  >
                    <option value="gateway">Payment gateway (Razorpay reverse)</option>
                    <option value="direct_transfer">Direct UPI / bank transfer</option>
                  </select>
                </label>
              )}

              {refundKind === "partial" && (
                <label className="kc-field">
                  <span className="kc-field__label">Amount (₹)</span>
                  <input
                    className="kc-input"
                    type="number"
                    min="1"
                    step="0.01"
                    value={refundAmount}
                    onChange={(e) => setRefundAmount(e.target.value)}
                    placeholder="e.g. 100"
                  />
                </label>
              )}

              <label className="kc-field">
                <span className="kc-field__label">Reason (optional)</span>
                <input
                  className="kc-input"
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  placeholder="Missing item, quality issue…"
                />
              </label>

              <button type="button" className="btn btn--primary" disabled={refundBusy} onClick={submitRefund}>
                {refundBusy
                  ? "Working…"
                  : refundKind === "full" && refundChannel === "gateway"
                    ? "Refund via gateway"
                    : "Create direct refund"}
              </button>

              {refunds.length > 0 && (
                <ul className="owner-detail-items" style={{ marginTop: "1rem" }}>
                  {refunds.map((r) => (
                    <li key={r.id} style={{ flexDirection: "column", alignItems: "stretch", gap: "0.5rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
                        <span>
                          {r.kind} · {r.channel} · {inr(r.amount)} · {r.status}
                          <br />
                          <small>Remark: {r.transfer_remark}</small>
                          {r.destination_upi && (
                            <>
                              <br />
                              <small>UPI: {r.destination_upi}</small>
                            </>
                          )}
                          {r.destination_bank_account_masked && (
                            <>
                              <br />
                              <small>
                                Bank: {r.destination_bank_account_masked} · {r.destination_bank_ifsc}
                              </small>
                            </>
                          )}
                        </span>
                        <span className="status-badge">{r.status}</span>
                      </div>
                      {r.channel === "direct_transfer" && r.status !== "completed" && (
                        <>
                          <label className="kc-field">
                            <span className="kc-field__label">Attach refund screenshot</span>
                            <input
                              type="file"
                              accept="image/jpeg,image/png,image/webp"
                              disabled={refundBusy}
                              onChange={(e) => onRefundEvidence(r.id, e.target.files?.[0] ?? null)}
                            />
                          </label>
                          {r.evidence_url && (
                            <a href={r.evidence_url} target="_blank" rel="noreferrer">
                              View evidence
                            </a>
                          )}
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            disabled={refundBusy || !r.evidence_url}
                            onClick={() => markDirectRefundDone(r.id)}
                          >
                            Mark transfer complete
                          </button>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
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
