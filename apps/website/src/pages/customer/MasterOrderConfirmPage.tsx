import { Link, useLocation, useParams } from "react-router-dom";
import { useState } from "react";
import { downloadCustomerMasterBillPdf } from "../../shared/customerCheckoutApi";
import type { MasterOrder, Settlement } from "../../shared/api";

type ConfirmState = {
  master: MasterOrder;
  paymentMethod?: string;
  settlements?: Settlement[];
};

export function MasterOrderConfirmPage() {
  const { masterOrderId } = useParams<{ masterOrderId: string }>();
  const location = useLocation();
  const state = location.state as ConfirmState | null;

  if (!state?.master || state.master.id !== masterOrderId) {
    return (
      <div className="container customer-checkout">
        <h1>Multi-kitchen order placed</h1>
        <p>Each kitchen has its own tracking order.</p>
        <Link to="/orders" className="btn btn--primary">View my orders</Link>
      </div>
    );
  }

  const { master, paymentMethod, settlements } = state;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const onDownload = async () => {
    setBusy(true);
    setError("");
    try {
      await downloadCustomerMasterBillPdf(master.id, master.master_order_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container customer-checkout">
      <header className="owner-page__head">
        <div>
          <h1>Master receipt</h1>
          <p>{master.master_order_code}</p>
        </div>
        <span className="status-badge status-badge--received status-badge--lg">Created</span>
      </header>

      <section className="glass">
        <p>
          Total <strong>₹{master.total.toFixed(0)}</strong> ·{" "}
          {(paymentMethod ?? master.payment_method).toUpperCase()}
        </p>
        <p>
          {master.orders.length} kitchens will confirm and update their orders independently.
        </p>
        {settlements && settlements.length > 0 && (
          <ul className="owner-detail-items">
            {settlements.map((settlement) => (
              <li key={settlement.id}>
                <span>Kitchen settlement</span>
                <span>₹{settlement.net_to_owner.toFixed(0)} · {settlement.settlement_status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {master.orders.map((order) => (
        <section key={order.id} className="glass customer-checkout__cart">
          <h2>{order.order_code}</h2>
          <p>
            ₹{order.total.toFixed(0)} · {order.delivery_type} · {order.status}
          </p>
          <ul className="owner-detail-items">
            {order.items.map((item) => (
              <li key={item.id}>
                <span>{item.quantity}× {item.dish_name}</span>
                <span>₹{(item.unit_price * item.quantity).toFixed(0)}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {error && <div className="auth-card__error">{error}</div>}
      <button type="button" className="btn btn--secondary" disabled={busy} onClick={onDownload}>
        {busy ? "Preparing PDF…" : "Download master PDF bill"}
      </button>
      <Link to="/orders" className="btn btn--primary">Track sub-orders</Link>
      <Link to="/#near-you" className="btn btn--ghost">Discover more kitchens</Link>
    </div>
  );
}
