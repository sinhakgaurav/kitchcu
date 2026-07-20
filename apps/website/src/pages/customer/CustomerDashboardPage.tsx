import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  fetchCustomerProfile,
  getCustomerToken,
  requestCustomerWhatsAppOtp,
  type CustomerProfile,
} from "../../shared/customerApi";
import {
  changeMyPassword,
  createMyTicket,
  deleteAddress,
  fetchCustomerDashboard,
  fetchMyAddresses,
  fetchMyRefunds,
  fetchMyTickets,
  saveAddress,
  updateMyProfile,
  type CustomerAddress,
  type CustomerDashboard,
  type CustomerRefund,
  type CustomerTicket,
  type DashboardOrder,
} from "../../shared/customerDashboardApi";
import { openStreetMapEmbedUrl } from "../../lib/locationMaps";
import {
  bulkCustomerKitchenReferrals,
  customerReferralTemplateUrl,
  fetchCustomerReferrals,
  submitCustomerKitchenReferral,
  uploadCustomerReferralCsv,
  type ReferralDashboard,
} from "../../shared/referralApi";

type Tab =
  | "overview"
  | "orders"
  | "savings"
  | "referrals"
  | "health"
  | "refunds"
  | "complaints"
  | "addresses"
  | "account";

const TABS: { id: Tab; labelKey: string }[] = [
  { id: "overview", labelKey: "owner.nav.overview" },
  { id: "orders", labelKey: "customer.nav.myOrders" },
  { id: "savings", labelKey: "customer.dashboard.title" },
  { id: "referrals", labelKey: "customer.dashboard.referrals" },
  { id: "health", labelKey: "customer.dashboard.title" },
  { id: "refunds", labelKey: "customer.account.payout" },
  { id: "complaints", labelKey: "customer.dashboard.tickets" },
  { id: "addresses", labelKey: "customer.account.addresses" },
  { id: "account", labelKey: "customer.nav.account" },
];

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function CustomerDashboardPage() {
  const { t } = useTranslation();
  const token = getCustomerToken();
  const [tab, setTab] = useState<Tab>("overview");
  const [dash, setDash] = useState<CustomerDashboard | null>(null);
  const [diet, setDiet] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [liveOnly, setLiveOnly] = useState(false);
  const [refunds, setRefunds] = useState<CustomerRefund[]>([]);
  const [tickets, setTickets] = useState<CustomerTicket[]>([]);
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadDash = useCallback(async () => {
    const data = await fetchCustomerDashboard({
      diet: diet || undefined,
      cuisine: cuisine || undefined,
      live_media_only: liveOnly || undefined,
    });
    setDash(data);
  }, [diet, cuisine, liveOnly]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [d, r, t, a, p] = await Promise.all([
        fetchCustomerDashboard({
          diet: diet || undefined,
          cuisine: cuisine || undefined,
          live_media_only: liveOnly || undefined,
        }),
        fetchMyRefunds().catch(() => []),
        fetchMyTickets().catch(() => ({ tickets: [], total: 0 })),
        fetchMyAddresses().catch(() => []),
        fetchCustomerProfile().catch(() => null),
      ]);
      setDash(d);
      setRefunds(r);
      setTickets(t.tickets);
      setAddresses(a);
      setProfile(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load dashboard");
    } finally {
      setLoading(false);
    }
  }, [diet, cuisine, liveOnly]);

  useEffect(() => {
    if (token) refreshAll();
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!token || loading) return;
    loadDash().catch(() => undefined);
  }, [diet, cuisine, liveOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!token) {
    return <Navigate to="/login?next=/dashboard" replace />;
  }

  return (
    <div className="container customer-dash">
      <header className="customer-dash__hero">
        <div>
          <p className="customer-dash__eyebrow">Your kitchCU space</p>
          <h1>
            {profile?.name
              ? `Hi, ${profile.name.split(" ")[0]}`
              : t("customer.dashboard.title")}
          </h1>
          <p>
            Orders, savings vs restaurants, health patterns, refunds, complaints, and delivery pins —
            everything in one place.
          </p>
        </div>
        <div className="customer-dash__hero-actions">
          <Link to="/#near-you" className="btn btn--ghost btn--sm">
            {t("customer.discovery.title")}
          </Link>
          <Link to="/account" className="btn btn--ghost btn--sm">
            {t("customer.account.payout")}
          </Link>
        </div>
      </header>

      <nav className="customer-dash__tabs" aria-label="Dashboard sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "active" : ""}
            onClick={() => setTab(item.id)}
          >
            {t(item.labelKey)}
          </button>
        ))}
      </nav>

      {error && <div className="auth-card__error">{error}</div>}
      {loading && <p className="app-loading">Loading dashboard…</p>}

      {!loading && dash && tab === "overview" && (
        <OverviewPanel dash={dash} refunds={refunds} tickets={tickets} onGo={setTab} />
      )}
      {!loading && dash && tab === "orders" && (
        <OrdersPanel
          dash={dash}
          diet={diet}
          cuisine={cuisine}
          liveOnly={liveOnly}
          setDiet={setDiet}
          setCuisine={setCuisine}
          setLiveOnly={setLiveOnly}
          onRaiseIssue={(code) => {
            setTab("complaints");
            window.dispatchEvent(new CustomEvent("kitchcu-raise-issue", { detail: code }));
          }}
        />
      )}
      {!loading && dash && tab === "savings" && <SavingsPanel dash={dash} />}
      {!loading && tab === "referrals" && (
        <ReferralsPanel setError={setError} busy={busy} setBusy={setBusy} />
      )}
      {!loading && dash && tab === "health" && <HealthPanel dash={dash} />}
      {!loading && tab === "refunds" && <RefundsPanel refunds={refunds} />}
      {!loading && tab === "complaints" && (
        <ComplaintsPanel
          tickets={tickets}
          busy={busy}
          setBusy={setBusy}
          setError={setError}
          onRefresh={async () => {
            const t = await fetchMyTickets();
            setTickets(t.tickets);
          }}
        />
      )}
      {!loading && tab === "addresses" && (
        <AddressesPanel
          addresses={addresses}
          busy={busy}
          setBusy={setBusy}
          setError={setError}
          onRefresh={async () => setAddresses(await fetchMyAddresses())}
        />
      )}
      {!loading && tab === "account" && profile && (
        <AccountPanel
          profile={profile}
          setProfile={setProfile}
          busy={busy}
          setBusy={setBusy}
          setError={setError}
        />
      )}
    </div>
  );
}

function OverviewPanel({
  dash,
  refunds,
  tickets,
  onGo,
}: {
  dash: CustomerDashboard;
  refunds: CustomerRefund[];
  tickets: CustomerTicket[];
  onGo: (t: Tab) => void;
}) {
  const openTickets = tickets.filter((t) => !["resolved", "closed"].includes(t.status)).length;
  const completedRefunds = refunds.filter((r) => r.status === "completed");
  return (
    <div className="customer-dash__grid">
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("orders")}>
        <strong>{dash.orders.length}</strong>
        <span>Orders in history</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("savings")}>
        <strong>{inr(dash.savings.total_saved)}</strong>
        <span>Est. saved vs restaurants</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("health")}>
        <strong>{dash.health.home_freshness_score}</strong>
        <span>Home freshness score</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("refunds")}>
        <strong>{completedRefunds.length}</strong>
        <span>Refunds received</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("complaints")}>
        <strong>{openTickets}</strong>
        <span>Open complaints</span>
      </button>
      <section className="glass customer-dash__card customer-dash__span2">
        <h2>Wellness after recent meals</h2>
        <ul className="customer-dash__tips">
          {dash.tips.slice(0, 3).map((tip, i) => (
            <li key={i}>
              <strong>
                Walk {tip.walk_minutes} min · {tip.water_ml} ml water
              </strong>
              <span>
                {tip.after_dish ? `After ${tip.after_dish}: ` : ""}
                {tip.message}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function OrdersPanel({
  dash,
  diet,
  cuisine,
  liveOnly,
  setDiet,
  setCuisine,
  setLiveOnly,
  onRaiseIssue,
}: {
  dash: CustomerDashboard;
  diet: string;
  cuisine: string;
  liveOnly: boolean;
  setDiet: (v: string) => void;
  setCuisine: (v: string) => void;
  setLiveOnly: (v: boolean) => void;
  onRaiseIssue: (orderCode: string) => void;
}) {
  return (
    <section className="customer-dash__section">
      <div className="customer-dash__filters">
        <label>
          Diet
          <select value={diet} onChange={(e) => setDiet(e.target.value)}>
            <option value="">Any</option>
            {dash.filters.diets.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cuisine
          <select value={cuisine} onChange={(e) => setCuisine(e.target.value)}>
            <option value="">Any</option>
            {dash.filters.cuisines.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="customer-dash__check">
          <input type="checkbox" checked={liveOnly} onChange={(e) => setLiveOnly(e.target.checked)} />
          Live-capture prep media only
        </label>
      </div>

      {dash.orders.length === 0 ? (
        <p className="glass customer-dash__card">No orders match these filters.</p>
      ) : (
        <ul className="customer-dash__orders">
          {dash.orders.map((row) => (
            <OrderCard key={row.order.id} row={row} onRaiseIssue={onRaiseIssue} />
          ))}
        </ul>
      )}
    </section>
  );
}

function OrderCard({
  row,
  onRaiseIssue,
}: {
  row: DashboardOrder;
  onRaiseIssue: (orderCode: string) => void;
}) {
  const media = useMemo(
    () => row.items.flatMap((i) => i.media.filter((m) => m.url)).slice(0, 6),
    [row.items],
  );
  return (
    <li className="glass customer-dash__order">
      <div className="customer-dash__order-head">
        <div>
          <strong>{row.order.order_code}</strong>
          <span>
            {formatWhen(row.order.created_at)} · {row.order.status.replace(/_/g, " ")} ·{" "}
            {inr(row.order.total)}
          </span>
          <span>
            {(row.cuisines.length ? row.cuisines.join(", ") : "—") +
              " · " +
              (row.diets.length ? row.diets.join(", ") : "—")}
            {row.has_live_media ? " · live media" : ""}
          </span>
        </div>
        <div className="customer-dash__order-actions">
          {row.can_rate && (
            <Link className="btn btn--primary btn--sm" to={`/orders/${row.order.id}/rate`}>
              Rate
            </Link>
          )}
          {row.tracking_token && (
            <Link className="btn btn--ghost btn--sm" to={`/t/${row.tracking_token}`}>
              Track
            </Link>
          )}
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onRaiseIssue(row.order.order_code)}
          >
            Raise issue
          </button>
        </div>
      </div>
      <ul className="customer-dash__order-items">
        {row.items.map((item) => (
          <li key={item.id}>
            {item.quantity}× {item.dish_name} · {inr(item.line_total)}
            {item.saved_vs_restaurant > 0 && (
              <em> saved ~{inr(item.saved_vs_restaurant)} vs restaurant</em>
            )}
          </li>
        ))}
      </ul>
      {media.length > 0 && (
        <div className="customer-dash__media">
          {media.map((m, i) => (
            <a key={i} href={m.url} target="_blank" rel="noreferrer" title="Prep / dish media">
              <img src={m.url} alt="" loading="lazy" />
              {m.is_live_capture ? <span>Live</span> : null}
            </a>
          ))}
        </div>
      )}
    </li>
  );
}

function ReferralsPanel({
  setError,
  busy,
  setBusy,
}: {
  setError: (v: string) => void;
  busy: boolean;
  setBusy: (v: boolean) => void;
}) {
  const [dash, setDash] = useState<ReferralDashboard | null>(null);
  const [rows, setRows] = useState([
    { kitchen_name: "", contact_name: "", contact_phone: "", contact_email: "", city: "", notes: "" },
    { kitchen_name: "", contact_name: "", contact_phone: "", contact_email: "", city: "", notes: "" },
  ]);

  const reload = useCallback(async () => {
    try {
      setDash(await fetchCustomerReferrals());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load referrals");
    }
  }, [setError]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = rows
        .filter((r) => r.contact_phone.trim() && r.kitchen_name.trim())
        .map((r) => ({
          kitchen_name: r.kitchen_name.trim(),
          contact_name: r.contact_name || undefined,
          contact_phone: r.contact_phone.trim(),
          contact_email: r.contact_email || undefined,
          city: r.city || undefined,
          notes: r.notes || undefined,
        }));
      if (payload.length === 1) {
        await submitCustomerKitchenReferral(payload[0]);
      } else {
        const result = await bulkCustomerKitchenReferrals(payload);
        if (result.rejected) {
          setError(`${result.accepted} accepted, ${result.rejected} rejected`);
        }
      }
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  };

  const downloadTemplate = async () => {
    const token = getCustomerToken();
    const res = await fetch(customerReferralTemplateUrl(), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "kitchcu-refer-kitchens-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="glass customer-dash__card">
      <h2>Refer a kitchen</h2>
      <p>
        Share kitchen details with KitchCu. When that kitchen onboards, you earn subscription credit
        (admin-configurable, default ₹10).
      </p>
      {dash && (
        <div className="customer-dash__grid">
          <div className="customer-dash__stat">
            <strong>{inr(dash.credit.balance_inr)}</strong>
            <span>Available credit</span>
          </div>
          <div className="customer-dash__stat">
            <strong>{inr(dash.credit.lifetime_earned_inr)}</strong>
            <span>Lifetime earned</span>
          </div>
          <div className="customer-dash__stat">
            <strong>{inr(dash.estimated_subscription_savings_inr)}</strong>
            <span>Ready for subscription savings</span>
          </div>
          <div className="customer-dash__stat">
            <strong>{inr(dash.credit.reward_per_conversion_inr)}</strong>
            <span>Per kitchen onboard</span>
          </div>
        </div>
      )}
      <p className="muted">{dash?.credit.subscription_credit_note}</p>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", margin: "1rem 0" }}>
        <button type="button" className="btn btn--ghost btn--sm" onClick={downloadTemplate}>
          Download Excel template
        </button>
        <label className="btn btn--ghost btn--sm">
          Upload CSV
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setBusy(true);
              try {
                await uploadCustomerReferralCsv(file);
                await reload();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Upload failed");
              } finally {
                setBusy(false);
              }
            }}
          />
        </label>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() =>
            setRows((r) => [
              ...r,
              {
                kitchen_name: "",
                contact_name: "",
                contact_phone: "",
                contact_email: "",
                city: "",
                notes: "",
              },
            ])
          }
        >
          Add row
        </button>
      </div>
      <div className="owner-table-wrap">
        <table className="owner-table">
          <thead>
            <tr>
              <th>Kitchen</th>
              <th>Contact</th>
              <th>Phone</th>
              <th>Email</th>
              <th>City</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {(
                  [
                    "kitchen_name",
                    "contact_name",
                    "contact_phone",
                    "contact_email",
                    "city",
                    "notes",
                  ] as const
                ).map((key) => (
                  <td key={key}>
                    <input
                      className="owner-input"
                      value={row[key]}
                      onChange={(e) =>
                        setRows((prev) =>
                          prev.map((r, idx) => (idx === i ? { ...r, [key]: e.target.value } : r)),
                        )
                      }
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button type="button" className="btn btn--primary" disabled={busy} onClick={submit}>
        {busy ? "Saving…" : "Submit kitchen referrals"}
      </button>
      {dash && dash.leads.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.5rem" }}>Your referrals</h3>
          <ul className="customer-dash__tips">
            {dash.leads.map((L) => (
              <li key={L.id}>
                <strong>{L.kitchen_name || "Kitchen"}</strong>
                <span>
                  {L.status}
                  {L.reward_inr != null ? ` · ${inr(L.reward_inr)}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function SavingsPanel({ dash }: { dash: CustomerDashboard }) {
  return (
    <section className="glass customer-dash__card">
      <h2>Savings vs typical restaurant pricing</h2>
      <p>
        For each dish we estimate restaurant plate pricing (~1.4× kitchen price + ₹40) unless a
        kitchen sets an explicit benchmark. Your mix shows home kitchens keep money with you — without
        aggregator commission.
      </p>
      <div className="customer-dash__grid">
        <div className="customer-dash__stat">
          <strong>{inr(dash.savings.kitchcu_spend)}</strong>
          <span>Spent on kitchCU</span>
        </div>
        <div className="customer-dash__stat">
          <strong>{inr(dash.savings.restaurant_equivalent_spend)}</strong>
          <span>Restaurant equivalent</span>
        </div>
        <div className="customer-dash__stat">
          <strong>{inr(dash.savings.total_saved)}</strong>
          <span>Estimated saved</span>
        </div>
      </div>
      <ul className="customer-dash__tips">
        {dash.savings.by_dish.map((d) => (
          <li key={d.dish_name}>
            <strong>{d.dish_name}</strong>
            <span>Saved ~{inr(d.saved)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HealthPanel({ dash }: { dash: CustomerDashboard }) {
  return (
    <section className="glass customer-dash__card">
      <h2>Health chart — home kitchen vs restaurant style</h2>
      <p>{dash.health.note}</p>
      <div className="customer-dash__bars">
        <div>
          <span>Veg {dash.health.veg_share_pct}%</span>
          <div className="customer-dash__bar">
            <i style={{ width: `${dash.health.veg_share_pct}%` }} />
          </div>
        </div>
        <div>
          <span>Non-veg {dash.health.non_veg_share_pct}%</span>
          <div className="customer-dash__bar">
            <i style={{ width: `${dash.health.non_veg_share_pct}%` }} />
          </div>
        </div>
        <div>
          <span>Vegan {dash.health.vegan_share_pct}%</span>
          <div className="customer-dash__bar">
            <i style={{ width: `${dash.health.vegan_share_pct}%` }} />
          </div>
        </div>
        <div>
          <span>Home freshness {dash.health.home_freshness_score}</span>
          <div className="customer-dash__bar customer-dash__bar--good">
            <i style={{ width: `${dash.health.home_freshness_score}%` }} />
          </div>
        </div>
        <div>
          <span>Restaurant processed {dash.health.restaurant_processed_score}</span>
          <div className="customer-dash__bar customer-dash__bar--warn">
            <i style={{ width: `${dash.health.restaurant_processed_score}%` }} />
          </div>
        </div>
      </div>
      <h3>Suggestions after meals</h3>
      <ul className="customer-dash__tips">
        {dash.tips.map((tip, i) => (
          <li key={i}>
            <strong>
              {tip.walk_minutes} min walk · {tip.water_ml} ml water
              {tip.after_dish ? ` · ${tip.after_dish}` : ""}
            </strong>
            <span>{tip.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function RefundsPanel({ refunds }: { refunds: CustomerRefund[] }) {
  return (
    <section className="glass customer-dash__card">
      <h2>Refunds received</h2>
      <p>
        Gateway reverses and direct UPI/bank transfers (remark = order id). Manage payout details under{" "}
        <Link to="/account">Payout details</Link>.
      </p>
      {refunds.length === 0 ? (
        <p>No refunds yet.</p>
      ) : (
        <ul className="customer-dash__tips">
          {refunds.map((r) => (
            <li key={r.id}>
              <strong>
                {inr(r.amount)} · {r.kind} · {r.status}
              </strong>
              <span>
                {r.channel} · remark {r.transfer_remark} · {formatWhen(r.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ComplaintsPanel({
  tickets,
  busy,
  setBusy,
  setError,
  onRefresh,
}: {
  tickets: CustomerTicket[];
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string) => void;
  onRefresh: () => Promise<void>;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [orderCode, setOrderCode] = useState("");
  const [category, setCategory] = useState("complaint");

  useEffect(() => {
    const onIssue = (e: Event) => {
      const code = (e as CustomEvent<string>).detail;
      if (code) setOrderCode(code);
    };
    window.addEventListener("kitchcu-raise-issue", onIssue);
    return () => window.removeEventListener("kitchcu-raise-issue", onIssue);
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await createMyTicket({
        category,
        subject,
        description,
        order_code: orderCode || undefined,
      });
      setSubject("");
      setDescription("");
      setOrderCode("");
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not raise complaint");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="customer-dash__split">
      <form className="glass customer-dash__card" onSubmit={submit}>
        <h2>Raise a complaint</h2>
        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="complaint">Complaint</option>
            <option value="order_issue">Order issue</option>
            <option value="quality">Quality</option>
            <option value="delivery">Delivery</option>
            <option value="billing">Billing / refund</option>
          </select>
        </label>
        <label>
          Subject
          <input value={subject} onChange={(e) => setSubject(e.target.value)} required minLength={3} />
        </label>
        <label>
          Order code (optional)
          <input value={orderCode} onChange={(e) => setOrderCode(e.target.value)} placeholder="CKPNQ001-BILL-…" />
        </label>
        <label>
          Details
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            minLength={10}
            rows={4}
          />
        </label>
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? "Submitting…" : "Submit complaint"}
        </button>
      </form>
      <section className="glass customer-dash__card">
        <h2>Complaint history</h2>
        {tickets.length === 0 ? (
          <p>No complaints yet.</p>
        ) : (
          <ul className="customer-dash__tips">
            {tickets.map((t) => (
              <li key={t.id}>
                <strong>
                  {t.ticket_number} · {t.status}
                </strong>
                <span>
                  {t.subject}
                  {t.order_code ? ` · ${t.order_code}` : ""} · {formatWhen(t.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function AddressesPanel({
  addresses,
  busy,
  setBusy,
  setError,
  onRefresh,
}: {
  addresses: CustomerAddress[];
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string) => void;
  onRefresh: () => Promise<void>;
}) {
  const [label, setLabel] = useState("Home");
  const [line, setLine] = useState("");
  const [city, setCity] = useState("Pune");
  const [state, setState] = useState("Maharashtra");
  const [pincode, setPincode] = useState("");
  const [lat, setLat] = useState<number | null>(18.5204);
  const [lng, setLng] = useState<number | null>(73.8567);

  const pinHere = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not available");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
      },
      () => setError("Could not read location — allow location permission"),
    );
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await saveAddress({
        label,
        address_line: line,
        city,
        state,
        pincode: pincode || null,
        landmark: null,
        latitude: lat,
        longitude: lng,
        is_default: addresses.length === 0,
      });
      setLine("");
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save address");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="customer-dash__split">
      <form className="glass customer-dash__card" onSubmit={submit}>
        <h2>Add address with map pin</h2>
        <label>
          Label
          <input value={label} onChange={(e) => setLabel(e.target.value)} required />
        </label>
        <label>
          Address line
          <input value={line} onChange={(e) => setLine(e.target.value)} required />
        </label>
        <label>
          City
          <input value={city} onChange={(e) => setCity(e.target.value)} required />
        </label>
        <label>
          State
          <input value={state} onChange={(e) => setState(e.target.value)} />
        </label>
        <label>
          Pincode
          <input value={pincode} onChange={(e) => setPincode(e.target.value)} />
        </label>
        <div className="customer-dash__pin-actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={pinHere}>
            Use my location
          </button>
          <span>
            Pin: {lat?.toFixed(5)}, {lng?.toFixed(5)}
          </span>
        </div>
        {lat != null && lng != null && (
          <iframe
            title="Address map pin"
            className="customer-dash__map"
            src={openStreetMapEmbedUrl(lat, lng)}
          />
        )}
        <button type="submit" className="btn btn--primary" disabled={busy}>
          Save address
        </button>
      </form>
      <section className="glass customer-dash__card">
        <h2>Saved addresses</h2>
        {addresses.length === 0 ? (
          <p>No saved addresses yet.</p>
        ) : (
          <ul className="customer-dash__tips">
            {addresses.map((a) => (
              <li key={a.id}>
                <strong>
                  {a.label}
                  {a.is_default ? " · default" : ""}
                </strong>
                <span>
                  {a.address_line}, {a.city}
                  {a.pincode ? ` · ${a.pincode}` : ""}
                  {a.latitude != null && a.longitude != null
                    ? ` · ${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}`
                    : ""}
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await deleteAddress(a.id);
                      await onRefresh();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Delete failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function AccountPanel({
  profile,
  setProfile,
  busy,
  setBusy,
  setError,
}: {
  profile: CustomerProfile;
  setProfile: (p: CustomerProfile) => void;
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string) => void;
}) {
  const [name, setName] = useState(profile.name);
  const [email, setEmail] = useState(profile.email ?? "");
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const next = await updateMyProfile({ name, email: email || null });
      setProfile(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const sendOtp = async () => {
    if (!profile.phone) {
      setError("Link a WhatsApp phone first to set a password");
      return;
    }
    setBusy(true);
    try {
      await requestCustomerWhatsAppOtp(profile.phone);
      setOtpSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OTP failed");
    } finally {
      setBusy(false);
    }
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const next = await changeMyPassword({
        new_password: password,
        current_password: currentPassword || undefined,
        otp: otp || undefined,
      });
      setProfile(next);
      setPassword("");
      setCurrentPassword("");
      setOtp("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="customer-dash__split">
      <form className="glass customer-dash__card" onSubmit={saveProfile}>
        <h2>Change details</h2>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <p className="auth-card__hint">Phone: {profile.phone || "not linked — use WhatsApp login"}</p>
        <button type="submit" className="btn btn--primary" disabled={busy}>
          Save profile
        </button>
      </form>
      <form className="glass customer-dash__card" onSubmit={savePassword}>
        <h2>Change password</h2>
        <p className="auth-card__hint">
          Customers primarily sign in with WhatsApp OTP / social login. An optional password can be
          added for convenience — first set requires WhatsApp OTP.
        </p>
        {profile.has_password && (
          <label>
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </label>
        )}
        <label>
          New password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>
        <label>
          WhatsApp OTP {otpSent ? "(sent)" : ""}
          <input value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="123456" maxLength={6} />
        </label>
        <div className="customer-dash__pin-actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={sendOtp} disabled={busy}>
            Send OTP
          </button>
          <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>
            Update password
          </button>
        </div>
      </form>
    </div>
  );
}
