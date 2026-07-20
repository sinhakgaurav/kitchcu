import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LiveCapturePhotoField } from "../../components/LiveCapturePhotoField";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchCrmCustomers,
  fetchDishTrial,
  promoteTrial,
  recordTrialRating,
  sendTrialSamples,
  setTrialInvites,
  updateDish,
  type CrmCustomer,
  type DishTrial,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function TrialDetailPage() {
  const { trialId } = useParams<{ trialId: string }>();
  const { kitchen } = useKitchen();
  const [trial, setTrial] = useState<DishTrial | null>(null);
  const [customers, setCustomers] = useState<CrmCustomer[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [heroUrl, setHeroUrl] = useState("");
  const [heroLive, setHeroLive] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!kitchen || !trialId) return;
    try {
      const [t, crm] = await Promise.all([
        fetchDishTrial(kitchen.id, trialId),
        fetchCrmCustomers(kitchen.id),
      ]);
      setTrial(t);
      setCustomers(crm.customers);
      setSelected(new Set(t.invites.map((i) => i.customer_id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trial not found");
    }
  };

  useEffect(() => {
    load();
  }, [kitchen, trialId]);

  const toggleCustomer = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const saveInvites = async () => {
    if (!kitchen || !trialId) return;
    if (selected.size < 5) {
      setError("Select at least 5 regular customers (max 20).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await setTrialInvites(kitchen.id, trialId, {
        customer_ids: [...selected].slice(0, 20),
        promo_type: "free",
      });
      setTrial(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save invites");
    } finally {
      setBusy(false);
    }
  };

  const sendSamples = async () => {
    if (!kitchen || !trialId) return;
    setBusy(true);
    setError("");
    try {
      const updated = await sendTrialSamples(kitchen.id, trialId);
      setTrial(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setBusy(false);
    }
  };

  const rateInvite = async (inviteId: string, home: number, quality: number) => {
    if (!kitchen || !trialId) return;
    setBusy(true);
    try {
      const updated = await recordTrialRating(kitchen.id, trialId, {
        invite_id: inviteId,
        home_taste_score: home,
        quality_score: quality,
      });
      setTrial(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rating failed");
    } finally {
      setBusy(false);
    }
  };

  const onHeroCapture = async (url: string) => {
    setHeroUrl(url);
    if (!url) {
      setHeroLive(false);
      return;
    }
    setHeroLive(true);
    if (!kitchen || !trial) return;
    setBusy(true);
    setError("");
    try {
      await updateDish(kitchen.id, trial.catalog_dish_id, {
        media: {
          url,
          is_hero: true,
          is_live_capture: true,
          captured_at: new Date().toISOString(),
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save live hero photo");
      setHeroLive(false);
    } finally {
      setBusy(false);
    }
  };

  const promote = async () => {
    if (!kitchen || !trialId) return;
    if (!heroLive) {
      setError("Capture a live hero photo before promoting — stock images cannot go live.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await promoteTrial(kitchen.id, trialId);
      setTrial(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Promote failed — need avg ≥ threshold");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen || !trial) {
    return (
      <OwnerPageShell
        eyebrow="Growth"
        title="Dish trial"
        backTo="/dashboard/learning"
        backLabel="← Back to learning"
      >
        <div className="app-loading">{error || "Loading trial…"}</div>
      </OwnerPageShell>
    );
  }

  const canPromote =
    trial.status !== "promoted" &&
    trial.avg_rating != null &&
    trial.avg_rating >= trial.rating_threshold;

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title={trial.dish_name}
      description="Trial dish — inactive on public menu until promoted"
      backTo="/dashboard/learning"
      backLabel="← Back to learning"
      meta={
        <div className="od-board__pills" style={{ marginTop: "0.75rem" }}>
          <span className={`status-badge status-badge--${trial.status === "promoted" ? "delivered" : "preparing"}`}>
            {trial.status}
          </span>
          {trial.avg_rating != null && (
            <span className="od-pill od-pill--sub">
              Avg {trial.avg_rating} / threshold {trial.rating_threshold}
            </span>
          )}
        </div>
      }
    >
      {error && <p className="form-error">{error}</p>}

      {trial.status === "draft" && (
        <OwnerPanel
          title="Select sample customers"
          description="Pick 5–20 regulars from your CRM for WhatsApp sample offers"
        >
          <ul className="owner-crm-list">
            {customers.map((c) => {
              const cid = c.customer_id ?? c.id;
              return (
                <li key={c.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selected.has(cid)}
                      onChange={() => toggleCustomer(cid)}
                    />
                    {c.customer_name ?? "Customer"} · {c.order_count} orders
                  </label>
                </li>
              );
            })}
          </ul>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={saveInvites}>
            Save invites ({selected.size})
          </button>
        </OwnerPanel>
      )}

      {trial.invite_count >= 5 && trial.status !== "promoted" && !trial.whatsapp_sent_at && (
        <OwnerPanel title="Send sample offers">
          <p className="owner-muted">
            WhatsApp blast to {trial.invite_count} customers — free sample trial.
          </p>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={sendSamples}>
            Send via WhatsApp
          </button>
        </OwnerPanel>
      )}

      {trial.invites.length > 0 && (
        <OwnerPanel title="Sample feedback">
          <ul className="owner-detail-items">
            {trial.invites.map((inv) => (
              <li key={inv.id}>
                <span>
                  {inv.customer_name ?? inv.customer_phone_masked} — {inv.status}
                  {inv.home_taste_score != null && ` · taste ${inv.home_taste_score} / quality ${inv.quality_score}`}
                </span>
                {inv.status === "sent" && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={busy}
                    onClick={() => rateInvite(inv.id, 5, 4)}
                  >
                    Log 5★ sample rating
                  </button>
                )}
              </li>
            ))}
          </ul>
        </OwnerPanel>
      )}

      {trial.status !== "promoted" && (
        <OwnerPanel
          title="Live-capture dish hero"
          description="Truth in media — replace the curated stock photo with a camera capture before promote."
        >
          <LiveCapturePhotoField
            kitchenId={kitchen.id}
            context="dish"
            requireLiveCapture
            value={heroUrl}
            onChange={onHeroCapture}
            label="Trial dish hero"
          />
          {heroLive && <p className="report-hint">Live hero saved on the trial dish.</p>}
        </OwnerPanel>
      )}

      {canPromote && (
        <OwnerPanel title="Promote to official menu">
          <p className="owner-muted">
            Average home-taste rating meets your threshold — activate this dish on your public menu.
            {!heroLive && " Capture a live hero photo above first."}
          </p>
          <button type="button" className="btn btn--primary" disabled={busy || !heroLive} onClick={promote}>
            Promote dish
          </button>
        </OwnerPanel>
      )}

      {trial.status === "promoted" && (
        <div className="auth-card__success">
          Promoted to your menu — customers can now order {trial.dish_name}.
        </div>
      )}
    </OwnerPageShell>
  );
}
