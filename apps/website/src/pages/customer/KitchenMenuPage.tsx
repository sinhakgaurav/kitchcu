import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { ListingToolbar } from "../../components/ListingToolbar";
import { useBrandedStorefront } from "../../customer/BrandedStorefront";
import { RichHtml } from "../../components/RichTextEditor";
import type { CuisineMenuGroup, Dish, KitchenMealPlan, Menu } from "../../shared/api";
import {
  fetchPublicSubscriptionPlans,
  requestKitchenSubscription,
} from "../../shared/api";
import { fetchKitchenRatingSummaries, type DishRatingSummary } from "../../shared/customerRatingsApi";
import { fetchPublicMenu } from "../../shared/publicApi";
import {
  addToCart,
  cartItemCount,
  getCart,
  projectKitchenReadyMin,
} from "../../shared/customerCart";
import { getCustomerToken } from "../../shared/customerApi";
import { getCustomerSession } from "../../shared/customerSession";
import {
  dishHighlightBadges,
  filterAndSortDishes,
  type DishHighlight,
  type DishSort,
} from "../../shared/listingControls";

const DIET_LABELS: Record<string, string> = {
  veg: "Veg",
  non_veg: "Non Veg",
  vegan: "Vegan",
  eggetarian: "Eggetarian",
};

const SECTION_META: { key: DishHighlight; title: string; dishesKey: "featured" | "chefs_special" | "unique_recipe" }[] = [
  { key: "featured", title: "Featured", dishesKey: "featured" },
  { key: "chefs_special", title: "Chef's special", dishesKey: "chefs_special" },
  { key: "unique_recipe", title: "Unique recipes", dishesKey: "unique_recipe" },
];

export function KitchenMenuPage() {
  const { kitchenId: kitchenIdParam } = useParams<{ kitchenId: string }>();
  const branded = useBrandedStorefront();
  const navigate = useNavigate();
  const location = useLocation();
  const kitchenId = kitchenIdParam || branded?.kitchen.id;
  const [menu, setMenu] = useState<Menu | null>(null);
  const [kitchenName, setKitchenName] = useState(branded?.kitchen.name ?? "");
  const [kitchenCode, setKitchenCode] = useState(branded?.kitchen.code ?? "");
  const [error, setError] = useState("");
  const [cartLines, setCartLines] = useState(0);
  const [cartReadyMin, setCartReadyMin] = useState(0);
  const [ratingMap, setRatingMap] = useState<Record<string, DishRatingSummary>>({});
  const [plans, setPlans] = useState<KitchenMealPlan[]>([]);
  const [subMsg, setSubMsg] = useState("");
  const [subBusy, setSubBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<DishSort>("name_asc");
  const [highlights, setHighlights] = useState<DishHighlight[]>([]);
  const [diet, setDiet] = useState("");
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
    fetchPublicSubscriptionPlans(kitchenId)
      .then((r) => setPlans(r.plans))
      .catch(() => setPlans([]));
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

  const dietChips = useMemo(() => {
    if (!menu) return [];
    return (menu.diet_categories || []).map((c) => ({
      id: c.slug,
      label: DIET_LABELS[c.slug] ?? c.name,
    }));
  }, [menu]);

  const filteredDishes = useMemo(() => {
    if (!menu) return [];
    return filterAndSortDishes(menu.dishes, {
      q: search,
      sort,
      highlights,
      diet: diet || undefined,
    });
  }, [menu, search, sort, highlights, diet]);

  const groups = useMemo(() => {
    if (!menu) return [];
    return rebuildGroups(menu, filteredDishes);
  }, [menu, filteredDishes]);

  const highlightSections = useMemo(() => {
    if (!menu) return [];
    return SECTION_META.map((meta) => {
      if (highlights.length && !highlights.includes(meta.key)) {
        return { ...meta, dishes: [] as Dish[] };
      }
      const bucket =
        menu.highlight_sections?.[meta.dishesKey] ??
        menu.dishes.filter((d) =>
          meta.key === "featured"
            ? d.is_featured
            : meta.key === "chefs_special"
              ? d.is_chefs_special
              : d.is_unique_recipe,
        );
      return {
        ...meta,
        dishes: filterAndSortDishes(bucket, {
          q: search,
          sort,
          diet: diet || undefined,
        }),
      };
    }).filter((s) => s.dishes.length > 0);
  }, [menu, search, diet, highlights, sort]);

  const requestPlan = async (planId: string) => {
    if (!kitchenId) return;
    if (!getCustomerToken()) {
      const next = `${location.pathname}${location.search}`;
      navigate(`/login?next=${encodeURIComponent(next)}`);
      return;
    }
    setSubBusy(true);
    setSubMsg("");
    try {
      await requestKitchenSubscription(kitchenId, planId);
      setSubMsg("Request sent — kitchen will accept or deny shortly.");
    } catch (err) {
      setSubMsg(err instanceof Error ? err.message : "Could not request subscription");
    } finally {
      setSubBusy(false);
    }
  };

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
      {!branded && <Link to="/" className="customer-menu__back">← Discover kitchens</Link>}
      {error && <p className="auth-card__error">{error}</p>}
      {!menu && !error && <p className="app-loading">Loading menu...</p>}

      {menu && (
        <>
          <header className="customer-menu__head">
            {!branded && <h1>{kitchenName || "Kitchen Menu"}</h1>}
            <p>{menu.dishes.length} dishes · live-capture when marked</p>
          </header>

          <ListingToolbar
            className="customer-menu__toolbar"
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Search menu…"
            sort={sort}
            onSortChange={(v) => setSort(v as DishSort)}
            highlights={highlights}
            onHighlightsChange={setHighlights}
            filterChips={dietChips}
            activeFilter={diet}
            onFilterChange={setDiet}
            resultCount={filteredDishes.length}
          />

          {plans.length > 0 && (
            <section className="customer-menu__cuisine customer-menu__tiffin">
              <h2 className="customer-menu__cuisine-title">Monthly thali / tiffin</h2>
              <p className="customer-menu__tiffin-lead">
                Request a plan — kitchen confirms before it starts.
              </p>
              {subMsg && <p className="customer-menu__tiffin-msg">{subMsg}</p>}
              <ul className="customer-tiffin-list">
                {plans.map((p) => {
                  const img = p.dishes_config?.image_url;
                  const dishCount = p.dishes_config?.dish_ids?.length ?? 0;
                  return (
                    <li key={p.id} className="customer-tiffin-card">
                      {img ? (
                        <img className="customer-tiffin-card__media" src={img} alt="" />
                      ) : (
                        <span className="customer-tiffin-card__media customer-tiffin-card__media--empty" aria-hidden />
                      )}
                      <div className="customer-tiffin-card__body">
                        <div className="customer-tiffin-card__meta">
                          <strong>{p.name}</strong>
                          <span>
                            {p.plan_type.replace(/_/g, " ")} · ₹{Math.round(p.price_monthly)}/mo
                            {dishCount > 0 ? ` · ${dishCount} dish${dishCount === 1 ? "" : "es"}` : ""}
                          </span>
                        </div>
                        {p.description ? (
                          <RichHtml html={p.description} className="customer-tiffin-card__desc" />
                        ) : null}
                      </div>
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={subBusy}
                        onClick={() => requestPlan(p.id)}
                      >
                        Request subscribe
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {highlightSections.map((section) => (
            <section key={section.key} className="customer-menu__highlight">
              <h2 className="customer-menu__cuisine-title">{section.title}</h2>
              <div className="customer-menu__grid">
                {section.dishes.map((d) => (
                  <DishCard
                    key={`${section.key}-${d.id}`}
                    dish={d}
                    summary={ratingMap[d.id]}
                    onAdd={() => handleAdd(d)}
                  />
                ))}
              </div>
            </section>
          ))}

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

          {filteredDishes.length === 0 && (
            <p className="owner-muted">No dishes match these filters.</p>
          )}

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

function rebuildGroups(menu: Menu, dishes: Dish[]): CuisineMenuGroup[] {
  if (!dishes.length) return [];
  const cuisineById = new Map(menu.cuisines.map((c) => [c.id, c]));
  const dietById = new Map(menu.diet_categories.map((c) => [c.id, c]));
  const byCuisine = new Map<string, CuisineMenuGroup>();

  for (const dish of dishes) {
    const cKey = dish.cuisine_id ?? "unknown";
    if (!byCuisine.has(cKey)) {
      const cuisine = (dish.cuisine_id && cuisineById.get(dish.cuisine_id)) || {
        id: cKey,
        kitchen_id: dish.kitchen_id,
        name: dish.cuisine_name ?? "Menu",
        slug: dish.cuisine_slug ?? "menu",
        sort_order: 0,
      };
      byCuisine.set(cKey, { cuisine, diets: [] });
    }
    const group = byCuisine.get(cKey)!;
    const dKey = dish.category_id ?? "unknown";
    let dietGroup = group.diets.find((d) => d.diet.id === dKey);
    if (!dietGroup) {
      const diet = (dish.category_id && dietById.get(dish.category_id)) || {
        id: dKey,
        kitchen_id: dish.kitchen_id,
        name: dish.category_name ?? "Dishes",
        slug: dish.category_slug ?? "veg",
        sort_order: 0,
      };
      dietGroup = { diet, dishes: [] };
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
  const badges = dishHighlightBadges(dish);
  const readyMin = dish.projected_ready_min ?? dish.max_time_min ?? dish.prep_time_min;
  const hasDetails = Boolean(dish.description || dish.ingredients_description);
  return (
    <article className="customer-dish">
      {hero?.url ? (
        <img src={hero.url} alt={dish.name} loading="lazy" className="customer-dish__img" />
      ) : (
        <div className="customer-dish__img customer-dish__img--pending" aria-hidden>
          Photo pending
        </div>
      )}
      <div className="customer-dish__body">
        <div className="customer-dish__title-row">
          <h4>{dish.name}</h4>
          <p className="customer-dish__price">₹{Math.round(dish.price)}</p>
        </div>
        <p className="customer-dish__eta">
          Ready within <strong>{readyMin} min</strong>
          {summary && summary.rating_count > 0
            ? ` · ★ ${summary.overall_rating.toFixed(1)}`
            : ""}
          {hero?.is_live_capture ? " · Live capture" : ""}
        </p>
        {badges.length > 0 && (
          <div className="dish-badges">
            {badges.slice(0, 2).map((b) => (
              <span key={b.key} className={`dish-badge dish-badge--${b.key}`}>
                {b.label}
              </span>
            ))}
          </div>
        )}
        {hasDetails && (
          <details className="customer-dish__more">
            <summary>Details</summary>
            {dish.description ? <RichHtml html={dish.description} /> : null}
            {dish.ingredients_description ? (
              <RichHtml html={dish.ingredients_description} className="customer-dish__ingredients" />
            ) : null}
          </details>
        )}
        <button type="button" className="btn btn--primary btn--sm customer-dish__add" onClick={onAdd}>
          Add to cart
        </button>
      </div>
    </article>
  );
}
