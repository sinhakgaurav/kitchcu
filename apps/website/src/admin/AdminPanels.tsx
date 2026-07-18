import { FormEvent, useEffect, useState } from "react";
import {
  clearAdminApiKey,
  clearAdminCustomerPassword,
  createAdminEmployee,
  fetchAdminApiKeys,
  fetchAdminCustomer,
  fetchAdminCustomers,
  fetchAdminEmployeeRoles,
  fetchAdminEmployees,
  fetchAdminFeatureFlags,
  fetchAdminFeatures,
  fetchAdminJourneys,
  fetchAdminMoneyStats,
  fetchAdminOwners,
  fetchAdminPackages,
  fetchAdminPayments,
  fetchAdminRefunds,
  patchAdminRefund,
  updateAdminApiKey,
  updateAdminCustomerStatus,
  updateAdminEmployee,
  updateAdminFeatureFlag,
  updateAdminOwnerSubscription,
  upsertAdminPackage,
  type AdminCustomer,
  type AdminCustomerDetail,
  type AdminEmployee,
  type AdminFeature,
  type AdminPackage,
  type AdminRefund,
  type FeatureFlag,
  type PlatformApiKey,
} from "./adminApi";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

const API_KEY_CATEGORY_LABEL: Record<string, string> = {
  billing: "Payments (Razorpay)",
  streaming: "Live streaming (LiveKit)",
  notification: "WhatsApp & AI support",
  identity: "Customer OAuth",
  platform: "Maps & platform",
};

export function AdminApiKeysPanel() {
  const [apiKeys, setApiKeys] = useState<PlatformApiKey[]>([]);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const keys = await fetchAdminApiKeys();
      setApiKeys(keys);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const byCategory = apiKeys.reduce<Record<string, PlatformApiKey[]>>((acc, k) => {
    (acc[k.category] ??= []).push(k);
    return acc;
  }, {});

  const saveKey = async (key: string) => {
    const value = (draftValues[key] || "").trim();
    if (!value) return;
    setBusyKey(key);
    setOkMsg("");
    try {
      await updateAdminApiKey(key, value);
      setDraftValues((prev) => ({ ...prev, [key]: "" }));
      setOkMsg(`Saved ${key}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "API key update failed");
    } finally {
      setBusyKey(null);
    }
  };

  const clearKey = async (key: string) => {
    setBusyKey(key);
    setOkMsg("");
    try {
      await clearAdminApiKey(key);
      setOkMsg(`Cleared ${key}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clear failed");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      {okMsg && <p className="admin-panel__note" role="status">{okMsg}</p>}

      <section className="glass admin-detail">
        <header className="admin-panel__head">
          <div>
            <h3>Platform API keys</h3>
            <p style={{ margin: "0.35rem 0 0", color: "var(--text-muted)" }}>
              Platform-wide secrets only: Meta WhatsApp App Secret / Verify Token, SaaS Razorpay,
              LiveKit, Maps, OAuth, AI. Per-kitchen WhatsApp phone ID and kitchen Razorpay keys
              live under Kitchens → workspace. Values encrypted at rest; masked after save.
            </p>
          </div>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => load()} disabled={loading}>
            Refresh
          </button>
        </header>

        {loading && <p className="admin-panel__empty">Loading API key slots…</p>}
        {!loading && apiKeys.length === 0 && (
          <p className="admin-panel__empty">
            No API key slots found. Run identity migrations (`009` / `010`) then refresh.
          </p>
        )}

        {!loading &&
          Object.entries(byCategory).map(([category, keys]) => (
            <div key={category} className="admin-table-wrap" style={{ marginBottom: "1.25rem" }}>
              <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>
                {API_KEY_CATEGORY_LABEL[category] || category}
              </h4>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Key</th>
                    <th>Status</th>
                    <th>Set / update value</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((k) => (
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
                      <td>
                        {k.configured ? (
                          <span>
                            Configured
                            {k.value_masked ? ` · ${k.value_masked}` : ""}
                            {k.updated_by ? (
                              <>
                                <br />
                                <small>by {k.updated_by}</small>
                              </>
                            ) : null}
                          </span>
                        ) : (
                          <span>Not set</span>
                        )}
                      </td>
                      <td>
                        <input
                          type={k.is_secret ? "password" : "text"}
                          className="admin-inline-input"
                          placeholder={k.configured ? "Enter new value to replace" : "Paste value to add"}
                          value={draftValues[k.key] ?? ""}
                          onChange={(e) =>
                            setDraftValues((prev) => ({ ...prev, [k.key]: e.target.value }))
                          }
                          autoComplete="off"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") void saveKey(k.key);
                          }}
                        />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--primary btn--sm"
                          disabled={busyKey === k.key || !(draftValues[k.key] || "").trim()}
                          onClick={() => void saveKey(k.key)}
                        >
                          {k.configured ? "Update" : "Add"}
                        </button>{" "}
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busyKey === k.key || !k.configured}
                          onClick={() => void clearKey(k.key)}
                        >
                          Clear
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </section>
    </div>
  );
}

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
  const [journeys, setJourneys] = useState<
    Awaited<ReturnType<typeof fetchAdminJourneys>>["stages"]
  >([]);
  const [payments, setPayments] = useState<Awaited<ReturnType<typeof fetchAdminPayments>>>([]);
  const [owners, setOwners] = useState<Awaited<ReturnType<typeof fetchAdminOwners>>>([]);
  const [error, setError] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const load = async () => {
    try {
      const [f, j, p, o] = await Promise.all([
        fetchAdminFeatureFlags(),
        fetchAdminJourneys(),
        fetchAdminPayments(),
        fetchAdminOwners(),
      ]);
      setFlags(f);
      setJourneys(j.stages);
      setPayments(p.slice(0, 40));
      setOwners(o);
      setError("");
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
          Manage Razorpay, LiveKit, WhatsApp, Maps, OAuth, and AI keys on the dedicated{" "}
          <strong>API Keys</strong> tab (Add / Update / Clear).
        </p>
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

export function AdminEmployeesPanel() {
  const [rows, setRows] = useState<AdminEmployee[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("support");

  const load = async () => {
    setLoading(true);
    try {
      const [emps, r] = await Promise.all([fetchAdminEmployees(), fetchAdminEmployeeRoles()]);
      setRows(emps);
      setRoles(r);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load employees");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await createAdminEmployee({ email, name, password, role });
      setEmail("");
      setName("");
      setPassword("");
      setOk("Employee created.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      {ok && <p className="auth-card__success">{ok}</p>}
      <section className="glass admin-detail" style={{ marginBottom: "1.25rem" }}>
        <header className="admin-panel__head">
          <div>
            <h3>Add employee</h3>
            <p style={{ margin: "0.35rem 0 0", color: "var(--text-muted)" }}>
              RBAC roles: superadmin, ops, support, finance — permissions enforced on admin APIs.
            </p>
          </div>
        </header>
        <form className="owner-forms" onSubmit={onCreate}>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {roles.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? "Saving…" : "Create employee"}
          </button>
        </form>
      </section>
      <div className="dash-card admin-table-wrap">
        {loading ? (
          <p className="admin-panel__empty">Loading…</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((emp) => (
                <tr key={emp.id}>
                  <td>{emp.name}</td>
                  <td>{emp.email}</td>
                  <td>
                    <select
                      value={emp.role}
                      onChange={async (e) => {
                        try {
                          await updateAdminEmployee(emp.id, { role: e.target.value });
                          await load();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Role update failed");
                        }
                      }}
                    >
                      {roles.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </td>
                  <td>{emp.is_active ? "active" : "inactive"}</td>
                  <td>
                    {emp.is_active && (
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        onClick={async () => {
                          try {
                            await updateAdminEmployee(emp.id, { is_active: false });
                            await load();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Deactivate failed");
                          }
                        }}
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export function AdminPackagesPanel() {
  const [packages, setPackages] = useState<AdminPackage[]>([]);
  const [features, setFeatures] = useState<AdminFeature[]>([]);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<AdminPackage | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [audience, setAudience] = useState("owner");
  const [description, setDescription] = useState("");
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [planTiers, setPlanTiers] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [p, f] = await Promise.all([fetchAdminPackages(), fetchAdminFeatures()]);
      setPackages(p);
      setFeatures(f);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load packages");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const startEdit = (pkg: AdminPackage | null) => {
    setEditing(pkg);
    setCode(pkg?.code ?? "");
    setName(pkg?.name ?? "");
    setAudience(pkg?.audience ?? "owner");
    setDescription(pkg?.description ?? "");
    setSelectedFeatures(pkg?.feature_keys ?? []);
    setPlanTiers((pkg?.plan_tiers ?? []).join(", "));
  };

  const onSave = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await upsertAdminPackage(
        {
          code,
          name,
          audience,
          description,
          is_active: true,
          feature_keys: selectedFeatures,
          plan_tiers: planTiers
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        },
        editing?.id,
      );
      setOk(editing ? "Package updated." : "Package created.");
      startEdit(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleFeat = (key: string) => {
    setSelectedFeatures((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  return (
    <div className="admin-panel">
      {error && <p className="auth-card__error">{error}</p>}
      {ok && <p className="auth-card__success">{ok}</p>}
      <p className="report-hint" style={{ marginBottom: "1rem" }}>
        Map platform features → packages → subscription plan tiers. Assign packages on kitchen workspace.
      </p>
      <div className="admin-split">
        <div className="dash-card admin-table-wrap">
          {loading ? (
            <p className="admin-panel__empty">Loading…</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Audience</th>
                  <th>Features</th>
                  <th>Plans</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {packages.map((p) => (
                  <tr key={p.id}>
                    <td><code className="admin-code">{p.code}</code></td>
                    <td>{p.name}</td>
                    <td>{p.audience}</td>
                    <td>{p.feature_keys.length}</td>
                    <td>{p.plan_tiers.join(", ") || "—"}</td>
                    <td>
                      <button type="button" className="btn btn--sm btn--ghost" onClick={() => startEdit(p)}>
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button type="button" className="btn btn--primary btn--sm" style={{ margin: "1rem" }} onClick={() => startEdit(null)}>
            New package
          </button>
        </div>
        <section className="glass admin-detail">
          <h3>{editing ? `Edit ${editing.code}` : "New package"}</h3>
          <form className="owner-forms" onSubmit={onSave}>
            <label>
              Code
              <input value={code} onChange={(e) => setCode(e.target.value)} required disabled={Boolean(editing)} />
            </label>
            <label>
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label>
              Audience
              <select value={audience} onChange={(e) => setAudience(e.target.value)}>
                <option value="owner">Owner</option>
                <option value="customer">Customer</option>
                <option value="both">Both</option>
              </select>
            </label>
            <label>
              Description
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            </label>
            <label>
              Plan tiers (comma-separated)
              <input value={planTiers} onChange={(e) => setPlanTiers(e.target.value)} placeholder="starter, growth" />
            </label>
            <fieldset style={{ border: "1px solid var(--surface-border)", borderRadius: 8, padding: "0.75rem" }}>
              <legend>Features</legend>
              {features.map((f) => (
                <label key={f.key} className="owner-forms__check">
                  <input
                    type="checkbox"
                    checked={selectedFeatures.includes(f.key)}
                    onChange={() => toggleFeat(f.key)}
                  />
                  {f.label} <span className="report-rank__meta">({f.key})</span>
                </label>
              ))}
            </fieldset>
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {busy ? "Saving…" : "Save package"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
