/** Demo credentials — keep in sync with scripts/demo_data.py */

export const DEMO = {
  ownerName: "Raj Sharma",
  phone: "9876543210",
  phoneE164: "+919876543210",
  email: "demo@kitchcu.dev",
  otp: "123456",
  kitchenName: "Sharma Home Kitchen",
  kitchenCode: "CKPNQ001",
  city: "Pune",
  customerName: "Priya Mehta",
  customerPhone: "9123456789",
  /** Fallback when geolocation is unavailable */
  defaultLocation: {
    latitude: 18.5362,
    longitude: 73.8958,
    label: "Koregaon Park, Pune",
  },
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
