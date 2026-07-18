import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useBrandedStorefront } from "../../customer/BrandedStorefront";
import { RichHtml } from "../../components/RichTextEditor";
import { sampleDishImages } from "../../data/content";
import type { CuisineMenuGroup, Dish, Menu } from "../../shared/api";
import { fetchKitchenRatingSummaries, type DishRatingSummary } from "../../shared/customerRatingsApi";
import { fetchPublicMenu } from "../../shared/publicApi";
import {
  addToCart,
  cartItemCount,
  getCart,
  projectKitchenReadyMin,
} from "../../shared/customerCart";
import { getCustomerSession } from "../../shared/customerSession";

const DIET_LABELS: Record<string, string> = {
  veg: "Veg",
  non_veg: "Non Veg",
  vegan: "Vegan",
  eggetarian: "Eggetarian",
};

export function KitchenMenuPage() {
  const { kitchenId: kitchenIdParam } = useParams<{ kitchenId: string }>();
  const branded = useBrandedStorefront();
  const kitchenId = kitchenIdParam || branded?.kitchen.id;
  const [menu, setMenu] = useState<Menu | null>(null);
  const [kitchenName, setKitchenName] = useState(branded?.kitchen.name ?? "");
  const [kitchenCode, setKitchenCode] = useState(branded?.kitchen.code ?? "");
  const [error, setError] = useState("");
  const [cartLines, setCartLines] = useState(0);
  const [cartReadyMin, setCartReadyMin] = useState(0);
  const [ratingMap, setRatingMap] = useState<Record<string, DishRatingSummary>>({});
  const checkoutHref = branded ? `${branded.basePath}/checkout` : "/checkout";

  useEffect(() => {
    if (!kitchenId) return;
    if (branded) {
      setKitchenName(branded.kitchen.name);
      setKitchenCode(branded.kitchen.code);
    }
    fetchPublicMenu(kitchenId)
      .then((m) => {
        setMenu(m);
        const saved = getCustomerSession()?.savedKitchens.find((k) => k.id === kitchenId);
        if (saved) {
          setKitchenName(saved.name);
          setKitchenCode(saved.code);
        } else if (branded) {
          setKitchenName(branded.kitchen.name);
          setKitchenCode(branded.kitchen.code);
        }
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Menu not available for this kitchen."),
      );
    fetchKitchenRatingSummaries(kitchenId)
      .then(({ summaries }) => {
        const map: Record<string, DishRatingSummary> = {};
        for (const s of summaries) map[s.dish_id] = s;
        setRatingMap(map);
      })
      .catch(() => {});
    const refreshCart = () => {
      const cart = getCart();
      setCartLines(cartItemCount(cart, kitchenId));
      const kitchen = cart?.kitchens.find((k) => k.kitchenId === kitchenId);
      setCartReadyMin(kitchen ? projectKitchenReadyMin(kitchen, true) : 0);
    };
    refreshCart();
    window.addEventListener("storage", refreshCart);
    return () => window.removeEventListener("storage", refreshCart);
  }, [kitchenId, branded]);

  const groups = menu?.grouped?.length ? menu.grouped : fallbackGroups(menu);

  const handleAdd = (dish: Dish) => {
    if (!kitchenId) return;
    addToCart(
      { id: kitchenId, name: kitchenName || "Kitchen", code: kitchenCode || "KITCHEN" },
      dish,
    );
    const cart = getCart();
    setCartLines(cartItemCount(cart, kitchenId));
    const kitchen = cart?.kitchens.find((k) => k.kitchenId === kitchenId);
    setCartReadyMin(kitchen ? projectKitchenReadyMin(kitchen, true) : 0);
  };

  return (
    <div className={`container customer-menu${branded ? " customer-menu--branded" : ""}`}>
      {!branded && <Link to="/" className="owner-back">← Back to discover</Link>}
      {error && <p className="auth-card__error">{error}</p>}
      {!menu && !error && <p className="app-loading">Loading menu...</p>}

      {menu && (
        <>
          <header className="customer-menu__head">
            {!branded && <h1>{kitchenName || "Kitchen Menu"}</h1>}
            <p>
              {menu.dishes.length} dishes · Cuisine → diet → dish · Live-capture verified heroes
            </p>
          </header>

          {groups.map((group) => (
            <section key={group.cuisine.id} className="customer-menu__cuisine">
              <h2 className="customer-menu__cuisine-title">{group.cuisine.name}</h2>
              {group.diets.map((dietGroup) => (
                <div key={dietGroup.diet.id} className="customer-menu__diet">
                  <h3 className="customer-menu__diet-title">
                    {DIET_LABELS[dietGroup.diet.slug] ?? dietGroup.diet.name}
                  </h3>
                  <div className="customer-menu__grid">
                    {dietGroup.dishes.map((d) => (
                      <DishCard
                        key={d.id}
                        dish={d}
                        summary={ratingMap[d.id]}
                        onAdd={() => handleAdd(d)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ))}

          {cartLines > 0 && kitchenId && (
            <div className="customer-cart-bar glass">
              <span>
                {cartLines} item{cartLines === 1 ? "" : "s"} · ready within ~{cartReadyMin} min
              </span>
              <Link to={checkoutHref} className="btn btn--primary btn--sm">
                Checkout
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function fallbackGroups(menu: Menu | null): CuisineMenuGroup[] {
  if (!menu?.dishes.length) return [];
  const byCuisine = new Map<string, CuisineMenuGroup>();
  for (const dish of menu.dishes) {
    const cKey = dish.cuisine_id ?? "unknown";
    if (!byCuisine.has(cKey)) {
      byCuisine.set(cKey, {
        cuisine: {
          id: dish.cuisine_id ?? cKey,
          kitchen_id: dish.kitchen_id,
          name: dish.cuisine_name ?? "Menu",
          slug: dish.cuisine_slug ?? "menu",
          sort_order: 0,
        },
        diets: [],
      });
    }
    const group = byCuisine.get(cKey)!;
    const dKey = dish.category_id ?? "unknown";
    let dietGroup = group.diets.find((d) => d.diet.id === dKey);
    if (!dietGroup) {
      dietGroup = {
        diet: {
          id: dish.category_id ?? dKey,
          kitchen_id: dish.kitchen_id,
          name: dish.category_name ?? "Dishes",
          slug: dish.category_slug ?? "veg",
          sort_order: 0,
        },
        dishes: [],
      };
      group.diets.push(dietGroup);
    }
    dietGroup.dishes.push(dish);
  }
  return [...byCuisine.values()];
}

function DishCard({
  dish,
  summary,
  onAdd,
}: {
  dish: Dish;
  summary?: DishRatingSummary;
  onAdd: () => void;
}) {
  const hero = dish.media.find((m) => m.is_hero) ?? dish.media[0];
  const placeholders = Object.values(sampleDishImages);
  const fallback =
    placeholders[Math.abs(hashCode(dish.name)) % placeholders.length];
  const imageSrc = hero?.url || fallback;
  return (
    <article className="glass customer-dish">
      <img src={imageSrc} alt={dish.name} loading="lazy" className="customer-dish__img" />
      <div>
        <h4>{dish.name}</h4>
        <p className="customer-dish__price">₹{dish.price}</p>
        <p className="customer-dish__eta">
          Prep {dish.prep_time_min} min
          {dish.delivery_time_min != null && dish.delivery_time_min > 0
            ? ` · Delivery ${dish.delivery_time_min} min`
            : ""}
          {" · "}
          <strong>
            Ready within {dish.projected_ready_min ?? dish.max_time_min ?? dish.prep_time_min} min
          </strong>
        </p>
        {summary && summary.rating_count > 0 && (
          <p className="owner-muted">
            ★ {summary.overall_rating.toFixed(1)} home taste · {summary.rating_count} rating
            {summary.rating_count === 1 ? "" : "s"}
          </p>
        )}
        {dish.description && <RichHtml html={dish.description} />}
        {hero?.is_live_capture && <span className="live-badge">Live capture</span>}
        {dish.ingredients_description && (
          <RichHtml html={dish.ingredients_description} className="customer-dish__ingredients" />
        )}
        <button type="button" className="btn btn--ghost btn--sm customer-dish__add" onClick={onAdd}>
          Add to cart
        </button>
      </div>
    </article>
  );
}

function hashCode(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) h = (h * 31 + value.charCodeAt(i)) | 0;
  return h;
}
