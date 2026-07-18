import { FormEvent, useEffect, useState } from "react";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  clearKitchenPaymentGateway,
  fetchKitchenPaymentGateway,
  upsertKitchenPaymentGateway,
  type KitchenPaymentGateway,
} from "../../lib/api";
import { useKitchen } from "../../shared/kitchenContext";

export function PaymentGatewayPage() {
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
      eyebrow="Integrations"
      title="Payment gateway"
      description="Razorpay keys for this kitchen — customer checkout and Route settlements. KitchCu takes no food commission."
    >
      <OwnerPanel title="Razorpay credentials">
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
    </OwnerPageShell>
  );
}
