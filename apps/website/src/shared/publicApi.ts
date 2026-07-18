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
