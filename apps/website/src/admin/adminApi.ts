import { APP_STORAGE_PREFIX } from "../shared/brand";

const TOKEN_KEY = `${APP_STORAGE_PREFIX}_admin_token`;

export function getAdminToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  return body as T;
}

export type PlatformStats = {
  owners: number;
  kitchens: number;
  active_kitchens: number;
  orders: number;
  dishes: number;
};

export async function adminLogin(email: string, password: string) {
  return adminFetch<{ access_token: string }>("/api/v1/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchAdminStats(): Promise<PlatformStats> {
  return adminFetch("/api/v1/admin/stats");
}

export async function fetchAdminKitchens() {
  return adminFetch<
    {
      id: string;
      code: string;
      name: string;
      city: string | null;
      status: string;
      owner_name: string;
      owner_phone: string;
    }[]
  >("/api/v1/admin/kitchens");
}

export async function fetchAdminOrders() {
  return adminFetch<
    {
      id: string;
      order_code: string;
      kitchen_name: string;
      status: string;
      total: number;
      customer_name: string | null;
      created_at: string;
    }[]
  >("/api/v1/admin/orders");
}

export async function updateKitchenStatus(kitchenId: string, status: string) {
  return adminFetch(`/api/v1/admin/kitchens/${kitchenId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function fetchAdminOwners() {
  return adminFetch<
    {
      id: string;
      name: string;
      phone: string;
      email: string | null;
      subscription_tier: string;
      subscription_status: string;
      kitchen_count: number;
    }[]
  >("/api/v1/admin/owners");
}

export type AdminTicket = {
  id: string;
  ticket_number: string;
  audience: string;
  category: string;
  status: string;
  priority: string;
  subject: string;
  description: string;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  order_code: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
  messages: { id: string; author_type: string; message: string; created_at: string }[];
};

export async function fetchAdminTickets(params?: { status?: string; audience?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.audience) qs.set("audience", params.audience);
  const q = qs.toString();
  return adminFetch<{ tickets: AdminTicket[]; total: number }>(
    `/api/v1/admin/tickets${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminTicket(id: string) {
  return adminFetch<AdminTicket>(`/api/v1/admin/tickets/${id}`);
}

export async function updateAdminTicket(
  id: string,
  data: { status?: string; priority?: string; resolution_note?: string },
) {
  return adminFetch<AdminTicket>(`/api/v1/admin/tickets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function replyAdminTicket(id: string, message: string) {
  return adminFetch<AdminTicket>(`/api/v1/admin/tickets/${id}/reply`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
