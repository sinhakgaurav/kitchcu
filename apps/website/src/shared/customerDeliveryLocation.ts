/** Persist the diner's chosen drop pin across discovery and checkout. */

import { APP_STORAGE_PREFIX } from "./brand";
import { cityCenterByName } from "../data/citiesPresence";
import type { CustomerAddress } from "./customerDashboardApi";
import { formatPhoneDisplay } from "./validation";

export const DELIVERY_SELECTION_KEY = `${APP_STORAGE_PREFIX}_delivery_selection`;

export type DeliverySource = "address" | "gps" | "demo";

export type DeliveryCoords = { latitude: number; longitude: number };

export type StoredDeliverySelection = {
  customerId: string;
  addressId: string;
  source: DeliverySource;
};

export function isFinitePin(lat: number | null | undefined, lng: number | null | undefined): boolean {
  return lat != null && lng != null && Number.isFinite(lat) && Number.isFinite(lng);
}

export function resolveAddressCoords(address: CustomerAddress): DeliveryCoords | null {
  if (isFinitePin(address.latitude, address.longitude)) {
    return { latitude: address.latitude as number, longitude: address.longitude as number };
  }
  const city = cityCenterByName(address.city);
  if (!city) return null;
  return { latitude: city.lat, longitude: city.lng };
}

export function pickDeliveryAddress(
  addresses: CustomerAddress[],
  storedId?: string | null,
): CustomerAddress | null {
  if (!addresses.length) return null;
  if (storedId) {
    const stored = addresses.find((row) => row.id === storedId);
    if (stored) return stored;
  }
  return addresses.find((row) => row.is_default) ?? addresses[0];
}

export function formatAddressChoice(address: CustomerAddress): string {
  const pin = resolveAddressCoords(address) ? "" : " · no pin";
  return `${address.label} · ${address.city}${address.is_default ? " (default)" : ""}${pin}`;
}

export function formatAddressLine(address: CustomerAddress): string {
  const bits = [address.address_line, address.city];
  if (address.pincode) bits.push(address.pincode);
  if (address.phone) bits.push(formatPhoneDisplay(address.phone));
  return bits.filter(Boolean).join(", ");
}

export function readStoredDeliverySelection(customerId?: string | null): StoredDeliverySelection | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(DELIVERY_SELECTION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredDeliverySelection;
    if (!parsed?.addressId || !parsed.customerId) return null;
    if (customerId && parsed.customerId !== customerId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeStoredDeliverySelection(value: StoredDeliverySelection | null): void {
  if (typeof localStorage === "undefined") return;
  if (!value) {
    localStorage.removeItem(DELIVERY_SELECTION_KEY);
    return;
  }
  localStorage.setItem(DELIVERY_SELECTION_KEY, JSON.stringify(value));
}

export function clearStoredDeliverySelection(): void {
  writeStoredDeliverySelection(null);
}
