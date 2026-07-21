import { Link, useLocation, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  downloadCustomerMasterBillPdf,
  fetchMyMasterOrder,
} from "../../shared/customerCheckoutApi";
import { getCustomerToken } from "../../shared/customerApi";
import type { MasterOrder, Settlement } from "../../shared/api";

type ConfirmState = {
  master: MasterOrder;
  paymentMethod?: string;
  settlements?: Settlement[];
};

export function MasterOrderConfirmPage() {
  const { masterOrderId } = useParams<{ masterOrderId: string }>();
  const location = useLocation();
  const navState = location.state as ConfirmState | null;

  const [master, setMaster] = useState<MasterOrder | null>(
    navState?.master && navState.master.id === masterOrderId ? navState.master : null,
  );
  const [settlements] = useState<Settlement[] | undefined>(navState?.settlements);
  const [paymentMethod, setPaymentMethod] = useState(
    navState?.paymentMethod ?? navState?.master?.payment_method ?? "cod",
  );
  const [loading, setLoading] = useState(!master && Boolean(masterOrderId));
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const loginNext = encodeURIComponent(location.pathname);

  useEffect(() => {
    if (!masterOrderId || master) return;
    if (!getCustomerToken()) {
      setLoading(false);
      setLoadError("sign_in");
      return;
    }
    let cancelled = false;
    setLoading(true);
    void fetchMyMasterOrder(masterOrderId)
      .then((fetched) => {
        if (cancelled) return;
        setMaster(fetched);
        setPaymentMethod(fetched.payment_method || "cod");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Could not load master order");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [masterOrderId, master]);

  const onDownload = async () => {
    if (!master) return;
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

  if (loading) {
    return (
      <div className="container customer-confirm">
        <p className="customer-confirm__loading">Loading master receipt…</p>
      </div>
    );
  }

  if (loadError === "sign_in") {
    return (
      <div className="container customer-confirm">
        <header className="customer-confirm__hero">
          <h1>Sign in to see this receipt</h1>
          <p>Use the same WhatsApp account you checked out with.</p>
        </header>
        <div className="customer-confirm__actions">
          <Link to={`/login?next=${loginNext}`} className="btn btn--primary">
            Sign in
          </Link>
          <Link to="/orders" className="btn btn--ghost">
            My orders
          </Link>
        </div>
      </div>
    );
  }

  if (!master) {
    return (
      <div className="container customer-confirm">
        <header className="customer-confirm__hero">
          <h1>Receipt unavailable</h1>
          <p>{loadError || "This multi-kitchen order isn’t on this account."}</p>
        </header>
        <div className="customer-confirm__actions">
          <Link to="/orders" className="btn btn--primary">
            View my orders
          </Link>
        </div>
      </div>
    );
  }

  const method = (paymentMethod || master.payment_method || "cod").toUpperCase();

  return (
    <div className="container customer-confirm">
      <header className="customer-confirm__hero">
        <p className="customer-confirm__eyebrow">Multi-kitchen order</p>
        <h1>Master receipt</h1>
        <p className="customer-confirm__code">{master.master_order_code}</p>
        <span className="status-badge status-badge--received status-badge--lg">Created</span>
      </header>

      <section className="customer-confirm__card">
        <div className="customer-confirm__total-row">
          <div>
            <strong>₹{Math.round(master.total)}</strong>
            <span>{method}</span>
          </div>
          <p>
            {master.orders.length} kitchen{master.orders.length === 1 ? "" : "s"} will update
            independently — track each sub-order separately.
          </p>
        </div>
        {settlements && settlements.length > 0 && (
          <ul className="customer-confirm__lines">
            {settlements.map((settlement) => (
              <li key={settlement.id}>
                <span>Kitchen settlement</span>
                <span>
                  ₹{Math.round(settlement.net_to_owner)} · {settlement.settlement_status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {master.orders.map((order) => (
        <section key={order.id} className="customer-confirm__card">
          <h2>{order.order_code}</h2>
          <p className="customer-confirm__hint">
            ₹{Math.round(order.total)} · {order.delivery_type} · {order.status}
          </p>
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
          {order.tracking_token && (
            <Link to={`/t/${order.tracking_token}`} className="btn btn--ghost btn--sm">
              Track this kitchen
            </Link>
          )}
        </section>
      ))}

      {error && <div className="auth-card__error">{error}</div>}
      <div className="customer-confirm__actions">
        <button type="button" className="btn btn--primary" disabled={busy} onClick={onDownload}>
          {busy ? "Preparing PDF…" : "Download master bill"}
        </button>
        <Link to="/orders" className="btn btn--ghost">
          Track sub-orders
        </Link>
        <Link to="/#near-you" className="btn btn--ghost">
          Discover more kitchens
        </Link>
      </div>
    </div>
  );
}
