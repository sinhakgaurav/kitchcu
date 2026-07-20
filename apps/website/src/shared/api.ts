/** Kitchen owner portal — isolated localStorage keys (kitchen.kitchcu.in only) */

import { APP_STORAGE_PREFIX } from "./brand";
import { apiHeaders, correlationHeaders } from "./http";

const TOKEN_KEY = `${APP_STORAGE_PREFIX}_kitchen_token`;
const KITCHEN_KEY = `${APP_STORAGE_PREFIX}_kitchen_active_id`;

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(KITCHEN_KEY);
}

export function getStoredKitchenId(): string | null {
  return localStorage.getItem(KITCHEN_KEY);
}

export function setStoredKitchenId(id: string): void {
  localStorage.setItem(KITCHEN_KEY, id);
}

export type OwnerProfile = {
  id: string;
  phone: string;
  name: string;
  email: string | null;
  subscription_tier: string;
  subscription_status: string;
};

export type KitchenBrandedPage = {
  enabled: boolean;
  tagline: string | null;
  accent_color: string | null;
  logo_url?: string | null;
  background_url?: string | null;
};

export type Kitchen = {
  id: string;
  owner_id: string;
  code: string;
  name: string;
  address_line: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  status: string;
  free_delivery_radius_km: number;
  max_delivery_radius_km: number;
  delivery_fee_per_km?: number;
  delivery_fee_flat_beyond?: number;
  min_order_for_free_delivery?: number | null;
  delivery_subsidy_percent?: number;
  porter_auto_book_enabled?: boolean;
  porter_auto_book_delay_min?: number;
  latitude: number;
  longitude: number;
  branded_page?: KitchenBrandedPage;
};

export type KitchenPublic = {
  id: string;
  code: string;
  name: string;
  city: string | null;
  state: string | null;
  status: string;
  description?: string | null;
  branded_page?: KitchenBrandedPage;
};

export type KitchenNearby = KitchenPublic & {
  distance_km: number;
  latitude: number;
  longitude: number;
  has_veg: boolean;
  has_non_veg: boolean;
  has_live_capture: boolean;
  is_live_now: boolean;
};

export type KitchenNearbyList = {
  kitchens: KitchenNearby[];
  total: number;
  customer_latitude: number;
  customer_longitude: number;
  sort: string;
};

export type Category = {
  id: string;
  kitchen_id: string;
  name: string;
  slug: string;
  sort_order: number;
};

export type Cuisine = {
  id: string;
  kitchen_id: string;
  name: string;
  slug: string;
  sort_order: number;
};

export type DishMedia = {
  id: string;
  url: string;
  is_hero: boolean;
  is_live_capture: boolean;
  captured_at: string | null;
};

export type Dish = {
  id: string;
  kitchen_id: string;
  cuisine_id: string | null;
  category_id: string | null;
  cuisine_name: string | null;
  cuisine_slug: string | null;
  category_name: string | null;
  category_slug: string | null;
  name: string;
  price: number;
  prep_time_min: number;
  delivery_time_min?: number | null;
  max_time_min: number;
  /** Customer-facing ready-within minutes (owner max_time). */
  projected_ready_min: number;
  description: string | null;
  ingredients_description: string | null;
  quality_measures: string | null;
  is_active: boolean;
  is_featured?: boolean;
  is_chefs_special?: boolean;
  is_unique_recipe?: boolean;
  created_at?: string | null;
  media: DishMedia[];
};

export type MenuHighlightSections = {
  featured: Dish[];
  chefs_special: Dish[];
  unique_recipe: Dish[];
};

export type DietMenuGroup = {
  diet: Category;
  dishes: Dish[];
};

export type CuisineMenuGroup = {
  cuisine: Cuisine;
  diets: DietMenuGroup[];
};

export type Menu = {
  kitchen_id: string;
  dishes: Dish[];
  grouped: CuisineMenuGroup[];
  cuisines: Cuisine[];
  diet_categories: Category[];
  highlight_sections?: MenuHighlightSections;
};

export type OrderItem = {
  id: string;
  dish_id: string;
  dish_name: string;
  quantity: number;
  unit_price: number;
  special_instructions: string | null;
  prep_time_min: number;
};

export type Order = {
  id: string;
  kitchen_id: string;
  master_order_id: string | null;
  bill_id: string;
  order_code: string;
  coupon_code?: string | null;
  discount_amount?: number;
  status: string;
  source: string;
  delivery_type: string;
  payment_method: string;
  customer_name: string | null;
  customer_phone: string | null;
  subtotal: number;
  delivery_fee: number;
  distance_km?: number | null;
  delivery_fee_accepted?: boolean | null;
  delivery_mode?: string | null;
  delivery_payer?: string | null;
  owner_delivery_cost?: number;
  courier_partner?: string | null;
  courier_job_id?: string | null;
  courier_status?: string | null;
  delivery_fee_payment?: string | null;
  customer_latitude?: number | null;
  customer_longitude?: number | null;
  tracking_token?: string | null;
  total: number;
  estimated_prep_min: number | null;
  estimated_ready_at: string | null;
  cancel_reason: string | null;
  created_at: string;
  items: OrderItem[];
  status_events: { id: string; from_status: string | null; to_status: string; note: string | null; created_at: string }[];
};

export type MasterOrder = {
  id: string;
  master_order_code: string;
  status: string;
  payment_method: string;
  currency: string;
  subtotal: number;
  delivery_fee: number;
  total: number;
  created_at: string;
  orders: Order[];
};

export type Settlement = {
  id: string;
  master_order_id: string;
  payment_id: string;
  kitchen_id: string;
  order_id: string;
  gross_amount: number;
  delivery_fee_amount: number;
  platform_fee: number;
  net_to_owner: number;
  razorpay_transfer_id: string | null;
  settlement_status: string;
  settled_at: string | null;
};

export type MasterPaymentCapture = {
  payment: Payment;
  settlements: Settlement[];
};

export type OrderDraft = {
  id: string;
  kitchen_id: string;
  status: string;
  source: string;
  raw_message: string;
  customer_phone: string | null;
  parsed_items: {
    raw: string;
    dish_id: string | null;
    dish_name: string | null;
    quantity: number;
    matched: boolean;
    unit_price: number | null;
  }[];
  unmatched_lines: string[];
  special_notes: string[];
  order_id: string | null;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type RevenueSummary = {
  window_days: number;
  total_orders: number;
  completed_orders: number;
  delivered_orders: number;
  cancelled_orders: number;
  active_orders: number;
  gross_revenue: number;
  avg_order_value: number;
  cancellation_rate: number;
  unique_customers: number;
  repeat_customers: number;
  repeat_rate: number;
};

export type RevenuePoint = { date: string; revenue: number; orders: number };
export type RevenueTimeseries = { window_days: number; points: RevenuePoint[] };

export type TopDish = {
  dish_id: string;
  dish_name: string;
  quantity: number;
  revenue: number;
  order_count: number;
};
export type TopDishes = { window_days: number; dishes: TopDish[] };

export type PeakHour = { hour: number; orders: number; revenue: number };
export type PeakHours = { window_days: number; hours: PeakHour[] };

export type CustomerRow = {
  customer_phone: string;
  customer_name: string | null;
  orders: number;
  total_spent: number;
  last_order_at: string;
};

export type CustomerSegments = {
  window_days: number;
  new_customers: number;
  repeat_customers: number;
  vip_customers: number;
  top_customers: CustomerRow[];
  churn_risk: CustomerRow[];
};

export type Payment = {
  id: string;
  order_id: string | null;
  master_order_id?: string | null;
  kitchen_id: string | null;
  amount: number;
  currency: string;
  method: string;
  status: string;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  created_at: string;
};

export type UpiIntent = {
  payment_id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: string;
  upi_uri: string;
};

export type SubscriptionPlan = {
  tier: string;
  monthly_amount: number;
  yearly_amount: number;
};

export type OwnerSubscription = {
  id: string;
  owner_id: string;
  plan_tier: string;
  billing_cycle: string;
  amount: number;
  status: string;
  razorpay_subscription_id: string | null;
  current_period_end: string | null;
  created_at: string;
};

export function normalizePhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 10) return `+91${digits}`;
  if (phone.trim().startsWith("+")) return phone.trim();
  return `+${digits}`;
}

/** Authenticated owner API fetch — used by feature modules (referrals, etc.). */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = apiHeaders({
    ...(init?.headers as Record<string, string> | undefined),
  });
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    if (
      res.status === 401 &&
      (detail === "Invalid token" || detail === "Not authenticated" || detail === "Invalid token type")
    ) {
      clearToken();
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?session=expired&next=${next}`;
      throw new Error("Session expired — please sign in again");
    }
    throw new Error(detail);
  }
  return body as T;
}

export async function registerOwner(data: {
  phone: string;
  name: string;
  email?: string;
}): Promise<OwnerProfile> {
  return apiFetch("/api/v1/owners/register", {
    method: "POST",
    body: JSON.stringify({ ...data, phone: normalizePhone(data.phone) }),
  });
}

export async function requestOtp(phone: string): Promise<void> {
  await apiFetch("/api/v1/auth/otp/request", {
    method: "POST",
    body: JSON.stringify({ phone: normalizePhone(phone) }),
  });
}

export async function verifyOtp(phone: string, otp: string): Promise<TokenResponse> {
  return apiFetch("/api/v1/auth/otp/verify", {
    method: "POST",
    body: JSON.stringify({ phone: normalizePhone(phone), otp }),
  });
}

export async function fetchOwnerProfile(): Promise<OwnerProfile> {
  return apiFetch("/api/v1/owners/me");
}

export async function fetchKitchens(): Promise<Kitchen[]> {
  return apiFetch("/api/v1/kitchens/me");
}

export async function updateKitchenBrandedPage(
  kitchenId: string,
  data: {
    enabled?: boolean;
    tagline?: string | null;
    accent_color?: string | null;
    logo_url?: string | null;
    background_url?: string | null;
  },
): Promise<Kitchen> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/branded-page`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** Multipart logo / background upload — persists branded_page in one step. */
export async function uploadKitchenBrandedMedia(
  kitchenId: string,
  file: Blob,
  slot: "logo" | "background",
  filename = "brand.jpg",
): Promise<Kitchen> {
  const form = new FormData();
  form.append("file", file, filename);
  form.append("slot", slot);

  const token = getToken();
  const headers = correlationHeaders(token ? { Authorization: `Bearer ${token}` } : undefined);

  const res = await fetch(`/api/v1/kitchens/${kitchenId}/branded-page/upload`, {
    method: "POST",
    headers,
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Brand image upload failed";
    throw new Error(detail);
  }
  return body as Kitchen;
}

export async function updateKitchenDeliverySettings(
  kitchenId: string,
  data: {
    free_delivery_radius_km?: number;
    max_delivery_radius_km?: number;
    delivery_fee_per_km?: number;
    delivery_fee_flat_beyond?: number;
    min_order_for_free_delivery?: number | null;
    delivery_subsidy_percent?: number;
    porter_auto_book_enabled?: boolean;
    porter_auto_book_delay_min?: number;
  },
): Promise<Kitchen> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/delivery-settings`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchKitchenByCode(code: string): Promise<KitchenPublic> {
  // Public lookup — never attach owner JWT or redirect to owner login
  const res = await fetch(
    `/api/v1/kitchens/public/by-code/${encodeURIComponent(code.trim().toUpperCase())}`,
    { headers: apiHeaders({ Accept: "application/json" }) },
  );
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Kitchen not found";
    throw new Error(detail);
  }
  return body as KitchenPublic;
}

export async function fetchNearbyKitchens(params: {
  latitude: number;
  longitude: number;
  limit?: number;
  max_km?: number;
  sort?: "asc" | "desc";
  diet?: "veg" | "non_veg" | "vegan";
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
  return apiFetch(`/api/v1/kitchens/public/nearby?${q.toString()}`);
}

export async function createKitchen(data: {
  name: string;
  address_line: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  description?: string;
  pincode?: string;
}): Promise<Kitchen> {
  return apiFetch("/api/v1/kitchens", { method: "POST", body: JSON.stringify(data) });
}

export async function fetchCategories(kitchenId: string): Promise<Category[]> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/categories`);
}

export async function fetchCuisines(kitchenId: string): Promise<Cuisine[]> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/cuisines`);
}

export async function fetchMenu(
  kitchenId: string,
  opts?: { highlight?: string; diet?: string; q?: string; sort?: string },
): Promise<Menu> {
  const q = new URLSearchParams();
  if (opts?.highlight) q.set("highlight", opts.highlight);
  if (opts?.diet) q.set("diet", opts.diet);
  if (opts?.q) q.set("q", opts.q);
  if (opts?.sort) q.set("sort", opts.sort);
  const qs = q.toString();
  return apiFetch(`/api/v1/kitchens/${kitchenId}/menu${qs ? `?${qs}` : ""}`);
}

export async function createDish(
  kitchenId: string,
  data: {
    name: string;
    price: number;
    prep_time_min: number;
    delivery_time_min?: number | null;
    max_time_min?: number;
    cuisine_id: string;
    category_id: string;
    description?: string;
    ingredients_description?: string;
    is_featured?: boolean;
    is_chefs_special?: boolean;
    is_unique_recipe?: boolean;
    media: { url: string; is_hero: boolean; is_live_capture: boolean; captured_at?: string };
  },
): Promise<Dish> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/dishes`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export type BulkDishImportResult = {
  accepted: number;
  rejected: number;
  images_mapped: number;
  images_unused: string[];
  note: string;
  results: {
    row: number;
    name: string | null;
    status: string;
    dish_id: string | null;
    detail: string | null;
  }[];
};

export async function downloadDishBulkTemplate(kitchenId: string): Promise<void> {
  const token = getToken();
  if (!token) throw new Error("Sign in required");
  const res = await fetch(`/api/v1/kitchens/${kitchenId}/dishes/bulk/template.xlsx`, {
    headers: correlationHeaders({ Authorization: `Bearer ${token}` }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Could not download template");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "kitchcu_dishes_bulk_template.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function bulkImportDishes(
  kitchenId: string,
  data: { spreadsheet: File; images?: File[]; imagesZip?: File | null },
): Promise<BulkDishImportResult> {
  const token = getToken();
  if (!token) throw new Error("Sign in required");
  const form = new FormData();
  form.append("spreadsheet", data.spreadsheet);
  for (const img of data.images || []) {
    form.append("images", img);
  }
  if (data.imagesZip) {
    form.append("images_zip", data.imagesZip);
  }
  const res = await fetch(`/api/v1/kitchens/${kitchenId}/dishes/bulk`, {
    method: "POST",
    headers: correlationHeaders({ Authorization: `Bearer ${token}` }),
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Bulk import failed");
  }
  return body as BulkDishImportResult;
}

export async function updateDish(
  kitchenId: string,
  dishId: string,
  data: {
    name?: string;
    price?: number;
    prep_time_min?: number;
    delivery_time_min?: number | null;
    max_time_min?: number;
    is_active?: boolean;
    is_featured?: boolean;
    is_chefs_special?: boolean;
    is_unique_recipe?: boolean;
    description?: string | null;
    ingredients_description?: string | null;
    quality_measures?: string | null;
    media?: {
      url: string;
      is_hero: boolean;
      is_live_capture: boolean;
      captured_at?: string;
    };
  },
): Promise<Dish> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/dishes/${dishId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchOrders(kitchenId: string, status?: string): Promise<{ orders: Order[]; total: number }> {
  const q = status ? `?status=${status}` : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/orders${q}`);
}

export async function fetchOrder(orderId: string): Promise<Order> {
  return apiFetch(`/api/v1/orders/${orderId}`);
}

export async function fetchDrafts(kitchenId: string): Promise<{ drafts: OrderDraft[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/orders/drafts`);
}

export async function confirmDraft(kitchenId: string, draftId: string): Promise<Order> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/orders/drafts/${draftId}/confirm`, { method: "POST" });
}

export async function parseMessage(kitchenId: string, message_text: string): Promise<OrderDraft> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/orders/parse-message`, {
    method: "POST",
    body: JSON.stringify({ message_text }),
  });
}

export async function createManualOrder(
  kitchenId: string,
  data: {
    items: { dish_id: string; quantity: number; special_instructions?: string }[];
    delivery_type: "pickup" | "delivery";
    payment_method: "cod" | "online" | "upi";
    customer_name?: string;
    customer_phone?: string;
    delivery_fee?: number;
  },
): Promise<Order> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/orders/manual`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateOrderStatus(
  orderId: string,
  data: { status: string; note?: string; cancel_reason?: string },
): Promise<Order> {
  return apiFetch(`/api/v1/orders/${orderId}/status`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchRevenueSummary(kitchenId: string, days = 30): Promise<RevenueSummary> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/analytics/summary?days=${days}`);
}

export async function fetchRevenueTimeseries(
  kitchenId: string,
  days = 30,
): Promise<RevenueTimeseries> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/analytics/revenue-timeseries?days=${days}`);
}

export async function fetchTopDishes(kitchenId: string, days = 30, limit = 10): Promise<TopDishes> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/analytics/top-dishes?days=${days}&limit=${limit}`);
}

export async function fetchPeakHours(kitchenId: string, days = 30): Promise<PeakHours> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/analytics/peak-hours?days=${days}`);
}

export async function fetchCustomerSegments(
  kitchenId: string,
  days = 90,
  limit = 10,
): Promise<CustomerSegments> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/analytics/customers?days=${days}&limit=${limit}`);
}

export async function fetchSubscriptionPlans(): Promise<{ plans: SubscriptionPlan[] }> {
  return apiFetch("/api/v1/billing/subscriptions/plans");
}

export async function fetchMySubscription(): Promise<OwnerSubscription> {
  return apiFetch("/api/v1/billing/subscriptions/me");
}

export async function createSubscription(data: {
  plan_tier: "starter" | "growth" | "pro";
  billing_cycle: "monthly" | "yearly";
}): Promise<OwnerSubscription> {
  return apiFetch("/api/v1/billing/subscriptions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function activateSubscription(subscriptionId: string): Promise<OwnerSubscription> {
  return apiFetch(`/api/v1/billing/subscriptions/${subscriptionId}/activate`, { method: "POST" });
}

export type KitchenPaymentGateway = {
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

export async function fetchKitchenPaymentGateway(kitchenId: string): Promise<KitchenPaymentGateway> {
  return apiFetch(`/api/v1/billing/kitchens/${kitchenId}/payment-gateway`);
}

export async function upsertKitchenPaymentGateway(
  kitchenId: string,
  data: {
    key_id?: string | null;
    key_secret?: string | null;
    webhook_secret?: string | null;
    linked_account_id?: string | null;
    is_active?: boolean;
    clear_key_secret?: boolean;
    clear_webhook_secret?: boolean;
  },
): Promise<KitchenPaymentGateway> {
  return apiFetch(`/api/v1/billing/kitchens/${kitchenId}/payment-gateway`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function clearKitchenPaymentGateway(
  kitchenId: string,
): Promise<KitchenPaymentGateway> {
  return apiFetch(`/api/v1/billing/kitchens/${kitchenId}/payment-gateway`, {
    method: "DELETE",
  });
}

export type MessagingWallet = {
  kitchen_id: string;
  balance_inr: number;
  low_balance: boolean;
  low_balance_threshold_inr: number;
  updated_at: string | null;
};

export async function fetchMessagingWallet(kitchenId: string): Promise<MessagingWallet> {
  return apiFetch(`/api/v1/billing/kitchens/${kitchenId}/messaging-wallet`);
}

export type KitchenWhatsAppIntegration = {
  kitchen_id: string;
  whatsapp_phone_id: string | null;
  whatsapp_display_phone: string | null;
  connected: boolean;
  platform_secrets_note: string;
};

export async function fetchKitchenWhatsAppIntegration(
  kitchenId: string,
): Promise<KitchenWhatsAppIntegration> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/whatsapp-integration`);
}

export async function upsertKitchenWhatsAppIntegration(
  kitchenId: string,
  data: {
    whatsapp_phone_id?: string | null;
    whatsapp_display_phone?: string | null;
    clear?: boolean;
  },
): Promise<KitchenWhatsAppIntegration> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/whatsapp-integration`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function createPayment(data: {
  order_id: string;
  method: "online" | "upi";
}): Promise<Payment> {
  return apiFetch("/api/v1/billing/payments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createUpiIntent(orderId: string): Promise<UpiIntent> {
  return apiFetch("/api/v1/billing/payments/upi-intent", {
    method: "POST",
    body: JSON.stringify({ order_id: orderId }),
  });
}

export async function capturePayment(paymentId: string): Promise<Payment> {
  return apiFetch(`/api/v1/billing/payments/${paymentId}/capture`, { method: "POST" });
}

export async function fetchPayment(paymentId: string): Promise<Payment> {
  return apiFetch(`/api/v1/billing/payments/${paymentId}`);
}

export type Refund = {
  id: string;
  payment_id: string;
  order_id: string;
  kitchen_id: string;
  kind: "full" | "partial" | string;
  channel: "gateway" | "direct_transfer" | string;
  amount: number;
  currency: string;
  status: string;
  destination_type: string;
  destination_upi: string | null;
  destination_bank_account_masked: string | null;
  destination_bank_ifsc: string | null;
  destination_account_name: string | null;
  transfer_remark: string;
  razorpay_refund_id: string | null;
  evidence_url: string | null;
  reason: string | null;
  created_at: string;
  completed_at: string | null;
};

export async function createRefund(data: {
  order_id: string;
  kind: "full" | "partial";
  channel?: "gateway" | "direct_transfer";
  amount?: number;
  destination_type?: "upi" | "bank";
  destination_upi?: string;
  destination_bank_account?: string;
  destination_bank_ifsc?: string;
  destination_account_name?: string;
  reason?: string;
}): Promise<Refund> {
  return apiFetch("/api/v1/billing/refunds", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchRefunds(orderId?: string): Promise<Refund[]> {
  const qs = orderId ? `?order_id=${encodeURIComponent(orderId)}` : "";
  return apiFetch(`/api/v1/billing/refunds${qs}`);
}

export async function processGatewayRefund(refundId: string): Promise<Refund> {
  return apiFetch(`/api/v1/billing/refunds/${refundId}/process`, { method: "POST" });
}

export async function completeDirectRefund(refundId: string): Promise<Refund> {
  return apiFetch(`/api/v1/billing/refunds/${refundId}/complete`, { method: "POST" });
}

export async function uploadRefundEvidence(refundId: string, file: File): Promise<Refund> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const headers = correlationHeaders(token ? { Authorization: `Bearer ${token}` } : undefined);
  const res = await fetch(`/api/v1/billing/refunds/${refundId}/evidence`, {
    method: "POST",
    headers,
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Upload failed");
  }
  return body as Refund;
}

export type CrmFavoriteDish = {
  dish_id: string;
  dish_name: string;
  quantity: number;
};

export type CrmCustomer = {
  id: string;
  kitchen_id: string;
  customer_id: string | null;
  customer_phone: string;
  customer_name: string | null;
  total_spend: number;
  monthly_spend: number;
  order_count: number;
  favorite_dishes: CrmFavoriteDish[];
  order_patterns: { peak_hours: number[]; weekday_orders: number; weekend_orders: number };
  tags: string[];
  last_order_at: string | null;
};

export type CrmCustomerList = {
  customers: CrmCustomer[];
  total: number;
  synced_at: string | null;
};

export type Coupon = {
  id: string;
  kitchen_id: string;
  code: string;
  discount_type: "percent" | "fixed";
  discount_value: number;
  min_order_amount: number | null;
  max_uses: number | null;
  used_count: number;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  created_at: string;
};

export type Promotion = {
  id: string;
  kitchen_id: string;
  name: string;
  dish_id: string;
  dish_name: string;
  special_price: number;
  segment: string;
  segment_limit: number | null;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
  created_at: string;
};

export async function fetchCrmCustomers(
  kitchenId: string,
  refresh = true,
): Promise<CrmCustomerList> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/crm/customers?refresh=${refresh ? "true" : "false"}`);
}

export async function updateCrmCustomerTags(
  kitchenId: string,
  customerId: string,
  tags: string[],
): Promise<CrmCustomer> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/crm/customers/${customerId}`, {
    method: "PATCH",
    body: JSON.stringify({ tags }),
  });
}

export async function fetchCoupons(kitchenId: string): Promise<{ coupons: Coupon[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/coupons`);
}

export async function createCoupon(
  kitchenId: string,
  data: {
    code: string;
    discount_type: "percent" | "fixed";
    discount_value: number;
    min_order_amount?: number;
    max_uses?: number;
  },
): Promise<Coupon> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/coupons`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deactivateCoupon(kitchenId: string, couponId: string): Promise<Coupon> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/coupons/${couponId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: false }),
  });
}

/** Kitchen tiffin / meal-plan (marketing) — distinct from SaaS `SubscriptionPlan`. */
export type KitchenMealPlan = {
  id: string;
  kitchen_id: string;
  name: string;
  description: string | null;
  plan_type: string;
  dishes_config: {
    dish_ids?: string[];
    weekdays?: number[];
    meals_per_day?: number;
    notes?: string | null;
    image_url?: string | null;
  };
  price_monthly: number;
  billing_cycle: string;
  delivery_included: boolean;
  max_subscribers: number | null;
  is_active: boolean;
  active_subscriber_count: number;
  pending_count: number;
  created_at: string;
};

/** @deprecated Use KitchenMealPlan — kept for older imports during rename. */
export type TiffinSubscriptionPlan = KitchenMealPlan;

export type CustomerKitchenSubscription = {
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

export type SubscriptionSummary = {
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

/** Kitchen tiffin / meal-plan catalog (marketing service) — not SaaS billing plans. */
export async function fetchKitchenSubscriptionPlans(
  kitchenId: string,
  activeOnly = false,
): Promise<{ plans: KitchenMealPlan[]; total: number }> {
  const q = activeOnly ? "?active_only=true" : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscription-plans${q}`);
}

export async function fetchPublicSubscriptionPlans(
  kitchenId: string,
): Promise<{ plans: KitchenMealPlan[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscription-plans/public`);
}

export async function createSubscriptionPlan(
  kitchenId: string,
  data: {
    name: string;
    description?: string;
    plan_type: string;
    price_monthly: number;
    dishes_config?: KitchenMealPlan["dishes_config"];
    delivery_included?: boolean;
    max_subscribers?: number | null;
  },
): Promise<KitchenMealPlan> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscription-plans`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSubscriptionPlan(
  kitchenId: string,
  planId: string,
  data: Partial<{
    name: string;
    description: string | null;
    plan_type: string;
    price_monthly: number;
    dishes_config: KitchenMealPlan["dishes_config"];
    delivery_included: boolean;
    max_subscribers: number | null;
    is_active: boolean;
  }>,
): Promise<KitchenMealPlan> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscription-plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchKitchenSubscriptions(
  kitchenId: string,
  status?: string,
): Promise<{ subscriptions: CustomerKitchenSubscription[]; total: number }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscriptions${q}`);
}

export async function fetchSubscriptionSummary(kitchenId: string): Promise<SubscriptionSummary> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscriptions/summary`);
}

export async function decideKitchenSubscription(
  kitchenId: string,
  subId: string,
  action: "accept" | "deny" | "activate" | "deactivate",
  data: { owner_note?: string; starts_on?: string } = {},
): Promise<CustomerKitchenSubscription> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscriptions/${subId}/${action}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function requestKitchenSubscription(
  kitchenId: string,
  planId: string,
  data: { customer_name?: string; note?: string } = {},
): Promise<CustomerKitchenSubscription> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/subscription-plans/${planId}/subscribe`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchMySubscriptions(): Promise<{
  subscriptions: CustomerKitchenSubscription[];
  total: number;
}> {
  return apiFetch("/api/v1/customers/me/subscriptions");
}

export async function cancelMySubscription(subId: string): Promise<CustomerKitchenSubscription> {
  return apiFetch(`/api/v1/customers/me/subscriptions/${subId}/cancel`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function fetchPromotions(
  kitchenId: string,
): Promise<{ promotions: Promotion[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/promotions`);
}

export async function createPromotion(
  kitchenId: string,
  data: {
    name: string;
    dish_id: string;
    special_price: number;
    segment: "all" | "top_spenders" | "repeat" | "vip" | "churn_risk";
    segment_limit?: number;
    starts_at: string;
    ends_at: string;
  },
): Promise<Promotion> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/promotions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePromotion(
  kitchenId: string,
  promotionId: string,
  data: { is_active: boolean },
): Promise<Promotion> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/promotions/${promotionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export interface GrowthSuggestion {
  id: string;
  kitchen_id: string;
  suggestion_type: string;
  title: string;
  description: string;
  action_payload: Record<string, unknown>;
  priority: number;
  dismissed: boolean;
  created_at: string;
}

export interface DishCombo {
  dish_a_id: string;
  dish_a_name: string;
  dish_b_id: string;
  dish_b_name: string;
  pair_count: number;
  support_pct: number;
}

export interface OrderPatternInsight {
  window_days: number;
  days: { day_of_week: number; day_name: string; orders: number; revenue: number }[];
  peak_hours: { hour: number; orders: number }[];
  insight: string;
}

export async function fetchGrowthSuggestions(
  kitchenId: string,
): Promise<{ suggestions: GrowthSuggestion[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/suggestions`);
}

export async function generateGrowthSuggestions(
  kitchenId: string,
  days = 90,
): Promise<{ suggestions: GrowthSuggestion[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/suggestions/generate?days=${days}`, {
    method: "POST",
  });
}

export async function dismissGrowthSuggestion(
  kitchenId: string,
  suggestionId: string,
): Promise<GrowthSuggestion> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/suggestions/${suggestionId}`, {
    method: "PATCH",
    body: JSON.stringify({ dismissed: true }),
  });
}

export interface GoldenRecipePin {
  id: string;
  kitchen_id: string;
  dish_id: string;
  suggestion_id: string | null;
  performance_date: string;
  dish_name: string;
  recipe_snapshot: {
    dish_id?: string;
    dish_name?: string;
    lines?: {
      ingredient_id: string;
      ingredient_name: string;
      quantity: number;
      unit: string;
    }[];
    prep_steps?: { step_order: number; title?: string; body_html?: string }[];
  };
  metrics: Record<string, unknown>;
  created_at: string;
}

export async function saveGoldenRecipe(
  kitchenId: string,
  suggestionId: string,
): Promise<GoldenRecipePin> {
  return apiFetch(
    `/api/v1/kitchens/${kitchenId}/growth/suggestions/${suggestionId}/save-golden-recipe`,
    { method: "POST" },
  );
}

export async function fetchGoldenRecipes(
  kitchenId: string,
  dishId?: string,
): Promise<{ pins: GoldenRecipePin[]; total: number }> {
  const q = dishId ? `?dish_id=${encodeURIComponent(dishId)}` : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/golden-recipes${q}`);
}

export async function fetchDishCombos(
  kitchenId: string,
  days = 90,
): Promise<{ window_days: number; multi_item_orders: number; combos: DishCombo[] }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/combos?days=${days}`);
}

export async function fetchOrderPatterns(kitchenId: string, days = 90): Promise<OrderPatternInsight> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/patterns?days=${days}`);
}

export type MarketingTemplate = {
  id: string;
  kitchen_id: string;
  channel: string;
  name: string;
  subject: string | null;
  body: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
};

export async function fetchMarketingTemplates(
  kitchenId: string,
  channel?: string,
): Promise<MarketingTemplate[]> {
  const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/templates${q}`);
}

export async function createMarketingTemplate(
  kitchenId: string,
  data: {
    channel: string;
    name: string;
    subject?: string | null;
    body: string;
    is_active?: boolean;
  },
): Promise<MarketingTemplate> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/templates`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateMarketingTemplate(
  kitchenId: string,
  templateId: string,
  data: { name?: string; subject?: string | null; body?: string; is_active?: boolean },
): Promise<MarketingTemplate> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/templates/${templateId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteMarketingTemplate(
  kitchenId: string,
  templateId: string,
): Promise<void> {
  await apiFetch(`/api/v1/kitchens/${kitchenId}/templates/${templateId}`, {
    method: "DELETE",
  });
}

export async function sendMarketingTemplate(
  kitchenId: string,
  templateId: string,
  data: {
    audience?: string;
    phones?: string[];
    dry_run?: boolean;
    sample_vars?: Record<string, string>;
  },
): Promise<{
  template_id: string;
  channel: string;
  queued: number;
  dry_run: boolean;
  preview: string;
  recipient_phones: string[];
}> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/templates/${templateId}/send`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export type KitchenEntitlements = {
  kitchen_id: string;
  package_code: string | null;
  package_name: string | null;
  source: string;
  hard_mode: boolean;
  feature_keys: string[];
  modules: Record<string, boolean>;
};

export async function fetchKitchenEntitlements(kitchenId: string): Promise<KitchenEntitlements> {
  return apiFetch(`/api/v1/billing/kitchens/${kitchenId}/entitlements`);
}

export async function pushDailyMenu(
  kitchenId: string,
  data: { dish_ids: string[]; message?: string },
): Promise<{
  kitchen_id: string;
  dish_ids: string[];
  dish_names: string[];
  recipient_count: number;
  message: string;
  status: string;
}> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/growth/daily-menu/push`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export type DeliveryModeOption = {
  mode: string;
  payer: string;
  customer_fee: number;
  owner_fee: number;
  label: string;
  description: string;
  partner?: string | null;
};

export type DeliveryQuote = {
  kitchen_id: string;
  distance_km: number;
  fee: number;
  status: string;
  in_range?: boolean;
  within_free_radius: boolean;
  free_delivery_radius_km: number;
  max_delivery_radius_km: number;
  modes?: DeliveryModeOption[];
  platform_fee?: number;
  kitchen_self_fee?: number;
  breakdown: Record<string, unknown>;
  quote_id: string | null;
};

export async function fetchDeliveryQuote(data: {
  kitchen_id: string;
  latitude: number;
  longitude: number;
  subtotal?: number;
}): Promise<DeliveryQuote> {
  return apiFetch("/api/v1/delivery/quote", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** F28: customer denies the quoted delivery fee — alerts the owner instead of a silent lost sale. */
export async function denyDeliveryFee(
  quoteId: string,
  data: { subtotal?: number; customer_phone?: string },
): Promise<{ acknowledged: boolean; kitchen_id: string }> {
  return apiFetch(`/api/v1/delivery/quote/${quoteId}/deny`, {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId, ...data }),
  });
}

export type TrackingInfo = {
  tracking_token: string;
  order_id: string;
  order_code: string;
  kitchen_id: string;
  kitchen_name: string | null;
  status: string;
  delivery_type: string;
  delivery_mode?: string | null;
  delivery_payer?: string | null;
  distance_km: number | null;
  delivery_fee: number;
  owner_delivery_cost?: number;
  courier_partner?: string | null;
  courier_job_id?: string | null;
  courier_status?: string | null;
  estimated_prep_min?: number | null;
  estimated_delivery_min?: number | null;
  estimated_ready_at: string | null;
  estimated_delivery_at?: string | null;
  tracking_notify_interval_min: number;
  updated_at: string | null;
  kitchen_latitude?: number | null;
  kitchen_longitude?: number | null;
  customer_latitude?: number | null;
  customer_longitude?: number | null;
  map_directions_url?: string | null;
};

export async function fetchTracking(token: string): Promise<TrackingInfo> {
  return apiFetch(`/api/v1/delivery/track/${encodeURIComponent(token)}`);
}

export async function setOrderDeliveryFulfillment(
  orderId: string,
  data: { mode: "self" | "platform"; customer_fee?: number },
): Promise<Order> {
  return apiFetch(`/api/v1/orders/${orderId}/delivery-fulfillment`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export type Ingredient = {
  id: string;
  kitchen_id: string;
  name: string;
  unit: string;
  current_stock: number;
  low_stock_threshold: number;
  photo_url?: string | null;
  is_low: boolean;
};

export type RecipeLine = {
  ingredient_id: string;
  ingredient_name: string;
  quantity: number;
  unit: string;
  photo_url?: string | null;
  sort_order?: number;
};

export type PrepStep = {
  id?: string;
  step_order: number;
  title?: string | null;
  body_html: string;
  photo_url?: string | null;
  duration_min?: number | null;
};

export type DishRecipe = {
  dish_id: string;
  dish_name: string;
  lines: RecipeLine[];
  prep_steps: PrepStep[];
};

export type StockWarning = {
  ingredient_id: string;
  ingredient_name: string;
  unit: string;
  required: number;
  available: number;
  shortfall: number;
  is_low: boolean;
};

export type OrderStockWarnings = {
  order_id: string;
  warnings: StockWarning[];
  has_shortfall: boolean;
};

export type MediaUploadContext =
  | "dish"
  | "ingredient"
  | "prep_step"
  | "general"
  | "brand_logo"
  | "brand_background";

export type MediaUploadResult = {
  url: string;
  object_key: string;
  content_type: string;
  is_live_capture: boolean;
  captured_at: string | null;
};

export async function uploadKitchenMedia(
  kitchenId: string,
  file: Blob,
  options: {
    context: MediaUploadContext;
    is_live_capture?: boolean;
    captured_at?: string;
    filename?: string;
  },
): Promise<MediaUploadResult> {
  const form = new FormData();
  form.append("file", file, options.filename ?? "photo.jpg");
  form.append("is_live_capture", String(options.is_live_capture ?? false));
  form.append("context", options.context);
  if (options.captured_at) form.append("captured_at", options.captured_at);

  const token = getToken();
  const headers = correlationHeaders(token ? { Authorization: `Bearer ${token}` } : undefined);

  const res = await fetch(`/api/v1/kitchens/${kitchenId}/media/upload`, {
    method: "POST",
    headers,
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Upload failed";
    throw new Error(detail);
  }
  return body as MediaUploadResult;
}

export async function fetchIngredients(
  kitchenId: string,
): Promise<{ ingredients: Ingredient[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/ingredients`);
}

export async function createIngredient(
  kitchenId: string,
  data: {
    name: string;
    unit: string;
    current_stock?: number;
    low_stock_threshold?: number;
    photo_url?: string;
  },
): Promise<Ingredient> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/ingredients`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adjustIngredientStock(
  kitchenId: string,
  ingredientId: string,
  data: { delta: number; reason?: string },
): Promise<Ingredient> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/ingredients/${ingredientId}/adjust-stock`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchDishRecipe(kitchenId: string, dishId: string): Promise<DishRecipe> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/dishes/${dishId}/recipe`);
}

export async function saveDishRecipe(
  kitchenId: string,
  dishId: string,
  data: {
    lines: {
      ingredient_id: string;
      quantity: number;
      unit: string;
      photo_url?: string;
      sort_order?: number;
    }[];
    prep_steps?: {
      step_order: number;
      title?: string;
      body_html: string;
      photo_url?: string;
      duration_min?: number;
    }[];
  },
): Promise<DishRecipe> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/dishes/${dishId}/recipe`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function fetchOrderStockWarnings(orderId: string): Promise<OrderStockWarnings> {
  return apiFetch(`/api/v1/orders/${orderId}/stock-warnings`);
}

export type StockDeductMode = "order_ready" | "prep_batch_only";

export type KitchenStockSettings = {
  kitchen_id: string;
  deduct_mode: StockDeductMode;
  updated_at?: string | null;
};

export type PrepBatchIngredientLine = {
  ingredient_id: string;
  ingredient_name?: string | null;
  quantity: number;
  unit: string;
  sort_order: number;
};

export type PrepBatch = {
  id: string;
  kitchen_id: string;
  name: string;
  batch_type: "single_dish" | "combo" | string;
  portions: number;
  status: string;
  notes?: string | null;
  prepared_at?: string | null;
  created_at: string;
  dishes: { dish_id: string; dish_name?: string | null; quantity_per_portion: number }[];
  ingredient_lines: PrepBatchIngredientLine[];
};

export async function fetchKitchenStockSettings(kitchenId: string): Promise<KitchenStockSettings> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stock-settings`);
}

export async function updateKitchenStockSettings(
  kitchenId: string,
  deduct_mode: StockDeductMode,
): Promise<KitchenStockSettings> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stock-settings`, {
    method: "PATCH",
    body: JSON.stringify({ deduct_mode }),
  });
}

export async function fetchPrepBatches(
  kitchenId: string,
  status?: string,
): Promise<{ batches: PrepBatch[]; total: number }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch(`/api/v1/kitchens/${kitchenId}/prep-batches${q}`);
}

export async function createPrepBatch(
  kitchenId: string,
  data: {
    name: string;
    batch_type: "single_dish" | "combo";
    portions: number;
    dishes: { dish_id: string; quantity_per_portion?: number }[];
    notes?: string;
  },
): Promise<PrepBatch> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/prep-batches`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updatePrepBatch(
  kitchenId: string,
  batchId: string,
  data: {
    name?: string;
    notes?: string;
    status?: "draft" | "preparing" | "cancelled";
    ingredient_lines?: { ingredient_id: string; quantity: number; unit: string; sort_order?: number }[];
  },
): Promise<PrepBatch> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/prep-batches/${batchId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function markPrepBatchPrepared(kitchenId: string, batchId: string): Promise<PrepBatch> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/prep-batches/${batchId}/mark-prepared`, {
    method: "POST",
  });
}

async function downloadPdf(path: string, filename: string): Promise<void> {
  const token = getToken();
  const res = await fetch(path, {
    headers: correlationHeaders(token ? { Authorization: `Bearer ${token}` } : undefined),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : "Could not download bill";
    throw new Error(detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function downloadOwnerOrderBillPdf(orderId: string, orderCode: string): Promise<void> {
  const safe = orderCode.replace(/[^\w.-]+/g, "_");
  return downloadPdf(`/api/v1/orders/${orderId}/bill.pdf`, `${safe}.pdf`);
}

export type CuratedRecipe = {
  id: string;
  title: string;
  slug: string;
  category: string;
  cuisine: string;
  description: string;
  ingredients: string[];
  prep_steps: string[];
  image_url: string;
  source_name: string;
  source_url: string | null;
};

export type DishTrial = {
  id: string;
  kitchen_id: string;
  curated_recipe_id: string | null;
  catalog_dish_id: string;
  dish_name: string;
  status: string;
  promo_type: string;
  sample_price: number | null;
  rating_threshold: number;
  avg_rating: number | null;
  invite_count: number;
  whatsapp_sent_at: string | null;
  promoted_at: string | null;
  created_at: string;
  invites: {
    id: string;
    customer_id: string;
    customer_name: string | null;
    customer_phone_masked: string;
    status: string;
    home_taste_score: number | null;
    quality_score: number | null;
  }[];
};

export async function fetchCuratedRecipes(category?: string): Promise<{ recipes: CuratedRecipe[]; total: number }> {
  const q = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch(`/api/v1/learning/recipes${q}`);
}

export async function learnRecipe(
  kitchenId: string,
  data: { recipe_id: string; dish_name?: string; price?: number },
): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/learn`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchDishTrials(kitchenId: string): Promise<{ trials: DishTrial[]; total: number }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials`);
}

export async function fetchDishTrial(kitchenId: string, trialId: string): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials/${trialId}`);
}

export async function setTrialInvites(
  kitchenId: string,
  trialId: string,
  data: { customer_ids: string[]; promo_type?: "free" | "paid_sample"; sample_price?: number },
): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials/${trialId}/invites`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function sendTrialSamples(kitchenId: string, trialId: string): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials/${trialId}/send-samples`, {
    method: "POST",
  });
}

export async function recordTrialRating(
  kitchenId: string,
  trialId: string,
  data: { invite_id: string; home_taste_score: number; quality_score: number; feedback?: string },
): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials/${trialId}/ratings`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function promoteTrial(kitchenId: string, trialId: string, force = false): Promise<DishTrial> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/learning/trials/${trialId}/promote?force=${force}`, {
    method: "POST",
  });
}

export type SharedRecipe = {
  id: string;
  kitchen_id: string;
  title: string;
  summary: string | null;
  recipe_html: string;
  cover_url: string | null;
  dish_id: string | null;
  appreciation_count: number;
  points_earned: number;
  kitchen_name: string | null;
  kitchen_code: string | null;
  created_at: string;
};

export type RewardBalance = {
  kitchen_id: string;
  points_balance: number;
  ledger: { id: string; delta: number; reason: string; balance_after: number; created_at: string }[];
};

export type ChefRankingEntry = {
  rank: number;
  kitchen_id: string;
  kitchen_code: string;
  kitchen_name: string;
  score: number;
  metrics: Record<string, number>;
};

export async function fetchSharedRecipes(kitchenId?: string): Promise<{ recipes: SharedRecipe[]; total: number }> {
  const q = kitchenId ? `?kitchen_id=${kitchenId}` : "";
  return apiFetch(`/api/v1/community/recipes${q}`);
}

export async function shareCommunityRecipe(
  kitchenId: string,
  data: {
    title: string;
    recipe_html: string;
    summary?: string;
    cover_url?: string;
    dish_id?: string;
  },
): Promise<SharedRecipe> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/community/recipes`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchRewardBalance(kitchenId: string): Promise<RewardBalance> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/community/rewards`);
}

export async function redeemRewardPoints(
  kitchenId: string,
  redemption_type: "subscription_discount" | "featured_listing",
): Promise<{ redemption_id: string; points_spent: number; points_balance: number; status: string }> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/community/rewards/redeem`, {
    method: "POST",
    body: JSON.stringify({ redemption_type }),
  });
}

export async function fetchChefRankings(
  scope = "city",
  regionKey?: string,
): Promise<{ period: string; scope: string; region_key: string; rankings: ChefRankingEntry[]; total: number }> {
  const params = new URLSearchParams({ scope });
  if (regionKey) params.set("region_key", regionKey);
  return apiFetch(`/api/v1/community/rankings?${params}`);
}

export async function computeChefRankings(
  kitchenId: string,
  scope: "city" | "state" | "national",
  regionKey?: string,
): Promise<{ period: string; scope: string; region_key: string; rankings: ChefRankingEntry[]; total: number }> {
  const params = new URLSearchParams({ scope });
  if (regionKey) params.set("region_key", regionKey);
  return apiFetch(`/api/v1/kitchens/${kitchenId}/community/rankings/compute?${params}`, { method: "POST" });
}

export type StreamSettings = {
  kitchen_id: string;
  live_sharing_enabled: boolean;
  q_and_a_enabled: boolean;
  is_live: boolean;
  livekit_configured: boolean;
};

export type ShowcasePhase = "idle" | "ingredients" | "prep" | "prepared";

export type LiveSession = {
  id: string;
  kitchen_id: string;
  title: string;
  room_name: string;
  status: string;
  order_id: string | null;
  dish_id: string | null;
  dish_name: string | null;
  showcase_phase: ShowcasePhase | string;
  active_prep_step_order: number | null;
  prepared_at: string | null;
  viewer_count: number;
  started_at: string;
  ended_at: string | null;
  livekit_url: string | null;
  publisher_token: string | null;
};

export type LiveShowcase = {
  session_id: string;
  kitchen_id: string;
  title: string;
  status: string;
  dish_id: string | null;
  dish_name: string | null;
  showcase_phase: ShowcasePhase | string;
  active_prep_step_order: number | null;
  prepared_at: string | null;
  ingredients: {
    ingredient_name: string;
    quantity: number;
    unit: string;
    photo_url?: string | null;
    sort_order: number;
  }[];
  prep_steps: {
    step_order: number;
    title?: string | null;
    body_html?: string | null;
    photo_url?: string | null;
    duration_min?: number | null;
  }[];
};

export type LiveKitchenSummary = {
  kitchen_id: string;
  kitchen_code: string;
  kitchen_name: string;
  session_id: string;
  title: string;
  started_at: string;
  dish_id?: string | null;
  dish_name?: string | null;
  showcase_phase?: string;
};

export async function fetchStreamSettings(kitchenId: string): Promise<StreamSettings> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/settings`);
}

export async function updateStreamSettings(
  kitchenId: string,
  data: { live_sharing_enabled?: boolean; q_and_a_enabled?: boolean },
): Promise<StreamSettings> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/settings`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function goKitchenLive(
  kitchenId: string,
  data: {
    title?: string;
    order_id?: string;
    dish_id?: string;
    showcase_phase?: ShowcasePhase | string;
  },
): Promise<LiveSession> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/go-live`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function endKitchenStream(kitchenId: string): Promise<LiveSession> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/end`, { method: "POST" });
}

export async function fetchStreamSession(kitchenId: string): Promise<LiveSession | null> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/session`);
}

export async function updateStreamShowcase(
  kitchenId: string,
  data: {
    dish_id?: string | null;
    showcase_phase?: ShowcasePhase | string;
    active_prep_step_order?: number | null;
    clear_dish?: boolean;
  },
): Promise<LiveSession> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/stream/showcase`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchLiveShowcase(sessionId: string): Promise<LiveShowcase> {
  return apiFetch(`/api/v1/stream/sessions/${sessionId}/showcase`);
}

export async function fetchLiveKitchens(): Promise<{ kitchens: LiveKitchenSummary[]; total: number }> {
  return apiFetch("/api/v1/stream/live-kitchens");
}

export async function fetchViewerToken(sessionId: string): Promise<{
  session_id: string;
  room_name: string;
  livekit_url: string | null;
  token: string | null;
  kitchen_name: string | null;
}> {
  return apiFetch(`/api/v1/stream/sessions/${sessionId}/viewer-token`, { method: "POST" });
}

export const ORDER_NEXT: Record<string, string[]> = {
  received: ["accepted", "cancelled"],
  accepted: ["preparing", "cancelled"],
  preparing: ["ready", "cancelled"],
  ready: ["out_for_delivery", "delivered", "cancelled"],
  out_for_delivery: ["delivered", "cancelled"],
};

export const STATUS_LABELS: Record<string, string> = {
  received: "Received",
  accepted: "Accepted",
  preparing: "Preparing",
  ready: "Ready",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export type GstProfile = {
  id: string;
  kitchen_id: string;
  gstin: string;
  legal_name: string;
  trade_name: string | null;
  state_code: string;
  registered_address: string;
  default_tax_rate: number;
  is_active: boolean;
  invoice_prefix: string | null;
  created_at: string;
  updated_at: string | null;
};

export type GstTaxInvoice = {
  id: string;
  kitchen_id: string;
  order_id: string;
  invoice_number: string;
  invoice_date: string;
  order_code: string;
  customer_name: string | null;
  place_of_supply_state_code: string;
  supply_type: string;
  taxable_value: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  tax_rate: number;
  gross_total: number;
};

export type GstMonthlyReport = {
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
  invoices: GstTaxInvoice[];
};

export type GstBalanceSheetLine = {
  label: string;
  amount: number;
};

export type GstBalanceSheet = {
  kitchen_id: string;
  period_year: number;
  period_month: number;
  assets: GstBalanceSheetLine[];
  liabilities: GstBalanceSheetLine[];
  equity: GstBalanceSheetLine[];
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
};

export type GstAudit = {
  id: string;
  kitchen_id: string;
  period_year: number;
  period_month: number;
  status: string;
  invoice_count: number;
  total_taxable: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  total_tax: number;
  total_gross_sales: number;
  closed_at: string | null;
  balance_sheet: GstBalanceSheet | null;
  invoices: GstTaxInvoice[];
};

export async function fetchGstProfile(kitchenId: string): Promise<GstProfile | null> {
  try {
    return await apiFetch(`/api/v1/kitchens/${kitchenId}/gst/profile`);
  } catch (err) {
    if (err instanceof Error && err.message.includes("GST profile not found")) return null;
    throw err;
  }
}

export async function upsertGstProfile(
  kitchenId: string,
  data: {
    gstin: string;
    legal_name: string;
    trade_name?: string | null;
    registered_address: string;
    default_tax_rate?: number;
    is_active?: boolean;
    invoice_prefix?: string | null;
  },
): Promise<GstProfile> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/gst/profile`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function syncGstInvoices(
  kitchenId: string,
  year?: number,
  month?: number,
): Promise<{ synced_count: number; invoices: GstTaxInvoice[] }> {
  const params = new URLSearchParams();
  if (year) params.set("year", String(year));
  if (month) params.set("month", String(month));
  const qs = params.toString();
  return apiFetch(`/api/v1/kitchens/${kitchenId}/gst/sync${qs ? `?${qs}` : ""}`, {
    method: "POST",
  });
}

export async function fetchGstMonthlyReport(
  kitchenId: string,
  year: number,
  month: number,
): Promise<GstMonthlyReport> {
  return apiFetch(
    `/api/v1/kitchens/${kitchenId}/gst/reports/monthly?year=${year}&month=${month}`,
  );
}

export async function downloadGstMonthlyExcel(
  kitchenId: string,
  year: number,
  month: number,
): Promise<void> {
  return downloadPdf(
    `/api/v1/kitchens/${kitchenId}/gst/reports/monthly/export.xlsx?year=${year}&month=${month}`,
    `kitchcu-gst-${year}-${String(month).padStart(2, "0")}.xlsx`,
  );
}

export async function downloadGstMonthlyPdf(
  kitchenId: string,
  year: number,
  month: number,
): Promise<void> {
  return downloadPdf(
    `/api/v1/kitchens/${kitchenId}/gst/reports/monthly/export.pdf?year=${year}&month=${month}`,
    `kitchcu-gst-${year}-${String(month).padStart(2, "0")}.pdf`,
  );
}

export async function fetchGstBalanceSheet(
  kitchenId: string,
  year: number,
  month: number,
): Promise<GstBalanceSheet> {
  return apiFetch(
    `/api/v1/kitchens/${kitchenId}/gst/reports/balance-sheet?year=${year}&month=${month}`,
  );
}

export async function fetchGstAudit(
  kitchenId: string,
  year: number,
  month: number,
): Promise<GstAudit> {
  return apiFetch(`/api/v1/kitchens/${kitchenId}/gst/audit?year=${year}&month=${month}`);
}

export async function closeGstAudit(
  kitchenId: string,
  year: number,
  month: number,
): Promise<GstAudit> {
  return apiFetch(
    `/api/v1/kitchens/${kitchenId}/gst/audit/close?year=${year}&month=${month}`,
    { method: "POST" },
  );
}
