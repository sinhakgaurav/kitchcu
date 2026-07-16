import { APP_STORAGE_PREFIX } from "../shared/brand";
import { apiHeaders } from "../shared/http";

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
  const headers = apiHeaders({
    ...(init?.headers as Record<string, string> | undefined),
  });
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
  customers?: number;
  refunds_open?: number;
  refunds_completed?: number;
  tickets_open?: number;
  payments_captured?: number;
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

export type AdminCustomer = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  status: string;
  has_password: boolean;
  has_payout: boolean;
  address_count: number;
  created_at: string;
};

export type AdminCustomerDetail = AdminCustomer & {
  upi_vpa: string | null;
  upi_qr_url: string | null;
  bank_account_number_masked: string | null;
  bank_ifsc: string | null;
  bank_account_name: string | null;
  addresses: Array<{
    id: string;
    label: string;
    address_line: string;
    city: string;
    state: string | null;
    pincode: string | null;
    latitude: number | null;
    longitude: number | null;
    is_default: boolean;
  }>;
};

export async function fetchAdminCustomers(q?: string) {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return adminFetch<AdminCustomer[]>(`/api/v1/admin/customers${qs}`);
}

export async function fetchAdminCustomer(id: string) {
  return adminFetch<AdminCustomerDetail>(`/api/v1/admin/customers/${id}`);
}

export async function updateAdminCustomerStatus(id: string, status: string) {
  return adminFetch<AdminCustomer>(`/api/v1/admin/customers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function clearAdminCustomerPassword(id: string) {
  return adminFetch<AdminCustomerDetail>(`/api/v1/admin/customers/${id}/clear-password`, {
    method: "POST",
  });
}

export async function updateAdminOwnerSubscription(
  id: string,
  data: { subscription_tier?: string; subscription_status?: string },
) {
  return adminFetch(`/api/v1/admin/owners/${id}/subscription`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export type AdminRefund = {
  id: string;
  payment_id: string;
  order_id: string;
  kitchen_id: string;
  kind: string;
  channel: string;
  amount: number;
  status: string;
  destination_type: string;
  destination_upi: string | null;
  transfer_remark: string;
  evidence_url: string | null;
  reason: string | null;
  created_at: string;
  completed_at: string | null;
};

export async function fetchAdminRefunds(params?: { status?: string; kind?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.kind) qs.set("kind", params.kind);
  const q = qs.toString();
  return adminFetch<AdminRefund[]>(`/api/v1/admin/refunds${q ? `?${q}` : ""}`);
}

export async function patchAdminRefund(
  id: string,
  data: { status?: string; admin_note?: string },
) {
  return adminFetch<AdminRefund>(`/api/v1/admin/refunds/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchAdminPayments(status?: string) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return adminFetch<
    {
      id: string;
      order_id: string | null;
      amount: number;
      method: string;
      status: string;
      created_at: string;
    }[]
  >(`/api/v1/admin/payments${qs}`);
}

export async function fetchAdminMoneyStats() {
  return adminFetch<{
    payments_captured: number;
    payments_pending: number;
    refunds_requested: number;
    refunds_completed: number;
    refunds_failed: number;
    refunds_amount_completed: number;
    settlements_transferred: number;
  }>("/api/v1/admin/money-stats");
}

export type FeatureFlag = {
  key: string;
  enabled: boolean;
  scope: string;
  description: string | null;
  updated_at: string;
};

export async function fetchAdminFeatureFlags() {
  return adminFetch<FeatureFlag[]>("/api/v1/admin/feature-flags");
}

export async function updateAdminFeatureFlag(key: string, enabled: boolean) {
  return adminFetch<FeatureFlag>(`/api/v1/admin/feature-flags/${key}`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
}

export type PlatformApiKey = {
  key: string;
  category: string;
  description: string | null;
  is_secret: boolean;
  configured: boolean;
  value_masked: string | null;
  updated_at: string;
  updated_by: string | null;
};

export async function fetchAdminApiKeys() {
  return adminFetch<PlatformApiKey[]>("/api/v1/admin/api-keys");
}

export async function updateAdminApiKey(key: string, value: string) {
  return adminFetch<PlatformApiKey>(`/api/v1/admin/api-keys/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export async function clearAdminApiKey(key: string) {
  return adminFetch<PlatformApiKey>(`/api/v1/admin/api-keys/${key}`, {
    method: "DELETE",
  });
}

export async function fetchAdminJourneys() {
  return adminFetch<{
    stages: Array<{
      id: string;
      label: string;
      control: string;
      count: number;
      meta?: string;
      health: string;
    }>;
  }>("/api/v1/admin/journeys");
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

export async function fetchAdminOrders(limit = 100) {
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
  >(`/api/v1/admin/orders?limit=${limit}`);
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
