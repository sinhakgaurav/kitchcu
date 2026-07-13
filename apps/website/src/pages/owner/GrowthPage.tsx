import { useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  dismissGrowthSuggestion,
  fetchDishCombos,
  fetchGrowthSuggestions,
  fetchMenu,
  fetchOrderPatterns,
  generateGrowthSuggestions,
  pushDailyMenu,
  type DishCombo,
  type GrowthSuggestion,
  type OrderPatternInsight,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function GrowthPage() {
  const { kitchen } = useKitchen();
  const [suggestions, setSuggestions] = useState<GrowthSuggestion[]>([]);
  const [combos, setCombos] = useState<DishCombo[]>([]);
  const [patterns, setPatterns] = useState<OrderPatternInsight | null>(null);
  const [dishOptions, setDishOptions] = useState<{ id: string; name: string }[]>([]);
  const [selectedDishes, setSelectedDishes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [error, setError] = useState("");
  const [pushResult, setPushResult] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [sug, comboRes, pat, menu] = await Promise.all([
        fetchGrowthSuggestions(kitchen.id),
        fetchDishCombos(kitchen.id),
        fetchOrderPatterns(kitchen.id),
        fetchMenu(kitchen.id),
      ]);
      setSuggestions(sug.suggestions);
      setCombos(comboRes.combos);
      setPatterns(pat);
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
          <OwnerPanel title="Suggestions" description="AI-powered actions from your order data">
            {suggestions.length === 0 ? (
              <OwnerEmpty message="No active suggestions — click Generate to analyze your orders." />
            ) : (
              <ul className="report-rank">
                {suggestions.map((s) => (
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
