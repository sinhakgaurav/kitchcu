import { FormEvent, useEffect, useState } from "react";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  clearKitchenPaymentGateway,
  fetchKitchenPaymentGateway,
  fetchKitchenSettlements,
  upsertKitchenPaymentGateway,
  type KitchenPaymentGateway,
  type Settlement,
} from "../../lib/api";
import { useKitchen } from "../../shared/kitchenContext";
import { useTranslation } from "react-i18next";

export function PaymentGatewayPage() {
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const [cfg, setCfg] = useState<KitchenPaymentGateway | null>(null);
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [linkedAccountId, setLinkedAccountId] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [settleStatus, setSettleStatus] = useState("");
  const [settleError, setSettleError] = useState("");

  const kitchenId = kitchen?.id;

  useEffect(() => {
    if (!kitchenId) return;
    setLoading(true);
    fetchKitchenPaymentGateway(kitchenId)
      .then((g) => {
        setCfg(g);
        setKeyId(g.key_id ?? "");
        setLinkedAccountId(g.linked_account_id ?? "");
        setIsActive(g.is_active);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load payment gateway"))
      .finally(() => setLoading(false));
  }, [kitchenId]);

  useEffect(() => {
    if (!kitchenId) return;
    setSettleError("");
    fetchKitchenSettlements(kitchenId, {
      status: settleStatus || undefined,
      limit: 50,
    })
      .then(setSettlements)
      .catch((e) => setSettleError(e instanceof Error ? e.message : "Could not load settlements"));
  }, [kitchenId, settleStatus]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchenId) return;
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await upsertKitchenPaymentGateway(kitchenId, {
        key_id: keyId,
        key_secret: keySecret || undefined,
        webhook_secret: webhookSecret || undefined,
        linked_account_id: linkedAccountId,
        is_active: isActive,
      });
      setCfg(next);
      setKeySecret("");
      setWebhookSecret("");
      setOk("Payment gateway saved. Secrets are stored encrypted and never shown in full.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onClear = async () => {
    if (!kitchenId) return;
    if (!window.confirm("Remove Razorpay credentials for this kitchen?")) return;
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await clearKitchenPaymentGateway(kitchenId);
      setCfg(next);
      setKeyId("");
      setKeySecret("");
      setWebhookSecret("");
      setLinkedAccountId("");
      setIsActive(true);
      setOk("Payment gateway cleared for this kitchen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clear failed");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchenId) {
    return <div className="owner-screen app-loading">Select a kitchen first.</div>;
  }
  if (loading) {
    return <div className="owner-screen app-loading">Loading payment gateway…</div>;
  }

  return (
    <OwnerPageShell
      eyebrow={t("owner.nav.paymentGateway")}
      title={t("owner.pages.paymentGateway")}
      description={t("owner.pageDesc.payments")}
    >
      <OwnerPanel title={t("owner.panels.razorpay")}>
        {error && <p className="auth-card__error">{error}</p>}
        {ok && <p className="owner-forms__success">{ok}</p>}
        <form className="owner-forms" onSubmit={onSubmit}>
          <label>
            Razorpay Key ID
            <input
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
              placeholder="rzp_live_… or rzp_test_…"
              autoComplete="off"
            />
          </label>
          <label>
            Razorpay Key Secret
            <input
              type="password"
              value={keySecret}
              onChange={(e) => setKeySecret(e.target.value)}
              placeholder={
                cfg?.key_secret_configured
                  ? `Configured (${cfg.key_secret_masked ?? "••••"}) — leave blank to keep`
                  : "Enter key secret"
              }
              autoComplete="new-password"
            />
          </label>
          <label>
            Webhook secret
            <input
              type="password"
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder={
                cfg?.webhook_secret_configured
                  ? `Configured (${cfg.webhook_secret_masked ?? "••••"}) — leave blank to keep`
                  : "Optional webhook signing secret"
              }
              autoComplete="new-password"
            />
          </label>
          <label>
            Route linked account ID
            <input
              value={linkedAccountId}
              onChange={(e) => setLinkedAccountId(e.target.value)}
              placeholder="acc_…"
              autoComplete="off"
            />
          </label>
          <label className="owner-forms__check">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            Active for this kitchen
          </label>
          <div className="owner-forms__actions">
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {busy ? "Saving…" : "Save payment gateway"}
            </button>
            {(cfg?.key_id || cfg?.key_secret_configured || cfg?.linked_account_id) && (
              <button type="button" className="btn btn--ghost" disabled={busy} onClick={onClear}>
                Clear credentials
              </button>
            )}
          </div>
        </form>
        <p className="owner-forms__hint">
          These keys belong to this kitchen (customer checkout + Route settlements). Platform
          subscription Razorpay keys and Meta WhatsApp App Secret live under Super Admin → API Keys
          — not here.
        </p>
      </OwnerPanel>
      <OwnerPanel
        title={t("owner.panels.routeSettlements")}
        description="Money transferred to this kitchen after multi-kitchen checkout. Platform food commission is always ₹0."
        action={
          <label className="od-settle__filter">
            Status
            <select value={settleStatus} onChange={(e) => setSettleStatus(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="transferred">Transferred</option>
            </select>
          </label>
        }
      >
        {settleError && <p className="auth-card__error">{settleError}</p>}
        {settlements.length === 0 ? (
          <p className="od-panel__empty">No settlements yet — they appear after a captured online / UPI split payment.</p>
        ) : (
          <table className="report-table od-settle__table">
            <thead>
              <tr>
                <th>When</th>
                <th>Gross</th>
                <th>Delivery</th>
                <th>Net to you</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {settlements.map((row) => (
                <tr key={row.id}>
                  <td>{row.settled_at ? new Date(row.settled_at).toLocaleDateString("en-IN") : "—"}</td>
                  <td>₹{Math.round(row.gross_amount).toLocaleString("en-IN")}</td>
                  <td>₹{Math.round(row.delivery_fee_amount).toLocaleString("en-IN")}</td>
                  <td>₹{Math.round(row.net_to_owner).toLocaleString("en-IN")}</td>
                  <td>
                    <span className={`status-badge status-badge--${row.settlement_status}`}>
                      {row.settlement_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
