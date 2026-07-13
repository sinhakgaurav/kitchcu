import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchMenu, type Dish } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function MenuPage() {
  const { kitchen } = useKitchen();
  const [dishes, setDishes] = useState<Dish[]>([]);

  useEffect(() => {
    if (!kitchen) return;
    fetchMenu(kitchen.id).then((m) => setDishes(m.dishes)).catch(() => {});
  }, [kitchen]);

  if (!kitchen) return null;

  return (
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>Menu</h1>
          <p>Live-capture dishes your customers can trust.</p>
        </div>
        <Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>
      </header>

      <div className="owner-menu-grid">
        {dishes.length === 0 && (
          <div className="glass owner-empty-card">
            <p>No dishes yet. Add your first dish with a live-capture photo.</p>
            <Link to="/dashboard/menu/new" className="btn btn--primary">Add dish</Link>
          </div>
        )}
        {dishes.map((d) => {
          const hero = d.media.find((m) => m.is_hero) ?? d.media[0];
          return (
            <article key={d.id} className="glass owner-dish-card">
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
    </div>
  );
}
