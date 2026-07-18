import { FormEvent, useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  createSubscriptionPlan,
  decideKitchenSubscription,
  fetchKitchenSubscriptions,
  fetchSubscriptionPlans,
  fetchSubscriptionSummary,
  updateSubscriptionPlan,
  type CustomerKitchenSubscription,
  type SubscriptionPlan,
  type SubscriptionSummary,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const PLAN_TYPES = [
  { value: "thali", label: "Thali" },
  { value: "tiffin", label: "Tiffin" },
  { value: "combo", label: "Combo" },
  { value: "single_dish", label: "Single dish pack" },
] as const;

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export function TiffinSubscriptionsPage() {
  const { kitchen } = useKitchen();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subs, setSubs] = useState<CustomerKitchenSubscription[]>([]);
  const [summary, setSummary] = useState<SubscriptionSummary | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [planType, setPlanType] = useState<(typeof PLAN_TYPES)[number]["value"]>("thali");
  const [price, setPrice] = useState(2499);
  const [description, setDescription] = useState("");

  const load = () => {
    if (!kitchen) return;
    setLoading(true);
    Promise.all([
      fetchSubscriptionPlans(kitchen.id),
      fetchKitchenSubscriptions(kitchen.id, filter || undefined),
      fetchSubscriptionSummary(kitchen.id),
    ])
      .then(([p, s, sum]) => {
        setPlans(p.plans);
        setSubs(s.subscriptions);
        setSummary(sum);
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [kitchen, filter]);

  const onCreatePlan = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen || !name.trim()) return;
    setBusy(true);
    setError("");
    try {
      await createSubscriptionPlan(kitchen.id, {
        name: name.trim(),
        description: description.trim() || undefined,
        plan_type: planType,
        price_monthly: price,
        dishes_config: { weekdays: [0, 1, 2, 3, 4], meals_per_day: 1 },
      });
      setName("");
      setDescription("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create plan");
    } finally {
      setBusy(false);
    }
  };

  const onDecide = async (
    subId: string,
    action: "accept" | "deny" | "activate" | "deactivate",
  ) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      await decideKitchenSubscription(kitchen.id, subId, action);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const togglePlan = async (plan: SubscriptionPlan) => {
    if (!kitchen) return;
    setBusy(true);
    try {
      await updateSubscriptionPlan(kitchen.id, plan.id, { is_active: !plan.is_active });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update plan");
    } finally {
      setBusy(false);
    }
  };

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title="Tiffin & monthly plans"
      description="Thali/tiffin subscriptions — customers request, you accept or deny. No food commission."
    >
      {error && <div className="auth-card__error">{error}</div>}

      {summary && (
        <div className="od-board__kpi-grid">
          <div className="owner-stat glass">
            <strong>{summary.pending}</strong>
            <span>Pending requests</span>
          </div>
          <div className="owner-stat glass">
            <strong>{summary.active}</strong>
            <span>Active subscribers</span>
          </div>
          <div className="owner-stat glass">
            <strong>{summary.paused}</strong>
            <span>Paused</span>
          </div>
          <div className="owner-stat glass">
            <strong>{inr(summary.mrr_estimate)}</strong>
            <span>MRR estimate</span>
          </div>
        </div>
      )}

      <OwnerPanel title="Create plan" description="Monthly price customers pay your kitchen directly.">
        <form className="owner-form owner-form--wide" onSubmit={onCreatePlan}>
          <div className="form-row">
            <label>
              Plan name
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Veg thali monthly" />
            </label>
            <label>
              Type
              <select value={planType} onChange={(e) => setPlanType(e.target.value as typeof planType)}>
                {PLAN_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              Monthly price (₹)
              <input type="number" min={1} value={price} onChange={(e) => setPrice(Number(e.target.value))} required />
            </label>
          </div>
          <label>
            Description
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Mon–Fri lunch delivery" />
          </label>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? "Saving…" : "Create plan"}
          </button>
        </form>
      </OwnerPanel>

      <OwnerPanel title="Plans">
        {loading ? (
          <p className="owner-muted">Loading…</p>
        ) : plans.length === 0 ? (
          <OwnerEmpty message="No plans yet — create a thali or tiffin plan above." />
        ) : (
          <ul className="owner-detail-items">
            {plans.map((p) => (
              <li key={p.id}>
                <span>
                  <strong>{p.name}</strong> · {p.plan_type} · {inr(p.price_monthly)}/mo
                  {" · "}
                  {p.active_subscriber_count} active · {p.pending_count} pending
                  {!p.is_active && " · inactive"}
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={() => togglePlan(p)}
                >
                  {p.is_active ? "Deactivate" : "Activate"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>

      <OwnerPanel title="Subscription requests">
        <div className="form-row" style={{ marginBottom: "0.75rem" }}>
          <label>
            Filter
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="denied">Denied</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
        </div>
        {subs.length === 0 ? (
          <OwnerEmpty message="No subscriptions in this filter." />
        ) : (
          <ul className="owner-detail-items">
            {subs.map((s) => (
              <li key={s.id}>
                <span>
                  <strong>{s.customer_name || s.customer_phone}</strong>
                  {" · "}
                  {s.plan_name || "Plan"} · {s.status}
                  {s.price_monthly != null && <> · {inr(s.price_monthly)}/mo</>}
                </span>
                <span className="owner-actions">
                  {s.status === "pending" && (
                    <>
                      <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onDecide(s.id, "accept")}>
                        Accept
                      </button>
                      <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onDecide(s.id, "deny")}>
                        Deny
                      </button>
                    </>
                  )}
                  {s.status === "active" && (
                    <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onDecide(s.id, "deactivate")}>
                      Deactivate
                    </button>
                  )}
                  {s.status === "paused" && (
                    <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onDecide(s.id, "activate")}>
                      Activate
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
