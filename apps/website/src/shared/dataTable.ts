/** Client-side search / sort / page helpers for DataTable lists. */

export type SortDir = "asc" | "desc";

export function compareValues(a: string | number | null | undefined, b: string | number | null | undefined): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { sensitivity: "base", numeric: true });
}

export function filterBySearch<T>(
  rows: T[],
  query: string,
  getText: (row: T) => string,
): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((row) => getText(row).toLowerCase().includes(q));
}

export function filterByChip<T>(
  rows: T[],
  chip: string,
  getValue: (row: T) => string,
): T[] {
  if (!chip) return rows;
  return rows.filter((row) => getValue(row) === chip);
}

export function sortRows<T>(
  rows: T[],
  sortKey: string,
  dir: SortDir,
  getSortValue: (row: T, key: string) => string | number | null | undefined,
): T[] {
  if (!sortKey) return rows;
  const copy = [...rows];
  const mul = dir === "desc" ? -1 : 1;
  copy.sort((a, b) => mul * compareValues(getSortValue(a, sortKey), getSortValue(b, sortKey)));
  return copy;
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const start = Math.max(0, page) * pageSize;
  return rows.slice(start, start + pageSize);
}

export function pageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(Math.max(0, total) / pageSize));
}
