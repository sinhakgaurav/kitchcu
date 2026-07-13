import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell } from "../../components/owner/OwnerPageShell";
import { fetchMenu, type Dish } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function MenuPage() {
  const { kitchen } = useKitchen();
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!kitchen) return;
    setLoading(true);
    fetchMenu(kitchen.id)
      .then((m) => setDishes(m.dishes))
      .catch(() => setDishes([]))
      .finally(() => setLoading(false));
  }, [kitchen]);

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Operations"
      title="Menu"
      description={`${dishes.length} live-capture dish${dishes.length !== 1 ? "es" : ""} · customers browse on your menu link`}
      actions={<Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>}
    >
      {loading ? (
        <p className="app-loading">Loading menu…</p>
      ) : dishes.length === 0 ? (
        <OwnerEmpty
          message="No dishes yet. Add your first dish with a live-capture photo — that's how customers trust your kitchen."
          action={<Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>}
        />
      ) : (
        <div className="owner-menu-grid">
          {dishes.map((d) => {
            const hero = d.media.find((m) => m.is_hero) ?? d.media[0];
            return (
              <article key={d.id} className="dash-card owner-dish-card">
                {hero && <img src={hero.url} alt={d.name} loading="lazy" />}
                <div>
                  <h3>{d.name}</h3>
                  <p>₹{d.price} · {d.prep_time_min} min prep</p>
                  {d.description && <p className="owner-dish-card__desc">{d.description}</p>}
                  {hero?.is_live_capture && <span className="live-badge">Live capture</span>}
                  <Link to={`/dashboard/ingredients?dish=${d.id}`} className="btn btn--ghost btn--sm">
                    Recipe & prep
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </OwnerPageShell>
  );
}
