import { useEffect, useState } from "react";
import {
  clearAdminApiKey,
  clearAdminCustomerPassword,
  fetchAdminApiKeys,
  fetchAdminCustomer,
  fetchAdminCustomers,
  fetchAdminFeatureFlags,
  fetchAdminJourneys,
  fetchAdminMoneyStats,
  fetchAdminOwners,
  fetchAdminPayments,
  fetchAdminRefunds,
  patchAdminRefund,
  updateAdminApiKey,
  updateAdminCustomerStatus,
  updateAdminFeatureFlag,
  updateAdminOwnerSubscription,
  type AdminCustomer,
  type AdminCustomerDetail,
  type AdminRefund,
  type FeatureFlag,
  type PlatformApiKey,
} from "./adminApi";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export function AdminCustomers() {
  const [rows, setRows] = useState<AdminCustomer[]>([]);
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<AdminCustomerDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async (query?: string) => {
    setError("");
    try {
      setRows(await fetchAdminCustomers(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load customers");
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      <form
        className="admin-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          load(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name / phone / email"
        />
        <button type="submit" className="btn btn--primary btn--sm">
          Search
        </button>
      </form>
      <div className="admin-split">
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Payout</th>
                <th>Addresses</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.phone || "—"}</td>
                  <td>
                    <span className={`status-badge status-badge--${c.status}`}>{c.status}</span>
                  </td>
                  <td>{c.has_payout ? "Yes" : "No"}</td>
                  <td>{c.address_count}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={async () => {
                        try {
                          setSelected(await fetchAdminCustomer(c.id));
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Load failed");
                        }
                      }}
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selected && (
          <aside className="admin-detail glass">
            <h3>{selected.name}</h3>
            <p>
              {selected.phone || "no phone"} · {selected.email || "no email"}
            </p>
            <p>
              Status: <strong>{selected.status}</strong>
              {selected.has_password ? " · password set" : " · OTP/social only"}
            </p>
            <h4>Payout</h4>
            <p>UPI: {selected.upi_vpa || "—"}</p>
            <p>
              Bank: {selected.bank_account_number_masked || "—"} · {selected.bank_ifsc || ""}
            </p>
            <h4>Addresses ({selected.addresses.length})</h4>
            <ul>
              {selected.addresses.map((a) => (
                <li key={a.id}>
                  {a.label}: {a.address_line}, {a.city}
                  {a.latitude != null ? ` · ${a.latitude.toFixed(4)}, ${a.longitude?.toFixed(4)}` : ""}
                </li>
              ))}
            </ul>
            <div className="admin-detail__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    const next = selected.status === "active" ? "suspended" : "active";
                    await updateAdminCustomerStatus(selected.id, next);
                    setSelected(await fetchAdminCustomer(selected.id));
                    await load(q);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Update failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {selected.status === "active" ? "Suspend customer" : "Activate customer"}
              </button>
              {selected.has_password && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      setSelected(await clearAdminCustomerPassword(selected.id));
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Clear failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Clear password
                </button>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export function AdminRefunds() {
  const [rows, setRows] = useState<AdminRefund[]>([]);
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState<AdminRefund | null>(null);
  const [note, setNote] = useState("");
  const [money, setMoney] = useState<Awaited<ReturnType<typeof fetchAdminMoneyStats>> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [refunds, stats] = await Promise.all([
        fetchAdminRefunds(status ? { status } : undefined),
        fetchAdminMoneyStats(),
      ]);
      setRows(refunds);
      setMoney(stats);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load refunds");
    }
  };

  useEffect(() => {
    load();
  }, [status]);

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      {money && (
        <div className="admin-stats admin-stats--rich">
          <div className="admin-stat">
            <strong>{money.refunds_requested}</strong>
            <span>Open refunds</span>
          </div>
          <div className="admin-stat">
            <strong>{money.refunds_completed}</strong>
            <span>Completed</span>
          </div>
          <div className="admin-stat">
            <strong>{inr(money.refunds_amount_completed)}</strong>
            <span>Refunded amount</span>
          </div>
          <div className="admin-stat">
            <strong>{money.payments_captured}</strong>
            <span>Captured payments</span>
          </div>
        </div>
      )}
      <div className="admin-toolbar">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="requested">requested</option>
          <option value="processing">processing</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
        </select>
      </div>
      <div className="admin-split">
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Amount</th>
                <th>Kind</th>
                <th>Channel</th>
                <th>Status</th>
                <th>Remark</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{inr(r.amount)}</td>
                  <td>{r.kind}</td>
                  <td>{r.channel}</td>
                  <td>{r.status}</td>
                  <td>{r.transfer_remark}</td>
                  <td>
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSelected(r)}>
                      Open
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selected && (
          <aside className="admin-detail glass">
            <h3>
              {inr(selected.amount)} · {selected.status}
            </h3>
            <p>
              {selected.kind} via {selected.channel}
            </p>
            <p>Remark: {selected.transfer_remark}</p>
            <p>UPI: {selected.destination_upi || "—"}</p>
            {selected.evidence_url && (
              <p>
                <a href={selected.evidence_url} target="_blank" rel="noreferrer">
                  Evidence screenshot
                </a>
              </p>
            )}
            <p>{selected.reason || "No reason"}</p>
            <label>
              Admin note
              <input value={note} onChange={(e) => setNote(e.target.value)} />
            </label>
            <div className="admin-detail__actions">
              {(["processing", "completed", "failed"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setError("");
                    try {
                      const updated = await patchAdminRefund(selected.id, {
                        status: s,
                        admin_note: note || undefined,
                      });
                      setSelected(updated);
                      setNote("");
                      await load();
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Update failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Mark {s}
                </button>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export function AdminControlPlane() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [apiKeys, setApiKeys] = useState<PlatformApiKey[]>([]);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [journeys, setJourneys] = useState<
    Awaited<ReturnType<typeof fetchAdminJourneys>>["stages"]
  >([]);
  const [payments, setPayments] = useState<Awaited<ReturnType<typeof fetchAdminPayments>>>([]);
  const [owners, setOwners] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  const [error, setError] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const load = async () => {
    try {
      const [f, j, p, o, keys] = await Promise.all([
        fetchAdminFeatureFlags(),
        fetchAdminJourneys(),
        fetchAdminPayments(),
        fetchAdminOwners(),
        fetchAdminApiKeys(),
      ]);
      setFlags(f);
      setJourneys(j.stages);
      setPayments(p.slice(0, 40));
      setOwners(o);
      setApiKeys(keys);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load control plane");
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}

      <section className="glass admin-detail" style={{ marginBottom: "1rem" }}>
        <h3>Platform API keys</h3>
        <p>
          Configure Razorpay (platform SaaS), LiveKit, WhatsApp, Maps, OAuth, and AI support keys.
          Secrets are encrypted at rest; responses only show masked values.
        </p>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Category</th>
              <th>Status</th>
              <th>Set / update value</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {apiKeys.map((k) => (
              <tr key={k.key}>
                <td>
                  <code>{k.key}</code>
                  {k.description && (
                    <>
                      <br />
                      <small>{k.description}</small>
                    </>
                  )}
                </td>
                <td>{k.category}</td>
                <td>
                  {k.configured ? (
                    <span>
                      Configured
                      {k.value_masked ? ` · ${k.value_masked}` : ""}
                    </span>
                  ) : (
                    <span>Not set</span>
                  )}
                </td>
                <td>
                  <input
                    type={k.is_secret ? "password" : "text"}
                    className="admin-inline-input"
                    placeholder={k.configured ? "Enter new value to replace" : "Enter value"}
                    value={draftValues[k.key] ?? ""}
                    onChange={(e) =>
                      setDraftValues((prev) => ({ ...prev, [k.key]: e.target.value }))
                    }
                    autoComplete="off"
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    disabled={busyKey === k.key || !(draftValues[k.key] || "").trim()}
                    onClick={async () => {
                      const value = (draftValues[k.key] || "").trim();
                      if (!value) return;
                      setBusyKey(k.key);
                      try {
                        await updateAdminApiKey(k.key, value);
                        setDraftValues((prev) => ({ ...prev, [k.key]: "" }));
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "API key update failed");
                      } finally {
                        setBusyKey(null);
                      }
                    }}
                  >
                    Save
                  </button>{" "}
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={busyKey === k.key || !k.configured}
                    onClick={async () => {
                      setBusyKey(k.key);
                      try {
                        await clearAdminApiKey(k.key);
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Clear failed");
                      } finally {
                        setBusyKey(null);
                      }
                    }}
                  >
                    Clear
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="glass admin-detail" style={{ marginBottom: "1rem" }}>
        <h3>Application data journeys</h3>
        <p>Full platform oversight of each product journey and where super-admin intervenes.</p>
        <div className="admin-journey-grid">
          {journeys.map((s) => (
            <article key={s.id} className="admin-journey-card">
              <strong>{s.label}</strong>
              <span>{s.control}</span>
              <em>
                {s.count}
                {s.meta ? ` · ${s.meta}` : ""}
              </em>
            </article>
          ))}
        </div>
      </section>

      <section className="glass admin-detail" style={{ marginBottom: "1rem" }}>
        <h3>Feature flags (kill-switches)</h3>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Scope</th>
              <th>Description</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {flags.map((f) => (
              <tr key={f.key}>
                <td>
                  <code>{f.key}</code>
                </td>
                <td>{f.scope}</td>
                <td>{f.description}</td>
                <td>
                  <button
                    type="button"
                    className={`btn btn--sm ${f.enabled ? "btn--primary" : "btn--ghost"}`}
                    disabled={busyKey === f.key}
                    onClick={async () => {
                      setBusyKey(f.key);
                      try {
                        await updateAdminFeatureFlag(f.key, !f.enabled);
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Flag update failed");
                      } finally {
                        setBusyKey(null);
                      }
                    }}
                  >
                    {f.enabled ? "ON" : "OFF"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="glass admin-detail" style={{ marginBottom: "1rem" }}>
        <h3>Owner subscription control</h3>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Owner</th>
              <th>Tier</th>
              <th>Status</th>
              <th>Force</th>
            </tr>
          </thead>
          <tbody>
            {owners.slice(0, 25).map((o) => (
              <tr key={o.id}>
                <td>
                  {o.name}
                  <br />
                  <small>{o.phone}</small>
                </td>
                <td>{o.subscription_tier}</td>
                <td>{o.subscription_status}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={async () => {
                      try {
                        await updateAdminOwnerSubscription(o.id, {
                          subscription_status: "active",
                          subscription_tier: "growth",
                        });
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Owner update failed");
                      }
                    }}
                  >
                    Set growth/active
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="glass admin-detail">
        <h3>Recent payments</h3>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Amount</th>
              <th>Method</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{inr(p.amount)}</td>
                <td>{p.method}</td>
                <td>{p.status}</td>
                <td>{new Date(p.created_at).toLocaleString("en-IN")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
