/** Client-side greetings — keep in sync with notification support.py openings. */

export const OWNER_GREETING =
  "Hi! I'm the kitchCU owner assistant.\n\n" +
  "I can help with pricing, WhatsApp orders, menus, delivery, billing/refunds, CRM, tiffin, and more. " +
  "Pick a topic below or type a question.";

export const CUSTOMER_GREETING =
  "Hello! I'm the kitchCU customer assistant.\n\n" +
  "I can help you find kitchens, checkout, track orders, payments, delivery fees, ratings, and tiffin plans. " +
  "Pick a topic below or type a question.";

export const OWNER_STARTER_OPTIONS = [
  { id: "1", label: "Pricing & plans" },
  { id: "2", label: "WhatsApp orders" },
  { id: "3", label: "Menu & live photos" },
  { id: "4", label: "Orders & refunds" },
  { id: "5", label: "Delivery & tracking" },
  { id: "6", label: "CRM, coupons, referrals" },
  { id: "7", label: "Billing & GST" },
  { id: "8", label: "Tiffin & stock" },
  { id: "9", label: "Raise a ticket" },
] as const;

export const CUSTOMER_STARTER_OPTIONS = [
  { id: "1", label: "Find a kitchen" },
  { id: "2", label: "Order & checkout" },
  { id: "3", label: "Track my order" },
  { id: "4", label: "Payments" },
  { id: "5", label: "Delivery fees" },
  { id: "6", label: "Live-capture photos" },
  { id: "7", label: "Ratings & reviews" },
  { id: "8", label: "Tiffin plans" },
  { id: "9", label: "Support / ticket" },
] as const;
