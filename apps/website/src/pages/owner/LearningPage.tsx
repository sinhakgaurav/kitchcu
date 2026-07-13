import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Learning portal</h1>
          <p className="owner-page__code">Browse curated recipes, learn dishes, run sample trials (F21–F22)</p>
        </div>
      </header>

      {error && <p className="owner-error">{error}</p>}

      <section className="glass owner-section">
        <h2>Your trials</h2>
        {trials.length === 0 ? (
          <p className="owner-page__code">No trials yet — pick a recipe below and tap &quot;I learned this dish&quot;.</p>
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
      </section>

      <section className="glass owner-section">
        <div className="owner-page__head">
          <h2>Curated recipes</h2>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c.value || "all"} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <p>Loading recipes…</p>
        ) : (
          <div className="owner-menu-grid">
            {recipes.map((r) => (
              <article key={r.id} className="glass owner-dish-card">
                <img src={r.image_url} alt={r.title} loading="lazy" />
                <div>
                  <h3>{r.title}</h3>
                  <p className="owner-dish-card__desc">{r.description}</p>
                  <p className="owner-page__code">
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
      </section>
    </div>
  );
}
