/** Unauthenticated customer-facing API (no owner JWT). */

import type { KitchenNearbyList, Menu } from "./api";

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
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

export async function fetchPublicMenu(kitchenId: string): Promise<Menu> {
  return publicFetch(`/api/v1/kitchens/${kitchenId}/menu`);
}

export async function fetchKitchenByCode(code: string): Promise<import("./api").KitchenPublic> {
  return publicFetch(
    `/api/v1/kitchens/public/by-code/${encodeURIComponent(code.trim().toUpperCase())}`,
  );
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
  return publicFetch(`/api/v1/kitchens/public/nearby?${q.toString()}`);
}
