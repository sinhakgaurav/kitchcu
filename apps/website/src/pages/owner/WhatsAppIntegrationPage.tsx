import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchKitchenWhatsAppIntegration,
  fetchMessagingWallet,
  upsertKitchenWhatsAppIntegration,
  type KitchenWhatsAppIntegration,
  type MessagingWallet,
} from "../../lib/api";
import { useKitchen } from "../../shared/kitchenContext";

export function WhatsAppIntegrationPage() {
  const { kitchen } = useKitchen();
  const [cfg, setCfg] = useState<KitchenWhatsAppIntegration | null>(null);
  const [wallet, setWallet] = useState<MessagingWallet | null>(null);
  const [phoneId, setPhoneId] = useState("");
  const [displayPhone, setDisplayPhone] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const kitchenId = kitchen?.id;

  useEffect(() => {
    if (!kitchenId) return;
    setLoading(true);
    setError("");
    Promise.all([
      fetchKitchenWhatsAppIntegration(kitchenId),
      fetchMessagingWallet(kitchenId).catch(() => null),
    ])
      .then(([wa, bal]) => {
        setCfg(wa);
        setPhoneId(wa.whatsapp_phone_id ?? "");
        setDisplayPhone(wa.whatsapp_display_phone ?? "");
        setWallet(bal);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load WhatsApp settings"))
      .finally(() => setLoading(false));
  }, [kitchenId]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchenId) return;
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await upsertKitchenWhatsAppIntegration(kitchenId, {
        whatsapp_phone_id: phoneId.trim() || null,
        whatsapp_display_phone: displayPhone.trim() || null,
      });
      setCfg(next);
      setOk("WhatsApp Business linked. Inbound Meta webhooks will route to this kitchen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onDisconnect = async () => {
    if (!kitchenId) return;
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await upsertKitchenWhatsAppIntegration(kitchenId, {
        clear: true,
        whatsapp_phone_id: null,
        whatsapp_display_phone: null,
      });
      setCfg(next);
      setPhoneId("");
      setDisplayPhone("");
      setOk("WhatsApp disconnected for this kitchen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchenId) {
    return <div className="owner-screen app-loading">Select a kitchen first.</div>;
  }
  if (loading) {
    return <div className="owner-screen app-loading">Loading WhatsApp…</div>;
  }

  return (
    <OwnerPageShell
      eyebrow="Integrations"
      title="WhatsApp Business"
      description="Connect your Meta phone number ID so customer WhatsApp orders land in this kitchen. Platform App Secret stays with Super Admin."
      actions={
        cfg?.connected ? (
          <span className="status-badge status-badge--lg owner-sub-badge owner-sub-badge--active">
            Connected
          </span>
        ) : (
          <span className="status-badge status-badge--lg owner-sub-badge owner-sub-badge--trial">
            Not connected
          </span>
        )
      }
    >
      {error && <p className="auth-card__error">{error}</p>}
      {ok && <p className="owner-forms__success">{ok}</p>}

      {wallet && (
        <OwnerPanel title="Messaging wallet">
          <p>
            Balance: <strong>₹{wallet.balance_inr.toFixed(0)}</strong>
            {wallet.low_balance ? " · Low balance — top up via Enterprise renewal" : ""}
          </p>
          <p className="owner-forms__hint">
            Enterprise plans credit ₹500/month here for daily menu and CRM blasts.{" "}
            <Link to="/dashboard/subscription">Manage subscription</Link>
          </p>
        </OwnerPanel>
      )}

      <OwnerPanel title="Meta Cloud API">
        <form className="owner-forms" onSubmit={onSubmit}>
          <label>
            Phone Number ID
            <input
              value={phoneId}
              onChange={(e) => setPhoneId(e.target.value)}
              placeholder="From Meta Business → WhatsApp → API Setup"
              autoComplete="off"
              required={!cfg?.connected}
            />
          </label>
          <label>
            Display phone (E.164)
            <input
              value={displayPhone}
              onChange={(e) => setDisplayPhone(e.target.value)}
              placeholder="+919876543210"
              autoComplete="tel"
            />
          </label>
          <div className="owner-forms__actions">
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {busy ? "Saving…" : cfg?.connected ? "Update connection" : "Connect WhatsApp"}
            </button>
            {cfg?.connected && (
              <button type="button" className="btn btn--ghost" disabled={busy} onClick={onDisconnect}>
                Disconnect
              </button>
            )}
          </div>
        </form>
        <p className="owner-forms__hint">
          {cfg?.platform_secrets_note ??
            "Verify Token and App Secret are platform-managed. Each Phone Number ID can only link to one kitchen."}
        </p>
      </OwnerPanel>
    </OwnerPageShell>
  );
}
