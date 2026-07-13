/** Customer app session — isolated from kitchen owner auth (customer.kitchcu.in only) */

import type { KitchenPublic } from "./api";
import { APP_STORAGE_PREFIX } from "./brand";

const SESSION_KEY = `${APP_STORAGE_PREFIX}_customer_session`;

export type SavedKitchen = {
  id: string;
  code: string;
  name: string;
  city: string | null;
};

export type CustomerSession = {
  customerId?: string;
  name: string;
  phone: string;
  email?: string | null;
  avatarUrl?: string | null;
  authProvider?: string;
  savedKitchens: SavedKitchen[];
};

export function getCustomerSession(): CustomerSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as CustomerSession;
  } catch {
    return null;
  }
}

export function setCustomerSession(session: CustomerSession): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearCustomerSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function saveKitchenToSession(kitchen: KitchenPublic): CustomerSession {
  const current = getCustomerSession() ?? { name: "", phone: "", savedKitchens: [] };
  const exists = current.savedKitchens.some((k) => k.id === kitchen.id);
  const savedKitchens = exists
    ? current.savedKitchens
    : [
        { id: kitchen.id, code: kitchen.code, name: kitchen.name, city: kitchen.city },
        ...current.savedKitchens,
      ].slice(0, 8);
  const next = { ...current, savedKitchens };
  setCustomerSession(next);
  return next;
}
