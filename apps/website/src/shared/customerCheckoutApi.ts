/** Customer checkout + billing API (customer JWT) */

import type { MasterOrder, MasterPaymentCapture, Order, Payment, UpiIntent } from "./api";
import { getCustomerToken } from "./customerApi";

async function checkoutFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getCustomerToken();
  if (!token) throw new Error("Sign in required");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
    Authorization: `Bearer ${token}`,
  };

  const res = await fetch(path, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    throw new Error(detail);
  }
  return body as T;
}

export async function createCustomerOrder(
  kitchenId: string,
  data: {
    items: { dish_id: string; quantity: number }[];
    delivery_type: "pickup" | "delivery";
    payment_method: "cod" | "online" | "upi";
    delivery_fee?: number;
    customer_phone?: string;
    distance_km?: number;
    delivery_fee_accepted?: boolean;
    customer_latitude?: number;
    customer_longitude?: number;
  },
): Promise<Order> {
  return checkoutFetch(`/api/v1/kitchens/${kitchenId}/orders/customer`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createMasterOrder(
  data: {
    groups: {
      kitchen_id: string;
      items: { dish_id: string; quantity: number }[];
      delivery_type: "pickup" | "delivery";
      delivery_fee: number;
      distance_km?: number;
      delivery_fee_accepted?: boolean;
      customer_latitude?: number;
      customer_longitude?: number;
    }[];
    payment_method: "cod" | "online" | "upi";
  },
  idempotencyKey: string,
): Promise<MasterOrder> {
  return checkoutFetch("/api/v1/customers/me/master-orders", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(data),
  });
}

export async function createMasterPayment(
  masterOrderId: string,
  method: "online" | "upi",
): Promise<Payment> {
  return checkoutFetch("/api/v1/billing/payments/customer/master", {
    method: "POST",
    body: JSON.stringify({ master_order_id: masterOrderId, method }),
  });
}

export async function captureMasterPayment(paymentId: string): Promise<MasterPaymentCapture> {
  return checkoutFetch(`/api/v1/billing/payments/customer/master/${paymentId}/capture`, {
    method: "POST",
  });
}

export async function fetchMyOrders(): Promise<{ orders: Order[]; total: number }> {
  return checkoutFetch("/api/v1/customers/me/orders");
}

export async function repeatCustomerOrder(orderId: string): Promise<Order> {
  return checkoutFetch(`/api/v1/customers/me/orders/${orderId}/repeat`, {
    method: "POST",
  });
}

export async function createCustomerPayment(
  orderId: string,
  method: "online" | "upi",
): Promise<Payment> {
  return checkoutFetch("/api/v1/billing/payments/customer", {
    method: "POST",
    body: JSON.stringify({ order_id: orderId, method }),
  });
}

export async function createCustomerUpiIntent(orderId: string): Promise<UpiIntent> {
  return checkoutFetch("/api/v1/billing/payments/customer/upi-intent", {
    method: "POST",
    body: JSON.stringify({ order_id: orderId }),
  });
}

export async function captureCustomerPayment(paymentId: string): Promise<Payment> {
  return checkoutFetch(`/api/v1/billing/payments/customer/${paymentId}/capture`, {
    method: "POST",
  });
}
