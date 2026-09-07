/** Razorpay Checkout.js helper — only used when billing returns provider_mode=live. */

import { APP_NAME, APP_STORAGE_PREFIX } from "./brand";
import type { Payment } from "./api";

export type RazorpayCheckoutResult = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};

type RazorpayCtor = new (options: Record<string, unknown>) => { open: () => void };

declare global {
  interface Window {
    Razorpay?: RazorpayCtor;
  }
}

function checkoutStorageKey(paymentId: string): string {
  return `${APP_STORAGE_PREFIX}_rzp:${paymentId}`;
}

export function rememberCheckoutSignature(paymentId: string, result: RazorpayCheckoutResult): void {
  sessionStorage.setItem(checkoutStorageKey(paymentId), JSON.stringify(result));
}

export function readCheckoutSignature(paymentId: string): RazorpayCheckoutResult | null {
  const raw = sessionStorage.getItem(checkoutStorageKey(paymentId));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as RazorpayCheckoutResult;
  } catch {
    return null;
  }
}

export function loadRazorpayCheckout(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Razorpay Checkout requires a browser"));
  }
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-kitchcu-razorpay]");
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Could not load Razorpay Checkout")));
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.dataset.kitchcuRazorpay = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Razorpay Checkout"));
    document.body.appendChild(script);
  });
}

export async function openRazorpayCheckout(payment: Payment): Promise<RazorpayCheckoutResult> {
  if (payment.provider_mode !== "live" || !payment.razorpay_key_id || !payment.razorpay_order_id) {
    throw new Error("This payment is not a live Razorpay Checkout session");
  }
  await loadRazorpayCheckout();
  const Ctor = window.Razorpay;
  if (!Ctor) throw new Error("Razorpay Checkout did not initialize");
  const amountPaise = Math.round(payment.amount * 100);
  return new Promise((resolve, reject) => {
    const checkout = new Ctor({
      key: payment.razorpay_key_id,
      amount: amountPaise,
      currency: payment.currency || "INR",
      name: APP_NAME,
      description: "Order payment — zero food commission",
      order_id: payment.razorpay_order_id,
      handler(response: RazorpayCheckoutResult) {
        rememberCheckoutSignature(payment.id, response);
        resolve(response);
      },
      modal: {
        ondismiss() {
          reject(new Error("Payment window closed — order is unpaid until you complete Checkout"));
        },
      },
    });
    checkout.open();
  });
}
