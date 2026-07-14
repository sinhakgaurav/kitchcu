/** Demo credentials — keep in sync with scripts/demo_data.py */

export const DEMO_OTP = "123456";

export const DEMO = {
  ownerName: "Raj Sharma",
  phone: "9876543210",
  phoneE164: "+919876543210",
  email: "demo@kitchcu.dev",
  otp: DEMO_OTP,
  kitchenName: "Sharma Home Kitchen",
  kitchenCode: "CKPNQ001",
  city: "Pune",
  customerName: "Priya Customer",
  customerPhone: "9123456789",
  /** Fallback when geolocation is unavailable */
  defaultLocation: {
    latitude: 18.5362,
    longitude: 73.8958,
    label: "Koregaon Park, Pune",
  },
} as const;

export type DemoOwnerAccount = {
  phone: string;
  name: string;
  email: string;
  kitchenLabel: string;
  kitchenCode?: string;
  primary?: boolean;
};

/** Owner phones that work with DEV OTP after seed-dev-data / seed-bulk-data */
export const DEMO_OWNERS: DemoOwnerAccount[] = [
  {
    phone: "9876543210",
    name: "Raj Sharma",
    email: "demo@kitchcu.dev",
    kitchenLabel: "Sharma Home Kitchen",
    kitchenCode: "CKPNQ001",
    primary: true,
  },
  {
    phone: "9876543211",
    name: "Priya Mehta",
    email: "priya@kitchcu.dev",
    kitchenLabel: "Mehta Tiffins",
  },
  {
    phone: "9876543212",
    name: "Amit Desai",
    email: "amit@kitchcu.dev",
    kitchenLabel: "Desai Cloud Kitchen",
  },
  {
    phone: "9876543213",
    name: "Sneha Kulkarni",
    email: "sneha@kitchcu.dev",
    kitchenLabel: "Kulkarni Home Food",
  },
];

export type DemoCustomerAccount = {
  phone: string;
  name: string;
  note: string;
};

export const DEMO_CUSTOMERS: DemoCustomerAccount[] = [
  { phone: "9123456789", name: "Priya Customer", note: "Default diner" },
  { phone: "9123456780", name: "Rahul Menon", note: "Repeat buyer" },
  { phone: "9988776655", name: "Ananya Guest", note: "Guest checkout" },
];

export const DEMO_ADMIN = {
  email: "admin@kitchcu.dev",
  password: "admin123456",
} as const;

export const DEMO_DISH_NAMES = [
  "Paneer Tikka",
  "Chicken Biryani",
  "Masala Dosa",
  "Butter Chicken",
  "Mango Lassi",
  "Gulab Jamun",
  "Veg Thali Combo",
  "Pav Bhaji",
] as const;
