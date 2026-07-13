import { FormEvent, useEffect, useState } from "react";
import {
  adminLogin,
  clearAdminToken,
  fetchAdminKitchens,
  fetchAdminOrders,
  fetchAdminOwners,
  fetchAdminStats,
  fetchAdminTicket,
  fetchAdminTickets,
  getAdminToken,
  replyAdminTicket,
  setAdminToken,
  updateAdminTicket,
  updateKitchenStatus,
  type AdminTicket,
  type PlatformStats,
} from "./adminApi";
import { ADMIN_DEV_EMAIL, ADMIN_HOST, APP_NAME, CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";
import "../owner-app.css";

type Tab = "overview" | "kitchens" | "owners" | "orders" | "tickets";

export default function AdminApp() {
  const [token, setToken] = useState(getAdminToken());
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    fetchAdminStats().then(setStats).catch((e) => setError(e.message));
  }, [token]);

  if (!token) {
    return <AdminLogin onSuccess={(t) => setToken(t)} />;
  }

  return (
    <div className="admin-app">
      <header className="admin-app__head">
        <div>
          <span className="admin-app__logo">{APP_NAME} Admin</span>
          <span className="admin-app__host">{ADMIN_HOST}</span>
        </div>
        <div className="admin-app__links">
          <a href={customerUrl("/")}>{CUSTOMER_HOST}</a>
          <a href={kitchenUrl("/")}>{KITCHEN_HOST}</a>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              clearAdminToken();
              setToken(null);
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      <nav className="admin-tabs">
        {(["overview", "kitchens", "owners", "orders", "tickets"] as Tab[]).map((t) => (
          <button key={t} type="button" className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      {error && <p className="auth-card__error container">{error}</p>}

      {tab === "overview" && stats && (
        <div className="container admin-stats">
          {[
            ["Owners", stats.owners],
            ["Kitchens", stats.kitchens],
            ["Active kitchens", stats.active_kitchens],
            ["Orders", stats.orders],
            ["Dishes", stats.dishes],
          ].map(([label, val]) => (
            <div key={label as string} className="glass owner-stat">
              <strong>{val as number}</strong>
              <span>{label as string}</span>
            </div>
          ))}
        </div>
      )}

      {tab === "kitchens" && <AdminKitchens />}
      {tab === "owners" && <AdminOwners />}
      {tab === "orders" && <AdminOrders />}
      {tab === "tickets" && <AdminTickets />}
    </div>
  );
}

function AdminLogin({ onSuccess }: { onSuccess: (token: string) => void }) {
  const [email, setEmail] = useState(ADMIN_DEV_EMAIL);
  const [password, setPassword] = useState("admin123456");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await adminLogin(email, password);
      setAdminToken(res.access_token);
      onSuccess(res.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="glass auth-card" onSubmit={submit}>
        <h1>Platform admin</h1>
        <p>Full control over cloud kitchens, owners, and orders.</p>
        {error && <div className="auth-card__error">{error}</div>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
        <p className="auth-card__hint">Dev default: {ADMIN_DEV_EMAIL} / admin123456</p>
      </form>
    </div>
  );
}

function AdminKitchens() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminKitchens>>>([]);
  useEffect(() => {
    fetchAdminKitchens().then(setRows).catch(() => {});
  }, []);

  const setStatus = async (id: string, status: string) => {
    await updateKitchenStatus(id, status);
    setRows(await fetchAdminKitchens());
  };

  return (
    <div className="container admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => (
            <tr key={k.id}>
              <td>{k.code}</td>
              <td>{k.name}</td>
              <td>{k.owner_name}</td>
              <td><span className={`status-badge status-badge--${k.status}`}>{k.status}</span></td>
              <td>
                {k.status !== "active" && (
                  <button type="button" className="btn btn--sm btn--primary" onClick={() => setStatus(k.id, "active")}>
                    Activate
                  </button>
                )}
                {k.status === "active" && (
                  <button type="button" className="btn btn--sm btn--ghost" onClick={() => setStatus(k.id, "suspended")}>
                    Suspend
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdminOwners() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  useEffect(() => {
    fetchAdminOwners().then(setRows).catch(() => {});
  }, []);
  return (
    <div className="container admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Tier</th>
            <th>Kitchens</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>{o.name}</td>
              <td>{o.phone}</td>
              <td>{o.subscription_tier}</td>
              <td>{o.kitchen_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdminOrders() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchAdminOrders>>>([]);
  useEffect(() => {
    fetchAdminOrders().then(setRows).catch(() => {});
  }, []);
  return (
    <div className="container admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Kitchen</th>
            <th>Customer</th>
            <th>Status</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.id}>
              <td>{o.order_code}</td>
              <td>{o.kitchen_name}</td>
              <td>{o.customer_name ?? "—"}</td>
              <td>{o.status}</td>
              <td>₹{o.total.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdminTickets() {
  const [tickets, setTickets] = useState<AdminTicket[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminTicket | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [audienceFilter, setAudienceFilter] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadTickets = async () => {
    const res = await fetchAdminTickets({
      status: statusFilter || undefined,
      audience: audienceFilter || undefined,
    });
    setTickets(res.tickets);
  };

  useEffect(() => {
    loadTickets().catch((e) => setError(e.message));
  }, [statusFilter, audienceFilter]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    fetchAdminTicket(selectedId)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [selectedId]);

  const refreshDetail = async () => {
    if (!selectedId) return;
    const t = await fetchAdminTicket(selectedId);
    setDetail(t);
    await loadTickets();
  };

  const handleStatusChange = async (status: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await updateAdminTicket(selectedId, { status });
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const handleReply = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedId || !reply.trim()) return;
    setBusy(true);
    try {
      await replyAdminTicket(selectedId, reply.trim());
      setReply("");
      await refreshDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reply failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container admin-tickets">
      <div className="admin-tickets__filters">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In progress</option>
          <option value="waiting_customer">Waiting customer</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <select value={audienceFilter} onChange={(e) => setAudienceFilter(e.target.value)}>
          <option value="">All audiences</option>
          <option value="customer">Customer</option>
          <option value="owner">Owner</option>
        </select>
      </div>

      {error && <p className="auth-card__error">{error}</p>}

      <div className="admin-tickets__grid">
        <div className="admin-tickets__list glass">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  className={selectedId === t.id ? "admin-tickets__row--active" : ""}
                  onClick={() => setSelectedId(t.id)}
                >
                  <td>
                    <strong>{t.ticket_number}</strong>
                    <span className="admin-tickets__meta">{t.audience} · {t.category}</span>
                  </td>
                  <td>{t.subject}</td>
                  <td><span className={`status-badge status-badge--${t.status}`}>{t.status}</span></td>
                  <td>{t.priority}</td>
                </tr>
              ))}
              {tickets.length === 0 && (
                <tr><td colSpan={4}>No tickets yet — customers can raise them via AI chat on the portal.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {detail && (
          <div className="admin-tickets__detail glass">
            <header>
              <h2>{detail.ticket_number}</h2>
              <p>{detail.subject}</p>
            </header>
            <dl className="admin-tickets__info">
              <div><dt>Status</dt><dd>{detail.status}</dd></div>
              <div><dt>Priority</dt><dd>{detail.priority}</dd></div>
              <div><dt>From</dt><dd>{detail.customer_name ?? "—"} ({detail.audience})</dd></div>
              <div><dt>Contact</dt><dd>{detail.customer_phone ?? detail.customer_email ?? "—"}</dd></div>
              {detail.order_code && <div><dt>Order</dt><dd>{detail.order_code}</dd></div>}
            </dl>
            <p className="admin-tickets__desc">{detail.description}</p>

            <div className="admin-tickets__actions">
              <select
                value={detail.status}
                disabled={busy}
                onChange={(e) => handleStatusChange(e.target.value)}
              >
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="waiting_customer">Waiting customer</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            <div className="admin-tickets__thread">
              {detail.messages.map((m) => (
                <div key={m.id} className={`admin-tickets__msg admin-tickets__msg--${m.author_type}`}>
                  <span>{m.author_type}</span>
                  <p>{m.message}</p>
                </div>
              ))}
            </div>

            <form className="admin-tickets__reply" onSubmit={handleReply}>
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Reply to customer..."
                rows={3}
                disabled={busy}
              />
              <button type="submit" className="btn btn--primary btn--sm" disabled={busy || !reply.trim()}>
                Send reply
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
