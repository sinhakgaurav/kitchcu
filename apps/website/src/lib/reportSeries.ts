import type { RevenuePoint } from "./api";

/** Daily bars stay readable up to a month; longer windows must roll up. */
const DAILY_MAX_DAYS = 31;
const WEEKLY_MAX_DAYS = 100;

function parseDay(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function ymd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function mondayOf(d: Date): Date {
  const copy = new Date(d);
  const weekday = copy.getDay();
  const back = weekday === 0 ? 6 : weekday - 1;
  copy.setDate(copy.getDate() - back);
  return copy;
}

function rollup(points: RevenuePoint[], keyOf: (d: Date) => string): RevenuePoint[] {
  const buckets = new Map<string, RevenuePoint>();
  for (const point of points) {
    const key = keyOf(parseDay(point.date));
    const current = buckets.get(key) ?? { date: key, revenue: 0, orders: 0 };
    current.revenue += point.revenue;
    current.orders += point.orders;
    buckets.set(key, current);
  }
  return [...buckets.values()];
}

export function bucketRevenuePoints(points: RevenuePoint[], days: number): RevenuePoint[] {
  if (days <= DAILY_MAX_DAYS) return points;
  if (days <= WEEKLY_MAX_DAYS) {
    return rollup(points, (d) => ymd(mondayOf(d)));
  }
  return rollup(points, (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`);
}

export function chartPointLabel(isoDate: string, days: number): string {
  const d = parseDay(isoDate);
  if (days <= 7) {
    return d.toLocaleDateString("en-IN", { weekday: "short" });
  }
  if (days <= DAILY_MAX_DAYS) {
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  }
  if (days <= WEEKLY_MAX_DAYS) {
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  }
  return d.toLocaleDateString("en-IN", { month: "short" });
}

export function chartGrainLabel(days: number): string {
  if (days <= DAILY_MAX_DAYS) return "Daily gross revenue over the selected period";
  if (days <= WEEKLY_MAX_DAYS) return "Weekly gross revenue over the selected period";
  return "Monthly gross revenue over the selected period";
}
