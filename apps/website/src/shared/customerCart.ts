/** Multi-kitchen cart — localStorage (customer PWA checkout). */

export type CartLine = {
  dishId: string;
  dishName: string;
  unitPrice: number;
  quantity: number;
  prepTimeMin: number;
};

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
}

export function clearCart(): void {
  localStorage.removeItem(CART_KEY);
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

export function addToCart(
  kitchen: { id: string; name: string; code: string },
  dish: { id: string; name: string; price: number; prep_time_min: number },
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
  if (line) {
    line.quantity += quantity;
  } else {
    kitchenCart.lines.push({
      dishId: dish.id,
      dishName: dish.name,
      unitPrice: dish.price,
      quantity,
      prepTimeMin: dish.prep_time_min,
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
