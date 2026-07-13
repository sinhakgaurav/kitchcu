import { Link, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import {
  confirmDraft,
  fetchDrafts,
  fetchOrders,
  parseMessage,
  STATUS_LABELS,
  type Order,
  type OrderDraft,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function OrdersPage() {
  const { kitchen } = useKitchen();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "active";
  const [orders, setOrders] = useState<Order[]>([]);
  const [drafts, setDrafts] = useState<OrderDraft[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!kitchen) return;
    const [o, d] = await Promise.all([fetchOrders(kitchen.id), fetchDrafts(kitchen.id)]);
    setOrders(o.orders);
    setDrafts(d.drafts);
  }, [kitchen]);

  useEffect(() => { load().catch(() => {}); }, [load]);

  if (!kitchen) return null;

  const activeOrders = orders.filter((o) => !["delivered", "cancelled"].includes(o.status));
  const shown = tab === "drafts" ? [] : tab === "all" ? orders : activeOrders;

  const handleParse = async () => {
    if (!message.trim()) return;
    setError("");
    setBusy(true);
    try {
      await parseMessage(kitchen.id, message);
      setMessage("");
      await load();
      setParams({ tab: "drafts" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Parse failed");
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = async (draftId: string) => {
    setBusy(true);
    try {
      await confirmDraft(kitchen.id, draftId);
      await load();
      setParams({ tab: "active" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Orders</h1>
          <p>WhatsApp drafts, manual orders, and lifecycle tracking.</p>
        </div>
        <Link to="/dashboard/orders/new" className="btn btn--primary">New Order</Link>
      </header>

      <div className="owner-tabs">
        {(["active", "all", "drafts"] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? "active" : ""}
            onClick={() => setParams({ tab: t })}
          >
            {t === "active" ? "Active" : t === "all" ? "All" : "Drafts"}
            {t === "drafts" && drafts.length > 0 && ` (${drafts.length})`}
          </button>
        ))}
      </div>

      <div className="glass owner-parse">
        <h3>Paste WhatsApp order message</h3>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="e.g. 2 butter chicken, 1 naan, no onion"
        />
        {error && <div className="auth-card__error">{error}</div>}
        <button type="button" className="btn btn--primary" disabled={busy} onClick={handleParse}>
          Parse to draft
        </button>
      </div>

      {tab === "drafts" ? (
        <div className="owner-list">
          {drafts.length === 0 && <p className="owner-empty">No drafts — paste a WhatsApp message above.</p>}
          {drafts.map((d) => (
            <article key={d.id} className="glass owner-order-card">
              <div className="owner-order-card__head">
                <span className="owner-order-card__source">{d.source}</span>
                <time>{new Date(d.created_at).toLocaleString()}</time>
              </div>
              <p className="owner-order-card__msg">{d.raw_message}</p>
              <ul className="owner-order-card__items">
                {d.parsed_items.map((p, i) => (
                  <li key={i} className={p.matched ? "" : "unmatched"}>
                    {p.quantity}× {p.dish_name ?? p.raw} {p.matched ? `₹${p.unit_price}` : "(unmatched)"}
                  </li>
                ))}
              </ul>
              <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => handleConfirm(d.id)}>
                Confirm order
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="owner-list">
          {shown.length === 0 && <p className="owner-empty">No orders yet.</p>}
          {shown.map((o) => (
            <Link key={o.id} to={`/dashboard/orders/${o.id}`} className="glass owner-order-card owner-order-card--link">
              <div className="owner-order-card__head">
                <strong>{o.order_code}</strong>
                <span className={`status-badge status-badge--${o.status}`}>{STATUS_LABELS[o.status] ?? o.status}</span>
              </div>
              <p>{o.items.map((i) => `${i.quantity}× ${i.dish_name}`).join(", ")}</p>
              <div className="owner-order-card__foot">
                <span>₹{o.total.toFixed(0)}</span>
                <span>{o.source} · {o.delivery_type}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
