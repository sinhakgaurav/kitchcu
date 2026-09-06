/** Multi-kitchen cart — localStorage (customer PWA checkout). */

export type CartLine = {
  dishId: string;
  dishName: string;
  unitPrice: number;
  quantity: number;
  prepTimeMin: number;
  deliveryTimeMin: number;
  maxTimeMin: number;
  special_instructions?: string;
};

export const CART_CHANGED_EVENT = "kitchcu-cart-changed";

function notifyCartChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CART_CHANGED_EVENT));
}

export function kitchenFromOrderCode(
  kitchenId: string,
  orderCode: string,
): { id: string; name: string; code: string } {
  const code = orderCode.split("-")[0] || "KITCHEN";
  return { id: kitchenId, name: code, code };
}

export type KitchenCart = {
  kitchenId: string;
  kitchenName: string;
  kitchenCode: string;
  lines: CartLine[];
  updatedAt: string;
};

/** Alias used by checkout — same shape as KitchenCart */
export type KitchenCartGroup = KitchenCart;

export type CustomerCart = {
  kitchens: KitchenCart[];
  updatedAt: string;
};

import { APP_STORAGE_PREFIX } from "./brand";

const CART_KEY = `${APP_STORAGE_PREFIX}_customer_cart`;

export function getCart(): CustomerCart | null {
  try {
    const raw = localStorage.getItem(CART_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CustomerCart | KitchenCart;
    if ("kitchens" in parsed && Array.isArray(parsed.kitchens)) {
      return parsed.kitchens.length ? parsed : null;
    }
    if ("kitchenId" in parsed && Array.isArray(parsed.lines)) {
      const migrated = {
        kitchens: [parsed],
        updatedAt: parsed.updatedAt || new Date().toISOString(),
      };
      saveCart(migrated);
      return migrated;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveCart(cart: CustomerCart): void {
  localStorage.setItem(CART_KEY, JSON.stringify({ ...cart, updatedAt: new Date().toISOString() }));
  notifyCartChanged();
}

export function clearCart(): void {
  localStorage.removeItem(CART_KEY);
  notifyCartChanged();
}

export function kitchenCartSubtotal(cart: KitchenCart): number {
  return cart.lines.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
}

export function cartSubtotal(cart: CustomerCart): number {
  return cart.kitchens.reduce((sum, kitchen) => sum + kitchenCartSubtotal(kitchen), 0);
}

export function cartItemCount(cart: CustomerCart | null, kitchenId?: string): number {
  if (!cart) return 0;
  return cart.kitchens
    .filter((kitchen) => !kitchenId || kitchen.kitchenId === kitchenId)
    .reduce(
      (total, kitchen) => total + kitchen.lines.reduce((sum, line) => sum + line.quantity, 0),
      0,
    );
}

/** Max prep across lines (parallel kitchen work — not a sum). */
export function projectKitchenPrepMin(kitchen: KitchenCart): number {
  if (!kitchen.lines.length) return 0;
  return Math.max(...kitchen.lines.map((line) => line.prepTimeMin || 0));
}

/** Max delivery travel across lines. */
export function projectKitchenDeliveryMin(kitchen: KitchenCart): number {
  if (!kitchen.lines.length) return 0;
  return Math.max(...kitchen.lines.map((line) => line.deliveryTimeMin || 0));
}

/**
 * Customer-facing doorstep ETA = max(prep) + max(delivery).
 * Quality-first: parallel prep, honest travel — not a fake speed race.
 */
export function projectKitchenReadyMin(kitchen: KitchenCart, forDelivery = true): number {
  if (!kitchen.lines.length) return 0;
  const prep = projectKitchenPrepMin(kitchen);
  if (!forDelivery) return prep;
  return prep + projectKitchenDeliveryMin(kitchen);
}

export function projectCartReadyMin(cart: CustomerCart | null, forDelivery = true): number {
  if (!cart?.kitchens.length) return 0;
  return Math.max(...cart.kitchens.map((k) => projectKitchenReadyMin(k, forDelivery)));
}

export function addToCart(
  kitchen: { id: string; name: string; code: string },
  dish: {
    id: string;
    name: string;
    price: number;
    prep_time_min: number;
    delivery_time_min?: number | null;
    max_time_min?: number;
    projected_ready_min?: number;
    special_instructions?: string;
  },
  quantity = 1,
): CustomerCart {
  const existing = getCart();
  const cart: CustomerCart = existing
    ? {
        ...existing,
        kitchens: existing.kitchens.map((group) => ({
          ...group,
          lines: group.lines.map((line) => ({ ...line })),
        })),
      }
    : { kitchens: [], updatedAt: "" };
  let kitchenCart = cart.kitchens.find((group) => group.kitchenId === kitchen.id);
  if (!kitchenCart) {
    kitchenCart = {
      kitchenId: kitchen.id,
      kitchenName: kitchen.name,
      kitchenCode: kitchen.code,
      lines: [],
      updatedAt: "",
    };
    cart.kitchens.push(kitchenCart);
  }
  const line = kitchenCart.lines.find((l) => l.dishId === dish.id);
  const note = dish.special_instructions?.trim();
  if (line) {
    line.quantity += quantity;
    if (note) line.special_instructions = note;
  } else {
    const delivery = dish.delivery_time_min ?? 0;
    const maxTime =
      dish.max_time_min ??
      dish.projected_ready_min ??
      dish.prep_time_min + delivery;
    kitchenCart.lines.push({
      dishId: dish.id,
      dishName: dish.name,
      unitPrice: dish.price,
      quantity,
      prepTimeMin: dish.prep_time_min,
      deliveryTimeMin: delivery,
      maxTimeMin: maxTime,
      ...(note ? { special_instructions: note } : {}),
    });
  }
  saveCart(cart);
  return cart;
}

export function updateLineQuantity(dishId: string, quantity: number): CustomerCart | null {
  const cart = getCart();
  if (!cart) return null;
  const next = {
    ...cart,
    kitchens: cart.kitchens
      .map((kitchen) => ({
        ...kitchen,
        lines: kitchen.lines
          .map((line) => (line.dishId === dishId ? { ...line, quantity } : line))
          .filter((line) => line.quantity > 0),
      }))
      .filter((kitchen) => kitchen.lines.length > 0),
  };
  if (!next.kitchens.length) {
    clearCart();
    return null;
  }
  saveCart(next);
  return next;
}

export function updateLineInstructions(
  dishId: string,
  specialInstructions: string,
): CustomerCart | null {
  const cart = getCart();
  if (!cart) return null;
  const note = specialInstructions.trim();
  const next = {
    ...cart,
    kitchens: cart.kitchens.map((kitchen) => ({
      ...kitchen,
      lines: kitchen.lines.map((line) => {
        if (line.dishId !== dishId) return line;
        const updated: CartLine = { ...line };
        if (note) updated.special_instructions = note;
        else delete updated.special_instructions;
        return updated;
      }),
    })),
  };
  saveCart(next);
  return next;
}

export function addItemsToCart(
  kitchen: { id: string; name: string; code: string },
  items: Array<{
    dish_id: string;
    dish_name: string;
    quantity: number;
    unit_price: number;
    prep_time_min?: number;
    special_instructions?: string | null;
  }>,
): CustomerCart {
  let cart: CustomerCart = getCart() ?? { kitchens: [], updatedAt: "" };
  for (const item of items) {
    cart = addToCart(
      kitchen,
      {
        id: item.dish_id,
        name: item.dish_name,
        price: item.unit_price,
        prep_time_min: item.prep_time_min ?? 20,
        special_instructions: item.special_instructions ?? undefined,
      },
      item.quantity,
    );
  }
  return cart;
}
