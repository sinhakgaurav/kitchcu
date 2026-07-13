import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchCrmCustomers,
  fetchDishTrial,
  promoteTrial,
  recordTrialRating,
  sendTrialSamples,
  setTrialInvites,
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

  const promote = async () => {
    if (!kitchen || !trialId) return;
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

  if (!trial) return <div className="owner-page app-loading">{error || "Loading trial…"}</div>;

  const canPromote =
    trial.status !== "promoted" &&
    trial.avg_rating != null &&
    trial.avg_rating >= trial.rating_threshold;

  return (
    <div className="owner-page">
      <Link to="/dashboard/learning" className="owner-back">← Back to learning</Link>

      <header className="owner-page__head">
        <div>
          <h1>{trial.dish_name}</h1>
          <p>
            Trial dish (inactive on public menu until promoted) ·{" "}
            <span className={`status-badge status-badge--${trial.status === "promoted" ? "delivered" : "preparing"}`}>
              {trial.status}
            </span>
          </p>
          {trial.avg_rating != null && (
            <p className="owner-page__code">
              Avg rating {trial.avg_rating} / threshold {trial.rating_threshold}
            </p>
          )}
        </div>
      </header>

      {error && <p className="owner-error">{error}</p>}

      {trial.status === "draft" && (
        <section className="glass owner-section">
          <h2>Select sample customers (5–20)</h2>
          <p className="owner-page__code">Pick regulars from your CRM for WhatsApp sample offers.</p>
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
        </section>
      )}

      {trial.invite_count >= 5 && trial.status !== "promoted" && !trial.whatsapp_sent_at && (
        <section className="glass owner-section">
          <h2>Send sample offers</h2>
          <p className="owner-page__code">
            WhatsApp blast to {trial.invite_count} customers — free sample trial.
          </p>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={sendSamples}>
            Send via WhatsApp
          </button>
        </section>
      )}

      {trial.invites.length > 0 && (
        <section className="glass owner-section">
          <h2>Sample feedback</h2>
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
        </section>
      )}

      {canPromote && (
        <section className="glass owner-section">
          <h2>Promote to official menu</h2>
          <p className="owner-page__code">
            Average home-taste rating meets your threshold — activate this dish on your public menu.
          </p>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={promote}>
            Promote dish
          </button>
        </section>
      )}

      {trial.status === "promoted" && (
        <p className="owner-success">Promoted to your menu — customers can now order {trial.dish_name}.</p>
      )}
    </div>
  );
}
