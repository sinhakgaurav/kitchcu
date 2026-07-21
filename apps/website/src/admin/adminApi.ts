import { APP_STORAGE_PREFIX } from "../shared/brand";
import { apiHeaders, correlationHeaders } from "../shared/http";

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

export type AdminLoginHint = {
  email: string;
  password: string | null;
  revealed: boolean;
  source: string;
};

/** Public bring-up hint — password only when identity allows reveal (demo / flag). */
export async function fetchAdminLoginHint(): Promise<AdminLoginHint> {
  const res = await fetch("/api/v1/admin/auth/login-hint", {
    headers: apiHeaders(),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  return body as AdminLoginHint;
}

export type AdminMe = {
  id: string;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  allowed_tabs: string[];
};

export async function fetchAdminMe(): Promise<AdminMe> {
  return adminFetch("/api/v1/admin/me");
}

export type AdminAuditEvent = {
  id: string;
  actor_admin_id: string | null;
  actor_email: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  kitchen_id: string | null;
  summary: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  correlation_id: string | null;
  created_at: string;
};

export async function fetchAdminAuditEvents(params?: {
  limit?: number;
  resource_type?: string;
}): Promise<{ total: number; items: AdminAuditEvent[] }> {
  const q = new URLSearchParams();
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.resource_type) q.set("resource_type", params.resource_type);
  const suffix = q.toString() ? `?${q}` : "";
  return adminFetch(`/api/v1/admin/audit-events${suffix}`);
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

export type AdminKitchenBrandedPage = {
  enabled: boolean;
  tagline: string | null;
  accent_color: string | null;
  logo_url?: string | null;
  background_url?: string | null;
  logo_align?: "left" | "center" | "right";
  heading_align?: "left" | "center" | "right";
};

export type AdminKitchen = {
  id: string;
  code: string;
  name: string;
  city: string | null;
  status: string;
  owner_name: string;
  owner_phone: string;
  whatsapp_connected: boolean;
  payment_gateway_configured: boolean;
  branded_page_enabled?: boolean;
  last_order_at?: string | null;
  open_ticket_count?: number;
  open_refund_count?: number;
};

export type AdminKitchenDetail = AdminKitchen & {
  owner_id: string;
  address_line: string | null;
  state: string | null;
  pincode: string | null;
  whatsapp_phone_id: string | null;
  whatsapp_display_phone: string | null;
  branded_page?: AdminKitchenBrandedPage;
  porter_auto_book_enabled?: boolean;
  porter_auto_book_delay_min?: number;
  platform_secrets_note: string;
};

export type AdminKitchenWhatsApp = {
  kitchen_id: string;
  whatsapp_phone_id: string | null;
  whatsapp_display_phone: string | null;
  connected: boolean;
  platform_secrets_note: string;
};

export type AdminKitchenPaymentGateway = {
  kitchen_id: string;
  provider: string;
  key_id: string | null;
  key_secret_configured: boolean;
  key_secret_masked: string | null;
  webhook_secret_configured: boolean;
  webhook_secret_masked: string | null;
  linked_account_id: string | null;
  is_active: boolean;
  updated_at: string | null;
};

export type AdminKitchenModuleFlags = {
  kitchen_id: string;
  kitchen_code: string;
  modules: { module_key: string; enabled: boolean; updated_at: string }[];
};

export async function fetchAdminKitchens() {
  return adminFetch<AdminKitchen[]>("/api/v1/admin/kitchens");
}

export async function fetchAdminKitchen(kitchenId: string) {
  return adminFetch<AdminKitchenDetail>(`/api/v1/admin/kitchens/${kitchenId}`);
}

export async function updateAdminKitchenBrandedPage(
  kitchenId: string,
  data: {
    enabled?: boolean;
    tagline?: string | null;
    accent_color?: string | null;
    logo_url?: string | null;
    background_url?: string | null;
    logo_align?: "left" | "center" | "right";
    heading_align?: "left" | "center" | "right";
  },
) {
  return adminFetch<AdminKitchenDetail>(`/api/v1/admin/kitchens/${kitchenId}/branded-page`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function uploadAdminKitchenBrandMedia(
  kitchenId: string,
  file: Blob,
  slot: "logo" | "background",
  filename = "brand.jpg",
) {
  const form = new FormData();
  form.append("file", file, filename);
  form.append("slot", slot);
  const token = getAdminToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api/v1/admin/kitchens/${kitchenId}/branded-page/media`, {
    method: "POST",
    headers,
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Brand media upload failed";
    throw new Error(detail);
  }
  return body as AdminKitchenDetail;
}

export async function fetchAdminKitchenWhatsApp(kitchenId: string) {
  return adminFetch<AdminKitchenWhatsApp>(
    `/api/v1/admin/kitchens/${kitchenId}/whatsapp-integration`,
  );
}

export async function upsertAdminKitchenWhatsApp(
  kitchenId: string,
  data: {
    whatsapp_phone_id?: string | null;
    whatsapp_display_phone?: string | null;
    clear?: boolean;
  },
) {
  return adminFetch<AdminKitchenWhatsApp>(
    `/api/v1/admin/kitchens/${kitchenId}/whatsapp-integration`,
    { method: "PUT", body: JSON.stringify(data) },
  );
}

export async function fetchAdminKitchenPaymentGateway(kitchenId: string) {
  return adminFetch<AdminKitchenPaymentGateway>(
    `/api/v1/admin/kitchens/${kitchenId}/payment-gateway`,
  );
}

export async function upsertAdminKitchenPaymentGateway(
  kitchenId: string,
  data: {
    key_id?: string | null;
    key_secret?: string | null;
    webhook_secret?: string | null;
    linked_account_id?: string | null;
    is_active?: boolean;
  },
) {
  return adminFetch<AdminKitchenPaymentGateway>(
    `/api/v1/admin/kitchens/${kitchenId}/payment-gateway`,
    { method: "PUT", body: JSON.stringify(data) },
  );
}

export async function clearAdminKitchenPaymentGateway(kitchenId: string) {
  return adminFetch<AdminKitchenPaymentGateway>(
    `/api/v1/admin/kitchens/${kitchenId}/payment-gateway`,
    { method: "DELETE" },
  );
}

export async function fetchAdminKitchenModuleFlags(kitchenId: string) {
  return adminFetch<AdminKitchenModuleFlags>(
    `/api/v1/admin/kitchens/${kitchenId}/module-flags`,
  );
}

export async function updateAdminKitchenModuleFlag(
  kitchenId: string,
  moduleKey: string,
  enabled: boolean,
) {
  return adminFetch<{ module_key: string; enabled: boolean; updated_at: string }>(
    `/api/v1/admin/kitchens/${kitchenId}/module-flags/${moduleKey}`,
    { method: "PATCH", body: JSON.stringify({ enabled }) },
  );
}

export async function updateAdminKitchenDeliverySettings(
  kitchenId: string,
  data: {
    porter_auto_book_enabled?: boolean;
    porter_auto_book_delay_min?: number;
  },
) {
  return adminFetch<AdminKitchenDetail>(
    `/api/v1/admin/kitchens/${kitchenId}/delivery-settings`,
    { method: "PATCH", body: JSON.stringify(data) },
  );
}

export type AdminOrder = {
  id: string;
  order_code: string;
  kitchen_id: string;
  kitchen_name: string;
  customer_id: string | null;
  status: string;
  total: number;
  customer_name: string | null;
  customer_phone: string | null;
  created_at: string;
};

export async function fetchAdminOrders(
  limit = 100,
  params?: { kitchen_id?: string; customer_id?: string; status?: string },
) {
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  if (params?.kitchen_id) qs.set("kitchen_id", params.kitchen_id);
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
  if (params?.status) qs.set("status", params.status);
  return adminFetch<AdminOrder[]>(`/api/v1/admin/orders?${qs}`);
}

export type AdminSettlement = {
  id: string;
  kitchen_id: string;
  order_id: string;
  gross_amount: number;
  platform_fee: number;
  net_to_owner: number;
  settlement_status: string;
  settled_at: string | null;
};

export async function fetchAdminSettlements(params?: { kitchen_id?: string; limit?: number }) {
  const qs = new URLSearchParams();
  if (params?.kitchen_id) qs.set("kitchen_id", params.kitchen_id);
  qs.set("limit", String(params?.limit ?? 200));
  return adminFetch<AdminSettlement[]>(`/api/v1/admin/settlements?${qs}`);
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
  customer_id: string | null;
  order_code: string | null;
  kitchen_id: string | null;
  assigned_admin_id: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
  messages: { id: string; author_type: string; message: string; created_at: string }[];
};

export async function fetchAdminTickets(params?: {
  status?: string;
  audience?: string;
  kitchen_id?: string;
  customer_id?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.audience) qs.set("audience", params.audience);
  if (params?.kitchen_id) qs.set("kitchen_id", params.kitchen_id);
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
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
  data: {
    status?: string;
    priority?: string;
    assigned_admin_id?: string | null;
    resolution_note?: string;
  },
) {
  return adminFetch<AdminTicket>(`/api/v1/admin/tickets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** Cross-tab navigation inside the admin shell (kitchen/refunds/tickets deep-links). */
export type AdminNavDetail = {
  tab: string;
  kitchenId?: string;
  refundSearch?: string;
  customerId?: string;
};

export function adminNavigate(detail: AdminNavDetail) {
  window.dispatchEvent(new CustomEvent("kitchcu-admin-nav", { detail }));
}

export async function replyAdminTicket(id: string, message: string) {
  return adminFetch<AdminTicket>(`/api/v1/admin/tickets/${id}/reply`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export type AdminEmployee = {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  permissions: string[];
};

export async function fetchAdminEmployees() {
  return adminFetch<AdminEmployee[]>("/api/v1/admin/employees");
}

export async function fetchAdminEmployeeRoles() {
  return adminFetch<string[]>("/api/v1/admin/employees/roles");
}

export async function createAdminEmployee(data: {
  email: string;
  name: string;
  password: string;
  role: string;
}) {
  return adminFetch<AdminEmployee>("/api/v1/admin/employees", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAdminEmployee(
  id: string,
  data: { name?: string; role?: string; password?: string; is_active?: boolean },
) {
  return adminFetch<AdminEmployee>(`/api/v1/admin/employees/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export type AdminPackage = {
  id: string;
  code: string;
  name: string;
  audience: string;
  description: string | null;
  is_active: boolean;
  feature_keys: string[];
  plan_tiers: string[];
};

export type AdminFeature = {
  key: string;
  label: string;
  description: string | null;
  audience: string;
  module_key: string | null;
};

export async function fetchAdminFeatures() {
  return adminFetch<AdminFeature[]>("/api/v1/admin/features");
}

export async function fetchAdminPackages(audience?: string) {
  const q = audience ? `?audience=${encodeURIComponent(audience)}` : "";
  return adminFetch<AdminPackage[]>(`/api/v1/admin/packages${q}`);
}

export async function upsertAdminPackage(
  data: {
    code: string;
    name: string;
    audience: string;
    description?: string | null;
    is_active?: boolean;
    feature_keys: string[];
    plan_tiers: string[];
  },
  packageId?: string,
) {
  if (packageId) {
    return adminFetch<AdminPackage>(`/api/v1/admin/packages/${packageId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }
  return adminFetch<AdminPackage>("/api/v1/admin/packages", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export type AdminKitchenPackage = {
  kitchen_id: string;
  package: AdminPackage | null;
  source: string;
  owner_plan_tier: string | null;
};

export async function fetchAdminKitchenPackage(kitchenId: string) {
  return adminFetch<AdminKitchenPackage>(`/api/v1/admin/kitchens/${kitchenId}/package`);
}

export async function assignAdminKitchenPackage(
  kitchenId: string,
  data: { package_id: string; notes?: string; sync_module_flags?: boolean },
) {
  return adminFetch<AdminKitchenPackage>(`/api/v1/admin/kitchens/${kitchenId}/package`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export type AdminTiffinSummary = {
  kitchen_id: string;
  plans_total: number;
  plans_active: number;
  pending: number;
  active: number;
  paused: number;
  denied: number;
  cancelled: number;
  mrr_estimate: number;
};

export async function fetchAdminKitchenTiffinSummary(kitchenId: string) {
  return adminFetch<AdminTiffinSummary>(`/api/v1/admin/kitchens/${kitchenId}/tiffin-summary`);
}

export type AdminTiffinSubscription = {
  id: string;
  kitchen_id: string;
  plan_id: string;
  plan_name: string | null;
  plan_type: string | null;
  price_monthly: number | null;
  customer_id: string;
  customer_phone: string;
  customer_name: string | null;
  status: string;
  billing_status: string;
  owner_note: string | null;
  starts_on: string | null;
  created_at: string;
  decided_at: string | null;
};

export async function fetchAdminKitchenSubscriptions(
  kitchenId: string,
  status?: string,
) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return adminFetch<{ subscriptions: AdminTiffinSubscription[]; total: number }>(
    `/api/v1/admin/kitchens/${kitchenId}/subscriptions${q}`,
  );
}

export async function decideAdminKitchenSubscription(
  kitchenId: string,
  subId: string,
  action: "accept" | "deny" | "activate" | "deactivate",
  body: { owner_note?: string; starts_on?: string } = {},
) {
  return adminFetch<AdminTiffinSubscription>(
    `/api/v1/admin/kitchens/${kitchenId}/subscriptions/${subId}/${action}`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export type AdminGstProfile = {
  id: string;
  kitchen_id: string;
  gstin: string;
  legal_name: string;
  trade_name: string | null;
  state_code: string;
  registered_address: string;
  default_tax_rate: number;
  is_active: boolean;
};

export type AdminGstMonthlyReport = {
  kitchen_id: string;
  period_year: number;
  period_month: number;
  gstin: string;
  legal_name: string;
  invoice_count: number;
  total_taxable: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  total_tax: number;
  total_gross_sales: number;
  audit_status: string;
  invoices: Array<{
    id: string;
    invoice_number: string;
    order_code: string;
    invoice_date: string;
    taxable_value: number;
    cgst_amount: number;
    sgst_amount: number;
    gross_total: number;
  }>;
};

export async function fetchAdminKitchenGstProfile(kitchenId: string) {
  return adminFetch<AdminGstProfile>(`/api/v1/admin/kitchens/${kitchenId}/gst/profile`);
}

export async function fetchAdminKitchenGstMonthly(
  kitchenId: string,
  year: number,
  month: number,
) {
  return adminFetch<AdminGstMonthlyReport>(
    `/api/v1/admin/kitchens/${kitchenId}/gst/reports/monthly?year=${year}&month=${month}`,
  );
}

async function adminDownloadBlob(path: string, filename: string): Promise<void> {
  const token = getAdminToken();
  const res = await fetch(path, {
    headers: correlationHeaders(token ? { Authorization: `Bearer ${token}` } : undefined),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadAdminKitchenGstExcel(
  kitchenId: string,
  year: number,
  month: number,
) {
  return adminDownloadBlob(
    `/api/v1/admin/kitchens/${kitchenId}/gst/reports/monthly/export.xlsx?year=${year}&month=${month}`,
    `kitchcu-gst-${year}-${String(month).padStart(2, "0")}.xlsx`,
  );
}

export async function downloadAdminKitchenGstPdf(
  kitchenId: string,
  year: number,
  month: number,
) {
  return adminDownloadBlob(
    `/api/v1/admin/kitchens/${kitchenId}/gst/reports/monthly/export.pdf?year=${year}&month=${month}`,
    `kitchcu-gst-${year}-${String(month).padStart(2, "0")}.pdf`,
  );
}

export async function fetchAdminKitchenTemplates(kitchenId: string) {
  return adminFetch<
    {
      id: string;
      channel: string;
      name: string;
      is_active: boolean;
      body: string;
    }[]
  >(`/api/v1/admin/kitchens/${kitchenId}/templates`);
}

export type AdminReferralSettings = {
  enabled: boolean;
  customer_to_kitchen_reward_inr: number;
  kitchen_to_customer_reward_inr: number;
  kitchen_reward_trigger: string;
};

export type AdminReferralLead = {
  id: string;
  direction: string;
  status: string;
  kitchen_name: string | null;
  contact_name: string | null;
  contact_phone: string;
  contact_email: string | null;
  city: string | null;
  reward_inr: number | null;
  created_at: string;
  converted_at: string | null;
  rejection_reason: string | null;
};

export async function fetchReferralSettings() {
  return adminFetch<AdminReferralSettings>("/api/v1/admin/referrals/settings");
}

export async function patchReferralSettings(patch: Partial<AdminReferralSettings>) {
  return adminFetch<AdminReferralSettings>("/api/v1/admin/referrals/settings", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function fetchReferralLeads(params?: {
  direction?: string;
  status_filter?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.direction) qs.set("direction", params.direction);
  if (params?.status_filter) qs.set("status_filter", params.status_filter);
  const q = qs.toString() ? `?${qs}` : "";
  return adminFetch<{ leads: AdminReferralLead[] }>(`/api/v1/admin/referrals/leads${q}`);
}

export async function rejectReferralLead(id: string, reason: string) {
  return adminFetch<AdminReferralLead>(`/api/v1/admin/referrals/leads/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function grantReferralLead(id: string, note?: string) {
  return adminFetch<AdminReferralLead>(`/api/v1/admin/referrals/leads/${id}/grant`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}
