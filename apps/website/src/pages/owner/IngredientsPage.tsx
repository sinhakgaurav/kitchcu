import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ListingToolbar } from "../../components/ListingToolbar";
import { LiveCapturePhotoField } from "../../components/LiveCapturePhotoField";
import { RichTextEditor } from "../../components/RichTextEditor";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  adjustIngredientStock,
  createIngredient,
  fetchDishRecipe,
  fetchGoldenRecipes,
  fetchGrowthSuggestions,
  fetchIngredients,
  fetchMenu,
  saveDishRecipe,
  type DishRecipe,
  type GoldenRecipePin,
  type GrowthSuggestion,
  type Ingredient,
  type PrepStep,
  type RecipeLine,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const EMPTY_LINE = (): RecipeLine => ({
  ingredient_id: "",
  ingredient_name: "",
  quantity: 10,
  unit: "g",
  photo_url: "",
  sort_order: 0,
});

const EMPTY_STEP = (order: number): PrepStep => ({
  step_order: order,
  title: "",
  body_html: "",
  photo_url: "",
  duration_min: undefined,
});

export function IngredientsPage() {
  const { kitchen } = useKitchen();
  const [searchParams] = useSearchParams();
  const dishFromUrl = searchParams.get("dish") ?? "";
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [dishes, setDishes] = useState<{ id: string; name: string }[]>([]);
  const [selectedDishId, setSelectedDishId] = useState("");
  const [recipe, setRecipe] = useState<DishRecipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pantrySearch, setPantrySearch] = useState("");
  const [pantrySort, setPantrySort] = useState<"name_asc" | "name_desc" | "stock_asc" | "stock_desc">("name_asc");
  const [pantryFilter, setPantryFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const [dishGolden, setDishGolden] = useState<GrowthSuggestion | GoldenRecipePin | null>(null);

  const [newName, setNewName] = useState("");
  const [newUnit, setNewUnit] = useState("g");
  const [newStock, setNewStock] = useState("500");
  const [newThreshold, setNewThreshold] = useState("50");
  const [newPhoto, setNewPhoto] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [ingRes, menu] = await Promise.all([
        fetchIngredients(kitchen.id),
        fetchMenu(kitchen.id),
      ]);
      setIngredients(ingRes.ingredients);
      const active = menu.dishes.filter((d) => d.is_active).map((d) => ({ id: d.id, name: d.name }));
      setDishes(active);
      if (dishFromUrl && active.some((d) => d.id === dishFromUrl)) {
        setSelectedDishId(dishFromUrl);
      } else if (!selectedDishId && active[0]) {
        setSelectedDishId(active[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ingredients");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  useEffect(() => {
    if (!kitchen || !selectedDishId) return;
    fetchDishRecipe(kitchen.id, selectedDishId)
      .then((r) => {
        setRecipe({
          ...r,
          lines: r.lines.length ? r.lines : [],
          prep_steps: r.prep_steps?.length ? r.prep_steps : [],
        });
      })
      .catch(() =>
        setRecipe({
          dish_id: selectedDishId,
          dish_name: dishes.find((d) => d.id === selectedDishId)?.name ?? "",
          lines: [],
          prep_steps: [],
        }),
      );
    Promise.all([
      fetchGoldenRecipes(kitchen.id, selectedDishId).catch(() => ({ pins: [] as GoldenRecipePin[] })),
      fetchGrowthSuggestions(kitchen.id).catch(() => ({ suggestions: [] as GrowthSuggestion[] })),
    ]).then(([pins, sug]) => {
      if (pins.pins[0]) {
        setDishGolden(pins.pins[0]);
        return;
      }
      const hit = sug.suggestions.find(
        (s) =>
          s.suggestion_type === "golden_performance_day" &&
          String(s.action_payload.dish_id) === selectedDishId,
      );
      setDishGolden(hit ?? null);
    });
  }, [kitchen, selectedDishId, dishes]);

  const onAddIngredient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen || !newName.trim()) return;
    setBusy(true);
    setError("");
    try {
      const row = await createIngredient(kitchen.id, {
        name: newName.trim(),
        unit: newUnit,
        current_stock: Number(newStock) || 0,
        low_stock_threshold: Number(newThreshold) || 0,
        photo_url: newPhoto.trim() || undefined,
      });
      setIngredients((prev) => [...prev, row].sort((a, b) => a.name.localeCompare(b.name)));
      setNewName("");
      setNewPhoto("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add ingredient");
    } finally {
      setBusy(false);
    }
  };

  const onAdjust = async (ingredientId: string, delta: number) => {
    if (!kitchen) return;
    setBusy(true);
    try {
      const updated = await adjustIngredientStock(kitchen.id, ingredientId, {
        delta,
        reason: delta > 0 ? "Manual restock" : "Manual adjustment",
      });
      setIngredients((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Adjust failed");
    } finally {
      setBusy(false);
    }
  };

  const onSaveRecipe = async () => {
    if (!kitchen || !selectedDishId || !recipe) return;
    setBusy(true);
    setError("");
    setSavedMsg("");
    try {
      const saved = await saveDishRecipe(kitchen.id, selectedDishId, {
        lines: recipe.lines
          .filter((l) => l.ingredient_id)
          .map((l, idx) => ({
            ingredient_id: l.ingredient_id,
            quantity: l.quantity,
            unit: l.unit,
            photo_url: l.photo_url || undefined,
            sort_order: idx,
          })),
        prep_steps: recipe.prep_steps.map((s, idx) => ({
          step_order: s.step_order || idx + 1,
          title: s.title || undefined,
          body_html: s.body_html,
          photo_url: s.photo_url || undefined,
          duration_min: s.duration_min,
        })),
      });
      setRecipe(saved);
      setSavedMsg("Recipe and prep steps saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save recipe");
    } finally {
      setBusy(false);
    }
  };

  const addRecipeLine = () => {
    const first = ingredients[0];
    setRecipe((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        lines: [
          ...prev.lines,
          {
            ...EMPTY_LINE(),
            ingredient_id: first?.id ?? "",
            ingredient_name: first?.name ?? "",
            unit: first?.unit ?? "g",
            sort_order: prev.lines.length,
          },
        ],
      };
    });
  };

  const addPrepStep = () => {
    setRecipe((prev) => {
      if (!prev) return prev;
      const nextOrder = prev.prep_steps.length + 1;
      return { ...prev, prep_steps: [...prev.prep_steps, EMPTY_STEP(nextOrder)] };
    });
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    setRecipe((prev) => {
      if (!prev) return prev;
      const target = index + direction;
      if (target < 0 || target >= prev.prep_steps.length) return prev;
      const steps = [...prev.prep_steps];
      [steps[index], steps[target]] = [steps[target], steps[index]];
      return {
        ...prev,
        prep_steps: steps.map((s, i) => ({ ...s, step_order: i + 1 })),
      };
    });
  };

  const shownIngredients = useMemo(() => {
    let list = [...ingredients];
    if (pantrySearch.trim()) {
      const n = pantrySearch.trim().toLowerCase();
      list = list.filter((i) => i.name.toLowerCase().includes(n) || i.unit.toLowerCase().includes(n));
    }
    if (pantryFilter === "low") list = list.filter((i) => i.is_low);
    list.sort((a, b) => {
      if (pantrySort === "name_desc") return b.name.localeCompare(a.name);
      if (pantrySort === "stock_asc") return a.current_stock - b.current_stock;
      if (pantrySort === "stock_desc") return b.current_stock - a.current_stock;
      return a.name.localeCompare(b.name);
    });
    return list;
  }, [ingredients, pantrySearch, pantrySort, pantryFilter]);

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Operations"
      title="Ingredient mapper"
      description="Recipe standards, prep steps with photos, and stock tracking (F19)"
    >
      {error && <p className="form-error">{error}</p>}
      {savedMsg && <div className="auth-card__success">{savedMsg}</div>}
      {loading ? (
        <div className="app-loading">Loading pantry…</div>
      ) : (
        <>
          <OwnerPanel title="Pantry stock" description="Track ingredients and low-stock alerts">
            <form className="owner-form owner-form--grid" onSubmit={onAddIngredient}>
              <label>
                Name
                <input value={newName} onChange={(e) => setNewName(e.target.value)} required placeholder="Garam masala" />
              </label>
              <label>
                Unit
                <select value={newUnit} onChange={(e) => setNewUnit(e.target.value)}>
                  <option value="g">g</option>
                  <option value="ml">ml</option>
                  <option value="pcs">pcs</option>
                </select>
              </label>
              <label>
                Stock
                <input type="number" min={0} value={newStock} onChange={(e) => setNewStock(e.target.value)} />
              </label>
              <label>
                Low threshold
                <input type="number" min={0} value={newThreshold} onChange={(e) => setNewThreshold(e.target.value)} />
              </label>
              <div className="owner-form__wide">
                <LiveCapturePhotoField
                  kitchenId={kitchen.id}
                  context="ingredient"
                  label="Reference photo"
                  value={newPhoto}
                  onChange={setNewPhoto}
                />
              </div>
              <div className="owner-form__actions owner-form__wide">
                <button type="submit" className="btn btn--primary" disabled={busy}>
                  Add ingredient
                </button>
              </div>
            </form>

            <ListingToolbar
              search={pantrySearch}
              onSearchChange={setPantrySearch}
              searchPlaceholder="Search pantry…"
              sort={pantrySort}
              onSortChange={(v) => setPantrySort(v as typeof pantrySort)}
              sortOptions={[
                { value: "name_asc", label: "Name A–Z" },
                { value: "name_desc", label: "Name Z–A" },
                { value: "stock_asc", label: "Stock ↑" },
                { value: "stock_desc", label: "Stock ↓" },
              ]}
              filterChips={[{ id: "low", label: "Low stock" }]}
              activeFilter={pantryFilter}
              onFilterChange={setPantryFilter}
              resultCount={shownIngredients.length}
            />
            <div className="owner-table-wrap">
              <table className="owner-table">
                <thead>
                  <tr>
                    <th>Photo</th>
                    <th>Name</th>
                    <th>Stock</th>
                    <th>Low at</th>
                    <th>Status</th>
                    <th>Adjust</th>
                  </tr>
                </thead>
                <tbody>
                  {shownIngredients.map((ing) => (
                    <tr key={ing.id} className={ing.is_low ? "owner-row--warn" : undefined}>
                      <td>
                        {ing.photo_url ? (
                          <img src={ing.photo_url} alt="" className="owner-thumb" onError={(e) => {
                            (e.currentTarget as HTMLImageElement).style.display = "none";
                          }} />
                        ) : (
                          <span className="owner-thumb owner-thumb--empty">—</span>
                        )}
                      </td>
                      <td>
                        {ing.name} <small>({ing.unit})</small>
                      </td>
                      <td>{ing.current_stock}</td>
                      <td>{ing.low_stock_threshold}</td>
                      <td>{ing.is_low ? "Low" : "OK"}</td>
                      <td>
                        <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onAdjust(ing.id, 100)}>
                          +100
                        </button>
                        <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onAdjust(ing.id, -10)}>
                          −10
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </OwnerPanel>

          <OwnerPanel title="Dish recipe & prep" description="Standard portions and preparation steps">
            <div className="owner-form">
            <label>
              Dish
              <select value={selectedDishId} onChange={(e) => setSelectedDishId(e.target.value)}>
                {dishes.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>

            {dishGolden && (
              <div className="owner-dish-card__golden" style={{ marginTop: "0.75rem" }}>
                <span className="golden-day-badge">
                  {"performance_date" in dishGolden && "recipe_snapshot" in dishGolden
                    ? "Golden recipe saved"
                    : "Golden day"}
                </span>
                <p>
                  {"performance_date" in dishGolden && "recipe_snapshot" in dishGolden
                    ? `Pinned baseline from ${dishGolden.performance_date} — keep this ingredient mix as your reference.`
                    : String((dishGolden as GrowthSuggestion).description).slice(0, 140) + "…"}
                </p>
                <Link to="/dashboard/growth" className="od-panel__link">
                  Open Growth →
                </Link>
              </div>
            )}

            {recipe && (
              <>
                <h3 className="owner-subhead">Ingredients (per portion)</h3>
                <div className="owner-recipe-cards">
                  {recipe.lines.map((line, idx) => (
                    <div key={`line-${idx}`} className="owner-recipe-card">
                      <div className="owner-recipe-card__row">
                        <label>
                          Ingredient
                          <select
                            value={line.ingredient_id}
                            onChange={(e) => {
                              const ing = ingredients.find((i) => i.id === e.target.value);
                              setRecipe((prev) => {
                                if (!prev) return prev;
                                const lines = [...prev.lines];
                                lines[idx] = {
                                  ...lines[idx],
                                  ingredient_id: e.target.value,
                                  ingredient_name: ing?.name ?? "",
                                  unit: ing?.unit ?? lines[idx].unit,
                                  photo_url: lines[idx].photo_url || ing?.photo_url || "",
                                };
                                return { ...prev, lines };
                              });
                            }}
                          >
                            <option value="">Select…</option>
                            {ingredients.map((ing) => (
                              <option key={ing.id} value={ing.id}>
                                {ing.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Qty
                          <input
                            type="number"
                            min={0.1}
                            step={0.1}
                            value={line.quantity}
                            onChange={(e) => {
                              const qty = Number(e.target.value);
                              setRecipe((prev) => {
                                if (!prev) return prev;
                                const lines = [...prev.lines];
                                lines[idx] = { ...lines[idx], quantity: qty };
                                return { ...prev, lines };
                              });
                            }}
                          />
                        </label>
                        <label>
                          Unit
                          <select
                            value={line.unit}
                            onChange={(e) => {
                              setRecipe((prev) => {
                                if (!prev) return prev;
                                const lines = [...prev.lines];
                                lines[idx] = { ...lines[idx], unit: e.target.value };
                                return { ...prev, lines };
                              });
                            }}
                          >
                            <option value="g">g</option>
                            <option value="ml">ml</option>
                            <option value="pcs">pcs</option>
                          </select>
                        </label>
                      </div>
                      <LiveCapturePhotoField
                        kitchenId={kitchen.id}
                        context="ingredient"
                        label="Portion photo"
                        value={line.photo_url ?? ""}
                        onChange={(url) => {
                          setRecipe((prev) => {
                            if (!prev) return prev;
                            const lines = [...prev.lines];
                            lines[idx] = { ...lines[idx], photo_url: url };
                            return { ...prev, lines };
                          });
                        }}
                      />
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() =>
                          setRecipe((prev) =>
                            prev ? { ...prev, lines: prev.lines.filter((_, i) => i !== idx) } : prev,
                          )
                        }
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <button type="button" className="btn btn--ghost" onClick={addRecipeLine} disabled={!ingredients.length}>
                  + Add ingredient line
                </button>

                <h3 className="owner-subhead">Preparation steps</h3>
                <div className="owner-prep-steps">
                  {recipe.prep_steps.map((step, idx) => (
                    <div key={`step-${idx}`} className="owner-prep-step">
                      <div className="owner-prep-step__head">
                        <strong>Step {step.step_order || idx + 1}</strong>
                        <div className="owner-prep-step__move">
                          <button type="button" className="btn btn--ghost btn--sm" onClick={() => moveStep(idx, -1)}>
                            ↑
                          </button>
                          <button type="button" className="btn btn--ghost btn--sm" onClick={() => moveStep(idx, 1)}>
                            ↓
                          </button>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() =>
                              setRecipe((prev) =>
                                prev
                                  ? {
                                      ...prev,
                                      prep_steps: prev.prep_steps
                                        .filter((_, i) => i !== idx)
                                        .map((s, i) => ({ ...s, step_order: i + 1 })),
                                    }
                                  : prev,
                              )
                            }
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                      <label>
                        Step title
                        <input
                          value={step.title ?? ""}
                          placeholder="Marinate paneer"
                          onChange={(e) => {
                            const title = e.target.value;
                            setRecipe((prev) => {
                              if (!prev) return prev;
                              const prep_steps = [...prev.prep_steps];
                              prep_steps[idx] = { ...prep_steps[idx], title };
                              return { ...prev, prep_steps };
                            });
                          }}
                        />
                      </label>
                      <label>
                        Duration (min)
                        <input
                          type="number"
                          min={0}
                          value={step.duration_min ?? ""}
                          onChange={(e) => {
                            const duration_min = e.target.value ? Number(e.target.value) : undefined;
                            setRecipe((prev) => {
                              if (!prev) return prev;
                              const prep_steps = [...prev.prep_steps];
                              prep_steps[idx] = { ...prep_steps[idx], duration_min };
                              return { ...prev, prep_steps };
                            });
                          }}
                        />
                      </label>
                      <div className="kc-field">
                        <span className="kc-field__label">Instructions (rich text)</span>
                        <RichTextEditor
                          value={step.body_html}
                          onChange={(html) => {
                            setRecipe((prev) => {
                              if (!prev) return prev;
                              const prep_steps = [...prev.prep_steps];
                              prep_steps[idx] = { ...prep_steps[idx], body_html: html };
                              return { ...prev, prep_steps };
                            });
                          }}
                          kitchenId={kitchen.id}
                          uploadContext="prep_step"
                          placeholder="Describe this step — quality notes, temperature, timing…"
                          minHeight={110}
                        />
                      </div>
                      <LiveCapturePhotoField
                        kitchenId={kitchen.id}
                        context="prep_step"
                        label="Step photo"
                        value={step.photo_url ?? ""}
                        onChange={(url) => {
                          setRecipe((prev) => {
                            if (!prev) return prev;
                            const prep_steps = [...prev.prep_steps];
                            prep_steps[idx] = { ...prep_steps[idx], photo_url: url };
                            return { ...prev, prep_steps };
                          });
                        }}
                      />
                    </div>
                  ))}
                </div>
                <button type="button" className="btn btn--ghost" onClick={addPrepStep}>
                  + Add prep step
                </button>

                <div className="owner-actions">
                  <button type="button" className="btn btn--primary" onClick={onSaveRecipe} disabled={busy}>
                    {busy ? "Saving…" : "Save recipe & prep steps"}
                  </button>
                </div>
              </>
            )}
            </div>
          </OwnerPanel>
        </>
      )}
    </OwnerPageShell>
  );
}
