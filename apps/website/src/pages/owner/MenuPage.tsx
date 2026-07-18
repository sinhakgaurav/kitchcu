import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ListingToolbar } from "../../components/ListingToolbar";
import { OwnerEmpty, OwnerPageShell } from "../../components/owner/OwnerPageShell";
import {
  fetchGoldenRecipes,
  fetchGrowthSuggestions,
  fetchMenu,
  updateDish,
  type Dish,
  type GoldenRecipePin,
  type GrowthSuggestion,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import {
  dishHighlightBadges,
  filterAndSortDishes,
  type DishHighlight,
  type DishSort,
} from "../../shared/listingControls";

export function MenuPage() {
  const { kitchen } = useKitchen();
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [goldenByDish, setGoldenByDish] = useState<Record<string, GrowthSuggestion | GoldenRecipePin>>({});
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<DishSort>("name_asc");
  const [highlights, setHighlights] = useState<DishHighlight[]>([]);
  const [diet, setDiet] = useState("");

  const reload = async () => {
    if (!kitchen) return;
    const [m, sug, pins] = await Promise.all([
      fetchMenu(kitchen.id),
      fetchGrowthSuggestions(kitchen.id).catch(() => ({ suggestions: [] as GrowthSuggestion[] })),
      fetchGoldenRecipes(kitchen.id).catch(() => ({ pins: [] as GoldenRecipePin[] })),
    ]);
    setDishes(m.dishes);
    const map: Record<string, GrowthSuggestion | GoldenRecipePin> = {};
    for (const p of pins.pins) {
      map[p.dish_id] = p;
    }
    for (const s of sug.suggestions) {
      if (s.suggestion_type !== "golden_performance_day") continue;
      const dishId = String(s.action_payload.dish_id ?? "");
      if (dishId && !map[dishId]) map[dishId] = s;
    }
    setGoldenByDish(map);
  };

  useEffect(() => {
    if (!kitchen) return;
    setLoading(true);
    reload()
      .catch(() => setDishes([]))
      .finally(() => setLoading(false));
  }, [kitchen]);

  const dietChips = useMemo(() => {
    const slugs = new Map<string, string>();
    for (const d of dishes) {
      if (d.category_slug) slugs.set(d.category_slug, d.category_name || d.category_slug);
    }
    return [...slugs.entries()].map(([id, label]) => ({ id, label }));
  }, [dishes]);

  const visible = useMemo(
    () =>
      filterAndSortDishes(dishes, {
        q: search,
        sort,
        highlights,
        diet: diet || undefined,
      }),
    [dishes, search, sort, highlights, diet],
  );

  const goldenCount = useMemo(() => Object.keys(goldenByDish).length, [goldenByDish]);

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Operations"
      title="Menu"
      description={`${dishes.length} live-capture dish${dishes.length !== 1 ? "es" : ""} · highlights, timing & filters${goldenCount ? ` · ${goldenCount} golden day signal${goldenCount !== 1 ? "s" : ""}` : ""}`}
      actions={<Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>}
    >
      {error && <p className="auth-card__error">{error}</p>}
      {loading ? (
        <p className="app-loading">Loading menu…</p>
      ) : dishes.length === 0 ? (
        <OwnerEmpty
          message="No dishes yet. Add your first dish with a live-capture photo — that's how customers trust your kitchen."
          action={<Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>}
        />
      ) : (
        <>
          <ListingToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Search dishes…"
            sort={sort}
            onSortChange={(v) => setSort(v as DishSort)}
            highlights={highlights}
            onHighlightsChange={setHighlights}
            filterChips={dietChips}
            activeFilter={diet}
            onFilterChange={setDiet}
            resultCount={visible.length}
          />
          <div className="owner-menu-grid">
            {visible.map((d) => {
              const hero = d.media.find((m) => m.is_hero) ?? d.media[0];
              const golden = goldenByDish[d.id];
              const isPin = golden && "performance_date" in golden && "recipe_snapshot" in golden;
              const badges = dishHighlightBadges(d);
              return (
                <article key={d.id} className="dash-card owner-dish-card">
                  {hero && <img src={hero.url} alt={d.name} loading="lazy" />}
                  <div>
                    <h3>{d.name}</h3>
                    <p>
                      ₹{d.price} · prep {d.prep_time_min}m
                      {d.delivery_time_min != null ? ` · delivery ${d.delivery_time_min}m` : ""}
                      {" · "}
                      <strong>ready within {d.max_time_min ?? d.projected_ready_min}m</strong>
                    </p>
                    {badges.length > 0 && (
                      <div className="dish-badges">
                        {badges.map((b) => (
                          <span key={b.key} className={`dish-badge dish-badge--${b.key}`}>
                            {b.label}
                          </span>
                        ))}
                      </div>
                    )}
                    {d.description && <p className="owner-dish-card__desc">{d.description}</p>}
                    {hero?.is_live_capture && <span className="live-badge">Live capture</span>}
                    {golden && (
                      <div className="owner-dish-card__golden">
                        <span className="golden-day-badge">
                          {isPin ? "Golden recipe saved" : "Golden day"}
                        </span>
                        <p>
                          {isPin
                            ? `Baseline from ${(golden as GoldenRecipePin).performance_date}`
                            : String((golden as GrowthSuggestion).description).slice(0, 120) + "…"}
                        </p>
                        <Link to="/dashboard/growth" className="od-panel__link">
                          {isPin ? "View in Growth →" : "Save recipe in Growth →"}
                        </Link>
                      </div>
                    )}
                    <div className="owner-dish-card__actions">
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setEditingId(editingId === d.id ? null : d.id)}
                      >
                        {editingId === d.id ? "Close edit" : "Edit highlights & timing"}
                      </button>
                      <Link to={`/dashboard/ingredients?dish=${d.id}`} className="btn btn--ghost btn--sm">
                        Recipe & prep
                      </Link>
                    </div>
                    {editingId === d.id && (
                      <DishEditForm
                        dish={d}
                        onSaved={async () => {
                          setError("");
                          try {
                            await reload();
                            setEditingId(null);
                          } catch (e) {
                            setError(e instanceof Error ? e.message : "Reload failed");
                          }
                        }}
                        onError={setError}
                        kitchenId={kitchen.id}
                      />
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </OwnerPageShell>
  );
}

function DishEditForm({
  kitchenId,
  dish,
  onSaved,
  onError,
}: {
  kitchenId: string;
  dish: Dish;
  onSaved: () => void | Promise<void>;
  onError: (msg: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [featured, setFeatured] = useState(!!dish.is_featured);
  const [chefs, setChefs] = useState(!!dish.is_chefs_special);
  const [unique, setUnique] = useState(!!dish.is_unique_recipe);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    onError("");
    try {
      const prep = Number(fd.get("prep_time_min"));
      const delivery = Number(fd.get("delivery_time_min"));
      const maxTime = Number(fd.get("max_time_min"));
      await updateDish(kitchenId, dish.id, {
        prep_time_min: prep,
        delivery_time_min: delivery,
        max_time_min: maxTime,
        is_featured: featured,
        is_chefs_special: chefs,
        is_unique_recipe: unique,
      });
      await onSaved();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not update dish");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="owner-timing-form owner-timing-form--highlights" onSubmit={submit}>
      <label className="dish-highlight-check">
        <input type="checkbox" checked={featured} onChange={(e) => setFeatured(e.target.checked)} />
        Featured
      </label>
      <label className="dish-highlight-check">
        <input type="checkbox" checked={chefs} onChange={(e) => setChefs(e.target.checked)} />
        Chef&apos;s special
      </label>
      <label className="dish-highlight-check">
        <input type="checkbox" checked={unique} onChange={(e) => setUnique(e.target.checked)} />
        Unique recipe
      </label>
      <label>
        Prep
        <input name="prep_time_min" type="number" min={5} defaultValue={dish.prep_time_min} required />
      </label>
      <label>
        Delivery
        <input
          name="delivery_time_min"
          type="number"
          min={0}
          defaultValue={dish.delivery_time_min ?? 0}
          required
        />
      </label>
      <label>
        Max (customer)
        <input
          name="max_time_min"
          type="number"
          min={5}
          defaultValue={dish.max_time_min ?? dish.projected_ready_min}
          required
        />
      </label>
      <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>
        {busy ? "Saving…" : "Save"}
      </button>
    </form>
  );
}
