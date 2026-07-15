/** Customer auth API — social OAuth + WhatsApp OTP (customer.kitchcu.in) */

import { APP_STORAGE_PREFIX } from "./brand";

const TOKEN_KEY = `${APP_STORAGE_PREFIX}_customer_token`;

export type CustomerProfile = {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  avatar_url: string | null;
  upi_vpa: string | null;
  upi_qr_url: string | null;
  bank_account_number_masked: string | null;
  bank_ifsc: string | null;
  bank_account_name: string | null;
  has_password?: boolean;
  status: string;
};

export type CustomerAuthResult = {
  access_token: string;
  token_type: string;
  expires_in: number;
  customer: CustomerProfile;
};

export type OAuthProvider = {
  id: string;
  label: string;
  method?: string;
};

export function getCustomerToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setCustomerToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearCustomerToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function customerOAuthRedirectUri(): string {
  return `${window.location.origin}/oauth/callback`;
}

async function customerFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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

export async function fetchOAuthProviders(): Promise<OAuthProvider[]> {
  const data = await customerFetch<{ providers: OAuthProvider[] }>(
    "/api/v1/auth/customer/oauth/providers",
  );
  return data.providers;
}

export async function startCustomerOAuth(provider: string): Promise<{
  provider: string;
  state: string;
  authorization_url: string | null;
  dev_mode: boolean;
}> {
  const redirect_uri = customerOAuthRedirectUri();
  const params = new URLSearchParams({ redirect_uri });
  return customerFetch(`/api/v1/auth/customer/oauth/${provider}/start?${params}`);
}

export async function completeCustomerOAuth(
  provider: string,
  payload: { code: string; state: string; redirect_uri: string },
): Promise<CustomerAuthResult> {
  return customerFetch(`/api/v1/auth/customer/oauth/${provider}/complete`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function requestCustomerWhatsAppOtp(phone: string): Promise<void> {
  await customerFetch("/api/v1/auth/customer/whatsapp/request", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}

export async function verifyCustomerWhatsAppOtp(
  phone: string,
  otp: string,
): Promise<CustomerAuthResult> {
  return customerFetch("/api/v1/auth/customer/whatsapp/verify", {
    method: "POST",
    body: JSON.stringify({ phone, otp }),
  });
}

export async function fetchCustomerProfile(): Promise<CustomerProfile> {
  return customerFetch("/api/v1/customers/me");
}

export async function updateCustomerPayout(data: {
  upi_vpa?: string | null;
  bank_account_number?: string | null;
  bank_ifsc?: string | null;
  bank_account_name?: string | null;
}): Promise<CustomerProfile> {
  return customerFetch("/api/v1/customers/me/payout", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function uploadCustomerPayoutQr(file: File): Promise<CustomerProfile> {
  const token = getCustomerToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/v1/customers/me/payout/qr", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Upload failed");
  }
  return body as CustomerProfile;
}

export async function loginWithCustomerOAuthProvider(provider: string): Promise<CustomerAuthResult> {
  const start = await startCustomerOAuth(provider);
  const redirect_uri = customerOAuthRedirectUri();

  if (start.dev_mode) {
    return completeCustomerOAuth(provider, {
      code: "dev",
      state: start.state,
      redirect_uri,
    });
  }

  if (!start.authorization_url) {
    throw new Error(`${provider} login is not configured`);
  }

  sessionStorage.setItem(
    `${APP_STORAGE_PREFIX}_oauth_pending_${provider}`,
    JSON.stringify({ state: start.state, redirect_uri, provider }),
  );
  window.location.assign(start.authorization_url);
  return new Promise(() => {
    /* redirect */
  });
}
