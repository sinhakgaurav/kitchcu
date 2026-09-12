import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchDishSuggestions,
  fetchOwnerDishes,
  fetchOwnerRatingSummaries,
  updateDishSuggestion,
  type DishRatingSummary,
  type DishSuggestion,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

function stars(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—";
  return `${n.toFixed(1)} / 5`;
}

export function RatingsPage() {
  const { kitchen } = useKitchen();
  const [summaries, setSummaries] = useState<DishRatingSummary[]>([]);
  const [suggestions, setSuggestions] = useState<DishSuggestion[]>([]);
  const [dishNames, setDishNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [replies, setReplies] = useState<Record<string, string>>({});

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [ratings, pending, dishes] = await Promise.all([
        fetchOwnerRatingSummaries(kitchen.id),
        fetchDishSuggestions(kitchen.id, "pending").catch(() => ({ suggestions: [] })),
        fetchOwnerDishes(kitchen.id).catch(() => ({ dishes: [], total: 0 })),
      ]);
      setSummaries(ratings.summaries);
      setSuggestions(pending.suggestions);
      const names: Record<string, string> = {};
      for (const dish of dishes.dishes) names[dish.id] = dish.name;
      setDishNames(names);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load ratings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [kitchen?.id]);

  const ranked = useMemo(
    () => [...summaries].sort((a, b) => b.overall_rating - a.overall_rating),
    [summaries],
  );

  const kitchenStats = useMemo(() => {
    const total = summaries.reduce((n, row) => n + row.rating_count, 0);
    if (!total) return null;
    const overall =
      summaries.reduce((n, row) => n + row.overall_rating * row.rating_count, 0) / total;
    const taste =
      summaries.reduce((n, row) => n + row.avg_home_taste * row.rating_count, 0) / total;
    const quality =
      summaries.reduce((n, row) => n + row.avg_quality * row.rating_count, 0) / total;
    return { total, overall, taste, quality };
  }, [summaries]);

  const decide = async (row: DishSuggestion, status: "accepted" | "rejected") => {
    if (!kitchen) return;
    setBusyId(row.id);
    setError("");
    try {
      const reply = replies[row.id]?.trim();
      const updated = await updateDishSuggestion(kitchen.id, row.id, {
        status,
        owner_response: reply || undefined,
      });
      setSuggestions((current) => current.filter((item) => item.id !== updated.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update suggestion");
    } finally {
      setBusyId(null);
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Grow"
      title="Ratings"
      description="Home-taste scores from delivered orders, plus customer dish suggestions to accept or reject."
      actions={
        <>
          <Link to="/dashboard/reports" className="btn btn--ghost btn--sm">Reports →</Link>
          <Link to="/dashboard/menu" className="btn btn--ghost btn--sm">Menu →</Link>
        </>
      }
    >
      {error && <div className="auth-card__error">{error}</div>}
      {loading ? (
        <p className="od-panel__empty dash-card od-panel">Loading ratings…</p>
      ) : (
        <>
          {kitchenStats && (
            <OwnerPanel title="Kitchen score" description="Weighted from verified purchase ratings">
              <p className="od-ratings__kitchen-score">
                <strong>{stars(kitchenStats.overall)}</strong>
                <span className="report-rank__meta">
                  Taste {stars(kitchenStats.taste)} · Quality {stars(kitchenStats.quality)} ·{" "}
                  {kitchenStats.total} rating{kitchenStats.total === 1 ? "" : "s"}
                </span>
              </p>
            </OwnerPanel>
          )}

          <OwnerPanel title="Dish scores" description="Verified purchase ratings only">
            {ranked.length === 0 ? (
              <OwnerEmpty message="No ratings yet — scores appear after delivered orders are rated." />
            ) : (
              <ul className="report-rank od-ratings__list">
                {ranked.map((row) => (
                  <li key={row.dish_id}>
                    <div className="report-rank__row">
                      <span>{dishNames[row.dish_id] ?? "Dish"}</span>
                      <strong>{stars(row.overall_rating)}</strong>
                    </div>
                    <span className="report-rank__meta">
                      Taste {stars(row.avg_home_taste)} · Quality {stars(row.avg_quality)} ·{" "}
                      {row.rating_count} rating{row.rating_count === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </OwnerPanel>

          <OwnerPanel title="Pending suggestions" description="Customers asking for a dish change or new item">
            {suggestions.length === 0 ? (
              <p className="od-panel__empty">No pending suggestions.</p>
            ) : (
              <ul className="od-ratings__suggestions">
                {suggestions.map((row) => (
                  <li key={row.id} className="dash-card od-ratings__card">
                    <p className="od-ratings__dish">{dishNames[row.dish_id] ?? "Dish"}</p>
                    <p>{row.suggestion_text}</p>
                    <label className="kc-field">
                      <span className="kc-field__label">Reply (optional)</span>
                      <input
                        className="kc-input"
                        value={replies[row.id] ?? ""}
                        onChange={(e) =>
                          setReplies((current) => ({ ...current, [row.id]: e.target.value }))
                        }
                        placeholder="Thanks — we'll try this next week"
                      />
                    </label>
                    <div className="owner-forms__actions">
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={busyId === row.id}
                        onClick={() => void decide(row, "accepted")}
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busyId === row.id}
                        onClick={() => void decide(row, "rejected")}
                      >
                        Reject
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </OwnerPanel>
        </>
      )}
    </OwnerPageShell>
  );
}
