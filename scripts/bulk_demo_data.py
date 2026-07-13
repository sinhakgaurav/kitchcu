"""Large demo dataset for bulk seeding — kitchens, dishes, orders, WhatsApp drafts."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime

from demo_data import CAPTURED_AT, DEMO_OTP, DEMO_OWNER, unsplash

random.seed(42)

# Pune center (customer demo location)
PUNE_CENTER = {"latitude": 18.5362, "longitude": 73.8958, "city": "Pune", "state": "Maharashtra"}

PUNE_AREAS = [
    "Koregaon Park",
    "Kalyani Nagar",
    "Camp",
    "Baner",
    "Hinjewadi",
    "Wakad",
    "Viman Nagar",
    "Kothrud",
    "Deccan",
    "Shivajinagar",
    "Hadapsar",
    "Magarpatta",
    "Aundh",
    "Pimple Saudagar",
    "Kharadi",
    "Yerwada",
    "Bund Garden",
    "Swargate",
    "Karve Nagar",
    "Sinhgad Road",
]

KITCHEN_SUFFIXES = [
    "Home Kitchen",
    "Cloud Kitchen",
    "Tiffins",
    "Meals",
    "Curry House",
    "Snacks Hub",
    "Kitchen",
    "Food Studio",
]

EXTRA_OWNERS = [
    {"phone": "9876543211", "phone_e164": "+919876543211", "name": "Priya Mehta", "email": "priya@ckac.dev"},
    {"phone": "9876543212", "phone_e164": "+919876543212", "name": "Amit Desai", "email": "amit@ckac.dev"},
    {"phone": "9876543213", "phone_e164": "+919876543213", "name": "Sneha Kulkarni", "email": "sneha@ckac.dev"},
    {"phone": "9876543214", "phone_e164": "+919876543214", "name": "Vikram Patil", "email": "vikram@ckac.dev"},
    {"phone": "9876543215", "phone_e164": "+919876543215", "name": "Ananya Joshi", "email": "ananya@ckac.dev"},
]

CUSTOMER_NAMES = [
    "Priya Mehta",
    "Amit Desai",
    "Sneha Kulkarni",
    "Vikram Patil",
    "Ananya Joshi",
    "Rahul Gupta",
    "Neha Shah",
    "Karan Malhotra",
    "Divya Iyer",
    "Arjun Nair",
    "Pooja Reddy",
    "Sanjay Verma",
    "Meera Krishnan",
    "Rohan Kapoor",
    "Isha Menon",
    "Walk-in Customer",
    "Office Lunch Order",
    "Building 4 Flat 12",
    "Regular - Table 3",
    "Guest Order",
]

UNSPLASH_DISH_IDS = [
    "photo-1563379927098-05c457674dd8",
    "photo-1585937421612-70a008592f82",
    "photo-1630385930673-614492270638",
    "photo-1603894584373-5e6e4bcb1d5c",
    "photo-1626074353815-4aa7c2609e59",
    "photo-1571875250683-875e8d8e8c8e",
    "photo-1606491956689-2ea8660f9640",
    "photo-1596797038530-2c107229654b",
    "photo-1546069901-ba9599a7e63c",
    "photo-1565958011703-398f087be584",
    "photo-1565299624946-b28f40a0ae38",
    "photo-1512621776951-a57141f2eefd",
    "photo-1567620905732-2d1ec7ab7518",
    "photo-1555939594-58d7cb561ad1",
    "photo-1493770348163-869783f6a188",
]

# 55 dishes across all catalog categories
BULK_DISHES: list[dict] = [
    {"name": "Paneer Tikka", "category_slug": "veg", "price": 199, "prep_time_min": 25},
    {"name": "Palak Paneer", "category_slug": "veg", "price": 189, "prep_time_min": 22},
    {"name": "Dal Tadka", "category_slug": "veg", "price": 149, "prep_time_min": 20},
    {"name": "Aloo Gobi", "category_slug": "veg", "price": 159, "prep_time_min": 18},
    {"name": "Bhindi Masala", "category_slug": "veg", "price": 169, "prep_time_min": 20},
    {"name": "Chole Bhature", "category_slug": "veg", "price": 179, "prep_time_min": 25},
    {"name": "Masala Dosa", "category_slug": "veg", "price": 149, "prep_time_min": 20},
    {"name": "Idli Sambar (4 pc)", "category_slug": "veg", "price": 99, "prep_time_min": 15},
    {"name": "Veg Biryani", "category_slug": "veg", "price": 219, "prep_time_min": 35},
    {"name": "Methi Thepla (3 pc)", "category_slug": "veg", "price": 89, "prep_time_min": 12},
    {"name": "Chicken Biryani", "category_slug": "non_veg", "price": 279, "prep_time_min": 40},
    {"name": "Butter Chicken", "category_slug": "non_veg", "price": 299, "prep_time_min": 35},
    {"name": "Chicken Tikka", "category_slug": "non_veg", "price": 249, "prep_time_min": 30},
    {"name": "Mutton Curry", "category_slug": "non_veg", "price": 349, "prep_time_min": 45},
    {"name": "Fish Fry", "category_slug": "non_veg", "price": 289, "prep_time_min": 28},
    {"name": "Egg Curry", "category_slug": "non_veg", "price": 159, "prep_time_min": 22},
    {"name": "Chicken Keema Pav", "category_slug": "non_veg", "price": 199, "prep_time_min": 25},
    {"name": "Tandoori Roti (2 pc)", "category_slug": "non_veg", "price": 49, "prep_time_min": 10},
    {"name": "Tofu Stir Fry", "category_slug": "vegan", "price": 219, "prep_time_min": 20},
    {"name": "Vegan Buddha Bowl", "category_slug": "vegan", "price": 249, "prep_time_min": 18},
    {"name": "Coconut Curry (Vegan)", "category_slug": "vegan", "price": 199, "prep_time_min": 22},
    {"name": "Mango Lassi", "category_slug": "beverages", "price": 89, "prep_time_min": 5},
    {"name": "Sweet Lassi", "category_slug": "beverages", "price": 79, "prep_time_min": 5},
    {"name": "Fresh Lime Soda", "category_slug": "beverages", "price": 59, "prep_time_min": 5},
    {"name": "Buttermilk (Chaas)", "category_slug": "beverages", "price": 49, "prep_time_min": 3},
    {"name": "Masala Chai", "category_slug": "hot_drinks", "price": 39, "prep_time_min": 8},
    {"name": "Filter Coffee", "category_slug": "hot_drinks", "price": 49, "prep_time_min": 8},
    {"name": "Hot Chocolate", "category_slug": "hot_drinks", "price": 99, "prep_time_min": 10},
    {"name": "Cold Coffee", "category_slug": "cold_drinks", "price": 89, "prep_time_min": 5},
    {"name": "Iced Tea", "category_slug": "cold_drinks", "price": 69, "prep_time_min": 5},
    {"name": "Watermelon Juice", "category_slug": "cold_drinks", "price": 79, "prep_time_min": 5},
    {"name": "Pav Bhaji", "category_slug": "snacks", "price": 129, "prep_time_min": 18},
    {"name": "Vada Pav (2 pc)", "category_slug": "snacks", "price": 79, "prep_time_min": 12},
    {"name": "Samosa (2 pc)", "category_slug": "snacks", "price": 59, "prep_time_min": 10},
    {"name": "Bhel Puri", "category_slug": "snacks", "price": 69, "prep_time_min": 8},
    {"name": "French Fries", "category_slug": "snacks", "price": 99, "prep_time_min": 12},
    {"name": "Gulab Jamun", "category_slug": "desserts", "price": 99, "prep_time_min": 10},
    {"name": "Kheer", "category_slug": "desserts", "price": 89, "prep_time_min": 12},
    {"name": "Rasmalai", "category_slug": "desserts", "price": 119, "prep_time_min": 10},
    {"name": "Chocolate Brownie", "category_slug": "desserts", "price": 129, "prep_time_min": 8},
    {"name": "Veg Thali Combo", "category_slug": "combos", "price": 249, "prep_time_min": 30},
    {"name": "Non-Veg Thali", "category_slug": "combos", "price": 329, "prep_time_min": 35},
    {"name": "Office Lunch Box", "category_slug": "combos", "price": 199, "prep_time_min": 25},
    {"name": "Family Feast (4 pax)", "category_slug": "combos", "price": 899, "prep_time_min": 45},
    {"name": "Monsoon Pakora Platter", "category_slug": "seasonal_special", "price": 149, "prep_time_min": 15},
    {"name": "Winter Gajar Halwa", "category_slug": "seasonal_special", "price": 109, "prep_time_min": 12},
    {"name": "Summer Mango Special", "category_slug": "seasonal_special", "price": 179, "prep_time_min": 15},
    {"name": "Festive Sweets Box", "category_slug": "seasonal_special", "price": 299, "prep_time_min": 20},
    {"name": "Sunday Brunch Combo", "category_slug": "seasonal_special", "price": 399, "prep_time_min": 30},
    {"name": "Jeera Rice", "category_slug": "veg", "price": 119, "prep_time_min": 15},
    {"name": "Garlic Naan (2 pc)", "category_slug": "veg", "price": 79, "prep_time_min": 12},
    {"name": "Chicken Wings (6 pc)", "category_slug": "non_veg", "price": 269, "prep_time_min": 25},
    {"name": "Paneer Butter Masala", "category_slug": "veg", "price": 229, "prep_time_min": 28},
    {"name": "Misal Pav", "category_slug": "snacks", "price": 119, "prep_time_min": 15},
    {"name": "Sabudana Khichdi", "category_slug": "veg", "price": 109, "prep_time_min": 18},
]

WHATSAPP_MESSAGES = [
    "2 butter chicken\n1 garlic naan\nno onion",
    "1 chicken biryani\n2 mango lassi",
    "3 paneer tikka\n1 dal tadka",
    "2 masala dosa\n1 filter coffee",
    "1 family feast\nextra spicy",
    "2 pav bhaji\n1 sweet lassi",
    "1 mutton curry\n2 tandoori roti",
    "4 idli sambar\n2 masala chai",
    "1 veg thali combo\nno pickle",
    "2 chicken tikka\n1 cold coffee",
    "1 tofu stir fry\n1 iced tea",
    "3 samosa\n1 masala chai",
    "2 egg curry\n1 jeera rice",
    "1 office lunch box\nurgent by 1pm",
    "2 mystery special dish\n1 naan",
    "5 vada pav\nextra chutney",
    "1 non veg thali\nless oil",
    "2 bhel puri\n1 watermelon juice",
    "1 sunday brunch combo\nfor 2 people",
    "1 chicken keema pav x 4\nno coriander",
    "2 palak paneer\n1 butter naan",
    "1 fish fry\n2 buttermilk",
    "3 gulab jamun\n1 hot chocolate",
    "2 chole bhature\nextra bhatura",
    "1 vegan buddha bowl\nno peanuts",
]

STATUS_CHAINS: dict[str, list[str]] = {
    "received": [],
    "accepted": ["accepted"],
    "preparing": ["accepted", "preparing"],
    "ready": ["accepted", "preparing", "ready"],
    "out_for_delivery": ["accepted", "preparing", "ready", "out_for_delivery"],
    "delivered": ["accepted", "preparing", "ready", "delivered"],
    "delivered_delivery": ["accepted", "preparing", "ready", "out_for_delivery", "delivered"],
    "cancelled": ["cancelled"],
    "cancelled_late": ["accepted", "cancelled"],
}

# Weighted distribution for ~250 orders
ORDER_STATUS_WEIGHTS: list[tuple[str, int]] = [
    ("received", 18),
    ("accepted", 15),
    ("preparing", 22),
    ("ready", 14),
    ("out_for_delivery", 12),
    ("delivered", 130),
    ("delivered_delivery", 25),
    ("cancelled", 8),
    ("cancelled_late", 6),
]


def dish_with_media(dish: dict, index: int) -> dict:
    photo = UNSPLASH_DISH_IDS[index % len(UNSPLASH_DISH_IDS)]
    return {
        **dish,
        "description": f"Home-style {dish['name']} — live-capture, made fresh to order.",
        "ingredients_description": "Fresh local ingredients, house spices",
        "media_url": unsplash(photo, 900),
    }


def enriched_dishes() -> list[dict]:
    return [dish_with_media(d, i) for i, d in enumerate(BULK_DISHES)]


def kitchen_location(index: int, area: str) -> dict:
    """Spread kitchens around Pune for nearby search."""
    angle = random.uniform(0, 2 * math.pi)
    km = 0.4 + (index % 20) * 1.1 + random.uniform(0, 0.8)
    lat = PUNE_CENTER["latitude"] + (km / 111.0) * math.cos(angle)
    lng = PUNE_CENTER["longitude"] + (km / (111.0 * math.cos(math.radians(PUNE_CENTER["latitude"])))) * math.sin(
        angle
    )
    suffix = KITCHEN_SUFFIXES[index % len(KITCHEN_SUFFIXES)]
    name = f"{area} {suffix}"
    pin = 411000 + (index % 37)
    return {
        "name": name,
        "description": f"{name} — cloud kitchen serving Pune with live-capture menu.",
        "address_line": f"{area}, Pune",
        "city": PUNE_CENTER["city"],
        "state": PUNE_CENTER["state"],
        "pincode": str(pin),
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
    }


def bulk_kitchen_specs(count: int) -> list[dict]:
    specs: list[dict] = []
    used_names: set[str] = set()
    for i in range(count):
        area = PUNE_AREAS[i % len(PUNE_AREAS)]
        spec = kitchen_location(i, area)
        base = spec["name"]
        n = 1
        while spec["name"] in used_names:
            spec = kitchen_location(i + n * 7, area)
            spec["name"] = f"{base} #{n + 1}"
            n += 1
        used_names.add(spec["name"])
        specs.append(spec)
    return specs


def owner_kitchen_specs(owner_index: int, per_owner: int, owner_name: str = "") -> list[dict]:
    start = owner_index * per_owner + 100
    if owner_index == 0:
        return bulk_kitchen_specs(per_owner)
    specs: list[dict] = []
    used: set[str] = set()
    for j in range(per_owner):
        area = PUNE_AREAS[(start + j) % len(PUNE_AREAS)]
        spec = kitchen_location(start + j, area)
        if owner_name:
            spec["name"] = f"{owner_name.split()[0]}'s {area} Kitchen"
        while spec["name"] in used:
            spec["name"] = f"{spec['name']} #{j + 2}"
        used.add(spec["name"])
        specs.append(spec)
    return specs


def order_status_plan(total: int) -> list[str]:
    pool: list[str] = []
    for status, weight in ORDER_STATUS_WEIGHTS:
        pool.extend([status] * weight)
    random.shuffle(pool)
    while len(pool) < total:
        pool.extend([s for s, _ in ORDER_STATUS_WEIGHTS for _ in range(3)])
    return pool[:total]


def random_phone() -> str:
    return f"+9198{random.randint(10000000, 99999999)}"


def captured_at() -> str:
    return CAPTURED_AT or datetime.now(UTC).isoformat()
