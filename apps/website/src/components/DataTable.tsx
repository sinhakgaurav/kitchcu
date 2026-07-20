import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ListingToolbar } from "./ListingToolbar";
import {
  filterByChip,
  filterBySearch,
  pageCount,
  paginateRows,
  sortRows,
  type SortDir,
} from "../shared/dataTable";

export type DataColumn<T> = {
  id: string;
  header: string;
  /** When set, column header is clickable for sort */
  sortable?: boolean;
  sortValue?: (row: T) => string | number | null | undefined;
  cell: (row: T) => ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
};

type FilterChip = { id: string; label: string };

type Props<T> = {
  rows: T[];
  columns: DataColumn<T>[];
  rowKey: (row: T) => string;
  /** Concatenated search haystack per row */
  getSearchText: (row: T) => string;
  searchPlaceholder?: string;
  filterChips?: FilterChip[];
  getFilterValue?: (row: T) => string;
  defaultPageSize?: number;
  loading?: boolean;
  emptyMessage?: string;
  rowClassName?: (row: T) => string | undefined;
  className?: string;
  /** Seed the search box (e.g. deep-link from tickets → refunds). */
  initialSearch?: string;
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  getSearchText,
  searchPlaceholder = "Search…",
  filterChips,
  getFilterValue,
  defaultPageSize = 25,
  loading = false,
  emptyMessage = "No rows yet.",
  rowClassName,
  className = "",
  initialSearch = "",
}: Props<T>) {
  const [search, setSearch] = useState(initialSearch);
  const [activeFilter, setActiveFilter] = useState("");
  const [sortKey, setSortKey] = useState(() => columns.find((c) => c.sortable)?.id ?? "");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(defaultPageSize);

  useEffect(() => {
    if (initialSearch) {
      setSearch(initialSearch);
      setPage(0);
    }
  }, [initialSearch]);

  const sortOptions = useMemo(
    () => [
      { value: "", label: "Default" },
      ...columns
        .filter((c) => c.sortable)
        .flatMap((c) => [
          { value: `${c.id}:asc`, label: `${c.header} ↑` },
          { value: `${c.id}:desc`, label: `${c.header} ↓` },
        ]),
    ],
    [columns],
  );

  const sortSelectValue = sortKey ? `${sortKey}:${sortDir}` : "";

  const processed = useMemo(() => {
    let list = filterBySearch(rows, search, getSearchText);
    if (getFilterValue) {
      list = filterByChip(list, activeFilter, getFilterValue);
    }
    const col = columns.find((c) => c.id === sortKey);
    if (col?.sortable) {
      list = sortRows(list, sortKey, sortDir, (row, key) => {
        const c = columns.find((x) => x.id === key);
        return c?.sortValue ? c.sortValue(row) : null;
      });
    }
    return list;
  }, [rows, search, activeFilter, sortKey, sortDir, columns, getSearchText, getFilterValue]);

  const pages = pageCount(processed.length, pageSize);
  const safePage = Math.min(page, pages - 1);
  const pageRows = paginateRows(processed, safePage, pageSize);

  useEffect(() => {
    setPage(0);
  }, [search, activeFilter, sortKey, sortDir, pageSize]);

  const onHeaderSort = (colId: string) => {
    if (sortKey === colId) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(colId);
      setSortDir("asc");
    }
  };

  return (
    <div className={`data-table ${className}`.trim()}>
      <ListingToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder={searchPlaceholder}
        sort={sortSelectValue}
        onSortChange={(v) => {
          if (!v) {
            setSortKey("");
            return;
          }
          const [key, dir] = v.split(":");
          setSortKey(key);
          setSortDir(dir === "desc" ? "desc" : "asc");
        }}
        sortOptions={sortOptions}
        filterChips={filterChips}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        resultCount={processed.length}
      />

      <div className="dash-card data-table__frame admin-table-wrap">
        {loading ? (
          <p className="admin-panel__empty">Loading…</p>
        ) : pageRows.length === 0 ? (
          <p className="admin-panel__empty">{emptyMessage}</p>
        ) : (
          <table className="admin-table data-table__table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.id}
                    className={[
                      col.className,
                      col.sortable ? "data-table__th--sortable" : "",
                      sortKey === col.id ? "data-table__th--sorted" : "",
                      col.align === "right" ? "data-table__th--right" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    aria-sort={
                      sortKey === col.id ? (sortDir === "asc" ? "ascending" : "descending") : undefined
                    }
                  >
                    {col.sortable ? (
                      <button type="button" className="data-table__sort-btn" onClick={() => onHeaderSort(col.id)}>
                        {col.header}
                        {sortKey === col.id ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => (
                <tr key={rowKey(row)} className={rowClassName?.(row)}>
                  {columns.map((col) => (
                    <td
                      key={col.id}
                      className={[col.className, col.align === "right" ? "data-table__td--right" : ""]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="data-table__pager">
        <span className="data-table__pager-meta">
          Page {safePage + 1} of {pages}
          {processed.length > 0
            ? ` · ${safePage * pageSize + 1}–${Math.min((safePage + 1) * pageSize, processed.length)} of ${processed.length}`
            : ""}
        </span>
        <div className="data-table__pager-actions">
          <label className="data-table__page-size">
            <span>Rows</span>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={safePage <= 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={safePage >= pages - 1}
            onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
