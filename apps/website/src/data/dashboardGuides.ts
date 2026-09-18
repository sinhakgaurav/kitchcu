export const OWNER_HOWTO_PAGES: {
  test: (path: string) => boolean;
  prefix: string;
  count: number;
}[] = [
  { test: (p) => p.startsWith("/dashboard/orders/new"), prefix: "owner.howto.newOrder", count: 5 },
  { test: (p) => p.startsWith("/dashboard/menu/new"), prefix: "owner.howto.addDish", count: 5 },
  { test: (p) => p.startsWith("/dashboard/orders"), prefix: "owner.howto.orders", count: 6 },
  { test: (p) => p.startsWith("/dashboard/menu"), prefix: "owner.howto.menu", count: 5 },
  { test: (p) => p.startsWith("/dashboard/ingredients"), prefix: "owner.howto.ingredients", count: 6 },
  { test: (p) => p.startsWith("/dashboard/prep"), prefix: "owner.howto.prep", count: 5 },
  { test: (p) => p.startsWith("/dashboard/brand"), prefix: "owner.howto.brand", count: 5 },
  { test: (p) => p.startsWith("/dashboard/reports"), prefix: "owner.howto.reports", count: 5 },
  { test: (p) => p.startsWith("/dashboard/ratings"), prefix: "owner.howto.ratings", count: 5 },
  { test: (p) => p.startsWith("/dashboard/growth"), prefix: "owner.howto.growth", count: 5 },
  { test: (p) => p.startsWith("/dashboard/crm"), prefix: "owner.howto.crm", count: 5 },
  { test: (p) => p.startsWith("/dashboard/coupons"), prefix: "owner.howto.coupons", count: 5 },
  { test: (p) => p.startsWith("/dashboard/tiffin"), prefix: "owner.howto.tiffin", count: 5 },
  { test: (p) => p.startsWith("/dashboard/templates"), prefix: "owner.howto.templates", count: 5 },
  { test: (p) => p.startsWith("/dashboard/stream"), prefix: "owner.howto.stream", count: 5 },
  { test: (p) => p.startsWith("/dashboard/learning"), prefix: "owner.howto.learning", count: 5 },
  { test: (p) => p.startsWith("/dashboard/community"), prefix: "owner.howto.community", count: 5 },
  { test: (p) => p.startsWith("/dashboard/subscription"), prefix: "owner.howto.subscription", count: 5 },
  { test: (p) => p.startsWith("/dashboard/referrals"), prefix: "owner.howto.referrals", count: 5 },
  { test: (p) => p.startsWith("/dashboard/whatsapp"), prefix: "owner.howto.whatsapp", count: 4 },
  { test: (p) => p.startsWith("/dashboard/payment-gateway"), prefix: "owner.howto.payments", count: 4 },
  { test: (p) => p.startsWith("/dashboard/gst"), prefix: "owner.howto.gst", count: 4 },
  { test: (p) => p.startsWith("/dashboard/setup"), prefix: "owner.howto.setup", count: 6 },
  { test: (p) => p === "/dashboard" || p === "/dashboard/", prefix: "owner.howto.home", count: 5 },
];

export const OWNER_TOUR_STEP_COUNT = 14;
export const CUSTOMER_TOUR_STEP_COUNT = 6;
