/** Unauthenticated customer-facing API (no owner JWT). */

import type { DishHealthSnapshot, KitchenNearbyList, Menu } from "./api";
import { getCustomerToken } from "./customerApi";
import { DEMO } from "./demo";

export type PublicActivePromotion = {
  promotion_id: string;
  name: string;
  dish_id: string;
  dish_name: string;
  special_price: number;
  segment: string;
};

export type DiscoveryKitchenCard = {
  id: string;
  code: string;
  name: string;
  city: string | null;
  distance_km: number;
  latitude: number;
  longitude: number;
  has_veg: boolean;
  has_non_veg: boolean;
  has_live_capture: boolean;
  is_live_now: boolean;
  is_featured: boolean;
  avg_rating: number | null;
  rating_count: number;
  min_dish_price: number | null;
  tagline: string | null;
  logo_url: string | null;
  compatible_dish_count?: number | null;
  better_for_report?: boolean;
};

export type DiscoveryDishCard = {
  dish_id: string;
  kitchen_id: string;
  kitchen_code: string;
  kitchen_name: string;
  dish_name: string;
  price: number;
  distance_km: number;
  is_live_capture_hero: boolean;
  image_url: string | null;
};

export type DiscoveryHome = {
  customer_latitude: number;
  customer_longitude: number;
  max_km: number;
  total_kitchens: number;
  near_you: DiscoveryKitchenCard[];
  featured: DiscoveryKitchenCard[];
  most_liked: DiscoveryKitchenCard[];
  live_now: DiscoveryKitchenCard[];
  cheapest_dishes: DiscoveryDishCard[];
  diet_filter_applied?: boolean;
};

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  const res = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers as Record<string, string> | undefined),
    },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    throw new Error(detail);
  }
  return body as T;
}

export async function fetchPublicMenu(
  kitchenId: string,
  opts?: { highlight?: string; diet?: string; q?: string; sort?: string },
): Promise<Menu> {
  const q = new URLSearchParams();
  if (opts?.highlight) q.set("highlight", opts.highlight);
  if (opts?.diet) q.set("diet", opts.diet);
  if (opts?.q) q.set("q", opts.q);
  if (opts?.sort) q.set("sort", opts.sort);
  const qs = q.toString();
  return publicFetch(`/api/v1/kitchens/${kitchenId}/menu${qs ? `?${qs}` : ""}`);
}

export async function fetchDishesHealth(dishIds: string[]): Promise<{
  dishes: DishHealthSnapshot[];
  total: number;
}> {
  const unique = [...new Set(dishIds.filter(Boolean))].slice(0, 40);
  if (unique.length === 0) return { dishes: [], total: 0 };
  return publicFetch(`/api/v1/dishes/health?ids=${unique.join(",")}`);
}

export async function fetchKitchenByCode(code: string): Promise<import("./api").KitchenPublic> {
  return publicFetch(
    `/api/v1/kitchens/public/by-code/${encodeURIComponent(code.trim().toUpperCase())}`,
  );
}

export async function resolveDemoKitchen(): Promise<import("./api").KitchenPublic> {
  try {
    const kitchen = await fetchKitchenByCode(DEMO.kitchenCode);
    if (kitchen.name === DEMO.kitchenName) return kitchen;
  } catch {
    /* code may have been consumed by leftover test data */
  }
  const nearby = await fetchPublicNearbyKitchens({
    latitude: DEMO.defaultLocation.latitude,
    longitude: DEMO.defaultLocation.longitude,
    max_km: 15,
    q: DEMO.kitchenName,
    limit: 20,
  });
  const match =
    nearby.kitchens.find((k) => k.name === DEMO.kitchenName) ??
    nearby.nearest.find((k) => k.name === DEMO.kitchenName);
  if (!match) throw new Error("Demo kitchen not found. Run seed-dev-data.py.");
  return fetchKitchenByCode(match.code);
}

export async function fetchPublicNearbyKitchens(params: {
  latitude: number;
  longitude: number;
  limit?: number;
  max_km?: number;
  sort?: "asc" | "desc";
  diet?: string;
  live_capture?: boolean;
  live_only?: boolean;
  q?: string;
}): Promise<KitchenNearbyList> {
  const q = new URLSearchParams({
    latitude: String(params.latitude),
    longitude: String(params.longitude),
    sort: params.sort ?? "asc",
  });
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.max_km != null) q.set("max_km", String(params.max_km));
  if (params.diet) q.set("diet", params.diet);
  if (params.live_capture) q.set("live_capture", "true");
  if (params.live_only) q.set("live_only", "true");
  if (params.q?.trim()) q.set("q", params.q.trim());
  return publicFetch(`/api/v1/kitchens/public/nearby?${q.toString()}`);
}

export async function fetchDiscoveryHome(params: {
  latitude: number;
  longitude: number;
  max_km?: number;
  section_limit?: number;
  q?: string;
}): Promise<DiscoveryHome> {
  const query = new URLSearchParams({
    latitude: String(params.latitude),
    longitude: String(params.longitude),
  });
  if (params.max_km != null) query.set("max_km", String(params.max_km));
  if (params.section_limit != null) query.set("section_limit", String(params.section_limit));
  if (params.q?.trim()) query.set("q", params.q.trim());
  return publicFetch(`/api/v1/discovery/home?${query.toString()}`);
}

export async function fetchPublicActivePromotions(
  kitchenId: string,
): Promise<{ promotions: PublicActivePromotion[] }> {
  const token = getCustomerToken();
  return publicFetch(`/api/v1/kitchens/${kitchenId}/promotions/active`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}
