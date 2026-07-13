export type AdminOrderRow = {
  id: string;
  order_code: string;
  kitchen_name: string;
  status: string;
  total: number;
  created_at: string;
};

export type AdminOwnerRow = {
  subscription_tier: string;
  kitchen_count: number;
};

export type TimelinePoint = { date: string; count: number; revenue: number };
export type StatusSlice = { status: string; count: number };
export type KitchenSlice = { name: string; count: number; revenue: number };
export type TierSlice = { tier: string; count: number };

/** Local calendar date YYYY-MM-DD (avoids UTC shift from toISOString). */
export function localDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function buildOrderTimeline(orders: AdminOrderRow[], days = 14): TimelinePoint[] {
  const map = new Map<string, TimelinePoint>();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = localDateKey(d);
    map.set(key, { date: key, count: 0, revenue: 0 });
  }

  for (const o of orders) {
    const parsed = new Date(o.created_at);
    if (Number.isNaN(parsed.getTime())) continue;
    const key = localDateKey(parsed);
    if (!map.has(key)) continue;
    const point = map.get(key)!;
    point.count += 1;
    point.revenue += o.total;
  }

  return [...map.values()];
}

export function buildStatusBreakdown(orders: AdminOrderRow[]): StatusSlice[] {
  const counts = new Map<string, number>();
  for (const o of orders) {
    counts.set(o.status, (counts.get(o.status) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([status, count]) => ({ status, count }))
    .sort((a, b) => b.count - a.count);
}

export function buildTopKitchens(orders: AdminOrderRow[], limit = 6): KitchenSlice[] {
  const byKitchen = new Map<string, KitchenSlice>();
  for (const o of orders) {
    const existing = byKitchen.get(o.kitchen_name) ?? { name: o.kitchen_name, count: 0, revenue: 0 };
    existing.count += 1;
    existing.revenue += o.total;
    byKitchen.set(o.kitchen_name, existing);
  }
  return [...byKitchen.values()].sort((a, b) => b.count - a.count).slice(0, limit);
}

export function buildTierBreakdown(owners: AdminOwnerRow[]): TierSlice[] {
  const counts = new Map<string, number>();
  for (const o of owners) {
    counts.set(o.subscription_tier, (counts.get(o.subscription_tier) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([tier, count]) => ({ tier, count }))
    .sort((a, b) => b.count - a.count);
}
