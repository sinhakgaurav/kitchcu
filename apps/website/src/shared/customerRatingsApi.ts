/** Customer ratings API (F16–F18) */

import { apiHeaders } from "./http";
import { getCustomerToken } from "./customerApi";

export type DishRatingSummary = {
  dish_id: string;
  rating_count: number;
  avg_home_taste: number;
  avg_quality: number;
  overall_rating: number;
};

export type DishRatingInput = {
  dish_id: string;
  home_taste_score: number;
  quality_score: number;
  media_url?: string;
  media_type?: "video" | "audio";
};

export type DishRating = {
  id: string;
  dish_id: string;
  order_id: string;
  home_taste_score: number;
  quality_score: number;
  media_url: string | null;
  media_type: string | null;
  is_anonymous: boolean;
  created_at: string;
};

export type HealthNudge = {
  message: string;
  walk_minutes: number;
  water_ml: number;
};

async function ratingsFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  const headers: Record<string, string> = {
    ...apiHeaders(),
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    throw new Error(detail);
  }
  return body as T;
}

export async function fetchKitchenRatingSummaries(
  kitchenId: string,
): Promise<{ summaries: DishRatingSummary[] }> {
  return ratingsFetch(`/api/v1/kitchens/${kitchenId}/ratings/summaries`);
}

export async function submitOrderRatings(
  orderId: string,
  ratings: DishRatingInput[],
): Promise<{ ratings: DishRating[]; health_nudge: HealthNudge }> {
  return ratingsFetch(`/api/v1/customers/me/orders/${orderId}/ratings`, {
    method: "POST",
    body: JSON.stringify({ ratings }),
  });
}

export async function fetchDishReviews(
  kitchenId: string,
  dishId: string,
): Promise<{ reviews: { id: string; home_taste_score: number; quality_score: number; media_url: string | null; media_type: string | null }[]; total: number }> {
  return ratingsFetch(`/api/v1/kitchens/${kitchenId}/dishes/${dishId}/ratings/reviews`);
}
