import { Link, useLocation, useParams } from "react-router-dom";
import { useState } from "react";
import { useBrandedStorefront } from "../../customer/BrandedStorefront";
import {
  captureCustomerPayment,
  downloadCustomerOrderBillPdf,
} from "../../shared/customerCheckoutApi";
import type { Order, Payment, UpiIntent } from "../../shared/api";

type ConfirmState = {
  order: Order;
  paymentMethod: string;
  upiIntent?: UpiIntent | null;
  paymentId?: string | null;
};

export function OrderConfirmPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const location = useLocation();
  const branded = useBrandedStorefront();
  const state = location.state as ConfirmState | null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [payStatus, setPayStatus] = useState(state?.upiIntent?.status ?? "created");
  const [capturing, setCapturing] = useState(false);
  const menuHref = branded ? `${branded.basePath}/menu` : "/";

  const paymentId = state?.upiIntent?.payment_id || state?.paymentId || null;

  if (!state?.order || state.order.id !== orderId) {
    return (
      <div className="container customer-checkout">
        <h1>Order placed</h1>
        <p>Thank you! Open My orders to track, rate, or repeat.</p>
        <div className="owner-actions">
          <Link to="/orders" className="btn btn--primary">
            View my orders
          </Link>
          <Link to={menuHref} className="btn btn--ghost">
            {branded ? "Back to menu" : "Back to home"}
          </Link>
        </div>
      </div>
    );
  }

  const { order, paymentMethod, upiIntent } = state;
  const trackHref = order.tracking_token ? `/t/${order.tracking_token}` : null;

  const onDownload = async () => {
    setBusy(true);
    setError("");
    try {
      await downloadCustomerOrderBillPdf(order.id, order.order_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusy(false);
    }
  };

  const onMarkPaid = async () => {
    if (!paymentId) return;
    setCapturing(true);
    setError("");
    try {
      const payment: Payment = await captureCustomerPayment(paymentId);
      setPayStatus(payment.status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm payment yet");
    } finally {
      setCapturing(false);
    }
  };

  return (
    <div className="container customer-checkout">
      <header className="owner-page__head">
        <div>
          <h1>Order confirmed</h1>
          <p>{order.order_code}</p>
        </div>
        <span className="status-badge status-badge--received status-badge--lg">Received</span>
      </header>

      <section className="glass">
        <p>
          Total <strong>₹{order.total.toFixed(0)}</strong> · {paymentMethod.toUpperCase()}
        </p>
        <p>The kitchen will update your order status. No per-order commission — subscription SaaS only.</p>
        <ul className="owner-detail-items">
          {order.items.map((item) => (
            <li key={item.id}>
              <span>
                {item.quantity}× {item.dish_name}
              </span>
              <span>₹{(item.unit_price * item.quantity).toFixed(0)}</span>
            </li>
          ))}
        </ul>
      </section>

      {paymentMethod === "upi" && upiIntent?.upi_uri && (
        <section className="glass">
          <h2>Complete UPI payment</h2>
          <p>
            Amount <strong>₹{Math.round(upiIntent.amount)}</strong> · status{" "}
            <strong>{payStatus}</strong>
          </p>
          {payStatus === "captured" ? (
            <p className="report-hint">Payment captured. Thank you.</p>
          ) : (
            <>
              <p className="report-hint">
                Scan the QR with any UPI app, or open the payment link on your phone. After you pay,
                tap “I’ve paid” — demo mode confirms capture immediately; production waits for the
                gateway webhook.
              </p>
              <img
                className="upi-qr"
                alt="UPI payment QR"
                width={200}
                height={200}
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiIntent.upi_uri)}`}
              />
              <div className="owner-actions" style={{ marginTop: "0.75rem" }}>
                <a className="btn btn--primary" href={upiIntent.upi_uri}>
                  Pay with UPI app
                </a>
                {paymentId && (
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={capturing}
                    onClick={onMarkPaid}
                  >
                    {capturing ? "Confirming…" : "I’ve paid"}
                  </button>
                )}
              </div>
              <p className="owner-muted" style={{ marginTop: "0.75rem", wordBreak: "break-all" }}>
                {upiIntent.upi_uri}
              </p>
            </>
          )}
        </section>
      )}
      {(order.discount_amount ?? 0) > 0 && (
        <p className="report-hint">
          Coupon {order.coupon_code} saved you ₹{Math.round(order.discount_amount || 0)}.
        </p>
      )}

      {paymentMethod === "online" && (
        <section className="glass">
          <p className="report-hint">
            Online payment was captured in demo mode. Production will open Razorpay Checkout with
            retry if capture fails — this screen will not pretend a live card widget exists yet.
          </p>
        </section>
      )}

      {error && <div className="auth-card__error">{error}</div>}
      <div className="owner-actions">
        {trackHref && (
          <Link to={trackHref} className="btn btn--primary">
            Track order
          </Link>
        )}
        <button type="button" className="btn btn--secondary" disabled={busy} onClick={onDownload}>
          {busy ? "Preparing PDF…" : "Download PDF bill"}
        </button>
        {!branded && (
          <Link to="/orders" className="btn btn--ghost">
            View my orders
          </Link>
        )}
        <Link to={menuHref} className="btn btn--ghost">
          {branded ? "Order again" : "Discover more kitchens"}
        </Link>
      </div>
    </div>
  );
}
