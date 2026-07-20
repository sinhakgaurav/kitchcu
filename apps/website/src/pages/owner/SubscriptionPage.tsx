import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { useKitchenAuth } from "../../shared/kitchenAuth";
import {
  activateSubscription,
  createSubscription,
  fetchMySubscription,
  fetchSubscriptionPlans,
  type OwnerSubscription,
  type SubscriptionPlan,
} from "../../lib/api";
import { fetchOwnerReferrals } from "../../shared/referralApi";
import { Link } from "react-router-dom";

const TIER_LABELS: Record<string, string> = {
  starter: "Starter",
  growth: "Growth",
  pro: "Pro",
};

const TIER_FEATURES: Record<string, string[]> = {
  starter: ["Manual + WhatsApp orders", "Live-capture menu", "Basic reports"],
  growth: ["Everything in Starter", "CRM + customer segments", "Peak-hour insights"],
  pro: ["Everything in Growth", "Multi-kitchen support", "Priority support"],
};

export function SubscriptionPage() {
  const { t } = useTranslation();
  const { owner, refresh } = useKitchenAuth();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscription, setSubscription] = useState<OwnerSubscription | null>(null);
  const [cycle, setCycle] = useState<"monthly" | "yearly">("monthly");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [referralBalance, setReferralBalance] = useState(0);

  useEffect(() => {
    Promise.all([
      fetchSubscriptionPlans(),
      fetchMySubscription().catch(() => null),
      fetchOwnerReferrals().catch(() => null),
    ])
      .then(([planRes, sub, refs]) => {
        setPlans(planRes.plans);
        setSubscription(sub);
        setReferralBalance(refs?.credit.balance_inr ?? 0);
      })
      .catch(() => setError(t("owner.subscription.loadError")))
      .finally(() => setLoading(false));
  }, [t]);

  const subscribe = async (tier: "starter" | "growth" | "pro") => {
    setError("");
    setBusy(true);
    try {
      const sub = await createSubscription({ plan_tier: tier, billing_cycle: cycle });
      setSubscription(sub);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Subscribe failed");
    } finally {
      setBusy(false);
    }
  };

  const activate = async () => {
    if (!subscription) return;
    setError("");
    setBusy(true);
    try {
      const sub = await activateSubscription(subscription.id);
      setSubscription(sub);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Activation failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="owner-screen app-loading">{t("owner.subscription.loading")}</div>;

  const activeTier = subscription?.status === "active" ? subscription.plan_tier : owner?.subscription_tier;
  const activeStatus = subscription?.status ?? owner?.subscription_status ?? "trial";

  return (
    <OwnerPageShell
      eyebrow="Billing"
      title={t("owner.subscription.title")}
      description="No per-order commission — flat kitchen SaaS billing only"
      actions={
        <span className={`status-badge status-badge--lg owner-sub-badge owner-sub-badge--${activeStatus}`}>
          {activeStatus} · {TIER_LABELS[activeTier ?? "starter"] ?? activeTier}
        </span>
      }
    >
      {error && <div className="auth-card__error">{error}</div>}

      {referralBalance > 0 && (
        <OwnerPanel title={t("owner.referrals.creditBalance")}>
          <p>
            {t("owner.subscription.referralCredit", { amount: referralBalance.toFixed(2) })}{" "}
            {t("owner.subscription.referralNote")}
          </p>
          <Link to="/dashboard/referrals" className="btn btn--ghost btn--sm">
            {t("owner.nav.referrals")}
          </Link>
        </OwnerPanel>
      )}

      {subscription && subscription.status !== "active" && (
        <OwnerPanel title="Complete payment">
          <p>
            {TIER_LABELS[subscription.plan_tier]} plan · ₹{subscription.amount.toFixed(0)} / {subscription.billing_cycle}
          </p>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={activate}>
            {t("owner.subscription.activate")}
          </button>
        </OwnerPanel>
      )}

      {subscription?.status === "active" && subscription.current_period_end && (
        <OwnerPanel title={t("owner.subscription.current")}>
          <p>
            Active until {new Date(subscription.current_period_end).toLocaleDateString()} ·
            ₹{subscription.amount.toFixed(0)} / {subscription.billing_cycle}
          </p>
        </OwnerPanel>
      )}

      <div className="owner-tabs">
        <button type="button" className={cycle === "monthly" ? "active" : ""} onClick={() => setCycle("monthly")}>
          {t("owner.subscription.monthly")}
        </button>
        <button type="button" className={cycle === "yearly" ? "active" : ""} onClick={() => setCycle("yearly")}>
          {t("owner.subscription.yearly")}
        </button>
      </div>

      <div className="owner-plan-grid">
        {plans.map((plan) => {
          const amount = cycle === "monthly" ? plan.monthly_amount : plan.yearly_amount;
          const afterCredit = Math.max(0, amount - referralBalance);
          const isCurrent = activeTier === plan.tier && activeStatus === "active";
          return (
            <article key={plan.tier} className={`dash-card owner-plan-card${isCurrent ? " owner-plan-card--current" : ""}`}>
              <h2>{TIER_LABELS[plan.tier] ?? plan.tier}</h2>
              <p className="owner-plan-card__price">
                <strong>₹{afterCredit.toFixed(0)}</strong>
                <span> / {cycle === "monthly" ? "month" : "year"}</span>
              </p>
              {referralBalance > 0 && afterCredit < amount && (
                <p className="muted">
                  List ₹{amount.toFixed(0)} − referral ₹{Math.min(referralBalance, amount).toFixed(0)}
                </p>
              )}
              <ul>
                {(TIER_FEATURES[plan.tier] ?? []).map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <button
                type="button"
                className="btn btn--primary"
                disabled={busy || isCurrent}
                onClick={() => subscribe(plan.tier as "starter" | "growth" | "pro")}
              >
                {isCurrent ? t("owner.subscription.current") : t("owner.subscription.subscribe")}
              </button>
            </article>
          );
        })}
      </div>
    </OwnerPageShell>
  );
}
