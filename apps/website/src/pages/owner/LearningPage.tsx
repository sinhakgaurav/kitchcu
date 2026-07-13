import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchCuratedRecipes,
  fetchDishTrials,
  learnRecipe,
  type CuratedRecipe,
  type DishTrial,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "north_indian", label: "North Indian" },
  { value: "south_indian", label: "South Indian" },
  { value: "desserts", label: "Desserts" },
];

export function LearningPage() {
  const { kitchen } = useKitchen();
  const [category, setCategory] = useState("");
  const [recipes, setRecipes] = useState<CuratedRecipe[]>([]);
  const [trials, setTrials] = useState<DishTrial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [recipeRes, trialRes] = await Promise.all([
        fetchCuratedRecipes(category || undefined),
        fetchDishTrials(kitchen.id),
      ]);
      setRecipes(recipeRes.recipes);
      setTrials(trialRes.trials);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load learning portal");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kitchen, category]);

  const onLearn = async (recipe: CuratedRecipe) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const trial = await learnRecipe(kitchen.id, {
        recipe_id: recipe.id,
        price: 149,
      });
      window.location.href = `/dashboard/learning/trials/${trial.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start trial");
      setBusy(false);
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title="Learning portal"
      description="Browse curated recipes, learn dishes, run sample trials (F21–F22)"
    >
      {error && <p className="form-error">{error}</p>}

      <OwnerPanel title="Your trials" description="Dishes you're testing before adding to menu">
        {trials.length === 0 ? (
          <OwnerEmpty message='No trials yet — pick a recipe below and tap "I learned this dish".' />
        ) : (
          <ul className="owner-detail-items">
            {trials.map((t) => (
              <li key={t.id}>
                <Link to={`/dashboard/learning/trials/${t.id}`}>
                  {t.dish_name} — <span className="status-badge">{t.status}</span>
                  {t.avg_rating != null && ` · ★ ${t.avg_rating}`}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>

      <OwnerPanel
        title="Curated recipes"
        description="Learn from the community and test with your regulars"
        action={
          <select
            className="owner-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c.value || "all"} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        }
      >
        {loading ? (
          <div className="app-loading">Loading recipes…</div>
        ) : recipes.length === 0 ? (
          <OwnerEmpty message="No recipes in this category yet." />
        ) : (
          <div className="owner-menu-grid">
            {recipes.map((r) => (
              <article key={r.id} className="dash-card owner-dish-card">
                <img src={r.image_url} alt={r.title} loading="lazy" />
                <div>
                  <h3>{r.title}</h3>
                  <p className="owner-dish-card__desc">{r.description}</p>
                  <p className="owner-muted">
                    {r.category.replace("_", " ")} · {r.source_name}
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    disabled={busy}
                    onClick={() => onLearn(r)}
                  >
                    I learned this dish
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
