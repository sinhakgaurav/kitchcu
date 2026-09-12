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
# Extra saved pins for the primary diner so discovery can switch cities.
DEMO_CUSTOMER_ADDRESSES = [
    {
        "phone_e164": "+919123456789",
        "addresses": [
            {
                "label": "Home",
                "address_line": "Koregaon Park Lane 7",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "phone": "+919123456789",
                "latitude": 18.5362,
                "longitude": 73.8958,
                "is_default": True,
            },
            {
                "label": "Work",
                "address_line": "Bandra West, Linking Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400050",
                "phone": "+919123456789",
                "latitude": 19.0596,
                "longitude": 72.8295,
                "is_default": False,
            },
        ],
    },
    {
        "phone_e164": "+919123456780",
        "addresses": [
            {
                "label": "Home",
                "address_line": "Kothrud main road",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411038",
                "phone": "+919123456780",
                "latitude": 18.5074,
                "longitude": 73.8077,
                "is_default": True,
            },
            {
                "label": "Parents",
                "address_line": "Gomti Nagar Extension",
                "city": "Lucknow",
                "state": "Uttar Pradesh",
                "pincode": "226010",
                "phone": "+919123456780",
                "latitude": 26.8467,
                "longitude": 80.9462,
                "is_default": False,
            },
        ],
    },
]

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

# Multi-city presence kitchens (primary demo owner) — discovery + “cities we serve”
DEMO_KITCHENS_CITIES = [
    {
        "name": "Delhi Home Thali",
        "description": "North Indian home thalis — Connaught Place area.",
        "address_line": "Connaught Place",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "latitude": 28.6315,
        "longitude": 77.2167,
    },
    {
        "name": "Gurugram Tiffin Hub",
        "description": "Office-area tiffins — Sector 29.",
        "address_line": "Sector 29",
        "city": "Gurugram",
        "state": "Haryana",
        "pincode": "122001",
        "latitude": 28.4682,
        "longitude": 77.0636,
    },
    {
        "name": "Noida Fresh Kitchen",
        "description": "Home-style veg meals — Sector 18.",
        "address_line": "Sector 18",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "pincode": "201301",
        "latitude": 28.5708,
        "longitude": 77.3261,
    },
    {
        "name": "Dehradun Valley Kitchen",
        "description": "Garhwali & North Indian home food.",
        "address_line": "Rajpur Road",
        "city": "Dehradun",
        "state": "Uttarakhand",
        "pincode": "248001",
        "latitude": 30.3253,
        "longitude": 78.0413,
    },
    {
        "name": "Prayagraj Ghar Ka Khana",
        "description": "Home taste from Prayagraj — Civil Lines.",
        "address_line": "Civil Lines",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "pincode": "211001",
        "latitude": 25.4493,
        "longitude": 81.833,
    },
    {
        "name": "Varanasi Banarasi Bites",
        "description": "Banarasi snacks & thalis near Assi Ghat.",
        "address_line": "Assi Ghat Road",
        "city": "Varanasi",
        "state": "Uttar Pradesh",
        "pincode": "221005",
        "latitude": 25.2885,
        "longitude": 83.0065,
    },
    {
        "name": "Kanpur Home Kitchen",
        "description": "Awadhi-inspired home meals — Civil Lines.",
        "address_line": "Civil Lines",
        "city": "Kanpur",
        "state": "Uttar Pradesh",
        "pincode": "208001",
        "latitude": 26.467,
        "longitude": 80.35,
    },
    {
        "name": "Lucknow Nawab Kitchen",
        "description": "Lucknowi home biryani & kebabs — Hazratganj.",
        "address_line": "Hazratganj",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "pincode": "226001",
        "latitude": 26.853,
        "longitude": 80.9462,
    },
    {
        "name": "Jhansi Fort Kitchen",
        "description": "Bundelkhand home food near Jhansi Fort.",
        "address_line": "Fort Road",
        "city": "Jhansi",
        "state": "Uttar Pradesh",
        "pincode": "284001",
        "latitude": 25.4486,
        "longitude": 78.5696,
    },
    {
        "name": "Mumbai Andheri Tiffins",
        "description": "Coastal & Maharashtrian tiffins — Andheri East.",
        "address_line": "Andheri East",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400069",
        "latitude": 19.1136,
        "longitude": 72.8697,
    },
]

# Default customer location for nearby search (Pune — demo kitchen area)
DEMO_CUSTOMER_LOCATION = {
    "latitude": 18.5362,
    "longitude": 73.8958,
    "label": "Koregaon Park, Pune",
}

# ── Image helpers ─────────────────────────────────────────────────────────────
# Prefer local PWA assets (apps/website/public/media/food/) so demo menus never
# depend on third-party CDNs. Relative paths resolve on customer/kitchen hosts.

FOOD_MEDIA_FILES = (
    "biryani.jpg",
    "dosa.jpg",
    "skewers.jpg",
    "bowls.jpg",
    "dessert.jpg",
    "dining.jpg",
    "samosa.jpg",
    "rice.jpg",
    "bbq.jpg",
    "pasta.jpg",
    "pizza.jpg",
    "salad.jpg",
    "burger.jpg",
    "kitchen.jpg",
    "service.jpg",
    "restaurant.jpg",
)


def food_media(file: str) -> str:
    return f"/media/food/{file}"


def unsplash(photo_id: str, width: int = 800) -> str:
    """Legacy helper — prefer food_media() for seeded dish heroes."""
    return f"https://images.unsplash.com/{photo_id}?w={width}&q=85&auto=format&fit=crop"


# ── Dish photo truth table ────────────────────────────────────────────────────
# A hero photo is a promise about what arrives in the bag, so every asset is
# described here by what it actually shows. An asset may be assigned to a dish
# only when the photo *is* that dish.
FOOD_ASSET_SUBJECTS: dict[str, str] = {
    "biryani.jpg": "Chicken biryani — bone-in chicken pieces in saffron basmati",
    "dosa.jpg": "Folded masala dosa on a plate with a chutney cup",
    "samosa.jpg": "Two deep-fried samosas on white",
    "salad.jpg": "Vegan bowl — avocado, chickpea, sweet potato, radish, greens",
    "bowls.jpg": "Seared tofu and boiled egg bowl with edamame, corn, greens",
    "rice.jpg": "Chicken fried rice with scrambled egg, peas, carrot",
    "pizza.jpg": "BBQ chicken pizza with pineapple, red onion, coriander",
    "pasta.jpg": "Spaghetti tossed in tomato sauce",
    "skewers.jpg": "Mixed grill platter — chicken skewers and wings, lamb chops, grilled veg",
    "bbq.jpg": "Glazed rib rack with fries, tomato, pickles",
    "dessert.jpg": "Apple turnovers dusted with icing sugar",
    # Venue photography. Fine as marketing backdrop, never a dish hero.
    "kitchen.jpg": "Kitchen interior (venue)",
    "dining.jpg": "Laid dining table (venue)",
    "service.jpg": "Counter service (venue)",
    "restaurant.jpg": "Restaurant room (venue)",
    # Fast-food chain product shot of a beef patty on branded paper: wrong meat for
    # an Indian demo menu and not ours to pass off as a kitchen's own cooking.
    "burger.jpg": "Beef cheeseburger, brand product shot",
}

VENUE_ASSETS = frozenset({"kitchen.jpg", "dining.jpg", "service.jpg", "restaurant.jpg"})
UNUSABLE_DISH_ASSETS = VENUE_ASSETS | {"burger.jpg"}
# Shows meat or egg, so it can never sit on a veg or vegan dish.
NON_VEG_ASSETS = frozenset({"biryani.jpg", "rice.jpg", "pizza.jpg", "skewers.jpg", "bbq.jpg", "bowls.jpg"})

# One asset, one dish — shared by the primary and bulk seeders so they cannot drift.
# A dish missing from this map seeds with no hero, which keeps it an inactive draft
# and off the public menu until an owner captures a real photo. That is deliberate:
# a dish with no photo costs the demo a tile, a dish with someone else's photo costs
# the diner their trust.
DISH_MEDIA_BY_NAME: dict[str, str] = {
    "Chicken Biryani": "biryani.jpg",
    "Masala Dosa": "dosa.jpg",
    "Samosa (2 pc)": "samosa.jpg",
    "Vegan Buddha Bowl": "salad.jpg",
    "Egg & Tofu Protein Bowl": "bowls.jpg",
    "Chicken Fried Rice": "rice.jpg",
    "BBQ Chicken Pizza": "pizza.jpg",
    "Tomato Basil Spaghetti": "pasta.jpg",
    "Mixed Grill Platter": "skewers.jpg",
    "Smoky BBQ Ribs": "bbq.jpg",
    "Apple Cinnamon Turnovers": "dessert.jpg",
}


def media_for_dish(name: str) -> str | None:
    """Hero URL for a seeded dish, or None when no asset honestly shows it."""
    asset = DISH_MEDIA_BY_NAME.get(name.strip())
    return food_media(asset) if asset else None


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


# Sample dishes for seeded menu (cuisine -> diet category -> dish).
#
# Heroes come from DISH_MEDIA_BY_NAME, so the menu splits in two:
#   * dishes whose photo genuinely shows them go live;
#   * the house classics below have no honest asset yet, so they seed as drafts
#     and demo the live-capture gate an owner walks through on day one.
DEMO_DISHES: list[dict] = [
    {
        "name": "Chicken Biryani",
        "cuisine_slug": "north_indian",
        "category_slug": "non_veg",
        "price": 279.0,
        "prep_time_min": 40,
        "description": "Fragrant basmati rice with tender chicken and whole spices.",
        "ingredients_description": "Chicken, basmati rice, saffron, fried onions, biryani masala",
    },
    {
        "name": "Masala Dosa",
        "cuisine_slug": "south_indian",
        "category_slug": "veg",
        "price": 149.0,
        "prep_time_min": 20,
        "description": "Crispy rice crepe filled with spiced potato masala, served with sambar.",
        "ingredients_description": "Rice, urad dal, potato, mustard seeds, curry leaves",
    },
    {
        "name": "Samosa (2 pc)",
        "cuisine_slug": "street_food",
        "category_slug": "veg",
        "price": 59.0,
        "prep_time_min": 10,
        "description": "Flaky pastry triangles stuffed with spiced potato and peas.",
        "ingredients_description": "Wheat flour, potato, green peas, cumin, garam masala",
    },
    {
        "name": "Chicken Fried Rice",
        "cuisine_slug": "chinese",
        "category_slug": "non_veg",
        "price": 219.0,
        "prep_time_min": 22,
        "description": "Wok-tossed rice with chicken, egg, peas, and carrot.",
        "ingredients_description": "Rice, chicken, egg, peas, carrot, soy, spring onion",
    },
    {
        "name": "Egg & Tofu Protein Bowl",
        "cuisine_slug": "continental",
        "category_slug": "eggetarian",
        "price": 249.0,
        "prep_time_min": 18,
        "description": "Seared tofu and boiled egg over greens with edamame and sweetcorn.",
        "ingredients_description": "Tofu, egg, edamame, sweetcorn, cucumber, lettuce, chilli flakes",
    },
    {
        "name": "Vegan Buddha Bowl",
        "cuisine_slug": "continental",
        "category_slug": "vegan",
        "price": 249.0,
        "prep_time_min": 18,
        "description": "Avocado, chickpea, roast sweet potato, and radish over crisp greens.",
        "ingredients_description": "Avocado, chickpea, sweet potato, radish, cabbage, tahini",
    },
    {
        "name": "BBQ Chicken Pizza",
        "cuisine_slug": "continental",
        "category_slug": "non_veg",
        "price": 329.0,
        "prep_time_min": 26,
        "description": "Thin crust with pulled BBQ chicken, pineapple, and red onion.",
        "ingredients_description": "Wheat flour, mozzarella, chicken, BBQ sauce, pineapple, red onion",
    },
    {
        "name": "Tomato Basil Spaghetti",
        "cuisine_slug": "continental",
        "category_slug": "veg",
        "price": 229.0,
        "prep_time_min": 20,
        "description": "Spaghetti tossed in slow-cooked tomato sauce with basil.",
        "ingredients_description": "Spaghetti, tomato, garlic, basil, olive oil",
    },
    {
        "name": "Mixed Grill Platter",
        "cuisine_slug": "north_indian",
        "category_slug": "non_veg",
        "price": 449.0,
        "prep_time_min": 35,
        "description": "Chicken skewers, wings, and lamb chops with grilled veg and dips.",
        "ingredients_description": "Chicken, lamb, yogurt marinade, capsicum, aubergine, potato",
    },
    {
        "name": "Smoky BBQ Ribs",
        "cuisine_slug": "continental",
        "category_slug": "non_veg",
        "price": 479.0,
        "prep_time_min": 45,
        "description": "Slow-cooked glazed rib rack with fries and house pickles.",
        "ingredients_description": "Ribs, BBQ glaze, paprika, potato, gherkins",
    },
    {
        "name": "Apple Cinnamon Turnovers",
        "cuisine_slug": "continental",
        "category_slug": "veg",
        "price": 159.0,
        "prep_time_min": 25,
        "description": "Baked puff pastry parcels of cinnamon apple, dusted with icing sugar.",
        "ingredients_description": "Puff pastry, apple, cinnamon, butter, icing sugar",
    },
    # ── House classics awaiting a live-capture hero (seed as drafts) ──────────
    {
        "name": "Paneer Tikka",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 199.0,
        "prep_time_min": 25,
        "description": "Char-grilled cottage cheese with bell peppers and mint chutney.",
        "ingredients_description": "Paneer, capsicum, onion, yogurt marinade, spices",
    },
    {
        "name": "Butter Chicken",
        "cuisine_slug": "north_indian",
        "category_slug": "non_veg",
        "price": 299.0,
        "prep_time_min": 35,
        "description": "Creamy tomato gravy with tandoori chicken — home-style, not restaurant heavy.",
        "ingredients_description": "Chicken, tomato, butter, cream, kasuri methi",
    },
    {
        "name": "Veg Thali Combo",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 249.0,
        "prep_time_min": 30,
        "description": "Dal, seasonal sabzi, rice, roti, pickle, and papad — complete meal.",
        "ingredients_description": "Dal, seasonal vegetables, wheat roti, rice, accompaniments",
    },
    {
        "name": "Pav Bhaji",
        "cuisine_slug": "street_food",
        "category_slug": "veg",
        "price": 129.0,
        "prep_time_min": 18,
        "description": "Mumbai-style mashed veggie curry with butter-toasted pav (2 pcs).",
        "ingredients_description": "Mixed vegetables, pav, butter, bhaji masala",
    },
    {
        "name": "Gulab Jamun",
        "cuisine_slug": "north_indian",
        "category_slug": "veg",
        "price": 99.0,
        "prep_time_min": 10,
        "description": "Warm milk-solid dumplings in rose-cardamom syrup (2 pcs).",
        "ingredients_description": "Khoya, flour, sugar, rose water, cardamom",
    },
    {
        "name": "Mango Lassi",
        "cuisine_slug": "home_style",
        "category_slug": "veg",
        "price": 89.0,
        "prep_time_min": 5,
        "description": "Thick yogurt drink blended with Alphonso mango pulp.",
        "ingredients_description": "Yogurt, mango pulp, cardamom, ice",
    },
]

DEMO_DISHES = [{**dish, "media_url": media_for_dish(dish["name"])} for dish in DEMO_DISHES]

# Sample orders (created after dishes exist; dish names matched at runtime).
# Only live dishes are orderable, so every item here must be a photo-backed dish
# from DISH_MEDIA_BY_NAME — otherwise the item is silently dropped at seed time.
DEMO_ORDERS: list[dict] = [
    {
        "customer_name": "Priya Mehta",
        "customer_phone": "+919876543210",
        "delivery_type": "delivery",
        "payment_method": "upi",
        "delivery_fee": 40.0,
        "items": [{"dish_name": "Chicken Biryani", "quantity": 1}, {"dish_name": "Samosa (2 pc)", "quantity": 2}],
        "target_status": "preparing",
    },
    {
        "customer_name": "Amit Desai",
        "customer_phone": "+919812345678",
        "delivery_type": "pickup",
        "payment_method": "cod",
        "delivery_fee": 0.0,
        "items": [{"dish_name": "Masala Dosa", "quantity": 2}],
        "target_status": "received",
    },
    {
        "customer_name": "Walk-in Customer",
        "customer_phone": None,
        "delivery_type": "pickup",
        "payment_method": "cod",
        "delivery_fee": 0.0,
        "items": [
            {"dish_name": "Vegan Buddha Bowl", "quantity": 1},
            {"dish_name": "Apple Cinnamon Turnovers", "quantity": 1},
        ],
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
