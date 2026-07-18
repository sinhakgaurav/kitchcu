import { useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  dismissGrowthSuggestion,
  fetchDishCombos,
  fetchGoldenRecipes,
  fetchGrowthSuggestions,
  fetchMenu,
  fetchOrderPatterns,
  generateGrowthSuggestions,
  pushDailyMenu,
  saveGoldenRecipe,
  type DishCombo,
  type GoldenRecipePin,
  type GrowthSuggestion,
  type OrderPatternInsight,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

function isGolden(s: GrowthSuggestion) {
  return s.suggestion_type === "golden_performance_day";
}

export function GrowthPage() {
  const { kitchen } = useKitchen();
  const [suggestions, setSuggestions] = useState<GrowthSuggestion[]>([]);
  const [combos, setCombos] = useState<DishCombo[]>([]);
  const [patterns, setPatterns] = useState<OrderPatternInsight | null>(null);
  const [goldenPins, setGoldenPins] = useState<GoldenRecipePin[]>([]);
  const [dishOptions, setDishOptions] = useState<{ id: string; name: string }[]>([]);
  const [selectedDishes, setSelectedDishes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [pushResult, setPushResult] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [sug, comboRes, pat, menu, pins] = await Promise.all([
        fetchGrowthSuggestions(kitchen.id),
        fetchDishCombos(kitchen.id),
        fetchOrderPatterns(kitchen.id),
        fetchMenu(kitchen.id),
        fetchGoldenRecipes(kitchen.id),
      ]);
      setSuggestions(sug.suggestions);
      setCombos(comboRes.combos);
      setPatterns(pat);
      setGoldenPins(pins.pins);
      const dishes = menu.dishes
        .filter((d) => d.is_active)
        .map((d) => ({ id: d.id, name: d.name }));
      setDishOptions(dishes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load growth data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const onGenerate = async () => {
    if (!kitchen) return;
    setGenerating(true);
    setError("");
    try {
      const res = await generateGrowthSuggestions(kitchen.id);
      setSuggestions((prev) => [...res.suggestions, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate suggestions");
    } finally {
      setGenerating(false);
    }
  };

  const onDismiss = async (id: string) => {
    if (!kitchen) return;
    try {
      await dismissGrowthSuggestion(kitchen.id, id);
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not dismiss");
    }
  };

  const onSaveGolden = async (id: string) => {
    if (!kitchen) return;
    setSavingId(id);
    setError("");
    try {
      const pin = await saveGoldenRecipe(kitchen.id, id);
      setGoldenPins((prev) => [pin, ...prev.filter((p) => p.id !== pin.id)]);
      setSuggestions((prev) =>
        prev.map((s) =>
          s.id === id
            ? { ...s, action_payload: { ...s.action_payload, recipe_saved: true } }
            : s,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save golden recipe");
    } finally {
      setSavingId(null);
    }
  };

  const onPushMenu = async () => {
    if (!kitchen || selectedDishes.length === 0) return;
    setPushing(true);
    setPushResult("");
    setError("");
    try {
      const res = await pushDailyMenu(kitchen.id, { dish_ids: selectedDishes });
      setPushResult(
        `Queued WhatsApp blast to ${res.recipient_count} CRM contact(s): ${res.message}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not queue daily menu push");
    } finally {
      setPushing(false);
    }
  };

  const toggleDish = (id: string) => {
    setSelectedDishes((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id].slice(0, 10),
    );
  };

  if (!kitchen) return null;

  const goldenSuggestions = suggestions.filter(isGolden);
  const otherSuggestions = suggestions.filter((s) => !isGolden(s));

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title="Growth intelligence"
      description="Actionable suggestions, dish combos & daily menu WhatsApp push"
      actions={
        <button type="button" className="btn btn--primary" onClick={onGenerate} disabled={generating}>
          {generating ? "Generating…" : "Generate suggestions"}
        </button>
      }
    >
      {error && <div className="auth-card__error">{error}</div>}
      {pushResult && <div className="auth-card__success">{pushResult}</div>}
      {loading ? (
        <div className="app-loading">Loading growth insights…</div>
      ) : (
        <>
          {(goldenSuggestions.length > 0 || goldenPins.length > 0) && (
            <OwnerPanel
              title="Golden performance days"
              description="Peak order days with strong ratings & positive comments — save that recipe"
            >
              {goldenSuggestions.length > 0 && (
                <ul className="report-rank golden-day-list">
                  {goldenSuggestions.map((s) => {
                    const saved = Boolean(s.action_payload.recipe_saved);
                    const qty = Number(s.action_payload.order_qty ?? 0);
                    const rating = s.action_payload.avg_rating;
                    return (
                      <li key={s.id} className="golden-day-card">
                        <div className="report-rank__row">
                          <span>
                            <strong>{s.title}</strong>
                            <span className="report-rank__meta">
                              {" "}
                              · {qty} portions
                              {rating != null ? ` · ${Number(rating).toFixed(1)}★` : ""}
                            </span>
                          </span>
                          <div className="golden-day-card__actions">
                            {!saved && (
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                disabled={savingId === s.id}
                                onClick={() => onSaveGolden(s.id)}
                              >
                                {savingId === s.id ? "Saving…" : "Save recipe"}
                              </button>
                            )}
                            {saved && <span className="golden-day-badge">Saved</span>}
                            <button type="button" className="btn btn--ghost btn--sm" onClick={() => onDismiss(s.id)}>
                              Dismiss
                            </button>
                          </div>
                        </div>
                        <p className="report-hint">{s.description}</p>
                      </li>
                    );
                  })}
                </ul>
              )}
              {goldenPins.length > 0 && (
                <ul className="report-rank" style={{ marginTop: goldenSuggestions.length ? "1rem" : 0 }}>
                  {goldenPins.map((p) => (
                    <li key={p.id}>
                      <div className="report-rank__row">
                        <span>
                          <strong>{p.dish_name}</strong>
                          <span className="report-rank__meta">
                            {" "}
                            · pinned {p.performance_date}
                            {p.recipe_snapshot.lines?.length
                              ? ` · ${p.recipe_snapshot.lines.length} ingredients`
                              : ""}
                          </span>
                        </span>
                        <span className="golden-day-badge">Golden baseline</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </OwnerPanel>
          )}

          <OwnerPanel title="Suggestions" description="AI-powered actions from your order data">
            {otherSuggestions.length === 0 ? (
              <OwnerEmpty message="No active suggestions — click Generate to analyze your orders." />
            ) : (
              <ul className="report-rank">
                {otherSuggestions.map((s) => (
                  <li key={s.id}>
                    <div className="report-rank__row">
                      <span>
                        <strong>{s.title}</strong>
                        <span className="report-rank__meta"> · {s.suggestion_type}</span>
                      </span>
                      <button type="button" className="btn btn--ghost" onClick={() => onDismiss(s.id)}>
                        Dismiss
                      </button>
                    </div>
                    <p className="report-hint">{s.description}</p>
                  </li>
                ))}
              </ul>
            )}
          </OwnerPanel>

          <div className="report-grid">
            <OwnerPanel title="Top dish combos" description="Frequently ordered together">
              {combos.length === 0 ? (
                <OwnerEmpty message="Need more multi-item orders to detect combos." />
              ) : (
                <ul className="report-rank">
                  {combos.map((c) => (
                    <li key={`${c.dish_a_id}-${c.dish_b_id}`}>
                      <div className="report-rank__row">
                        <span>
                          {c.dish_a_name} + {c.dish_b_name}
                        </span>
                        <strong>{c.support_pct}%</strong>
                      </div>
                      <span className="report-rank__meta">{c.pair_count} orders together</span>
                    </li>
                  ))}
                </ul>
              )}
            </OwnerPanel>

            <OwnerPanel title="Order patterns" description="Busiest days of the week">
              {patterns ? (
                <>
                  <p className="report-hint">{patterns.insight}</p>
                  {patterns.days.length > 0 && (
                    <table className="report-table">
                      <tbody>
                        {patterns.days.map((d) => (
                          <tr key={d.day_of_week}>
                            <td>{d.day_name}</td>
                            <td>{d.orders} orders</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              ) : (
                <OwnerEmpty message="No pattern data yet." />
              )}
            </OwnerPanel>
          </div>

          <OwnerPanel
            title="Daily menu WhatsApp push"
            description="Select today's dishes — we queue a blast to your CRM contacts (F39)"
          >
            <div className="owner-tabs" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
              {dishOptions.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  className={selectedDishes.includes(d.id) ? "active" : ""}
                  onClick={() => toggleDish(d.id)}
                >
                  {d.name}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="btn btn--primary"
              style={{ marginTop: "1rem" }}
              disabled={pushing || selectedDishes.length === 0}
              onClick={onPushMenu}
            >
              {pushing ? "Queuing…" : "Push to WhatsApp contacts"}
            </button>
          </OwnerPanel>
        </>
      )}
    </OwnerPageShell>
  );
}
