/** Shared filter + sort helpers for platform list surfaces. */

export type DishSort =
  | "name_asc"
  | "name_desc"
  | "price_asc"
  | "price_desc"
  | "prep_asc"
  | "newest";

export type DishHighlight = "featured" | "chefs_special" | "unique_recipe";

export const DISH_SORT_OPTIONS: { value: DishSort; label: string }[] = [
  { value: "name_asc", label: "Name A–Z" },
  { value: "name_desc", label: "Name Z–A" },
  { value: "price_asc", label: "Price ↑" },
  { value: "price_desc", label: "Price ↓" },
  { value: "prep_asc", label: "Prep time ↑" },
  { value: "newest", label: "Newest" },
];

export const DISH_HIGHLIGHT_OPTIONS: { value: DishHighlight; label: string }[] = [
  { value: "featured", label: "Featured" },
  { value: "chefs_special", label: "Chef's special" },
  { value: "unique_recipe", label: "Unique recipe" },
];

export type DishListItem = {
  id: string;
  name: string;
  price: number;
  prep_time_min: number;
  description?: string | null;
  cuisine_name?: string | null;
  category_slug?: string | null;
  is_featured?: boolean;
  is_chefs_special?: boolean;
  is_unique_recipe?: boolean;
  created_at?: string | null;
};

export type DishListOptions = {
  highlights?: DishHighlight[];
  diet?: string;
  q?: string;
  sort?: DishSort;
};

export function filterAndSortDishes<T extends DishListItem>(
  dishes: T[],
  opts: DishListOptions,
): T[] {
  let out = [...dishes];
  const highlights = opts.highlights ?? [];
  if (highlights.length) {
    out = out.filter(
      (d) =>
        (highlights.includes("featured") && d.is_featured) ||
        (highlights.includes("chefs_special") && d.is_chefs_special) ||
        (highlights.includes("unique_recipe") && d.is_unique_recipe),
    );
  }
  if (opts.diet) {
    const slug = opts.diet.toLowerCase();
    out = out.filter((d) => (d.category_slug || "").toLowerCase() === slug);
  }
  if (opts.q?.trim()) {
    const needle = opts.q.trim().toLowerCase();
    out = out.filter(
      (d) =>
        d.name.toLowerCase().includes(needle) ||
        (d.description || "").toLowerCase().includes(needle) ||
        (d.cuisine_name || "").toLowerCase().includes(needle),
    );
  }
  const sort = opts.sort ?? "name_asc";
  out.sort((a, b) => {
    switch (sort) {
      case "name_desc":
        return b.name.localeCompare(a.name);
      case "price_asc":
        return a.price - b.price || a.name.localeCompare(b.name);
      case "price_desc":
        return b.price - a.price || a.name.localeCompare(b.name);
      case "prep_asc":
        return a.prep_time_min - b.prep_time_min || a.name.localeCompare(b.name);
      case "newest": {
        const ta = a.created_at ? Date.parse(a.created_at) : 0;
        const tb = b.created_at ? Date.parse(b.created_at) : 0;
        return tb - ta || b.name.localeCompare(a.name);
      }
      default:
        return a.name.localeCompare(b.name);
    }
  });
  return out;
}

export function filterAndSortByName<T extends { name: string; created_at?: string | null }>(
  items: T[],
  opts: { q?: string; sort?: "name_asc" | "name_desc" | "newest" },
): T[] {
  let out = [...items];
  if (opts.q?.trim()) {
    const needle = opts.q.trim().toLowerCase();
    out = out.filter((i) => i.name.toLowerCase().includes(needle));
  }
  const sort = opts.sort ?? "name_asc";
  out.sort((a, b) => {
    if (sort === "newest") {
      const ta = a.created_at ? Date.parse(a.created_at) : 0;
      const tb = b.created_at ? Date.parse(b.created_at) : 0;
      return tb - ta || b.name.localeCompare(a.name);
    }
    if (sort === "name_desc") return b.name.localeCompare(a.name);
    return a.name.localeCompare(b.name);
  });
  return out;
}

export function dishHighlightBadges(dish: {
  is_featured?: boolean;
  is_chefs_special?: boolean;
  is_unique_recipe?: boolean;
}): { key: DishHighlight; label: string }[] {
  const badges: { key: DishHighlight; label: string }[] = [];
  if (dish.is_featured) badges.push({ key: "featured", label: "Featured" });
  if (dish.is_chefs_special) badges.push({ key: "chefs_special", label: "Chef's special" });
  if (dish.is_unique_recipe) badges.push({ key: "unique_recipe", label: "Unique recipe" });
  return badges;
}
