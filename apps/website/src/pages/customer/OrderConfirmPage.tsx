import { Link, useLocation, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useBrandedStorefront } from "../../customer/BrandedStorefront";
import {
  captureCustomerPayment,
  downloadCustomerOrderBillPdf,
  fetchMyOrder,
} from "../../shared/customerCheckoutApi";
import { getCustomerToken } from "../../shared/customerApi";
import { STATUS_LABELS, type Order, type Payment, type UpiIntent } from "../../shared/api";

type ConfirmState = {
  order: Order;
  paymentMethod: string;
  upiIntent?: UpiIntent | null;
  paymentId?: string | null;
};

function nextSteps(order: Order): string[] {
  const steps = [
    "Kitchen received your order",
    "They’ll accept and start prep",
    order.delivery_type === "delivery"
      ? "Out for delivery with ready-within timing"
      : "Ready for pickup when marked ready",
  ];
  if (order.tracking_token) steps.push("Track live status anytime");
  return steps;
}

export function OrderConfirmPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const location = useLocation();
  const branded = useBrandedStorefront();
  const navState = location.state as ConfirmState | null;

  const [order, setOrder] = useState<Order | null>(
    navState?.order && navState.order.id === orderId ? navState.order : null,
  );
  const [paymentMethod, setPaymentMethod] = useState(
    navState?.paymentMethod ?? navState?.order?.payment_method ?? "cod",
  );
  const [upiIntent] = useState<UpiIntent | null | undefined>(navState?.upiIntent);
  const [paymentId] = useState<string | null>(
    navState?.upiIntent?.payment_id || navState?.paymentId || null,
  );
  const [payStatus, setPayStatus] = useState(navState?.upiIntent?.status ?? "created");
  const [loading, setLoading] = useState(!order && Boolean(orderId));
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [capturing, setCapturing] = useState(false);

  const menuHref = branded ? `${branded.basePath}/menu` : "/";
  const ordersHref = "/orders";
  const loginNext = encodeURIComponent(location.pathname);

  useEffect(() => {
    if (!orderId || order) return;
    if (!getCustomerToken()) {
      setLoading(false);
      setLoadError("sign_in");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError("");
    void fetchMyOrder(orderId)
      .then((fetched) => {
        if (cancelled) return;
        setOrder(fetched);
        setPaymentMethod(fetched.payment_method || "cod");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Could not load order");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orderId, order]);

  const onDownload = async () => {
    if (!order) return;
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

  if (loading) {
    return (
      <div className="container customer-confirm">
        <p className="customer-confirm__loading">Loading your order…</p>
      </div>
    );
  }

  if (loadError === "sign_in") {
    return (
      <div className="container customer-confirm">
        <header className="customer-confirm__hero">
          <p className="customer-confirm__eyebrow">Almost there</p>
          <h1>Sign in to see this order</h1>
          <p>Your confirmation is saved — open it with the same WhatsApp account you used at checkout.</p>
        </header>
        <div className="customer-confirm__actions">
          <Link to={`/login?next=${loginNext}`} className="btn btn--primary">
            Sign in
          </Link>
          <Link to={menuHref} className="btn btn--ghost">
            {branded ? "Back to menu" : "Discover kitchens"}
          </Link>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="container customer-confirm">
        <header className="customer-confirm__hero">
          <p className="customer-confirm__eyebrow">Order</p>
          <h1>We couldn’t open this receipt</h1>
          <p>{loadError || "This order isn’t available on this account."}</p>
        </header>
        <div className="customer-confirm__actions">
          <Link to={ordersHref} className="btn btn--primary">
            View my orders
          </Link>
          <Link to={menuHref} className="btn btn--ghost">
            {branded ? "Back to menu" : "Discover kitchens"}
          </Link>
        </div>
      </div>
    );
  }

  const trackHref = order.tracking_token ? `/t/${order.tracking_token}` : null;
  const statusLabel = STATUS_LABELS[order.status] ?? order.status;
  const method = (paymentMethod || order.payment_method || "cod").toLowerCase();

  return (
    <div className="container customer-confirm">
      <header className="customer-confirm__hero">
        <p className="customer-confirm__eyebrow">Order confirmed</p>
        <h1>Thank you — we’re on it</h1>
        <p className="customer-confirm__code">{order.order_code}</p>
        <span className={`status-badge status-badge--${order.status} status-badge--lg`}>
          {statusLabel}
        </span>
      </header>

      <section className="customer-confirm__card">
        <div className="customer-confirm__total-row">
          <div>
            <strong>₹{Math.round(order.total)}</strong>
            <span>{method.toUpperCase()}</span>
          </div>
          <p>
            Food goes to the kitchen — kitchCU takes zero food commission.
          </p>
        </div>
        <ul className="customer-confirm__lines">
          {order.items.map((item) => (
            <li key={item.id}>
              <span>
                {item.quantity}× {item.dish_name}
              </span>
              <span>₹{Math.round(item.unit_price * item.quantity)}</span>
            </li>
          ))}
        </ul>
        {(order.discount_amount ?? 0) > 0 && (
          <p className="customer-confirm__coupon">
            Coupon {order.coupon_code} saved you ₹{Math.round(order.discount_amount || 0)}.
          </p>
        )}
      </section>

      <section className="customer-confirm__card customer-confirm__next">
        <h2>What happens next</h2>
        <ol>
          {nextSteps(order).map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      {method === "upi" && upiIntent?.upi_uri && (
        <section className="customer-confirm__card">
          <h2>Complete UPI payment</h2>
          <p>
            Amount <strong>₹{Math.round(upiIntent.amount)}</strong> · status{" "}
            <strong>{payStatus}</strong>
          </p>
          {payStatus === "captured" ? (
            <p className="customer-confirm__hint">Payment captured. Thank you.</p>
          ) : (
            <>
              <p className="customer-confirm__hint">
                Scan with any UPI app, or open the payment link. After you pay, tap “I’ve paid”.
              </p>
              <img
                className="upi-qr"
                alt="UPI payment QR"
                width={200}
                height={200}
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiIntent.upi_uri)}`}
              />
              <div className="customer-confirm__actions customer-confirm__actions--inline">
                <a className="btn btn--primary" href={upiIntent.upi_uri}>
                  Pay with UPI app
                </a>
                {paymentId && (
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={capturing}
                    onClick={onMarkPaid}
                  >
                    {capturing ? "Confirming…" : "I’ve paid"}
                  </button>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {method === "online" && navState?.paymentMethod === "online" && (
        <section className="customer-confirm__card">
          <p className="customer-confirm__hint">
            Online payment was captured in demo mode. Production opens Razorpay Checkout with retry.
          </p>
        </section>
      )}

      {error && <div className="auth-card__error">{error}</div>}

      <div className="customer-confirm__actions">
        {trackHref && (
          <Link to={trackHref} className="btn btn--primary">
            Track order
          </Link>
        )}
        <button type="button" className="btn btn--primary" disabled={busy} onClick={onDownload}>
          {busy ? "Preparing PDF…" : "Download bill"}
        </button>
        <Link to={ordersHref} className="btn btn--ghost">
          View my orders
        </Link>
        <Link to={menuHref} className="btn btn--ghost">
          {branded ? "Order again" : "Discover more kitchens"}
        </Link>
      </div>
    </div>
  );
}
