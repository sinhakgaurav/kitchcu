import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  fetchCustomerProfile,
  getCustomerToken,
  requestCustomerWhatsAppOtp,
  type CustomerProfile,
} from "../../shared/customerApi";
import {
  cancelMySubscription,
  changeMyPassword,
  createMyTicket,
  deleteAddress,
  fetchCustomerDashboard,
  fetchMyAddresses,
  fetchMyRefunds,
  fetchMySubscriptions,
  fetchMyTickets,
  saveAddress,
  updateMyNotificationPrefs,
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
import type { CustomerKitchenSubscription } from "../../shared/api";
import { useCustomerAuth } from "../../shared/customerAuth";
import { addItemsToCart, kitchenFromOrderCode } from "../../shared/customerCart";
import { PhoneField } from "../../components/PhoneField";
import {
  firstError,
  otpInputValue,
  pincodeInputValue,
  toE164,
  validateEmail,
  validateNationalPhone,
  validateOtp,
  validatePersonName,
  validatePincode,
  validateText,
} from "../../shared/validation";

type Tab =
  | "overview"
  | "orders"
  | "plans"
  | "savings"
  | "referrals"
  | "health"
  | "refunds"
  | "complaints"
  | "addresses"
  | "account";

const PRIMARY_TABS: { id: Tab; labelKey: string }[] = [
  { id: "overview", labelKey: "customer.dashboard.tabOverview" },
  { id: "orders", labelKey: "customer.dashboard.tabOrders" },
  { id: "addresses", labelKey: "customer.dashboard.tabAddresses" },
  { id: "account", labelKey: "customer.dashboard.tabAccount" },
];

const MORE_TABS: { id: Tab; labelKey: string }[] = [
  { id: "complaints", labelKey: "customer.dashboard.tabComplaints" },
  { id: "plans", labelKey: "customer.dashboard.tabPlans" },
  { id: "savings", labelKey: "customer.dashboard.tabSavings" },
  { id: "referrals", labelKey: "customer.dashboard.tabReferrals" },
  { id: "health", labelKey: "customer.dashboard.tabHealth" },
  { id: "refunds", labelKey: "customer.dashboard.tabRefunds" },
];

const ALL_TABS: Tab[] = [
  "overview",
  "orders",
  "plans",
  "savings",
  "referrals",
  "health",
  "refunds",
  "complaints",
  "addresses",
  "account",
];

function isTab(value: string | null): value is Tab {
  return Boolean(value && ALL_TABS.includes(value as Tab));
}

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => {
    const requested = searchParams.get("tab");
    return isTab(requested) ? requested : "overview";
  });
  const [dash, setDash] = useState<CustomerDashboard | null>(null);
  const [diet, setDiet] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [liveOnly, setLiveOnly] = useState(false);
  const [refunds, setRefunds] = useState<CustomerRefund[]>([]);
  const [tickets, setTickets] = useState<CustomerTicket[]>([]);
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [subs, setSubs] = useState<CustomerKitchenSubscription[]>([]);
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
      const [d, r, t, a, p, s] = await Promise.all([
        fetchCustomerDashboard({
          diet: diet || undefined,
          cuisine: cuisine || undefined,
          live_media_only: liveOnly || undefined,
        }),
        fetchMyRefunds().catch(() => []),
        fetchMyTickets().catch(() => ({ tickets: [], total: 0 })),
        fetchMyAddresses().catch(() => []),
        fetchCustomerProfile().catch(() => null),
        fetchMySubscriptions().catch(() => ({ subscriptions: [], total: 0 })),
      ]);
      setDash(d);
      setRefunds(r);
      setTickets(t.tickets);
      setAddresses(a);
      setProfile(p);
      setSubs(s.subscriptions);
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

  useEffect(() => {
    const requested = searchParams.get("tab");
    if (isTab(requested) && requested !== tab) setTab(requested);
  }, [searchParams, tab]);

  useEffect(() => {
    if (tab !== "account") return;
    if (window.location.hash !== "#notifications") return;
    document.getElementById("notifications")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [tab, loading]);

  const selectTab = (next: Tab) => {
    setTab(next);
    setSearchParams(
      (prev) => {
        const nextParams = new URLSearchParams(prev);
        if (next === "overview") nextParams.delete("tab");
        else nextParams.set("tab", next);
        return nextParams;
      },
      { replace: true },
    );
  };

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
          <p>{t("customer.dashboard.subtitle")}</p>
        </div>
        <div className="customer-dash__hero-actions">
          <Link to="/#near-you" className="btn btn--primary btn--sm">
            {t("customer.dashboard.findFood")}
          </Link>
          <Link to="/account" className="btn btn--ghost btn--sm">
            {t("customer.dashboard.refundDetails")}
          </Link>
        </div>
      </header>

      <nav className="customer-dash__tabs" aria-label="Dashboard sections">
        {PRIMARY_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "active" : ""}
            onClick={() => selectTab(item.id)}
          >
            {t(item.labelKey)}
          </button>
        ))}
        <label className="customer-dash__more">
          <span className="visually-hidden">{t("customer.dashboard.moreTabs")}</span>
          <select
            value={MORE_TABS.some((m) => m.id === tab) ? tab : ""}
            onChange={(e) => {
              const next = e.target.value as Tab;
              if (next) selectTab(next);
            }}
            aria-label={t("customer.dashboard.moreTabs")}
          >
            <option value="">{t("customer.dashboard.moreTabs")}</option>
            {MORE_TABS.map((item) => (
              <option key={item.id} value={item.id}>
                {t(item.labelKey)}
              </option>
            ))}
          </select>
        </label>
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
      {!loading && tab === "plans" && (
        <PlansPanel
          subs={subs}
          busy={busy}
          setBusy={setBusy}
          setError={setError}
          onRefresh={async () => {
            const s = await fetchMySubscriptions();
            setSubs(s.subscriptions);
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
        <span>Your orders</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("savings")}>
        <strong>{inr(dash.savings.total_saved)}</strong>
        <span>Saved vs eating out</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("health")}>
        <strong>{dash.health.home_freshness_score}</strong>
        <span>Home-cooked score</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("refunds")}>
        <strong>{completedRefunds.length}</strong>
        <span>Refunds received</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("complaints")}>
        <strong>{openTickets}</strong>
        <span>Open help requests</span>
      </button>
      <section className="glass customer-dash__card customer-dash__span2">
        <h2>Tips after your meals</h2>
        {dash.tips.length === 0 ? (
          <p className="customer-dash__empty-hint">
            Order a few home meals — light walk and water tips will show up here.
          </p>
        ) : (
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
        )}
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
  const navigate = useNavigate();
  const media = useMemo(
    () => row.items.flatMap((i) => i.media.filter((m) => m.url)).slice(0, 6),
    [row.items],
  );
  const onRepeat = () => {
    if (!row.items.length || row.order.status === "cancelled") return;
    addItemsToCart(
      kitchenFromOrderCode(row.order.kitchen_id, row.order.order_code),
      row.items.map((item) => ({
        dish_id: item.dish_id,
        dish_name: item.dish_name,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
    );
    navigate("/checkout");
  };
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
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={row.order.status === "cancelled" || row.items.length === 0}
            onClick={onRepeat}
          >
            Repeat
          </button>
          {row.can_rate && (
            <Link className="btn btn--ghost btn--sm" to={`/orders/${row.order.id}/rate`}>
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

type ReferralRow = {
  kitchen_name: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  city: string;
  notes: string;
};
type ReferralRowErrors = Partial<Record<keyof ReferralRow, string>>;

const REFERRAL_FIELDS = [
  "kitchen_name",
  "contact_name",
  "contact_phone",
  "contact_email",
  "city",
  "notes",
] as const;

const emptyReferralRow = (): ReferralRow => ({
  kitchen_name: "",
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  city: "",
  notes: "",
});

const isBlankReferralRow = (row: ReferralRow) =>
  REFERRAL_FIELDS.every((key) => !row[key].trim());

const validateReferralRow = (row: ReferralRow): ReferralRowErrors => ({
  kitchen_name: validateText(row.kitchen_name, "the kitchen name", { max: 120 }) ?? undefined,
  contact_name: validatePersonName(row.contact_name, { required: false }) ?? undefined,
  contact_phone: validateNationalPhone(row.contact_phone) ?? undefined,
  contact_email: validateEmail(row.contact_email, { required: false }) ?? undefined,
  city: validateText(row.city, "a city", { required: false, max: 80 }) ?? undefined,
  notes: validateText(row.notes, "a note", { required: false, max: 500 }) ?? undefined,
});

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
  const [rows, setRows] = useState<ReferralRow[]>([emptyReferralRow(), emptyReferralRow()]);
  const [rowErrors, setRowErrors] = useState<ReferralRowErrors[]>([]);

  const updateRow = (index: number, key: keyof ReferralRow, value: string) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [key]: value } : r)));
    setRowErrors((prev) => prev.map((e, i) => (i === index ? { ...e, [key]: undefined } : e)));
  };

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
    const filled = rows.filter((r) => !isBlankReferralRow(r));
    if (filled.length === 0) {
      setError("Add at least one kitchen with a mobile number");
      return;
    }
    const nextRowErrors = rows.map((r) => (isBlankReferralRow(r) ? {} : validateReferralRow(r)));
    setRowErrors(nextRowErrors);
    const firstMessage = nextRowErrors.map(firstError).find(Boolean);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = filled.map((r) => ({
        kitchen_name: r.kitchen_name.trim(),
        contact_name: r.contact_name.trim() || undefined,
        contact_phone: toE164(r.contact_phone),
        contact_email: r.contact_email.trim() || undefined,
        city: r.city.trim() || undefined,
        notes: r.notes.trim() || undefined,
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
          onClick={() => setRows((r) => [...r, emptyReferralRow()])}
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
                {REFERRAL_FIELDS.map((key) => (
                  <td key={key}>
                    {key === "contact_phone" ? (
                      <PhoneField
                        className="phone-field--bare"
                        label="Phone"
                        value={row.contact_phone}
                        onChange={(national) => updateRow(i, key, national)}
                        error={rowErrors[i]?.contact_phone}
                      />
                    ) : (
                      <>
                        <input
                          className={
                            rowErrors[i]?.[key] ? "owner-input input-invalid" : "owner-input"
                          }
                          value={row[key]}
                          onChange={(e) => updateRow(i, key, e.target.value)}
                          aria-invalid={Boolean(rowErrors[i]?.[key])}
                        />
                        {rowErrors[i]?.[key] ? (
                          <span className="field-error">{rowErrors[i][key]}</span>
                        ) : null}
                      </>
                    )}
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

function PlansPanel({
  subs,
  busy,
  setBusy,
  setError,
  onRefresh,
}: {
  subs: CustomerKitchenSubscription[];
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string) => void;
  onRefresh: () => Promise<void>;
}) {
  const cancel = async (id: string) => {
    setBusy(true);
    setError("");
    try {
      await cancelMySubscription(id);
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel plan");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass customer-dash__card">
      <h2>My thali / tiffin plans</h2>
      <p className="owner-muted">
        Request plans from a kitchen menu. The kitchen accepts or denies before billing starts.
      </p>
      {subs.length === 0 ? (
        <p>
          No plan requests yet.{" "}
          <Link to="/#near-you">Find a kitchen</Link> and tap Request subscribe on their monthly plan.
        </p>
      ) : (
        <ul className="customer-dash__tips">
          {subs.map((s) => (
            <li key={s.id}>
              <strong>{s.plan_name || "Plan"}</strong>
              <span>
                {s.status}
                {s.price_monthly != null ? ` · ${inr(s.price_monthly)}/mo` : ""}
                {s.plan_type ? ` · ${s.plan_type}` : ""}
              </span>
              {(s.status === "pending" || s.status === "active" || s.status === "paused") && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={() => cancel(s.id)}
                >
                  Cancel
                </button>
              )}
            </li>
          ))}
        </ul>
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
  const [fieldErrors, setFieldErrors] = useState<{
    label?: string;
    line?: string;
    city?: string;
    pincode?: string;
  }>({});

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
    const nextErrors = {
      label: validateText(label, "a label", { max: 40 }) ?? undefined,
      line: validateText(line, "the address", { min: 5, max: 240 }) ?? undefined,
      city: validateText(city, "a city", { max: 80 }) ?? undefined,
      pincode: validatePincode(pincode, { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
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
          <input
            value={label}
            onChange={(e) => {
              setLabel(e.target.value);
              setFieldErrors((f) => ({ ...f, label: undefined }));
            }}
            required
            maxLength={40}
            className={fieldErrors.label ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.label)}
          />
          {fieldErrors.label ? <span className="field-error">{fieldErrors.label}</span> : null}
        </label>
        <label>
          Address line
          <input
            value={line}
            onChange={(e) => {
              setLine(e.target.value);
              setFieldErrors((f) => ({ ...f, line: undefined }));
            }}
            required
            maxLength={240}
            className={fieldErrors.line ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.line)}
          />
          {fieldErrors.line ? <span className="field-error">{fieldErrors.line}</span> : null}
        </label>
        <label>
          City
          <input
            value={city}
            onChange={(e) => {
              setCity(e.target.value);
              setFieldErrors((f) => ({ ...f, city: undefined }));
            }}
            required
            maxLength={80}
            className={fieldErrors.city ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.city)}
          />
          {fieldErrors.city ? <span className="field-error">{fieldErrors.city}</span> : null}
        </label>
        <label>
          State
          <input value={state} onChange={(e) => setState(e.target.value)} />
        </label>
        <label>
          Pincode
          <input
            value={pincode}
            onChange={(e) => {
              setPincode(pincodeInputValue(e.target.value));
              setFieldErrors((f) => ({ ...f, pincode: undefined }));
            }}
            inputMode="numeric"
            maxLength={6}
            placeholder="411001"
            className={fieldErrors.pincode ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.pincode)}
          />
          {fieldErrors.pincode ? <span className="field-error">{fieldErrors.pincode}</span> : null}
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
  const { logout } = useCustomerAuth();
  const navigate = useNavigate();
  const [name, setName] = useState(profile.name);
  const [email, setEmail] = useState(profile.email ?? "");
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    email?: string;
    otp?: string;
  }>({});

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    const nextErrors = {
      name: validatePersonName(name) ?? undefined,
      email: validateEmail(email, { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
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
    // The OTP is only required on the first password set; skip the check when blank.
    const otpMessage = otp ? validateOtp(otp) : null;
    setFieldErrors((f) => ({ ...f, otp: otpMessage ?? undefined }));
    if (otpMessage) {
      setError(otpMessage);
      return;
    }
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

  const saveNotifications = async (patch: {
    notify_order_updates?: boolean;
    notify_offers?: boolean;
    notify_channel?: string;
  }) => {
    setBusy(true);
    setError("");
    try {
      setProfile(await updateMyNotificationPrefs(patch));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save notification settings");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="customer-dash__split">
      <form className="glass customer-dash__card" onSubmit={saveProfile}>
        <h2>My profile</h2>
        <label>
          Name
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setFieldErrors((f) => ({ ...f, name: undefined }));
            }}
            required
            className={fieldErrors.name ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.name)}
          />
          {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
        </label>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setFieldErrors((f) => ({ ...f, email: undefined }));
            }}
            className={fieldErrors.email ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.email)}
          />
          {fieldErrors.email ? <span className="field-error">{fieldErrors.email}</span> : null}
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
          <input
            value={otp}
            onChange={(e) => {
              setOtp(otpInputValue(e.target.value));
              setFieldErrors((f) => ({ ...f, otp: undefined }));
            }}
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="123456"
            maxLength={6}
            className={fieldErrors.otp ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.otp)}
          />
          {fieldErrors.otp ? <span className="field-error">{fieldErrors.otp}</span> : null}
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

      <section id="notifications" className="glass customer-dash__card">
        <h2>Notifications</h2>
        <p className="auth-card__hint">
          Choose what reaches you. Order updates keep you posted from kitchen to doorstep; offers
          are the kitchen&apos;s daily menu and deals.
        </p>
        <label className="customer-dash__toggle">
          <input
            type="checkbox"
            checked={profile.notify_order_updates}
            disabled={busy || profile.notify_channel === "none"}
            onChange={(e) => saveNotifications({ notify_order_updates: e.target.checked })}
          />
          <span>Order updates</span>
        </label>
        <label className="customer-dash__toggle">
          <input
            type="checkbox"
            checked={profile.notify_offers}
            disabled={busy || profile.notify_channel === "none"}
            onChange={(e) => saveNotifications({ notify_offers: e.target.checked })}
          />
          <span>Offers and daily menus</span>
        </label>
        <label>
          Send them on
          <select
            value={profile.notify_channel}
            disabled={busy}
            onChange={(e) => saveNotifications({ notify_channel: e.target.value })}
          >
            <option value="whatsapp">WhatsApp</option>
            <option value="none">Nothing — mute all</option>
          </select>
        </label>
      </section>

      <section className="glass customer-dash__card">
        <h2>Sign out</h2>
        <p className="auth-card__hint">
          Signs you out on this device. Your orders, addresses, and saved kitchens stay on your
          account.
        </p>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
        >
          Log out
        </button>
      </section>
    </div>
  );
}
