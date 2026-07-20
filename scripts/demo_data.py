"""Shared demo credentials and seed payloads for local development."""

from __future__ import annotations

from datetime import datetime, timezone

# ── Demo owner & kitchen ────────────────────────────────────────────────────

DEMO_OTP = "123456"

DEMO_OWNER = {
    "phone": "9876543210",
    "phone_e164": "+919876543210",
    "name": "Raj Sharma",
    "email": "demo@kitchcu.dev",
    "kitchen_label": "Sharma Home Kitchen",
    "kitchen_code": "CKPNQ001",
    "role": "primary",
}

# Additional owner logins (same OTP). Seeded by seed-dev-data / seed-bulk-data.
DEMO_OWNERS_EXTRA = [
    {
        "phone": "9876543211",
        "phone_e164": "+919876543211",
        "name": "Priya Mehta",
        "email": "priya@kitchcu.dev",
        "kitchen_label": "Mehta Tiffins",
        "role": "growth",
    },
    {
        "phone": "9876543212",
        "phone_e164": "+919876543212",
        "name": "Amit Desai",
        "email": "amit@kitchcu.dev",
        "kitchen_label": "Desai Cloud Kitchen",
        "role": "non_veg",
    },
    {
        "phone": "9876543213",
        "phone_e164": "+919876543213",
        "name": "Sneha Kulkarni",
        "email": "sneha@kitchcu.dev",
        "kitchen_label": "Kulkarni Home Food",
        "role": "veg",
    },
]

DEMO_OWNERS = [DEMO_OWNER, *DEMO_OWNERS_EXTRA]

DEMO_ADMIN = {
    "email": "admin@kitchcu.dev",
    "password": "admin123456",
}

# Customer WhatsApp OTP demos (dev OTP always DEMO_OTP)
DEMO_CUSTOMERS = [
    {
        "phone": "9123456789",
        "phone_e164": "+919123456789",
        "name": "Priya Customer",
        "note": "Default diner",
    },
    {
        "phone": "9123456780",
        "phone_e164": "+919123456780",
        "name": "Rahul Menon",
        "note": "Repeat buyer",
    },
    {
        "phone": "9988776655",
        "phone_e164": "+919988776655",
        "name": "Ananya Guest",
        "note": "Guest checkout",
    },
    {
        "phone": "9123456781",
        "phone_e164": "+919123456781",
        "name": "Kabir Singh",
        "note": "Frequent orderer (CRM/learning trial pool)",
    },
    {
        "phone": "9123456782",
        "phone_e164": "+919123456782",
        "name": "Meera Iyer",
        "note": "Health-conscious diner (CRM/learning trial pool)",
    },
]

# P37 dual referrals — reserved phones for seed states (not used as login personas).
# OTP still DEMO_OTP when the onboard-convert customer is verified during seed.
DEMO_REFERRAL = {
    # Customer → kitchen: leave submitted for admin / customer dashboards
    "pending_kitchen_leads": [
        {
            "kitchen_name": "Seed Spice House",
            "contact_name": "Ravi Seed",
            "contact_phone": "9110001001",
            "city": "Pune",
        },
        {
            "kitchen_name": "Seed Reject Kitchen",
            "contact_name": "Neha Seed",
            "contact_phone": "9110001002",
            "city": "Mumbai",
            "reject": True,
        },
    ],
    # Customer → kitchen: admin-granted convert (₹ credit on primary customer)
    "grant_kitchen_lead": {
        "kitchen_name": "Seed Granted Kitchen",
        "contact_name": "Asha Seed",
        "contact_phone": "9110001003",
        "city": "Pune",
    },
    # Owner → customer: leave submitted
    "pending_customer_leads": [
        {
            "contact_name": "Pending Guest",
            "contact_phone": "9110002001",
            "city": "Pune",
        },
    ],
    # Owner → customer: WhatsApp verify during seed → owner SaaS credit
    "onboard_customer": {
        "contact_name": "Referral Convert",
        "contact_phone": "9110002003",
        "phone_e164": "+919110002003",
        "city": "Pune",
    },
}

DEMO_KITCHEN = {
    "name": "Sharma Home Kitchen",
    "description": "Authentic Pune home-style cloud kitchen — live-capture menu, zero commission.",
    "address_line": "Koregaon Park, Lane 7",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "latitude": 18.5362,
    "longitude": 73.8958,
}

DEMO_KITCHEN_CODE = "CKPNQ001"

# Extra kitchens for nearby-distance demo (same owner, different Pune coords)
DEMO_KITCHENS_EXTRA = [
    {
        "name": "Kalyani Nagar Tiffins",
        "description": "South Indian breakfast & meals — Kalyani Nagar.",
        "address_line": "Kalyani Nagar, Main Road",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411006",
        "latitude": 18.5490,
        "longitude": 73.9075,
    },
    {
        "name": "Camp Street Kitchen",
        "description": "Maharashtrian home food near Camp.",
        "address_line": "Camp, MG Road",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411001",
        "latitude": 18.5195,
        "longitude": 73.8745,
    },
]

# Default customer location for nearby search (Pune — demo kitchen area)
DEMO_CUSTOMER_LOCATION = {
    "latitude": 18.5362,
    "longitude": 73.8958,
    "label": "Koregaon Park, Pune",
}

# ── Image helpers (Unsplash — same IDs as apps/website/src/data/content.ts) ───

def unsplash(photo_id: str, width: int = 800) -> str:
    return f"https://images.unsplash.com/{photo_id}?w={width}&q=85&auto=format&fit=crop"


CAPTURED_AT = datetime.now(timezone.utc).isoformat()

# Legacy category slugs mapped to diet types (veg / non_veg / vegan / eggetarian)
CATEGORY_LEGACY_MAP: dict[str, str] = {
    "beverages": "veg",
    "hot_drinks": "veg",
    "cold_drinks": "veg",
    "snacks": "veg",
    "desserts": "veg",
    "combos": "veg",
    "seasonal_special": "veg",
}

CUISINE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("south_indian", ("dosa", "idli", "sambar", "uttapam", "filter coffee")),
    ("maharashtrian", ("pav bhaji", "misal", "vada pav", "poha")),
    ("street_food", ("bhel", "pani puri", "samosa", "pav bhaji", "vada pav")),
    ("chinese", ("noodle", "manchurian", "fried rice", "hakka")),
    ("bengali", ("fish fry", "rosogolla", "mishti")),
    (
        "north_indian",
        (
            "biryani",
            "tikka",
            "paneer",
            "naan",
            "dal",
            "chole",
            "palak",
            "butter chicken",
            "tandoori",
            "kheer",
            "gulab",
            "thali",
            "aloo",
            "bhindi",
            "methi",
        ),
    ),
    ("continental", ("pasta", "pizza", "burger", "brownie", "fries", "stir fry", "buddha bowl")),
]


def normalize_category_slug(dish: dict) -> str:
    slug = dish.get("category_slug", "veg")
    name = dish["name"].lower()
    if slug in ("veg", "non_veg", "vegan", "eggetarian"):
        return slug
    if "non veg" in name or "non-veg" in name:
        return "non_veg"
    if any(w in name for w in ("chicken", "mutton", "fish", "egg curry", "keema", "wings")):
        return "non_veg"
    if "vegan" in name or slug == "vegan":
        return "vegan"
    return CATEGORY_LEGACY_MAP.get(slug, "veg")


def infer_cuisine_slug(dish: dict) -> str:
    if dish.get("cuisine_slug"):
        return dish["cuisine_slug"]
    name = dish["name"].lower()
    for slug, keywords in CUISINE_KEYWORDS:
        if any(k in name for k in keywords):
            return slug
    return "home_style"


# Sample dishes for seeded menu (cuisine -> diet category -> dish)
DEMO_DISHES: list[dict] = [
    {
        "name": "Paneer Tikka",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 199.0,
        "prep_time_min": 25,
        "description": "Char-grilled cottage cheese with bell peppers and mint chutney.",
        "ingredients_description": "Paneer, capsicum, onion, yogurt marinade, spices",
        "media_url": unsplash("photo-1563379927098-05c457674dd8", 900),
    },
    {
        "name": "Chicken Biryani",
        "cuisine_slug": "north_indian",
        "category_slug": "non_veg",
        "price": 279.0,
        "prep_time_min": 40,
        "description": "Fragrant basmati rice with tender chicken and whole spices.",
        "ingredients_description": "Chicken, basmati rice, saffron, fried onions, biryani masala",
        "media_url": unsplash("photo-1585937421612-70a008592f82", 900),
    },
    {
        "name": "Masala Dosa",
        "cuisine_slug": "south_indian",
        "category_slug": "veg",
        "price": 149.0,
        "prep_time_min": 20,
        "description": "Crispy rice crepe filled with spiced potato masala, served with sambar.",
        "ingredients_description": "Rice, urad dal, potato, mustard seeds, curry leaves",
        "media_url": unsplash("photo-1630385930673-614492270638", 900),
    },
    {
        "name": "Butter Chicken",
        "cuisine_slug": "north_indian",
        "category_slug": "non_veg",
        "price": 299.0,
        "prep_time_min": 35,
        "description": "Creamy tomato gravy with tandoori chicken — home-style, not restaurant heavy.",
        "ingredients_description": "Chicken, tomato, butter, cream, kasuri methi",
        "media_url": unsplash("photo-1603894584373-5e6e4bcb1d5c", 900),
    },
    {
        "name": "Mango Lassi",
        "cuisine_slug": "home_style",
        "category_slug": "veg",
        "price": 89.0,
        "prep_time_min": 5,
        "description": "Thick yogurt drink blended with Alphonso mango pulp.",
        "ingredients_description": "Yogurt, mango pulp, cardamom, ice",
        "media_url": unsplash("photo-1626074353815-4aa7c2609e59", 900),
    },
    {
        "name": "Gulab Jamun",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 99.0,
        "prep_time_min": 10,
        "description": "Warm milk-solid dumplings in rose-cardamom syrup (2 pcs).",
        "ingredients_description": "Khoya, flour, sugar, rose water, cardamom",
        "media_url": unsplash("photo-1571875250683-875e8d8e8c8e", 900),
    },
    {
        "name": "Veg Thali Combo",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 249.0,
        "prep_time_min": 30,
        "description": "Dal, seasonal sabzi, rice, roti, pickle, and papad — complete meal.",
        "ingredients_description": "Dal, seasonal vegetables, wheat roti, rice, accompaniments",
        "media_url": unsplash("photo-1606491956689-2ea8660f9640", 900),
    },
    {
        "name": "Pav Bhaji",
        "cuisine_slug": "street_food",
        "category_slug": "veg",
        "price": 129.0,
        "prep_time_min": 18,
        "description": "Mumbai-style mashed veggie curry with butter-toasted pav (2 pcs).",
        "ingredients_description": "Mixed vegetables, pav, butter, bhaji masala",
        "media_url": unsplash("photo-1596797038530-2c107229654b", 900),
    },
]

# Sample orders (created after dishes exist; dish names matched at runtime)
DEMO_ORDERS: list[dict] = [
    {
        "customer_name": "Priya Mehta",
        "customer_phone": "+919876543210",
        "delivery_type": "delivery",
        "payment_method": "upi",
        "delivery_fee": 40.0,
        "items": [{"dish_name": "Chicken Biryani", "quantity": 1}, {"dish_name": "Mango Lassi", "quantity": 2}],
        "target_status": "preparing",
    },
    {
        "customer_name": "Amit Desai",
        "customer_phone": "+919812345678",
        "delivery_type": "pickup",
        "payment_method": "cod",
        "delivery_fee": 0.0,
        "items": [{"dish_name": "Paneer Tikka", "quantity": 2}],
        "target_status": "received",
    },
    {
        "customer_name": "Walk-in Customer",
        "customer_phone": None,
        "delivery_type": "pickup",
        "payment_method": "cod",
        "delivery_fee": 0.0,
        "items": [{"dish_name": "Veg Thali Combo", "quantity": 1}, {"dish_name": "Gulab Jamun", "quantity": 1}],
        "target_status": "delivered",
    },
]

# Marketing / website image catalog (reference for docs)
WEBSITE_IMAGES = {
    "hero_chef": unsplash("photo-1556910103-1c02745aae4d", 1400),
    "hero_dining": unsplash("photo-1414235077428-338989a2e8c0", 1000),
    "hero_grill": unsplash("photo-1555939594-58d7cb561ad1", 900),
    "hero_bowls": unsplash("photo-1606787366856-119e63814833", 600),
    "login": unsplash("photo-1556911220-e15b29be8c8f", 1200),
    "customers": unsplash("photo-1493770348163-869783f6a188", 1200),
    "owners": unsplash("photo-1552566626-c96b1358752f", 900),
    "contact": unsplash("photo-1559339352-11d035aa65de", 1000),
}
