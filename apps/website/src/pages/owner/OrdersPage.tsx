import { Link, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
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

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function formatWhen(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function OrdersSkeleton() {
  return (
    <div className="od-orders__loading">
      <div className="od-skeleton od-skeleton--wide" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="od-skeleton od-skeleton--card" />
      ))}
    </div>
  );
}

export function OrdersPage() {
  const { kitchen } = useKitchen();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "active";
  const [orders, setOrders] = useState<Order[]>([]);
  const [drafts, setDrafts] = useState<OrderDraft[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!kitchen) return;
    setLoading(true);
    try {
      const [o, d] = await Promise.all([fetchOrders(kitchen.id), fetchDrafts(kitchen.id)]);
      setOrders(o.orders);
      setDrafts(d.drafts);
    } catch {
      setError("Could not load orders");
    } finally {
      setLoading(false);
    }
  }, [kitchen]);

  useEffect(() => { load().catch(() => {}); }, [load]);

  const activeOrders = useMemo(
    () => orders.filter((o) => !["delivered", "cancelled"].includes(o.status)),
    [orders],
  );
  const todayOrders = useMemo(() => {
    const today = new Date().toDateString();
    return orders.filter((o) => new Date(o.created_at).toDateString() === today);
  }, [orders]);
  const todayRevenue = useMemo(
    () => todayOrders.reduce((sum, o) => sum + o.total, 0),
    [todayOrders],
  );

  const shown = tab === "drafts" ? [] : tab === "all" ? orders : activeOrders;

  if (!kitchen) return null;

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
    <div className="owner-screen od-board od-orders">
      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">Order operations</p>
          <h1>Orders</h1>
          <p className="od-board__meta">
            WhatsApp drafts · manual intake · lifecycle tracking
          </p>
          {drafts.length > 0 && (
            <div className="od-board__pills">
              <button
                type="button"
                className="od-pill od-pill--alert"
                onClick={() => setParams({ tab: "drafts" })}
              >
                {drafts.length} draft{drafts.length !== 1 ? "s" : ""} need review
              </button>
            </div>
          )}
        </div>
        <div className="od-board__hero-actions">
          <Link to="/dashboard/orders/new" className="btn btn--primary">New order</Link>
          <Link to="/dashboard" className="btn btn--ghost">Dashboard</Link>
        </div>
      </section>

      <div className="od-board__kpi-grid od-orders__kpis">
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--orders" aria-hidden="true" />
          <div>
            <strong>{activeOrders.length}</strong>
            <span>Active now</span>
            <em>In kitchen pipeline</em>
          </div>
        </div>
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--drafts" aria-hidden="true" />
          <div>
            <strong>{drafts.length}</strong>
            <span>WhatsApp drafts</span>
            <em>Awaiting confirmation</em>
          </div>
        </div>
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--revenue" aria-hidden="true" />
          <div>
            <strong>{inr(todayRevenue)}</strong>
            <span>Today&apos;s revenue</span>
            <em>{todayOrders.length} order{todayOrders.length !== 1 ? "s" : ""}</em>
          </div>
        </div>
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--menu" aria-hidden="true" />
          <div>
            <strong>{orders.length}</strong>
            <span>All-time orders</span>
            <em>{orders.filter((o) => o.status === "delivered").length} delivered</em>
          </div>
        </div>
      </div>

      <div className="owner-tabs od-orders__tabs">
        {(["active", "all", "drafts"] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? "active" : ""}
            onClick={() => setParams({ tab: t })}
          >
            {t === "active" ? `Active (${activeOrders.length})` : t === "all" ? `All (${orders.length})` : `Drafts (${drafts.length})`}
          </button>
        ))}
      </div>

      <section className="dash-card od-panel od-orders__parse">
        <header className="od-panel__head">
          <div>
            <h2>Paste WhatsApp order</h2>
            <p>We match dishes from your menu and create a draft you can confirm</p>
          </div>
        </header>
        <label className="kc-field od-orders__parse-field">
          <span className="kc-field__label">WhatsApp message</span>
          <textarea
            className="kc-textarea"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            placeholder="e.g. 2 butter chicken, 1 garlic naan, less spicy"
            disabled={busy}
          />
          <span className="kc-field__hint">Paste the full customer message — we match dishes from your menu.</span>
        </label>
        {error && <div className="auth-card__error">{error}</div>}
        <div className="kc-actions kc-actions--stack-sm">
          <button type="button" className="btn btn--primary" disabled={busy || !message.trim()} onClick={handleParse}>
            {busy ? "Parsing…" : "Parse to draft"}
          </button>
        </div>
      </section>

      {loading ? (
        <OrdersSkeleton />
      ) : tab === "drafts" ? (
        <div className="od-orders__list">
          {drafts.length === 0 && (
            <p className="od-panel__empty dash-card od-panel">
              No drafts yet — paste a WhatsApp message above or share your menu link with customers.
            </p>
          )}
          {drafts.map((d) => (
            <article key={d.id} className="dash-card od-order-draft">
              <div className="od-order-draft__head">
                <span className="od-order-draft__source">{d.source}</span>
                <time>{formatWhen(d.created_at)}</time>
              </div>
              <p className="od-order-draft__msg">{d.raw_message}</p>
              <ul className="od-order-draft__items">
                {d.parsed_items.map((p, i) => (
                  <li key={i} className={p.matched ? "" : "od-order-draft__item--bad"}>
                    <span>{p.quantity}× {p.dish_name ?? p.raw}</span>
                    <span>{p.matched ? inr((p.unit_price ?? 0) * p.quantity) : "Unmatched"}</span>
                  </li>
                ))}
              </ul>
              {d.unmatched_lines.length > 0 && (
                <p className="od-order-draft__warn">Unmatched lines: {d.unmatched_lines.join(", ")}</p>
              )}
              <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => handleConfirm(d.id)}>
                Confirm order
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="od-orders__list">
          {shown.length === 0 && (
            <p className="od-panel__empty dash-card od-panel">
              {tab === "active"
                ? "No active orders — you're all caught up!"
                : "No orders yet. Create a manual order or parse a WhatsApp message."}
            </p>
          )}
          <ul className="od-recent dash-card od-panel">
            {shown.map((o) => (
              <li key={o.id}>
                <Link to={`/dashboard/orders/${o.id}`} className="od-recent__row">
                  <div>
                    <strong>{o.order_code}</strong>
                    <span>{o.customer_name ?? o.customer_phone ?? "Walk-in"} · {o.items.map((i) => `${i.quantity}× ${i.dish_name}`).join(", ")}</span>
                  </div>
                  <div className="od-recent__end">
                    <span className={`status-badge status-badge--${o.status}`}>
                      {STATUS_LABELS[o.status] ?? o.status}
                    </span>
                    <span className="od-recent__meta">
                      {inr(o.total)} · {o.source} · {formatWhen(o.created_at)}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
