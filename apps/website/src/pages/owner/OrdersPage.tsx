import { Link, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ListingToolbar } from "../../components/ListingToolbar";
import {
  confirmDraft,
  downloadOrdersCsv,
  fetchDrafts,
  fetchMenu,
  fetchOrders,
  fetchParseStats,
  parseMessage,
  updateDraft,
  STATUS_LABELS,
  type Dish,
  type Order,
  type OrderDraft,
  type ParseStats,
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
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "active";
  const [orders, setOrders] = useState<Order[]>([]);
  const [drafts, setDrafts] = useState<OrderDraft[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"newest" | "name_asc" | "name_desc">("newest");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [dateFilter, setDateFilter] = useState<"all" | "today" | "7d" | "30d" | "90d" | "180d">("all");
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [parseStats, setParseStats] = useState<ParseStats | null>(null);
  const [exporting, setExporting] = useState(false);

  const dateBounds = useMemo(() => {
    if (dateFilter === "all") return {};
    const before = new Date();
    const after = new Date();
    if (dateFilter === "today") after.setHours(0, 0, 0, 0);
    else if (dateFilter === "7d") after.setDate(after.getDate() - 7);
    else if (dateFilter === "30d") after.setDate(after.getDate() - 30);
    else if (dateFilter === "90d") after.setDate(after.getDate() - 90);
    else after.setDate(after.getDate() - 180);
    return { created_after: after.toISOString(), created_before: before.toISOString() };
  }, [dateFilter]);

  // In-flight tickets are at most two days old. The active inbox must not pull
  // six months of delivered history every 20s just to find the live queue.
  const listBounds = useMemo(() => {
    if (tab === "all" || dateFilter !== "all") return dateBounds;
    const after = new Date();
    after.setDate(after.getDate() - 3);
    return { created_after: after.toISOString() };
  }, [tab, dateFilter, dateBounds]);

  const load = useCallback(async () => {
    if (!kitchen) return;
    setLoading(true);
    try {
      const [o, d, menu, stats] = await Promise.all([
        fetchOrders(kitchen.id, statusFilter || undefined, {
          source: sourceFilter || undefined,
          ...listBounds,
        }),
        fetchDrafts(kitchen.id),
        fetchMenu(kitchen.id).catch(() => null),
        fetchParseStats(kitchen.id, 30).catch(() => null),
      ]);
      setOrders(o.orders);
      setDrafts(d.drafts);
      setParseStats(stats);
      if (menu) setDishes(menu.dishes.filter((dish) => dish.is_active));
    } catch {
      setError("Could not load orders");
    } finally {
      setLoading(false);
    }
  }, [kitchen, statusFilter, sourceFilter, listBounds]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  // Service-mode inbox: poll for new received orders / drafts without full-page refresh noise.
  useEffect(() => {
    if (!kitchen) return;
    if (tab === "all" && dateFilter === "all") return;
    const tick = () => {
      Promise.all([
        fetchOrders(kitchen.id, statusFilter || undefined, {
          source: sourceFilter || undefined,
          ...listBounds,
        }),
        fetchDrafts(kitchen.id),
      ])
        .then(([o, d]) => {
          setOrders(o.orders);
          setDrafts(d.drafts);
        })
        .catch(() => undefined);
    };
    const id = window.setInterval(tick, 20000);
    const onVis = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [kitchen, statusFilter, sourceFilter, listBounds]);

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

  const shown = useMemo(() => {
    const base = tab === "drafts" ? [] : tab === "all" ? orders : activeOrders;
    let list = [...base];
    if (search.trim()) {
      const n = search.trim().toLowerCase();
      list = list.filter(
        (o) =>
          o.order_code.toLowerCase().includes(n) ||
          (o.customer_name || "").toLowerCase().includes(n) ||
          (o.customer_phone || "").includes(n) ||
          o.items.some((i) => i.dish_name.toLowerCase().includes(n)),
      );
    }
    list.sort((a, b) => {
      if (sort === "name_asc") {
        return (a.customer_name || a.order_code).localeCompare(b.customer_name || b.order_code);
      }
      if (sort === "name_desc") {
        return (b.customer_name || b.order_code).localeCompare(a.customer_name || a.order_code);
      }
      return Date.parse(b.created_at) - Date.parse(a.created_at);
    });
    return list;
  }, [tab, orders, activeOrders, search, sort]);

  const shownDrafts = useMemo(() => {
    let list = [...drafts];
    if (search.trim()) {
      const n = search.trim().toLowerCase();
      list = list.filter(
        (d) =>
          d.raw_message.toLowerCase().includes(n) ||
          d.parsed_items.some((p) => (p.dish_name ?? p.raw).toLowerCase().includes(n)),
      );
    }
    list.sort((a, b) => {
      if (sort === "name_asc") {
        return (a.raw_message || "").localeCompare(b.raw_message || "");
      }
      if (sort === "name_desc") {
        return (b.raw_message || "").localeCompare(a.raw_message || "");
      }
      return Date.parse(b.created_at) - Date.parse(a.created_at);
    });
    return list;
  }, [drafts, search, sort]);

  if (!kitchen) return null;

  const handleExportCsv = async () => {
    setBusy(true);
    setExporting(true);
    setError("");
    try {
      await downloadOrdersCsv(kitchen.id, kitchen.code, {
        status: statusFilter || undefined,
        source: sourceFilter || undefined,
        ...dateBounds,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not export CSV");
    } finally {
      setBusy(false);
      setExporting(false);
    }
  };

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

  const handleRemap = async (draft: OrderDraft, index: number, dishId: string) => {
    setBusy(true);
    setError("");
    try {
      const next = await updateDraft(kitchen.id, draft.id, {
        parsed_items: draft.parsed_items.map((item, i) => ({
          raw: item.raw,
          quantity: item.quantity,
          dish_id: i === index ? (dishId || null) : item.dish_id,
        })),
      });
      setDrafts((current) => current.map((row) => (row.id === next.id ? next : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update draft");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="owner-screen od-board od-orders">
      <section className="od-board__hero dash-card">
        <div className="od-board__hero-text">
          <p className="od-board__eyebrow">{t("owner.nav.operations")}</p>
          <h1>{t("owner.pages.orders")}</h1>
          <p className="od-board__meta">
            {t("owner.orders.drafts")} · {t("owner.orders.newOrder")} · {t("owner.orders.updateStatus")}
          </p>
          {drafts.length > 0 && (
            <div className="od-board__pills">
              <button
                type="button"
                className="od-pill od-pill--alert"
                onClick={() => setParams({ tab: "drafts" })}
              >
                {t("owner.orders.draftsNeedReview", { count: drafts.length })}
              </button>
            </div>
          )}
        </div>
        <div className="od-board__hero-actions">
          <button type="button" className="btn btn--ghost" disabled={exporting} onClick={() => void handleExportCsv()}>
            {exporting ? t("owner.orders.exporting") : t("owner.orders.exportCsv")}
          </button>
          <Link to="/dashboard/orders/new" className="btn btn--primary">{t("owner.orders.newOrder")}</Link>
          <Link to="/dashboard" className="btn btn--ghost">{t("common.dashboard")}</Link>
        </div>
      </section>

      <div className="od-board__kpi-grid od-orders__kpis">
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--orders" aria-hidden="true" />
          <div>
            <strong>{activeOrders.length}</strong>
            <span>{t("owner.orders.activeNow")}</span>
            <em>{t("owner.orders.inPipeline")}</em>
          </div>
        </div>
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--drafts" aria-hidden="true" />
          <div>
            <strong>{drafts.length}</strong>
            <span>{t("owner.home.kpiDrafts")}</span>
            <em>
              {parseStats && parseStats.lines_total > 0
                ? t("owner.orders.linesMapped", { pct: Math.round((parseStats.match_rate ?? 0) * 100) })
                : t("owner.orders.awaitingConfirm")}
            </em>
          </div>
        </div>
        <div className="od-kpi dash-card">
          <span className="od-kpi__icon od-kpi__icon--revenue" aria-hidden="true" />
          <div>
            <strong>{inr(todayRevenue)}</strong>
            <span>{t("owner.orders.todayRevenue")}</span>
            <em>{t("owner.orders.orderCount", { count: todayOrders.length })}</em>
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

      {error && tab !== "drafts" && <div className="auth-card__error">{error}</div>}

      {tab !== "drafts" && (
        <div className="od-orders__filters">
          <label>
            Status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {Object.keys(STATUS_LABELS).map((value) => (
                <option key={value} value={value}>{t(`status.${value}`, { defaultValue: value })}</option>
              ))}
            </select>
          </label>
          <label>
            Source
            <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
              <option value="">All sources</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="customer_pwa">Customer app</option>
              <option value="manual">Manual</option>
              <option value="customer_pwa_multi">Multi-kitchen</option>
            </select>
          </label>
          <label>
            Date
            <select
              value={dateFilter}
              onChange={(e) =>
                setDateFilter(e.target.value as "all" | "today" | "7d" | "30d" | "90d" | "180d")
              }
            >
              <option value="all">Any time</option>
              <option value="today">Today</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="180d">Last 6 months</option>
            </select>
          </label>
        </div>
      )}

      <ListingToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder={t("owner.list.searchOrders")}
        sort={sort}
        onSortChange={(v) => setSort(v as "newest" | "name_asc" | "name_desc")}
        sortOptions={[
          { value: "newest", label: "Newest" },
          { value: "name_asc", label: "Customer A–Z" },
          { value: "name_desc", label: "Customer Z–A" },
        ]}
        resultCount={tab === "drafts" ? shownDrafts.length : shown.length}
      />

      {loading ? (
        <OrdersSkeleton />
      ) : tab === "drafts" ? (
        <div className="od-orders__list">
          {parseStats && parseStats.lines_total > 0 && (
            <p className="dash-card od-panel od-orders__parse-rate">
              Parse match rate (30 days):{" "}
              <strong>
                {parseStats.lines_matched} of {parseStats.lines_total} lines mapped
                {parseStats.match_rate != null ? ` (${Math.round(parseStats.match_rate * 100)}%)` : ""}
              </strong>
              {parseStats.drafts_with_unmatched > 0
                ? ` · ${parseStats.drafts_with_unmatched} draft${parseStats.drafts_with_unmatched === 1 ? "" : "s"} still need remapping`
                : ""}
            </p>
          )}
          <details className="dash-card od-panel od-orders__parse" open={shownDrafts.length === 0}>
            <summary className="od-orders__parse-summary">
              <strong>Paste WhatsApp order</strong>
              <span>Match dishes → draft → confirm</span>
            </summary>
            <label className="kc-field od-orders__parse-field">
              <span className="kc-field__label">WhatsApp message</span>
              <textarea
                className="kc-textarea"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
                placeholder="e.g. 2 butter chicken, 1 garlic naan, less spicy"
                disabled={busy}
              />
            </label>
            {error && <div className="auth-card__error">{error}</div>}
            <div className="kc-actions kc-actions--stack-sm">
              <button type="button" className="btn btn--primary" disabled={busy || !message.trim()} onClick={handleParse}>
                {busy ? "Parsing…" : "Parse to draft"}
              </button>
            </div>
          </details>
          {shownDrafts.length === 0 && (
            <p className="od-panel__empty dash-card od-panel">
              No drafts yet — paste a WhatsApp message or share your menu link.
            </p>
          )}
          {shownDrafts.map((d) => (
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
                    {!p.matched && (
                      <select
                        aria-label={`Map ${p.raw} to a dish`}
                        disabled={busy}
                        value={p.dish_id ?? ""}
                        onChange={(e) => void handleRemap(d, i, e.target.value)}
                      >
                        <option value="">Map to dish…</option>
                        {dishes.map((dish) => (
                          <option key={dish.id} value={dish.id}>{dish.name}</option>
                        ))}
                      </select>
                    )}
                  </li>
                ))}
              </ul>
              {d.unmatched_lines.length > 0 && (
                <p className="od-order-draft__warn">Unmatched lines: {d.unmatched_lines.join(", ")}</p>
              )}
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={busy || !d.parsed_items.some((p) => p.matched)}
                title={!d.parsed_items.some((p) => p.matched) ? "Map at least one dish before confirming" : undefined}
                onClick={() => handleConfirm(d.id)}
              >
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
          <div className="dash-card od-panel od-orders__table">
            {shown.length > 0 && (
              <div className="od-recent__head" aria-hidden="true">
                <span>Order</span>
                <span>Customer / items</span>
                <span>Status</span>
                <span>Total</span>
              </div>
            )}
            <ul className="od-recent">
              {shown.map((o) => (
                <li key={o.id}>
                  <Link to={`/dashboard/orders/${o.id}`} className="od-recent__row">
                    <div className="od-recent__cell od-recent__cell--code">
                      <strong>{o.order_code}</strong>
                    </div>
                    <div className="od-recent__cell od-recent__cell--who">
                      <span className="od-recent__who">
                        {o.customer_name ?? o.customer_phone ?? "Walk-in"}
                      </span>
                      <span className="od-recent__dishes">
                        {o.items.map((i) => `${i.quantity}× ${i.dish_name}`).join(", ")}
                      </span>
                    </div>
                    <div className="od-recent__cell od-recent__cell--status">
                      <span className={`status-badge status-badge--${o.status}`}>
                        {t(`status.${o.status}`, { defaultValue: STATUS_LABELS[o.status] ?? o.status })}
                      </span>
                    </div>
                    <div className="od-recent__cell od-recent__cell--meta">
                      <span className="od-recent__amount">{inr(o.total)}</span>
                      <span className="od-recent__meta">
                        {o.distance_km != null ? `${o.distance_km.toFixed(1)} km · ` : ""}
                        {o.source} · {formatWhen(o.created_at)}
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
