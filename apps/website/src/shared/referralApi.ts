import { apiFetch, getToken } from "./api";
import { getCustomerToken } from "./customerApi";
import { correlationHeaders } from "./http";

export type ReferralLead = {
  id: string;
  direction: string;
  status: string;
  kitchen_name: string | null;
  contact_name: string | null;
  contact_phone: string;
  contact_email: string | null;
  city: string | null;
  notes: string | null;
  reward_inr: number | null;
  created_at: string;
  converted_at: string | null;
  rejection_reason: string | null;
};

export type ReferralDashboard = {
  settings: {
    enabled: boolean;
    customer_to_kitchen_reward_inr: number;
    kitchen_to_customer_reward_inr: number;
    kitchen_reward_trigger: string;
  };
  credit: {
    balance_inr: number;
    lifetime_earned_inr: number;
    lifetime_applied_inr: number;
    reward_per_conversion_inr: number;
    subscription_credit_note: string;
  };
  leads: ReferralLead[];
  converted_count: number;
  pending_count: number;
  estimated_subscription_savings_inr: number;
};

export type BulkReferralResult = {
  accepted: number;
  rejected: number;
  errors: string[];
};

async function customerFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  if (!token) throw new Error("Not signed in");
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function fetchCustomerReferrals(): Promise<ReferralDashboard> {
  return customerFetch("/api/v1/customers/me/referrals");
}

export async function submitCustomerKitchenReferral(data: {
  kitchen_name: string;
  contact_name?: string;
  contact_phone: string;
  contact_email?: string;
  city?: string;
  address_line?: string;
  notes?: string;
}): Promise<ReferralLead> {
  return customerFetch("/api/v1/customers/me/referrals/kitchens", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function bulkCustomerKitchenReferrals(
  rows: Array<Record<string, string | undefined>>,
): Promise<BulkReferralResult> {
  return customerFetch("/api/v1/customers/me/referrals/bulk", {
    method: "POST",
    body: JSON.stringify({ rows }),
  });
}

export function customerReferralTemplateUrl(): string {
  return "/api/v1/customers/me/referrals/template.csv";
}

export async function uploadCustomerReferralCsv(file: File): Promise<BulkReferralResult> {
  const token = getCustomerToken();
  if (!token) throw new Error("Not signed in");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/v1/customers/me/referrals/upload", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function fetchOwnerReferrals(): Promise<ReferralDashboard> {
  return apiFetch("/api/v1/owners/me/referrals");
}

export async function submitOwnerCustomerReferral(data: {
  kitchen_id: string;
  contact_name?: string;
  contact_phone: string;
  contact_email?: string;
  city?: string;
  notes?: string;
}): Promise<ReferralLead> {
  return apiFetch("/api/v1/owners/me/referrals/customers", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function bulkOwnerCustomerReferrals(
  kitchenId: string,
  rows: Array<Record<string, string | undefined>>,
): Promise<BulkReferralResult> {
  return apiFetch("/api/v1/owners/me/referrals/bulk", {
    method: "POST",
    body: JSON.stringify({ kitchen_id: kitchenId, rows }),
  });
}

export function ownerReferralTemplateUrl(): string {
  return "/api/v1/owners/me/referrals/template.csv";
}

export async function uploadOwnerReferralCsv(
  kitchenId: string,
  file: File,
): Promise<BulkReferralResult> {
  const token = getToken();
  if (!token) throw new Error("Not signed in");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `/api/v1/owners/me/referrals/upload?kitchen_id=${encodeURIComponent(kitchenId)}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        ...correlationHeaders(),
      },
      body: form,
    },
  );
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Upload failed");
  }
  return body as BulkReferralResult;
}
