/** Customer dashboard APIs — orders insights, refunds, tickets, addresses, profile. */

import { getCustomerToken, type CustomerProfile } from "./customerApi";

async function dashFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  const headers: Record<string, string> = {
    ...(init?.body && !(init.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  }
  return body as T;
}

export type DashboardOrder = {
  order: {
    id: string;
    order_code: string;
    status: string;
    total: number;
    created_at: string;
    kitchen_id: string;
    tracking_token: string | null;
    payment_method: string;
  };
  items: Array<{
    id: string;
    dish_id: string;
    dish_name: string;
    quantity: number;
    unit_price: number;
    line_total: number;
    cuisine_name: string | null;
    diet: string | null;
    media: Array<{ url: string; is_live_capture?: boolean; is_hero?: boolean }>;
    restaurant_benchmark_price: number | null;
    saved_vs_restaurant: number;
  }>;
  can_rate: boolean;
  tracking_token: string | null;
  has_live_media: boolean;
  diets: string[];
  cuisines: string[];
};

export type CustomerDashboard = {
  orders: DashboardOrder[];
  savings: {
    total_saved: number;
    restaurant_equivalent_spend: number;
    kitchcu_spend: number;
    by_dish: Array<{ dish_name: string; saved: number }>;
  };
  health: {
    veg_share_pct: number;
    non_veg_share_pct: number;
    vegan_share_pct: number;
    home_freshness_score: number;
    restaurant_processed_score: number;
    note: string;
  };
  tips: Array<{
    after_dish: string | null;
    walk_minutes: number;
    water_ml: number;
    message: string;
  }>;
  filters: { cuisines: string[]; diets: string[] };
};

export type CustomerAddress = {
  id: string;
  label: string;
  address_line: string;
  city: string;
  state: string | null;
  pincode: string | null;
  landmark: string | null;
  latitude: number | null;
  longitude: number | null;
  is_default: boolean;
  created_at: string;
};

export type CustomerTicket = {
  id: string;
  ticket_number: string;
  category: string;
  status: string;
  subject: string;
  description: string;
  order_code: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerRefund = {
  id: string;
  order_id: string;
  kind: string;
  channel: string;
  amount: number;
  status: string;
  transfer_remark: string;
  completed_at: string | null;
  created_at: string;
};

export async function fetchCustomerDashboard(params?: {
  diet?: string;
  cuisine?: string;
  live_media_only?: boolean;
}): Promise<CustomerDashboard> {
  const qs = new URLSearchParams();
  if (params?.diet) qs.set("diet", params.diet);
  if (params?.cuisine) qs.set("cuisine", params.cuisine);
  if (params?.live_media_only) qs.set("live_media_only", "true");
  const q = qs.toString() ? `?${qs}` : "";
  return dashFetch(`/api/v1/customers/me/dashboard${q}`);
}

export async function fetchMyRefunds(): Promise<CustomerRefund[]> {
  return dashFetch("/api/v1/billing/refunds/customer/me");
}

export async function fetchMyTickets(): Promise<{ tickets: CustomerTicket[]; total: number }> {
  return dashFetch("/api/v1/customers/me/tickets");
}

export async function createMyTicket(data: {
  category: string;
  subject: string;
  description: string;
  order_code?: string;
}): Promise<CustomerTicket> {
  return dashFetch("/api/v1/customers/me/tickets", {
    method: "POST",
    body: JSON.stringify({
      audience: "customer",
      category: data.category,
      subject: data.subject,
      description: data.description,
      order_code: data.order_code,
      source: "web_form",
    }),
  });
}

export async function fetchMyAddresses(): Promise<CustomerAddress[]> {
  return dashFetch("/api/v1/customers/me/addresses");
}

export async function saveAddress(
  data: Omit<CustomerAddress, "id" | "created_at">,
  id?: string,
): Promise<CustomerAddress> {
  if (id) {
    return dashFetch(`/api/v1/customers/me/addresses/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }
  return dashFetch("/api/v1/customers/me/addresses", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteAddress(id: string): Promise<void> {
  await dashFetch(`/api/v1/customers/me/addresses/${id}`, { method: "DELETE" });
}

export async function updateMyProfile(data: {
  name?: string;
  email?: string | null;
}): Promise<CustomerProfile> {
  return dashFetch("/api/v1/customers/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function changeMyPassword(data: {
  new_password: string;
  current_password?: string;
  otp?: string;
}): Promise<CustomerProfile> {
  return dashFetch("/api/v1/customers/me/password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
