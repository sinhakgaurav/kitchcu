import { useTranslation } from "react-i18next";
import type { DishHighlight, DishSort } from "../shared/listingControls";
import { DISH_HIGHLIGHT_OPTIONS, DISH_SORT_OPTIONS } from "../shared/listingControls";

type Chip = { id: string; label: string };

type Props = {
  search?: string;
  onSearchChange?: (v: string) => void;
  searchPlaceholder?: string;
  sort: string;
  onSortChange: (v: string) => void;
  sortOptions?: { value: string; label: string }[];
  /** Multi-select highlight chips (dish lists) */
  highlights?: DishHighlight[];
  onHighlightsChange?: (next: DishHighlight[]) => void;
  /** Extra single-select filter chips (e.g. diet) */
  filterChips?: Chip[];
  activeFilter?: string;
  onFilterChange?: (id: string) => void;
  resultCount?: number;
  className?: string;
};

const SORT_KEYS: Record<string, string> = {
  name_asc: "owner.list.sortNameAsc",
  name_desc: "owner.list.sortNameDesc",
  price_asc: "owner.list.sortPriceAsc",
  price_desc: "owner.list.sortPriceDesc",
  prep_asc: "owner.list.sortPrepAsc",
  newest: "owner.list.sortNewest",
};

const HIGHLIGHT_KEYS: Record<DishHighlight, string> = {
  featured: "owner.list.highlightFeatured",
  chefs_special: "owner.list.highlightChefs",
  unique_recipe: "owner.list.highlightUnique",
};

export function ListingToolbar({
  search,
  onSearchChange,
  searchPlaceholder,
  sort,
  onSortChange,
  sortOptions = DISH_SORT_OPTIONS,
  highlights,
  onHighlightsChange,
  filterChips,
  activeFilter = "",
  onFilterChange,
  resultCount,
  className = "",
}: Props) {
  const { t, ready } = useTranslation();
  const tx = (key: string, fallback: string, opts?: Record<string, unknown>) =>
    ready ? t(key, { defaultValue: fallback, ...opts }) : fallback;
  const placeholder = searchPlaceholder ?? tx("owner.list.search", "Search…");

  const toggleHighlight = (h: DishHighlight) => {
    if (!onHighlightsChange || !highlights) return;
    if (highlights.includes(h)) {
      onHighlightsChange(highlights.filter((x) => x !== h));
    } else {
      onHighlightsChange([...highlights, h]);
    }
  };

  return (
    <div className={`listing-toolbar ${className}`.trim()}>
      <div className="listing-toolbar__row">
        {onSearchChange ? (
          <label className="listing-toolbar__search">
            <span className="sr-only">{tx("common.search", "Search")}</span>
            <input
              type="search"
              value={search ?? ""}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={placeholder}
            />
          </label>
        ) : null}
        <label className="listing-toolbar__sort">
          <span>{tx("owner.list.sort", "Sort")}</span>
          <select value={sort} onChange={(e) => onSortChange(e.target.value)}>
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {SORT_KEYS[o.value] ? tx(SORT_KEYS[o.value], o.label) : o.label}
              </option>
            ))}
          </select>
        </label>
        {typeof resultCount === "number" && (
          <span className="listing-toolbar__count">
            {tx("owner.list.results", `${resultCount} result${resultCount === 1 ? "" : "s"}`, { count: resultCount })}
          </span>
        )}
      </div>

      {(onHighlightsChange || (filterChips && onFilterChange)) && (
        <div className="listing-toolbar__chips" role="group" aria-label={tx("owner.list.filters", "Filters")}>
          {onHighlightsChange &&
            DISH_HIGHLIGHT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`listing-chip${highlights?.includes(opt.value) ? " listing-chip--on" : ""}`}
                aria-pressed={highlights?.includes(opt.value) ?? false}
                onClick={() => toggleHighlight(opt.value)}
              >
                {tx(HIGHLIGHT_KEYS[opt.value], opt.label)}
              </button>
            ))}
          {filterChips?.map((chip) => (
            <button
              key={chip.id || "all"}
              type="button"
              className={`listing-chip${activeFilter === chip.id ? " listing-chip--on" : ""}`}
              aria-pressed={activeFilter === chip.id}
              onClick={() => onFilterChange?.(activeFilter === chip.id ? "" : chip.id)}
            >
              {chip.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export type { DishSort, DishHighlight };
