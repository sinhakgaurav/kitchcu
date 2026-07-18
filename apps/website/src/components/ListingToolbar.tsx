import type { DishHighlight, DishSort } from "../shared/listingControls";
import { DISH_HIGHLIGHT_OPTIONS, DISH_SORT_OPTIONS } from "../shared/listingControls";

type Chip = { id: string; label: string };

type Props = {
  search: string;
  onSearchChange: (v: string) => void;
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

export function ListingToolbar({
  search,
  onSearchChange,
  searchPlaceholder = "Search…",
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
        <label className="listing-toolbar__search">
          <span className="sr-only">Search</span>
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
          />
        </label>
        <label className="listing-toolbar__sort">
          <span>Sort</span>
          <select value={sort} onChange={(e) => onSortChange(e.target.value)}>
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        {typeof resultCount === "number" && (
          <span className="listing-toolbar__count">{resultCount} result{resultCount === 1 ? "" : "s"}</span>
        )}
      </div>

      {(onHighlightsChange || (filterChips && onFilterChange)) && (
        <div className="listing-toolbar__chips" role="group" aria-label="Filters">
          {onHighlightsChange &&
            DISH_HIGHLIGHT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`listing-chip${highlights?.includes(opt.value) ? " listing-chip--on" : ""}`}
                aria-pressed={highlights?.includes(opt.value) ?? false}
                onClick={() => toggleHighlight(opt.value)}
              >
                {opt.label}
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
