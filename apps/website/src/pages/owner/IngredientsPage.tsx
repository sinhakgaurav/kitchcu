import { useEffect, useMemo, useRef, useState } from "react";
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
  fetchOwnerDishes,
  saveDishRecipe,
  updateDish,
  updateIngredient,
  type DishRecipe,
  type GoldenRecipePin,
  type GrowthSuggestion,
  type Ingredient,
  type PrepStep,
  type RecipeLine,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { useTranslation } from "react-i18next";
import {
  applyPantryToUnmappedLines,
  mergeDishIngredientsWithRecipe,
  parseDishIngredientTokens,
  type MapperRecipeLine,
} from "../../shared/ingredientMapper";

type OwnerDishOpt = {
  id: string;
  name: string;
  is_active: boolean;
  ingredients_description: string | null;
};

type MapperRecipe = Omit<DishRecipe, "lines"> & { lines: MapperRecipeLine[] };

const PCS = new Set(["pcs", "pc", "piece", "pieces"]);

function estimateLineKcal(
  ingredient: Ingredient | undefined,
  quantity: number,
  recipeUnit: string,
): number | null {
  if (!ingredient || ingredient.kcal_per_100 == null) return null;
  const kcal = Number(ingredient.kcal_per_100);
  const qty = Math.max(Number(quantity) || 0, 0);
  const pantry = (ingredient.unit || "g").trim().toLowerCase();
  const recipe = (recipeUnit || pantry).trim().toLowerCase();
  if (PCS.has(pantry)) {
    if (PCS.has(recipe)) return Math.round(kcal * qty * 10) / 10;
    const grams = recipe === "g" || recipe === "ml" ? qty : qty * 50;
    return Math.round(kcal * (grams / 50) * 10) / 10;
  }
  const grams = PCS.has(recipe) ? qty * 50 : qty;
  return Math.round(kcal * (grams / 100) * 10) / 10;
}

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
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const [searchParams, setSearchParams] = useSearchParams();
  const dishFromUrl = searchParams.get("dish") ?? "";
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [dishes, setDishes] = useState<OwnerDishOpt[]>([]);
  const [selectedDishId, setSelectedDishId] = useState("");
  const [recipe, setRecipe] = useState<MapperRecipe | null>(null);
  const [focusStockId, setFocusStockId] = useState("");
  const newNameRef = useRef<HTMLInputElement>(null);
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
  const [newBrand, setNewBrand] = useState("");
  const [newPackSize, setNewPackSize] = useState("");
  const [newPackLabel, setNewPackLabel] = useState("");
  const [newKcal, setNewKcal] = useState("");
  const [caloriesNote, setCaloriesNote] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [ingRes, ownerMenu] = await Promise.all([
        fetchIngredients(kitchen.id),
        fetchOwnerDishes(kitchen.id),
      ]);
      setIngredients(ingRes.ingredients);
      const allDishes = ownerMenu.dishes.map((d) => ({
        id: d.id,
        name: d.name,
        is_active: d.is_active,
        ingredients_description: d.ingredients_description,
      }));
      setDishes(allDishes);
      if (dishFromUrl && allDishes.some((d) => d.id === dishFromUrl)) {
        setSelectedDishId(dishFromUrl);
      } else if (!selectedDishId && allDishes[0]) {
        setSelectedDishId(allDishes[0].id);
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

  const selectedDish = dishes.find((d) => d.id === selectedDishId);
  const dishTokens = useMemo(
    () => parseDishIngredientTokens(selectedDish?.ingredients_description),
    [selectedDish?.ingredients_description],
  );

  const bindRecipeLines = (lines: RecipeLine[]): MapperRecipeLine[] =>
    mergeDishIngredientsWithRecipe(dishTokens, lines, ingredients);

  useEffect(() => {
    if (!kitchen || !selectedDishId) return;
    fetchDishRecipe(kitchen.id, selectedDishId)
      .then((r) => {
        setRecipe({
          ...r,
          lines: bindRecipeLines(r.lines),
          prep_steps: r.prep_steps?.length ? r.prep_steps : [],
        });
        setCaloriesNote(r.calories_description ?? "");
      })
      .catch(() => {
        setCaloriesNote("");
        setRecipe({
          dish_id: selectedDishId,
          dish_name: dishes.find((d) => d.id === selectedDishId)?.name ?? "",
          lines: bindRecipeLines([]),
          prep_steps: [],
        });
      });
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

  useEffect(() => {
    if (loading) return;
    const hash = window.location.hash.replace("#", "");
    const target = hash || (dishFromUrl ? "recipe-map" : "");
    if (!target) return;
    const el = document.getElementById(target);
    if (!el) return;
    if (target.startsWith("stock-")) setFocusStockId(target.slice("stock-".length));
    requestAnimationFrame(() => el.scrollIntoView({ behavior: "smooth", block: "start" }));
  }, [loading, selectedDishId, dishFromUrl]);

  const selectDish = (id: string) => {
    setSelectedDishId(id);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (id) next.set("dish", id);
      else next.delete("dish");
      return next;
    }, { replace: true });
  };

  const goToStock = (ingredientId?: string) => {
    const target = ingredientId ? `stock-${ingredientId}` : "pantry-stock";
    setFocusStockId(ingredientId ?? "");
    const el = document.getElementById(target);
    el?.scrollIntoView({ behavior: "smooth", block: ingredientId ? "center" : "start" });
  };

  const addToPantryFromToken = (name: string) => {
    setNewName(name);
    goToStock();
    requestAnimationFrame(() => newNameRef.current?.focus());
  };

  const onAddIngredient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen || !newName.trim()) return;
    setBusy(true);
    setError("");
    try {
      const packSize = Number(newPackSize);
      const row = await createIngredient(kitchen.id, {
        name: newName.trim(),
        unit: newUnit,
        current_stock: Number(newStock) || 0,
        low_stock_threshold: Number(newThreshold) || 0,
        brand: newBrand.trim() || undefined,
        pack_size: packSize > 0 ? packSize : undefined,
        pack_label: newPackLabel.trim() || undefined,
        photo_url: newPhoto.trim() || undefined,
        kcal_per_100: newKcal.trim() ? Number(newKcal) : undefined,
      });
      const nextPantry = [...ingredients, row].sort((a, b) => a.name.localeCompare(b.name));
      setIngredients(nextPantry);
      setRecipe((prev) => (prev ? { ...prev, lines: applyPantryToUnmappedLines(prev.lines, nextPantry) } : prev));
      setNewName("");
      setNewPhoto("");
      setNewBrand("");
      setNewPackSize("");
      setNewPackLabel("");
      setNewKcal("");
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

  const onSaveKcal = async (ingredientId: string, kcalPer100: number | null) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const updated = await updateIngredient(kitchen.id, ingredientId, { kcal_per_100: kcalPer100 });
      setIngredients((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save kcal");
    } finally {
      setBusy(false);
    }
  };

  const recipeCalories = useMemo(() => {
    if (!recipe) return { kcal: null as number | null, incomplete: false, total: 0, mapped: 0 };
    const lines = recipe.lines.filter((l) => l.ingredient_id);
    let mapped = 0;
    let acc = 0;
    for (const line of lines) {
      const kcal = estimateLineKcal(
        ingredients.find((i) => i.id === line.ingredient_id),
        line.quantity,
        line.unit,
      );
      if (kcal == null) continue;
      mapped += 1;
      acc += kcal;
    }
    return {
      kcal: mapped ? Math.round(acc) : null,
      incomplete: mapped > 0 && mapped < lines.length,
      mapped,
      total: lines.length,
    };
  }, [recipe, ingredients]);

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
          duration_min: s.duration_min ?? undefined,
        })),
      });
      const note = caloriesNote.trim() || null;
      let next = saved;
      if ((saved.calories_description ?? null) !== note) {
        const dish = await updateDish(kitchen.id, selectedDishId, { calories_description: note });
        next = { ...saved, calories_description: dish.calories_description };
      }
      setRecipe(next);
      setCaloriesNote(next.calories_description ?? "");
      setSavedMsg("Recipe, calories, and prep steps saved.");
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
      list = list.filter(
        (i) =>
          i.name.toLowerCase().includes(n) ||
          i.unit.toLowerCase().includes(n) ||
          (i.brand ?? "").toLowerCase().includes(n) ||
          (i.pack_label ?? "").toLowerCase().includes(n),
      );
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
      eyebrow={t("owner.nav.operations")}
      title={t("owner.pages.ingredientsMapper")}
      description={t("owner.pageDesc.ingredients")}
      actions={
        <>
          <a
            href="#recipe-map"
            className="btn btn--ghost btn--sm"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById("recipe-map")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            {t("owner.streamUi.mapIngredients")}
          </a>
          <a
            href="#pantry-stock"
            className="btn btn--ghost btn--sm"
            onClick={(e) => {
              e.preventDefault();
              goToStock();
            }}
          >
            {t("owner.streamUi.ingredientStocks")}
          </a>
        </>
      }
    >
      {error && <p className="form-error">{error}</p>}
      {savedMsg && <div className="auth-card__success">{savedMsg}</div>}
      {loading ? (
        <div className="app-loading">Loading pantry…</div>
      ) : (
        <div className="owner-mapper-flow">
          <OwnerPanel
            id="pantry-stock"
            className="owner-mapper-stock"
            title={t("owner.panels.ingredientStocks")}
            description={t("owner.panels.ingredientStocksDesc")}
            action={
              <a
                href="#recipe-map"
                className="od-panel__link"
                onClick={(e) => {
                  e.preventDefault();
                  document.getElementById("recipe-map")?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                {t("owner.panels.mapIngredients")} →
              </a>
            }
          >
            <form className="owner-form owner-form--grid" onSubmit={onAddIngredient}>
              <label>
                Name
                <input
                  ref={newNameRef}
                  id="new-ingredient-name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  placeholder="Garam masala"
                />
              </label>
              <label>
                Brand
                <input value={newBrand} onChange={(e) => setNewBrand(e.target.value)} placeholder="Everest" />
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
                Pack size
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  value={newPackSize}
                  onChange={(e) => setNewPackSize(e.target.value)}
                  placeholder="100"
                />
              </label>
              <label>
                Pack label
                <input
                  value={newPackLabel}
                  onChange={(e) => setNewPackLabel(e.target.value)}
                  placeholder="100 g carton"
                />
              </label>
              <label>
                kcal / 100 {newUnit === "pcs" ? "pc" : newUnit}
                <input
                  type="number"
                  min={0}
                  max={2000}
                  step={0.1}
                  value={newKcal}
                  onChange={(e) => setNewKcal(e.target.value)}
                  placeholder={newUnit === "pcs" ? "78" : "116"}
                />
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
              searchPlaceholder={t("owner.list.searchPantry")}
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
                    <th>Brand</th>
                    <th>Pack</th>
                    <th>kcal / 100</th>
                    <th>Stock</th>
                    <th>Health</th>
                    <th>Low at</th>
                    <th>Status</th>
                    <th>Adjust</th>
                  </tr>
                </thead>
                <tbody>
                  {shownIngredients.map((ing) => (
                    <tr
                      id={`stock-${ing.id}`}
                      key={ing.id}
                      className={[ing.is_low ? "owner-row--warn" : "", focusStockId === ing.id ? "owner-row--focus" : ""]
                        .filter(Boolean)
                        .join(" ") || undefined}
                    >
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
                      <td>{ing.brand || "—"}</td>
                      <td>
                        {ing.pack_label || (ing.pack_size ? `${ing.pack_size} ${ing.unit}` : "—")}
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          max={2000}
                          step={0.1}
                          className="owner-kcal-input"
                          aria-label={`${ing.name} kcal per 100 ${ing.unit === "pcs" ? "piece" : ing.unit}`}
                          defaultValue={ing.kcal_per_100 ?? ""}
                          key={`${ing.id}-${ing.kcal_per_100 ?? "none"}`}
                          disabled={busy}
                          onBlur={(e) => {
                            const raw = e.target.value.trim();
                            const next = raw === "" ? null : Number(raw);
                            const current = ing.kcal_per_100 ?? null;
                            if (next === current || (next == null && current == null)) return;
                            if (next != null && Number.isNaN(next)) return;
                            void onSaveKcal(ing.id, next);
                          }}
                        />
                      </td>
                      <td>
                        {ing.current_stock} {ing.unit}
                        {ing.packs_on_hand != null ? (
                          <small> · {ing.packs_on_hand} packs</small>
                        ) : null}
                      </td>
                      <td className="owner-table__health">
                        {ing.health_score != null ? (
                          <>
                            <strong>{ing.health_score}</strong>
                            {ing.health_benefits ? <small>{ing.health_benefits}</small> : null}
                            {ing.health_disadvantages ? (
                              <small className="owner-table__health-con">{ing.health_disadvantages}</small>
                            ) : null}
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        {ing.low_stock_threshold} {ing.unit}
                      </td>
                      <td>{ing.is_low ? "Low" : "OK"}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() => onAdjust(ing.id, ing.pack_size && ing.pack_size > 0 ? ing.pack_size : 100)}
                        >
                          {ing.pack_size && ing.pack_size > 0 ? "+1 pack" : "+100"}
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          disabled={busy}
                          onClick={() =>
                            onAdjust(ing.id, ing.pack_size && ing.pack_size > 0 ? -ing.pack_size : -10)
                          }
                        >
                          {ing.pack_size && ing.pack_size > 0 ? "−1 pack" : "−10"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </OwnerPanel>

          <OwnerPanel
            id="recipe-map"
            className="owner-mapper-dish"
            title={t("owner.panels.mapIngredients")}
            description={`Menu ingredients for this dish map to pantry stock. Calories are quantity × pantry kcal — Healthy is automatic when the map is complete, the plate is ≤ ${recipe?.healthy_max_kcal ?? 500} kcal, and the health score is ≥ ${recipe?.healthy_min_score ?? 65}.`}
            action={
              <button type="button" className="od-panel__link" onClick={() => goToStock()}>
                {t("owner.panels.ingredientStocks")} →
              </button>
            }
          >
            <div className="owner-form">
            <label>
              Dish
              <select value={selectedDishId} onChange={(e) => selectDish(e.target.value)}>
                {dishes.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                    {d.is_active ? "" : " (draft)"}
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
                <div className="owner-recipe-kcal">
                  {recipeCalories.kcal != null ? (
                    <p>
                      <strong>{recipeCalories.kcal} kcal</strong> per plate
                      {recipeCalories.incomplete ? " · incomplete pantry kcal" : ""}
                      {recipe.healthy_tag ? " · Healthy" : ""}
                    </p>
                  ) : (
                    <p>Add pantry kcal on every SKU to calculate this plate.</p>
                  )}
                  <p className="owner-mapper-coverage">
                    {recipe.lines.filter((l) => l.ingredient_id).length} of {recipe.lines.length || dishTokens.length}{" "}
                    dish ingredients mapped to pantry stock.
                    {dishTokens.length === 0
                      ? " Add an ingredients list on Menu so the mapper can pre-fill rows."
                      : ""}
                  </p>
                  <p className="auth-card__hint">
                    Kitchen estimate from recipe amounts — not a lab nutrition label. You cannot pin Healthy.
                  </p>
                </div>
                <label>
                  Calories note (optional)
                  <input
                    value={caloriesNote}
                    maxLength={500}
                    onChange={(e) => setCaloriesNote(e.target.value)}
                    placeholder="Light lunch bowl — dal + greens."
                  />
                </label>
                <h3 className="owner-subhead">Dish ingredients → pantry stock (per portion)</h3>
                {recipe.lines.length === 0 && (
                  <p className="auth-card__hint">
                    No ingredients on this dish yet. Add lines below, or write the ingredient list on Menu
                    and reopen this mapper.
                  </p>
                )}
                <div className="owner-recipe-cards">
                  {recipe.lines.map((line, idx) => (
                    <div
                      key={`line-${idx}`}
                      className={`owner-recipe-card${line.ingredient_id ? "" : " owner-recipe-card--unmapped"}`}
                    >
                      <div className="owner-recipe-card__map">
                        <div>
                          <p className="owner-recipe-card__source-label">Dish ingredient</p>
                          <p className="owner-recipe-card__source">{line.source_name || "Extra pantry line"}</p>
                        </div>
                        {(() => {
                          const picked = ingredients.find((i) => i.id === line.ingredient_id);
                          if (picked) {
                            return (
                              <button
                                type="button"
                                className="od-panel__link owner-recipe-card__stock"
                                onClick={() => goToStock(picked.id)}
                              >
                                Stock {picked.current_stock} {picked.unit}
                                {picked.is_low ? " · Low" : ""} →
                              </button>
                            );
                          }
                          return (
                            <button
                              type="button"
                              className="od-panel__link owner-recipe-card__stock"
                              onClick={() => addToPantryFromToken(line.source_name || "")}
                              disabled={!line.source_name}
                            >
                              Add to pantry stock →
                            </button>
                          );
                        })()}
                      </div>
                      <div className="owner-recipe-card__row">
                        <label>
                          Maps to stock
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
                                  ingredient_brand: ing?.brand ?? "",
                                  ingredient_photo_url: ing?.photo_url ?? "",
                                  pack_size: ing?.pack_size ?? null,
                                  pack_label: ing?.pack_label ?? "",
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
                                {ing.brand ? ` · ${ing.brand}` : ""}
                                {ing.pack_label ? ` (${ing.pack_label})` : ""}
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
                      {(() => {
                        const picked = ingredients.find((i) => i.id === line.ingredient_id);
                        const lineKcal = estimateLineKcal(picked, line.quantity, line.unit);
                        if (!picked || (picked.health_score == null && lineKcal == null)) return null;
                        return (
                          <p className="owner-recipe-card__health">
                            {picked.health_score != null ? `Health ${picked.health_score}` : "Unmapped health"}
                            {lineKcal != null ? ` · ${lineKcal} kcal` : " · kcal missing"}
                            {picked.kcal_per_100 != null
                              ? ` (${picked.kcal_per_100} / 100 ${picked.unit === "pcs" ? "pc" : picked.unit})`
                              : ""}
                            {picked.health_benefits ? ` · ${picked.health_benefits}` : ""}
                            {picked.health_disadvantages
                              ? ` · Watch: ${picked.health_disadvantages}`
                              : ""}
                          </p>
                        );
                      })()}
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
        </div>
      )}
    </OwnerPageShell>
  );
}
