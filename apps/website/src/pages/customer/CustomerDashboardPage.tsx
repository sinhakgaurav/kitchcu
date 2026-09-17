import {
  type Dispatch,
  type FormEvent,
  type RefObject,
  type SetStateAction,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  fetchCustomerProfile,
  fetchCustomerDietProfile,
  getCustomerToken,
  requestCustomerWhatsAppOtp,
  updateCustomerDietFilter,
  uploadCustomerCheckupReport,
  type CustomerDietProfile,
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
import { fetchDishesHealth } from "../../shared/publicApi";
import { aggregateOrderedHealth, DishHealthBlock } from "../../components/DishHealthBlock";
import type { DishHealthSnapshot } from "../../shared/api";
import { CITIES_PRESENCE, cityCenterByName, liveCities } from "../../data/citiesPresence";
import { openStreetMapEmbedUrl } from "../../lib/locationMaps";
import { useCustomerDelivery } from "../../shared/customerDelivery";
import { formatAddressLine } from "../../shared/customerDeliveryLocation";
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
import { CustomerAvatar } from "../../components/CustomerAvatar";
import { CustomerProfilePhotos } from "../../components/CustomerProfilePhotos";
import { PhoneField } from "../../components/PhoneField";
import {
  customerStatusTone,
  humanStatus,
  maskCustomerPhone,
} from "../../shared/customerUi";
import {
  firstError,
  otpInputValue,
  parsePhoneInput,
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
  const { loading: authLoading } = useCustomerAuth();
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
  const [plateHealth, setPlateHealth] = useState<DishHealthSnapshot | null>(null);
  const [dishHealth, setDishHealth] = useState<Record<string, DishHealthSnapshot>>({});
  const [healthLoading, setHealthLoading] = useState(false);

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

  useEffect(() => {
    if (!dash?.orders.length) {
      setPlateHealth(null);
      setDishHealth({});
      setHealthLoading(false);
      return;
    }
    const qty: Record<string, number> = {};
    const ids: string[] = [];
    for (const row of dash.orders) {
      for (const item of row.items) {
        qty[item.dish_id] = (qty[item.dish_id] ?? 0) + item.quantity;
        ids.push(item.dish_id);
      }
    }
    let cancelled = false;
    setHealthLoading(true);
    void fetchDishesHealth(ids)
      .then((res) => {
        if (cancelled) return;
        const map: Record<string, DishHealthSnapshot> = {};
        for (const snap of res.dishes) {
          if (snap.dish_id) map[String(snap.dish_id)] = snap;
        }
        setDishHealth(map);
        setPlateHealth(aggregateOrderedHealth(res.dishes, qty));
      })
      .catch(() => {
        if (cancelled) return;
        setDishHealth({});
        setPlateHealth(null);
      })
      .finally(() => {
        if (!cancelled) setHealthLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dash]);

  const selectTab = (next: Tab) => {
    setTab(next);
    setSearchParams(
      (prev) => {
        const nextParams = new URLSearchParams(prev);
        if (next === "overview") nextParams.delete("tab");
        else nextParams.set("tab", next);
        if (next !== "addresses") nextParams.delete("edit");
        return nextParams;
      },
      { replace: true },
    );
  };

  const setAddressEditId = useCallback(
    (id: string | null) => {
      setSearchParams(
        (prev) => {
          const nextParams = new URLSearchParams(prev);
          nextParams.set("tab", "addresses");
          if (id) nextParams.set("edit", id);
          else nextParams.delete("edit");
          return nextParams;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  if (authLoading) {
    return <p className="app-loading">Checking sign-in…</p>;
  }
  if (!token) {
    return <Navigate to="/login?next=/dashboard" replace />;
  }

  return (
    <div className="container customer-dash">
      <header className="customer-space__hero">
        <div className="customer-space__identity">
          <CustomerAvatar
            name={profile?.name}
            src={profile?.avatar_url}
            size="lg"
            live={Boolean(profile?.has_live_photo)}
          />
          <div>
            <p className="customer-dash__eyebrow">{t("customer.dashboard.spaceEyebrow")}</p>
            <h1>
              {profile?.name
                ? t("customer.dashboard.greeting", { name: profile.name.split(" ")[0] })
                : t("customer.dashboard.title")}
            </h1>
            <p className="customer-space__meta">
              {profile?.phone
                ? maskCustomerPhone(profile.phone)
                : t("customer.dashboard.phoneUnlinked")}
              {profile?.email ? ` · ${profile.email}` : ""}
            </p>
          </div>
        </div>
        <div className="customer-dash__hero-actions">
          <Link to="/#near-you" className="btn btn--primary btn--sm">
            {t("customer.dashboard.findFood")}
          </Link>
          {tab === "account" ? (
            <Link to="/account" className="btn btn--ghost btn--sm">
              {t("customer.dashboard.payoutShortcut")}
            </Link>
          ) : (
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => selectTab("account")}>
              {t("customer.dashboard.editProfile")}
            </button>
          )}
        </div>
      </header>

      <div className="customer-dash__tab-rail">
        <nav className="customer-dash__tabs" aria-label={t("customer.dashboard.title")}>
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
        </nav>
        <nav className="customer-dash__tabs customer-dash__tabs--more" aria-label={t("customer.dashboard.moreSections")}>
          {MORE_TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? "active" : ""}
              onClick={() => selectTab(item.id)}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </nav>
      </div>

      {error && <div className="auth-card__error">{error}</div>}
      {loading && <p className="app-loading">Loading dashboard…</p>}

      {!loading && dash && tab === "overview" && (
        <OverviewPanel
          dash={dash}
          refunds={refunds}
          tickets={tickets}
          plateHealth={plateHealth}
          onGo={selectTab}
        />
      )}
      {!loading && dash && tab === "orders" && (
        <OrdersPanel
          dash={dash}
          diet={diet}
          cuisine={cuisine}
          liveOnly={liveOnly}
          dishHealth={dishHealth}
          setDiet={setDiet}
          setCuisine={setCuisine}
          setLiveOnly={setLiveOnly}
          onRaiseIssue={(code) => {
            selectTab("complaints");
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
      {!loading && dash && tab === "health" && (
        <HealthPanel dash={dash} plateHealth={plateHealth} healthLoading={healthLoading} />
      )}
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
          requestedEditId={searchParams.get("edit")}
          onEditIdChange={setAddressEditId}
          onRefresh={async () => {
            const list = await fetchMyAddresses();
            setAddresses(list);
          }}
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
  plateHealth,
  onGo,
}: {
  dash: CustomerDashboard;
  refunds: CustomerRefund[];
  tickets: CustomerTicket[];
  plateHealth: DishHealthSnapshot | null;
  onGo: (t: Tab) => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const openTickets = tickets.filter((row) => !["resolved", "closed"].includes(row.status)).length;
  const completedRefunds = refunds.filter((r) => r.status === "completed");
  const latest = dash.orders[0];
  return (
    <div className="customer-dash__grid">
      {latest ? (
        <section className="glass customer-dash__card customer-dash__span2 customer-dash__resume">
          <p className="customer-dash__eyebrow">{t("customer.dashboard.resumeTitle")}</p>
          <div className="customer-dash__resume-row">
            <div>
              <strong>{latest.order.order_code}</strong>
              <span>
                {formatWhen(latest.order.created_at)} · {inr(latest.order.total)}
              </span>
              <span className={`customer-status customer-status--${customerStatusTone(latest.order.status)}`}>
                {humanStatus(latest.order.status)}
              </span>
            </div>
            <div className="customer-dash__order-actions">
              {latest.tracking_token ? (
                <Link className="btn btn--ghost btn--sm" to={`/t/${latest.tracking_token}`}>
                  {t("customer.orders.track")}
                </Link>
              ) : null}
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={latest.order.status === "cancelled" || latest.items.length === 0}
                onClick={() => {
                  if (!latest.items.length || latest.order.status === "cancelled") return;
                  addItemsToCart(
                    kitchenFromOrderCode(latest.order.kitchen_id, latest.order.order_code),
                    latest.items.map((item) => ({
                      dish_id: item.dish_id,
                      dish_name: item.dish_name,
                      quantity: item.quantity,
                      unit_price: item.unit_price,
                    })),
                  );
                  navigate("/checkout");
                }}
              >
                {t("customer.orders.repeat")}
              </button>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => onGo("orders")}>
                {t("customer.dashboard.tabOrders")}
              </button>
            </div>
          </div>
        </section>
      ) : (
        <section className="glass customer-dash__card customer-dash__span2 empty-state">
          <p className="empty-state__title">{t("customer.orders.empty")}</p>
          <p className="empty-state__hint">{t("customer.orders.emptyHint")}</p>
          <Link to="/#near-you" className="btn btn--primary">
            {t("customer.dashboard.findFood")}
          </Link>
        </section>
      )}
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("orders")}>
        <span className="customer-dash__stat-kicker">{t("customer.dashboard.statOrders")}</span>
        <strong>{dash.orders.length}</strong>
        <span>{t("customer.dashboard.statOrdersHint")}</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("savings")}>
        <span className="customer-dash__stat-kicker">{t("customer.dashboard.statSaved")}</span>
        <strong>{inr(dash.savings.total_saved)}</strong>
        <span>{t("customer.dashboard.statSavedHint")}</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("health")}>
        <span className="customer-dash__stat-kicker">{t("customer.dashboard.statFresh")}</span>
        <strong>{plateHealth?.score ?? dash.health.home_freshness_score}</strong>
        <span>{t("customer.dashboard.statFreshHint")}</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("refunds")}>
        <span className="customer-dash__stat-kicker">{t("customer.dashboard.statRefunds")}</span>
        <strong>{completedRefunds.length}</strong>
        <span>{t("customer.dashboard.statRefundsHint")}</span>
      </button>
      <button type="button" className="glass customer-dash__stat" onClick={() => onGo("complaints")}>
        <span className="customer-dash__stat-kicker">{t("customer.dashboard.statHelp")}</span>
        <strong>{openTickets}</strong>
        <span>{t("customer.dashboard.statHelpHint")}</span>
      </button>
      <section className="glass customer-dash__card customer-dash__span2">
        <h2>{t("customer.dashboard.tipsTitle")}</h2>
        {dash.tips.length === 0 ? (
          <p className="customer-dash__empty-hint">{t("customer.dashboard.tipsEmpty")}</p>
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
  dishHealth,
  setDiet,
  setCuisine,
  setLiveOnly,
  onRaiseIssue,
}: {
  dash: CustomerDashboard;
  diet: string;
  cuisine: string;
  liveOnly: boolean;
  dishHealth: Record<string, DishHealthSnapshot>;
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
        <div className="glass empty-state">
          <p className="empty-state__title">No orders match these filters.</p>
          <p className="empty-state__hint">Clear diet or cuisine filters, or find a kitchen nearby.</p>
          <Link to="/#near-you" className="btn btn--primary">
            Find food nearby
          </Link>
        </div>
      ) : (
        <ul className="customer-dash__orders">
          {dash.orders.map((row) => (
            <OrderCard key={row.order.id} row={row} dishHealth={dishHealth} onRaiseIssue={onRaiseIssue} />
          ))}
        </ul>
      )}
    </section>
  );
}

function OrderCard({
  row,
  dishHealth,
  onRaiseIssue,
}: {
  row: DashboardOrder;
  dishHealth: Record<string, DishHealthSnapshot>;
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
          <div className="customer-dash__order-title">
            <strong>{row.order.order_code}</strong>
            <span className={`customer-status customer-status--${customerStatusTone(row.order.status)}`}>
              {humanStatus(row.order.status)}
            </span>
          </div>
          <span>
            {formatWhen(row.order.created_at)} · {inr(row.order.total)}
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
          {row.is_rated && (
            <Link className="btn btn--ghost btn--sm" to={`/orders/${row.order.id}/rate`}>
              ★ {row.rating_home_taste?.toFixed(1) ?? "—"} taste
              {row.rating_quality != null ? ` · ${row.rating_quality.toFixed(1)} quality` : ""}
            </Link>
          )}
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
            {dishHealth[item.dish_id]?.score != null ? (
              <em> · health {dishHealth[item.dish_id].score}</em>
            ) : null}
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
      <header className="customer-dash__panel-head">
        <h2>My thali / tiffin plans</h2>
        <p>
          Request plans from a kitchen menu. The kitchen accepts or denies before billing starts.
        </p>
      </header>
      {subs.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">No meal plans yet</p>
          <p className="empty-state__hint">
            Find a kitchen and tap Request subscribe on their monthly plan.
          </p>
          <Link to="/#near-you" className="btn btn--primary">
            Find food nearby
          </Link>
        </div>
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

function HealthPanel({
  dash,
  plateHealth,
  healthLoading,
}: {
  dash: CustomerDashboard;
  plateHealth: DishHealthSnapshot | null;
  healthLoading: boolean;
}) {
  const { t } = useTranslation();
  const [diet, setDiet] = useState<CustomerDietProfile | null>(null);
  const [dietLoading, setDietLoading] = useState(true);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const loadDiet = useCallback(async () => {
    setDietLoading(true);
    try {
      setDiet(await fetchCustomerDietProfile());
    } catch {
      setDiet(null);
    } finally {
      setDietLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDiet();
  }, [loadDiet]);

  const onUpload = async (e: FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError(t("customer.dashboard.checkupNeedFile"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const next = await uploadCustomerCheckupReport(file, notes);
      setDiet(next);
      setNotes("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : t("customer.dashboard.checkupFailed"));
    } finally {
      setBusy(false);
    }
  };

  const setFilter = async (enabled: boolean) => {
    setBusy(true);
    setError("");
    try {
      setDiet(await updateCustomerDietFilter(enabled));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("customer.dashboard.checkupFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass customer-dash__card">
      <h2>{t("customer.dashboard.checkupTitle")}</h2>
      <p>{t("customer.dashboard.checkupIntro")}</p>
      {error ? <p className="auth-card__error">{error}</p> : null}
      <form className="customer-dash__checkup" onSubmit={(e) => void onUpload(e)}>
        <label>
          {t("customer.dashboard.checkupFile")}
          <input ref={fileRef} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" />
        </label>
        <label>
          {t("customer.dashboard.checkupNotes")}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder={t("customer.dashboard.checkupNotesHint")}
          />
        </label>
        <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>
          {busy ? t("customer.dashboard.checkupUploading") : t("customer.dashboard.checkupUpload")}
        </button>
      </form>
      {dietLoading ? (
        <p className="customer-dash__empty-hint">{t("customer.dashboard.healthLoading")}</p>
      ) : diet?.has_checkup_report ? (
        <div className="customer-dash__checkup-result">
          {diet.summary ? <p>{diet.summary}</p> : null}
          {diet.conditions.length > 0 ? (
            <p>
              {t("customer.dashboard.checkupConditions")}: {diet.conditions.join(", ")}
            </p>
          ) : null}
          <p className="customer-dash__empty-hint">{diet.disclaimer}</p>
          <p>{t("customer.dashboard.checkupAsk")}</p>
          <div className="customer-dash__hero-actions">
            <button
              type="button"
              className={`btn btn--sm${diet.diet_filter_enabled ? " btn--primary" : " btn--ghost"}`}
              disabled={busy}
              onClick={() => void setFilter(true)}
            >
              {t("customer.dashboard.checkupYes")}
            </button>
            <button
              type="button"
              className={`btn btn--sm${!diet.diet_filter_enabled ? " btn--primary" : " btn--ghost"}`}
              disabled={busy}
              onClick={() => void setFilter(false)}
            >
              {t("customer.dashboard.checkupNo")}
            </button>
          </div>
          <p>
            {diet.diet_filter_enabled
              ? t("customer.dashboard.checkupOn")
              : t("customer.dashboard.checkupOff")}
          </p>
          {diet.diet_filter_enabled ? (
            <Link to="/" className="btn btn--ghost btn--sm customer-dash__inline-cta">
              {t("customer.dashboard.checkupFindFood")}
            </Link>
          ) : null}
        </div>
      ) : (
        <p className="customer-dash__empty-hint">{t("customer.dashboard.checkupEmpty")}</p>
      )}
      <h2>{t("customer.dashboard.healthTitle")}</h2>
      <p>{t("customer.dashboard.healthIntro")}</p>
      {healthLoading ? (
        <p className="customer-dash__empty-hint">{t("customer.dashboard.healthLoading")}</p>
      ) : plateHealth ? (
        <DishHealthBlock health={plateHealth} />
      ) : (
        <p className="customer-dash__empty-hint">{t("customer.dashboard.healthEmpty")}</p>
      )}
      <h3>{t("customer.dashboard.dietMix")}</h3>
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
      </div>
      <h3>{t("customer.dashboard.tipsTitle")}</h3>
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
  const { t } = useTranslation();
  return (
    <section className="glass customer-dash__card">
      <header className="customer-dash__panel-head">
        <h2>{t("customer.dashboard.tabRefunds")}</h2>
        <p>
          Gateway reverses and direct UPI/bank transfers (remark = order id).
        </p>
      </header>
      <Link to="/account" className="btn btn--ghost btn--sm customer-dash__inline-cta">
        {t("customer.dashboard.payoutShortcut")}
      </Link>
      {refunds.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">No refunds yet</p>
          <p className="empty-state__hint">
            If a kitchen refunds you, the amount and channel show up here. Add UPI or bank so money
            can reach you quickly.
          </p>
          <Link to="/account" className="btn btn--primary">
            {t("customer.dashboard.payoutShortcut")}
          </Link>
        </div>
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

type AddressFieldErrors = {
  label?: string;
  line?: string;
  city?: string;
  pincode?: string;
  phone?: string;
};

function AddressBookForm({
  mode,
  busy,
  formRef,
  labelInputRef,
  label,
  setLabel,
  line,
  setLine,
  city,
  applyCity,
  state,
  setState,
  pincode,
  setPincode,
  landmark,
  setLandmark,
  phoneNational,
  setPhoneNational,
  lat,
  lng,
  makeDefault,
  setMakeDefault,
  fieldErrors,
  setFieldErrors,
  pinHere,
  onSubmit,
  onCancel,
}: {
  mode: "add" | "edit";
  busy: boolean;
  formRef: RefObject<HTMLFormElement | null>;
  labelInputRef: RefObject<HTMLInputElement | null>;
  label: string;
  setLabel: (v: string) => void;
  line: string;
  setLine: (v: string) => void;
  city: string;
  applyCity: (name: string) => void;
  state: string;
  setState: (v: string) => void;
  pincode: string;
  setPincode: (v: string) => void;
  landmark: string;
  setLandmark: (v: string) => void;
  phoneNational: string;
  setPhoneNational: (v: string) => void;
  lat: number | null;
  lng: number | null;
  makeDefault: boolean;
  setMakeDefault: (v: boolean) => void;
  fieldErrors: AddressFieldErrors;
  setFieldErrors: Dispatch<SetStateAction<AddressFieldErrors>>;
  pinHere: () => void;
  onSubmit: (e: FormEvent) => void;
  onCancel?: () => void;
}) {
  const { t } = useTranslation();
  const editing = mode === "edit";
  return (
    <form
      ref={formRef}
      className={editing ? "customer-dash__addr-form" : "glass customer-dash__card"}
      onSubmit={onSubmit}
    >
      <h2>{editing ? t("customer.delivery.editAddress") : "Add another address"}</h2>
      <p>
        {editing
          ? "Change the pin, contact number, or label. Discovery and checkout use this address when it is selected."
          : "Save Home, Work, or a family house. Discovery and checkout use the address you pick."}
      </p>
      <label>
        Label
        <input
          ref={labelInputRef}
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
        Landmark (optional)
        <input
          value={landmark}
          onChange={(e) => setLandmark(e.target.value)}
          maxLength={120}
          placeholder="Tower / gate / society"
        />
      </label>
      <label>
        City
        <select
          value={liveCities().some((c) => c.name === city) ? city : "__other__"}
          onChange={(e) => {
            if (e.target.value === "__other__") {
              setFieldErrors((f) => ({ ...f, city: undefined }));
              return;
            }
            applyCity(e.target.value);
            setFieldErrors((f) => ({ ...f, city: undefined }));
          }}
        >
          {liveCities().map((c) => (
            <option key={c.slug} value={c.name}>
              {c.name}
            </option>
          ))}
          <option value="__other__">Other city</option>
        </select>
      </label>
      {!liveCities().some((c) => c.name === city) ? (
        <label>
          City name
          <input
            value={city}
            onChange={(e) => {
              applyCity(e.target.value);
              setFieldErrors((f) => ({ ...f, city: undefined }));
            }}
            required
            maxLength={80}
            className={fieldErrors.city ? "input-invalid" : undefined}
            aria-invalid={Boolean(fieldErrors.city)}
          />
          {fieldErrors.city ? <span className="field-error">{fieldErrors.city}</span> : null}
        </label>
      ) : null}
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
      <PhoneField
        label={t("customer.delivery.contactPhone")}
        value={phoneNational}
        onChange={(national) => {
          setPhoneNational(national);
          setFieldErrors((f) => ({ ...f, phone: undefined }));
        }}
        required
        error={fieldErrors.phone}
        hint="Kitchen and rider call this number at this address."
      />
      <label className="customer-dash__check">
        <input
          type="checkbox"
          checked={makeDefault}
          onChange={(e) => setMakeDefault(e.target.checked)}
        />
        Default address
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
      <div className="customer-dash__addr-actions">
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {editing ? t("customer.delivery.updateAddress") : "Save address"}
        </button>
        {editing && onCancel ? (
          <button type="button" className="btn btn--ghost" onClick={onCancel}>
            {t("customer.delivery.cancelEdit")}
          </button>
        ) : null}
      </div>
    </form>
  );
}

function AddressesPanel({
  addresses,
  busy,
  setBusy,
  setError,
  requestedEditId,
  onEditIdChange,
  onRefresh,
}: {
  addresses: CustomerAddress[];
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (v: string) => void;
  requestedEditId: string | null;
  onEditIdChange: (id: string | null) => void;
  onRefresh: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const { session } = useCustomerAuth();
  const { selectedAddressId, selectAddress, refreshAddresses } = useCustomerDelivery();
  const loginNational = parsePhoneInput(session?.phone || "").national;
  const formRef = useRef<HTMLFormElement>(null);
  const labelInputRef = useRef<HTMLInputElement>(null);
  const skipUrlOpen = useRef(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [label, setLabel] = useState("Home");
  const [line, setLine] = useState("");
  const [city, setCity] = useState("Pune");
  const [state, setState] = useState("Maharashtra");
  const [pincode, setPincode] = useState("");
  const [landmark, setLandmark] = useState("");
  const [phoneNational, setPhoneNational] = useState(loginNational);
  const [lat, setLat] = useState<number | null>(18.5204);
  const [lng, setLng] = useState<number | null>(73.8567);
  const [makeDefault, setMakeDefault] = useState(addresses.length === 0);
  const [fieldErrors, setFieldErrors] = useState<AddressFieldErrors>({});

  useEffect(() => {
    if (editId || phoneNational || !loginNational) return;
    setPhoneNational(loginNational);
  }, [editId, phoneNational, loginNational]);

  const resetForm = useCallback(() => {
    skipUrlOpen.current = true;
    setEditId(null);
    setLabel("Home");
    setLine("");
    setCity("Pune");
    setState("Maharashtra");
    setPincode("");
    setLandmark("");
    setPhoneNational(loginNational);
    setLat(18.5204);
    setLng(73.8567);
    setMakeDefault(addresses.length === 0);
    setFieldErrors({});
    onEditIdChange(null);
  }, [addresses.length, loginNational, onEditIdChange]);

  const fillForm = useCallback(
    (a: CustomerAddress, syncUrl = true) => {
      setEditId(a.id);
      setLabel(a.label);
      setLine(a.address_line);
      setCity(a.city);
      setState(a.state || "");
      setPincode(a.pincode || "");
      setLandmark(a.landmark || "");
      setPhoneNational(parsePhoneInput(a.phone || loginNational).national);
      setLat(a.latitude);
      setLng(a.longitude);
      setMakeDefault(a.is_default);
      setFieldErrors({});
      if (syncUrl) onEditIdChange(a.id);
    },
    [loginNational, onEditIdChange],
  );

  useEffect(() => {
    if (!requestedEditId) {
      skipUrlOpen.current = false;
      return;
    }
    if (skipUrlOpen.current) return;
    if (editId === requestedEditId) return;
    const found = addresses.find((row) => row.id === requestedEditId);
    if (found) fillForm(found, false);
  }, [requestedEditId, addresses, editId, fillForm]);

  useEffect(() => {
    if (!editId) return;
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    labelInputRef.current?.focus();
  }, [editId]);

  const applyCity = (name: string) => {
    setCity(name);
    const known = CITIES_PRESENCE.find((c) => c.name === name);
    if (known) {
      setState(known.state);
      setLat(known.center.lat);
      setLng(known.center.lng);
      return;
    }
    const center = cityCenterByName(name);
    if (center) {
      setLat(center.lat);
      setLng(center.lng);
    }
  };

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

  const persistAndRefresh = async (savedId?: string) => {
    await onRefresh();
    const list = await refreshAddresses();
    if (savedId) selectAddress(savedId);
    else if (selectedAddressId && !list.some((row) => row.id === selectedAddressId)) {
      const next = list.find((row) => row.is_default) ?? list[0];
      if (next) selectAddress(next.id);
    }
  };

  const contactPhoneFor = (address: CustomerAddress): string => {
    if (address.phone) return address.phone;
    if (loginNational) return toE164(loginNational);
    return "";
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const nextErrors = {
      label: validateText(label, "a label", { max: 40 }) ?? undefined,
      line: validateText(line, "the address", { min: 5, max: 240 }) ?? undefined,
      city: validateText(city, "a city", { max: 80 }) ?? undefined,
      pincode: validatePincode(pincode, { required: false }) ?? undefined,
      phone: validateNationalPhone(phoneNational) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setBusy(true);
    setError("");
    const updatingId = editId;
    try {
      const saved = await saveAddress(
        {
          label,
          address_line: line,
          city,
          state: state || null,
          pincode: pincode || null,
          landmark: landmark.trim() || null,
          phone: toE164(phoneNational),
          latitude: lat,
          longitude: lng,
          is_default: makeDefault || addresses.length === 0,
        },
        updatingId ?? undefined,
      );
      resetForm();
      await persistAndRefresh(updatingId ? undefined : saved.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save address");
    } finally {
      setBusy(false);
    }
  };

  const formProps = {
    busy,
    formRef,
    labelInputRef,
    label,
    setLabel,
    line,
    setLine,
    city,
    applyCity,
    state,
    setState,
    pincode,
    setPincode,
    landmark,
    setLandmark,
    phoneNational,
    setPhoneNational,
    lat,
    lng,
    makeDefault,
    setMakeDefault,
    fieldErrors,
    setFieldErrors,
    pinHere,
    onSubmit: submit,
  };

  return (
    <div className="customer-dash__address-book">
      <section className="glass customer-dash__card">
        <h2>Saved addresses</h2>
        <p>Pick one for discovery and checkout. Tap Edit to change the pin or contact number.</p>
        {addresses.length === 0 ? (
          <p>No saved addresses yet.</p>
        ) : (
          <ul className="customer-dash__addr-list">
            {addresses.map((a) => (
              <li
                key={a.id}
                className={
                  editId === a.id
                    ? "customer-dash__addr-card customer-dash__addr-card--editing"
                    : "customer-dash__addr-card"
                }
              >
                {editId === a.id ? (
                  <AddressBookForm mode="edit" onCancel={resetForm} {...formProps} />
                ) : (
                  <>
                    <strong>
                      {a.label}
                      {a.is_default ? " · default" : ""}
                      {selectedAddressId === a.id ? " · in use" : ""}
                    </strong>
                    <span>{formatAddressLine(a)}</span>
                    {a.landmark ? <span>{a.landmark}</span> : null}
                    <div className="customer-dash__addr-actions">
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={busy || selectedAddressId === a.id}
                        onClick={() => selectAddress(a.id)}
                      >
                        Use for orders
                      </button>
                      {!a.is_default ? (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={async () => {
                            const phone = contactPhoneFor(a);
                            if (!phone) {
                              setError("Add a contact number before setting a default address.");
                              fillForm(a);
                              return;
                            }
                            setBusy(true);
                            try {
                              await saveAddress(
                                {
                                  label: a.label,
                                  address_line: a.address_line,
                                  city: a.city,
                                  state: a.state,
                                  pincode: a.pincode,
                                  landmark: a.landmark,
                                  phone,
                                  latitude: a.latitude,
                                  longitude: a.longitude,
                                  is_default: true,
                                },
                                a.id,
                              );
                              await persistAndRefresh(a.id);
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Could not set default");
                            } finally {
                              setBusy(false);
                            }
                          }}
                        >
                          Set default
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={() => fillForm(a)}
                      >
                        {t("customer.delivery.editAddress")}
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            await deleteAddress(a.id);
                            if (editId === a.id) resetForm();
                            await persistAndRefresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Delete failed");
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      {!editId ? <AddressBookForm mode="add" {...formProps} /> : null}
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
  const { t } = useTranslation();
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
    <div className="customer-dash__account">
      <section className="glass customer-profile-id">
        <CustomerAvatar
          name={profile.name}
          src={profile.avatar_url}
          size="lg"
          live={Boolean(profile.has_live_photo)}
        />
        <div className="customer-profile-id__copy">
          <h2>{profile.name || "Your profile"}</h2>
          <p>
            {profile.phone ? maskCustomerPhone(profile.phone) : t("customer.dashboard.phoneUnlinked")}
            {profile.email ? ` · ${profile.email}` : ""}
          </p>
          <p className="customer-profile-id__status">
            {profile.upi_vpa || profile.bank_account_number_masked
              ? t("customer.account.payoutStatusReady")
              : t("customer.account.payoutStatusMissing")}
          </p>
        </div>
        <div className="customer-profile-id__actions">
          <Link to="/dashboard?tab=addresses" className="btn btn--ghost btn--sm">
            {t("customer.nav.addresses")}
          </Link>
          <Link to="/account" className="btn btn--primary btn--sm">
            {t("customer.dashboard.payoutShortcut")}
          </Link>
        </div>
      </section>

      <CustomerProfilePhotos profile={profile} onUpdated={setProfile} />

      <div className="customer-dash__split">
      <form className="glass customer-dash__card" onSubmit={saveProfile}>
        <h2>{t("customer.nav.profile")}</h2>
        <p className="auth-card__hint">{t("customer.account.profileHint")}</p>
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
        <p className="auth-card__hint">
          Phone: {profile.phone ? maskCustomerPhone(profile.phone) : "not linked — use WhatsApp login"}
        </p>
        <button type="submit" className="btn btn--primary" disabled={busy}>
          Save profile
        </button>
      </form>
      <form className="glass customer-dash__card" onSubmit={savePassword}>
        <h2>Password</h2>
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
      </div>

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

      <section className="customer-dash__signout">
        <p>
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
