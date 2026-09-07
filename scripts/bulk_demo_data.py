"""Large demo dataset for bulk seeding — kitchens, dishes, orders, WhatsApp drafts."""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from demo_data import (
    CAPTURED_AT,
    DEMO_KITCHEN,
    DEMO_KITCHENS_CITIES,
    DEMO_OWNERS_EXTRA,
    food_media,
)

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

# Neighbourhoods for every CITIES_PRESENCE city (live + coming soon).
CITY_AREAS: dict[str, list[str]] = {
    "Pune": PUNE_AREAS,
    "Mumbai": ["Andheri East", "Bandra", "Powai", "Thane", "Worli", "Dadar"],
    "Delhi": ["Connaught Place", "Karol Bagh", "Saket", "Dwarka", "Rohini"],
    "Gurugram": ["Sector 29", "Cyber City", "Golf Course Road", "Sohna Road"],
    "Noida": ["Sector 18", "Sector 62", "Greater Noida", "Sector 137"],
    "Lucknow": ["Hazratganj", "Gomti Nagar", "Alambagh", "Aminabad"],
    "Kanpur": ["Civil Lines", "Swaroop Nagar", "Kakadeo", "Kalyanpur"],
    "Prayagraj": ["Civil Lines", "Chowk", "Naini", "George Town"],
    "Varanasi": ["Assi Ghat Road", "Lanka", "Sigra", "Bhelupur"],
    "Jhansi": ["Fort Road", "Civil Lines", "Sipri Bazar", "Elite"],
    "Dehradun": ["Rajpur Road", "Clock Tower", "Prem Nagar", "Ballupur"],
    "Bengaluru": ["Koramangala", "Indiranagar", "Whitefield", "Jayanagar"],
    "Hyderabad": ["Banjara Hills", "Hitech City", "Gachibowli", "Secunderabad"],
    "Chennai": ["T Nagar", "Adyar", "Anna Nagar", "Velachery"],
    "Kolkata": ["Park Street", "Salt Lake", "Ballygunge", "Howrah"],
}

COMING_SOON_CITIES = [
    {
        "name": "Bengaluru Home Kitchen",
        "address_line": "Koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560034",
        "latitude": 12.9352,
        "longitude": 77.6245,
    },
    {
        "name": "Hyderabad Cloud Kitchen",
        "address_line": "Hitech City",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500081",
        "latitude": 17.4435,
        "longitude": 78.3772,
    },
    {
        "name": "Chennai Home Thali",
        "address_line": "T Nagar",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode": "600017",
        "latitude": 13.0418,
        "longitude": 80.2341,
    },
    {
        "name": "Kolkata Home Kitchen",
        "address_line": "Park Street",
        "city": "Kolkata",
        "state": "West Bengal",
        "pincode": "700016",
        "latitude": 22.5488,
        "longitude": 88.3631,
    },
]

# Presence order: Pune first so kitchen #1 still mints CKPNQ.
_PRESENCE_CITY_ORDER = (
    "Pune",
    "Mumbai",
    "Delhi",
    "Gurugram",
    "Noida",
    "Lucknow",
    "Kanpur",
    "Prayagraj",
    "Varanasi",
    "Jhansi",
    "Dehradun",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Kolkata",
)


def _seed_city_row(name: str, state: str, pincode: str, latitude: float, longitude: float) -> dict:
    return {
        "name": name,
        "state": state,
        "pincode": str(pincode),
        "latitude": latitude,
        "longitude": longitude,
        "areas": CITY_AREAS[name],
    }


def _build_seed_cities() -> list[dict]:
    by_name = {
        "Pune": _seed_city_row(
            DEMO_KITCHEN["city"],
            DEMO_KITCHEN["state"],
            DEMO_KITCHEN["pincode"],
            DEMO_KITCHEN["latitude"],
            DEMO_KITCHEN["longitude"],
        )
    }
    for row in [*DEMO_KITCHENS_CITIES, *COMING_SOON_CITIES]:
        by_name[row["city"]] = _seed_city_row(
            row["city"],
            row["state"],
            row["pincode"],
            row["latitude"],
            row["longitude"],
        )
    return [by_name[name] for name in _PRESENCE_CITY_ORDER]


SEED_CITIES: list[dict] = _build_seed_cities()

# Reserved 62xx block — weekly QA uses 7/8, demo owners/customers use 9x.
CITY_CUSTOMER_PHONE_PREFIX = "62"

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
    {
        "phone": o["phone"],
        "phone_e164": o["phone_e164"],
        "name": o["name"],
        "email": o["email"],
    }
    for o in DEMO_OWNERS_EXTRA
] + [
    {"phone": "9876543214", "phone_e164": "+919876543214", "name": "Vikram Patil", "email": "vikram@kitchcu.dev"},
    {"phone": "9876543215", "phone_e164": "+919876543215", "name": "Ananya Joshi", "email": "ananya@kitchcu.dev"},
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


# Explicit dish → local food asset. This is the source of truth: keyword matching and
# index round-robin both produced contradictory heroes (Bhel Puri showing grilled meat,
# Aloo Gobi showing an unrelated plate).
#
# Two rules the seed data must respect:
#   1. Never put a venue photo (kitchen/service/restaurant/dining) on a dish.
#   2. When no asset honestly represents the dish — every drink, we have no beverage
#      shot — seed no hero at all. A missing photo beats a misleading one.
DISH_MEDIA_BY_NAME: dict[str, str | None] = {
    # Veg mains
    "Paneer Tikka": "skewers.jpg",
    "Palak Paneer": "bowls.jpg",
    "Dal Tadka": "bowls.jpg",
    "Aloo Gobi": "bowls.jpg",
    "Bhindi Masala": "bowls.jpg",
    "Chole Bhature": "bowls.jpg",
    "Masala Dosa": "dosa.jpg",
    "Idli Sambar (4 pc)": "dosa.jpg",
    "Veg Biryani": "biryani.jpg",
    "Methi Thepla (3 pc)": "dosa.jpg",
    "Jeera Rice": "rice.jpg",
    "Garlic Naan (2 pc)": "dosa.jpg",
    "Paneer Butter Masala": "bowls.jpg",
    "Sabudana Khichdi": "bowls.jpg",
    # Non-veg
    "Chicken Biryani": "biryani.jpg",
    "Butter Chicken": "bowls.jpg",
    "Chicken Tikka": "skewers.jpg",
    "Mutton Curry": "bowls.jpg",
    "Fish Fry": "bbq.jpg",
    "Egg Curry": "bowls.jpg",
    "Chicken Keema Pav": "burger.jpg",
    "Tandoori Roti (2 pc)": "dosa.jpg",
    "Chicken Wings (6 pc)": "bbq.jpg",
    # Vegan
    "Tofu Stir Fry": "salad.jpg",
    "Vegan Buddha Bowl": "salad.jpg",
    "Coconut Curry (Vegan)": "bowls.jpg",
    # Drinks — no beverage asset exists, so no hero.
    "Mango Lassi": None,
    "Sweet Lassi": None,
    "Fresh Lime Soda": None,
    "Buttermilk (Chaas)": None,
    "Masala Chai": None,
    "Filter Coffee": None,
    "Hot Chocolate": None,
    "Cold Coffee": None,
    "Iced Tea": None,
    "Watermelon Juice": None,
    # Snacks
    "Pav Bhaji": "bowls.jpg",
    "Vada Pav (2 pc)": "burger.jpg",
    "Samosa (2 pc)": "samosa.jpg",
    "Bhel Puri": "samosa.jpg",
    "French Fries": "burger.jpg",
    "Misal Pav": "bowls.jpg",
    # Desserts
    "Gulab Jamun": "dessert.jpg",
    "Kheer": "dessert.jpg",
    "Rasmalai": "dessert.jpg",
    "Chocolate Brownie": "dessert.jpg",
    # Combos
    "Veg Thali Combo": "rice.jpg",
    "Non-Veg Thali": "rice.jpg",
    "Office Lunch Box": "rice.jpg",
    "Family Feast (4 pax)": "biryani.jpg",
    # Seasonal
    "Monsoon Pakora Platter": "samosa.jpg",
    "Winter Gajar Halwa": "dessert.jpg",
    "Summer Mango Special": "dessert.jpg",
    "Festive Sweets Box": "dessert.jpg",
    "Sunday Brunch Combo": "rice.jpg",
}


def _media_for_dish(name: str) -> str | None:
    """Return the hero URL for a seeded dish, or None when no honest asset exists."""
    asset = DISH_MEDIA_BY_NAME.get(name.strip())
    return food_media(asset) if asset else None


def dish_with_media(dish: dict) -> dict:
    media_url = dish.get("media_url") or _media_for_dish(str(dish.get("name", "")))
    return {
        **dish,
        "description": f"Home-style {dish['name']} — live-capture, made fresh to order.",
        "ingredients_description": "Fresh local ingredients, house spices",
        "media_url": media_url,
    }


def enriched_dishes() -> list[dict]:
    return [dish_with_media(d) for d in BULK_DISHES]


def kitchen_location(index: int, city: dict) -> dict:
    """Spread kitchens around the given city centre for nearby search."""
    areas = city["areas"]
    area = areas[index % len(areas)]
    angle = random.uniform(0, 2 * math.pi)
    km = 0.4 + (index % 12) * 0.9 + random.uniform(0, 0.5)
    lat0 = float(city["latitude"])
    lng0 = float(city["longitude"])
    lat = lat0 + (km / 111.0) * math.cos(angle)
    lng = lng0 + (km / (111.0 * math.cos(math.radians(lat0)))) * math.sin(angle)
    suffix = KITCHEN_SUFFIXES[index % len(KITCHEN_SUFFIXES)]
    name = f"{area} {suffix}"
    pin = int(str(city["pincode"])) + (index % 9)
    return {
        "name": name,
        "description": f"{name} — cloud kitchen serving {city['name']} with live-capture menu.",
        "address_line": f"{area}, {city['name']}",
        "city": city["name"],
        "state": city["state"],
        "pincode": str(pin),
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
    }


def _city_for_index(index: int) -> dict:
    return SEED_CITIES[index % len(SEED_CITIES)]


def bulk_kitchen_specs(count: int) -> list[dict]:
    """Round-robin across every presence city. Count=1 stays Pune (dry-run)."""
    specs: list[dict] = []
    used_names: set[str] = set()
    for i in range(count):
        city = _city_for_index(i)
        spec = kitchen_location(i, city)
        base = spec["name"]
        n = 1
        while spec["name"] in used_names:
            spec = kitchen_location(i + n * 7, city)
            spec["name"] = f"{base} #{n + 1}"
            n += 1
        used_names.add(spec["name"])
        specs.append(spec)
    return specs


def owner_kitchen_specs(owner_index: int, per_owner: int, owner_name: str = "") -> list[dict]:
    if owner_index == 0:
        return bulk_kitchen_specs(per_owner)
    specs: list[dict] = []
    used: set[str] = set()
    start = owner_index * per_owner + 100
    for j in range(per_owner):
        city = _city_for_index(start + j)
        spec = kitchen_location(start + j, city)
        if owner_name:
            area = city["areas"][(start + j) % len(city["areas"])]
            spec["name"] = f"{owner_name.split()[0]}'s {area} Kitchen"
        while spec["name"] in used:
            spec["name"] = f"{spec['name']} #{j + 2}"
        used.add(spec["name"])
        specs.append(spec)
    return specs


def city_customer_phone(city_index: int, slot: int) -> str:
    """Deterministic 10-digit India mobile: 62{city:02d}{slot:06d}."""
    if not 1 <= city_index <= 99:
        raise ValueError(f"city_index out of range: {city_index}")
    if not 1 <= slot <= 999_999:
        raise ValueError(f"slot out of range: {slot}")
    phone = f"{CITY_CUSTOMER_PHONE_PREFIX}{city_index:02d}{slot:06d}"
    if len(phone) != 10:
        raise ValueError(f"Generated phone is not 10 digits: {phone}")
    return phone


def city_customer_specs(per_city: int = 3, *, cities: list[dict] | None = None) -> list[dict]:
    """Registered WhatsApp diners — one small pool per presence city."""
    if per_city < 0:
        raise ValueError("per_city must be >= 0")
    cities = cities if cities is not None else SEED_CITIES
    person_names = [n for n in CUSTOMER_NAMES if n[0].isalpha() and " " in n and not n.startswith(("Walk-in", "Office", "Building", "Regular", "Guest"))]
    specs: list[dict] = []
    for city_index, city in enumerate(cities, start=1):
        for slot in range(1, per_city + 1):
            phone = city_customer_phone(city_index, slot)
            name = person_names[(city_index + slot) % len(person_names)]
            area = city["areas"][(slot - 1) % len(city["areas"])]
            specs.append(
                {
                    "phone": phone,
                    "phone_e164": f"+91{phone}",
                    "name": name,
                    "city": city["name"],
                    "state": city["state"],
                    "pincode": str(city["pincode"]),
                    "address_line": f"{area}, {city['name']}",
                    "latitude": round(float(city["latitude"]) + slot * 0.003, 6),
                    "longitude": round(float(city["longitude"]) + slot * 0.003, 6),
                    "note": f"Bulk diner · {city['name']}",
                }
            )
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
    return CAPTURED_AT or datetime.now(timezone.utc).isoformat()
