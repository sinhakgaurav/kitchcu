"""Ingredient pantry + dish recipes for demo/bulk seed (F19).

Every pantry SKU carries a pack photo, brand, and retail pack size in the same
unit as `current_stock`. Dish recipes deduct from that stock (order ready /
prep prepared). Pack photos are pantry reference — not dish heroes.
"""

from __future__ import annotations

from demo_data import unsplash

_SPICE = unsplash("photo-1596040033229-a0b710c43606", 600)
_CHILLI = unsplash("photo-1583119022894-919a68a3d0e3", 600)
_TURMERIC = unsplash("photo-1615485290382-441e4d049cb5", 600)
_PANEER = unsplash("photo-1563379927098-05c457674dd8", 600)
_CHICKEN = unsplash("photo-1604503468506-a8da13d82791", 600)
_RICE = unsplash("photo-1585937421612-70a008592f82", 600)
_YOGURT = unsplash("photo-1488477181946-6428a0291777", 600)
_BUTTER = unsplash("photo-1589985270826-4dfd1f4fdd88", 600)
_TOMATO = unsplash("photo-1546470427-227c7369a62d", 600)
_POTATO = unsplash("photo-1518977676601-b53f82aba655", 600)
_FLOUR = unsplash("photo-1574323347407-f5e1ad6d020b", 600)
_MANGO = unsplash("photo-1553279768-865429fa0078", 600)
_KHOYA = unsplash("photo-1627308595229-7830a5c91f9f", 600)
_VEG = unsplash("photo-1540420773420-3366772f4999", 600)
_BREAD = unsplash("photo-1509440159596-0249088772ff", 600)
_SPINACH = unsplash("photo-1576045057995-568f588f82fb", 600)
_CHICKPEA = unsplash("photo-1515543237357-8b73d6e6e0d8", 600)
_MUTTON = unsplash("photo-1603360946369-dc9bb6870878", 600)
_APPLE = unsplash("photo-1560806887-1e4cd0b6cbd6", 600)
_TOFU = unsplash("photo-1546069901-ba9599a7e63c", 600)
_EGGS = unsplash("photo-1498654071236-c6dd2dac81fc", 600)
_COFFEE = unsplash("photo-1511920170031-708987893958", 600)
_TEA = unsplash("photo-1556679343-c7306c1976bc", 600)
_MILK = unsplash("photo-1550583724-b2692b85b150", 600)
_ONION = unsplash("photo-1508747703725-719777637510", 600)
_CAPSICUM = unsplash("photo-1563565375-f3fdfdbefa83", 600)
_LENTIL = unsplash("photo-1596797038530-2c107229654b", 600)
_CAULI = unsplash("photo-1568584711075-3d0171f6661d", 600)
_CINNAMON = unsplash("photo-1556909114-f6e7ad7d3136", 600)
_SUGAR = unsplash("photo-1558642452-9d2a7deb7f62", 600)
_RICE_FLOUR = unsplash("photo-1586201375761-83865001e31c", 600)


def _sku(
    name: str,
    unit: str,
    current_stock: float,
    low_stock_threshold: float,
    *,
    brand: str,
    pack_size: float,
    pack_label: str,
    photo_url: str,
    kcal_per_100: float,
) -> dict:
    return {
        "name": name,
        "unit": unit,
        "current_stock": current_stock,
        "low_stock_threshold": low_stock_threshold,
        "brand": brand,
        "pack_size": pack_size,
        "pack_label": pack_label,
        "photo_url": photo_url,
        "kcal_per_100": kcal_per_100,
    }


DEMO_PANTRY: list[dict] = [
    _sku("Garam Masala", "g", 500, 80, brand="Everest", pack_size=100, pack_label="100 g carton", photo_url=_SPICE, kcal_per_100=379),
    _sku("Lal Mirch", "g", 400, 60, brand="MDH", pack_size=100, pack_label="100 g carton", photo_url=_CHILLI, kcal_per_100=282),
    _sku("Haldi", "g", 350, 50, brand="Everest", pack_size=100, pack_label="100 g carton", photo_url=_TURMERIC, kcal_per_100=354),
    _sku("Paneer", "g", 2000, 400, brand="Amul", pack_size=200, pack_label="200 g pouch", photo_url=_PANEER, kcal_per_100=265),
    _sku("Chicken", "g", 3000, 600, brand="Suguna", pack_size=1000, pack_label="1000 g tray", photo_url=_CHICKEN, kcal_per_100=165),
    _sku("Basmati Rice", "g", 5000, 800, brand="India Gate", pack_size=1000, pack_label="1000 g pack", photo_url=_RICE, kcal_per_100=130),
    _sku("Yogurt", "g", 1600, 400, brand="Amul", pack_size=400, pack_label="400 g cup", photo_url=_YOGURT, kcal_per_100=61),
    _sku("Butter", "g", 800, 150, brand="Amul", pack_size=100, pack_label="100 g brick", photo_url=_BUTTER, kcal_per_100=717),
    _sku("Tomato", "g", 2000, 400, brand="Farm Fresh", pack_size=500, pack_label="500 g crate", photo_url=_TOMATO, kcal_per_100=18),
    _sku("Potato", "g", 2500, 500, brand="Farm Fresh", pack_size=1000, pack_label="1000 g bag", photo_url=_POTATO, kcal_per_100=77),
    _sku("Wheat Flour", "g", 4000, 700, brand="Aashirvaad", pack_size=1000, pack_label="1000 g pack", photo_url=_FLOUR, kcal_per_100=364),
    _sku("Mango Pulp", "ml", 1700, 425, brand="Ratna", pack_size=850, pack_label="850 ml tin", photo_url=_MANGO, kcal_per_100=89),
    _sku("Khoya", "g", 600, 120, brand="Amul", pack_size=200, pack_label="200 g block", photo_url=_KHOYA, kcal_per_100=421),
    _sku("Mixed Vegetables", "g", 2000, 400, brand="Farm Fresh", pack_size=500, pack_label="500 g pack", photo_url=_VEG, kcal_per_100=35),
    _sku("Pav Bread", "pcs", 120, 24, brand="Wibs", pack_size=6, pack_label="6 pcs pack", photo_url=_BREAD, kcal_per_100=150),
    _sku("Spinach", "g", 1500, 250, brand="Farm Fresh", pack_size=250, pack_label="250 g bunch", photo_url=_SPINACH, kcal_per_100=23),
    _sku("Chickpeas", "g", 2500, 500, brand="Tata Sampann", pack_size=500, pack_label="500 g pack", photo_url=_CHICKPEA, kcal_per_100=164),
    _sku("Mutton", "g", 2500, 500, brand="Local Fresh", pack_size=1000, pack_label="1000 g tray", photo_url=_MUTTON, kcal_per_100=250),
    _sku("Apple", "g", 2000, 400, brand="Farm Fresh", pack_size=1000, pack_label="1000 g bag", photo_url=_APPLE, kcal_per_100=52),
    _sku("Tofu", "g", 1200, 200, brand="Morinaga", pack_size=200, pack_label="200 g block", photo_url=_TOFU, kcal_per_100=76),
    _sku("Eggs", "pcs", 120, 24, brand="Country Eggs", pack_size=12, pack_label="12 pcs tray", photo_url=_EGGS, kcal_per_100=78),
    _sku("Coffee Powder", "g", 400, 50, brand="Bru", pack_size=50, pack_label="50 g pouch", photo_url=_COFFEE, kcal_per_100=2),
    _sku("Tea Leaves", "g", 500, 80, brand="Tata Tea", pack_size=100, pack_label="100 g pack", photo_url=_TEA, kcal_per_100=1),
    _sku("Milk", "ml", 5000, 1000, brand="Mother Dairy", pack_size=500, pack_label="500 ml pouch", photo_url=_MILK, kcal_per_100=67),
    _sku("Onion", "g", 3000, 500, brand="Farm Fresh", pack_size=1000, pack_label="1000 g bag", photo_url=_ONION, kcal_per_100=40),
    _sku("Capsicum", "g", 1500, 300, brand="Farm Fresh", pack_size=500, pack_label="500 g pack", photo_url=_CAPSICUM, kcal_per_100=31),
    _sku("Lentils", "g", 2500, 500, brand="Tata Sampann", pack_size=500, pack_label="500 g pack", photo_url=_LENTIL, kcal_per_100=116),
    _sku("Cauliflower", "g", 1500, 300, brand="Farm Fresh", pack_size=500, pack_label="500 g head", photo_url=_CAULI, kcal_per_100=25),
    _sku("Cinnamon", "g", 200, 40, brand="Everest", pack_size=50, pack_label="50 g carton", photo_url=_CINNAMON, kcal_per_100=247),
    _sku("Sugar", "g", 4000, 700, brand="Madhur", pack_size=1000, pack_label="1000 g pack", photo_url=_SUGAR, kcal_per_100=387),
    _sku("Rice Flour", "g", 2500, 400, brand="Aashirvaad", pack_size=500, pack_label="500 g pack", photo_url=_RICE_FLOUR, kcal_per_100=366),
]

# Per-dish recipe: dish name -> list of (ingredient name, qty, unit, optional line photo).
# Quantity is per portion and deducts from pantry current_stock in the same unit.
DISH_RECIPES: dict[str, list[tuple[str, float, str] | tuple[str, float, str, str]]] = {
    "Chicken Biryani": [
        ("Chicken", 200, "g", _CHICKEN),
        ("Basmati Rice", 180, "g", _RICE),
        ("Garam Masala", 10, "g"),
        ("Haldi", 3, "g"),
        ("Yogurt", 40, "g"),
        ("Onion", 50, "g"),
    ],
    "Masala Dosa": [
        ("Potato", 120, "g", _POTATO),
        ("Rice Flour", 80, "g"),
        ("Garam Masala", 5, "g"),
        ("Haldi", 2, "g"),
    ],
    "Samosa (2 pc)": [
        ("Potato", 120, "g"),
        ("Wheat Flour", 80, "g"),
        ("Garam Masala", 5, "g"),
    ],
    "Chicken Fried Rice": [
        ("Chicken", 150, "g"),
        ("Basmati Rice", 180, "g", _RICE),
        ("Mixed Vegetables", 80, "g"),
        ("Haldi", 2, "g"),
        ("Eggs", 1, "pcs"),
    ],
    "Mixed Grill Platter": [
        ("Chicken", 250, "g"),
        ("Yogurt", 50, "g"),
        ("Garam Masala", 10, "g"),
        ("Lal Mirch", 5, "g"),
        ("Capsicum", 40, "g"),
    ],
    "BBQ Chicken Pizza": [
        ("Chicken", 120, "g"),
        ("Wheat Flour", 150, "g"),
        ("Tomato", 90, "g"),
        ("Capsicum", 30, "g"),
        ("Butter", 15, "g"),
    ],
    "Tomato Basil Spaghetti": [
        ("Tomato", 200, "g"),
        ("Butter", 20, "g"),
        ("Lal Mirch", 2, "g"),
        ("Onion", 30, "g"),
    ],
    "Vegan Buddha Bowl": [
        ("Mixed Vegetables", 200, "g"),
        ("Potato", 100, "g"),
        ("Chickpeas", 80, "g"),
    ],
    "Egg & Tofu Protein Bowl": [
        ("Eggs", 2, "pcs", _EGGS),
        ("Tofu", 120, "g", _TOFU),
        ("Mixed Vegetables", 100, "g"),
    ],
    "Smoky BBQ Ribs": [
        ("Chicken", 300, "g"),
        ("Potato", 150, "g"),
        ("Lal Mirch", 8, "g"),
        ("Butter", 20, "g"),
    ],
    "Apple Cinnamon Turnovers": [
        ("Apple", 120, "g", _APPLE),
        ("Wheat Flour", 80, "g"),
        ("Cinnamon", 3, "g"),
        ("Butter", 25, "g"),
        ("Sugar", 20, "g"),
    ],
    "Paneer Tikka": [
        ("Paneer", 150, "g", _PANEER),
        ("Garam Masala", 8, "g"),
        ("Lal Mirch", 4, "g"),
        ("Yogurt", 40, "g"),
        ("Capsicum", 40, "g"),
    ],
    "Butter Chicken": [
        ("Chicken", 180, "g"),
        ("Tomato", 100, "g"),
        ("Butter", 30, "g"),
        ("Garam Masala", 6, "g"),
        ("Yogurt", 30, "g"),
    ],
    "Palak Paneer": [
        ("Spinach", 150, "g", _SPINACH),
        ("Paneer", 120, "g", _PANEER),
        ("Garam Masala", 6, "g"),
        ("Haldi", 2, "g"),
        ("Butter", 15, "g"),
    ],
    "Dal Tadka": [
        ("Lentils", 120, "g"),
        ("Haldi", 3, "g"),
        ("Garam Masala", 4, "g"),
        ("Butter", 15, "g"),
        ("Tomato", 40, "g"),
    ],
    "Aloo Gobi": [
        ("Potato", 100, "g"),
        ("Cauliflower", 120, "g"),
        ("Haldi", 3, "g"),
        ("Garam Masala", 5, "g"),
    ],
    "Chole Bhature": [
        ("Chickpeas", 150, "g"),
        ("Wheat Flour", 120, "g"),
        ("Garam Masala", 8, "g"),
        ("Tomato", 50, "g"),
    ],
    "Mutton Curry": [
        ("Mutton", 200, "g", _MUTTON),
        ("Yogurt", 50, "g"),
        ("Garam Masala", 10, "g"),
        ("Lal Mirch", 6, "g"),
        ("Tomato", 80, "g"),
    ],
    "Pav Bhaji": [
        ("Mixed Vegetables", 250, "g"),
        ("Pav Bread", 2, "pcs"),
        ("Butter", 20, "g"),
        ("Lal Mirch", 5, "g"),
        ("Potato", 80, "g"),
    ],
    "Veg Thali Combo": [
        ("Mixed Vegetables", 200, "g"),
        ("Wheat Flour", 100, "g"),
        ("Basmati Rice", 150, "g"),
        ("Haldi", 4, "g"),
        ("Lentils", 80, "g"),
    ],
    "Gulab Jamun": [
        ("Khoya", 80, "g"),
        ("Wheat Flour", 15, "g"),
        ("Sugar", 40, "g"),
    ],
    "Mango Lassi": [
        ("Yogurt", 200, "g"),
        ("Mango Pulp", 80, "ml"),
        ("Sugar", 15, "g"),
        ("Milk", 50, "ml"),
    ],
    "Masala Chai": [
        ("Tea Leaves", 5, "g", _TEA),
        ("Milk", 150, "ml"),
        ("Sugar", 10, "g"),
        ("Garam Masala", 1, "g"),
    ],
    "Cold Coffee": [
        ("Coffee Powder", 8, "g", _COFFEE),
        ("Milk", 200, "ml"),
        ("Sugar", 15, "g"),
    ],
}


def infer_recipe(dish_name: str, pantry_names: set[str]) -> list[tuple[str, float, str]]:
    """Keyword recipe for seeded dishes that are not in DISH_RECIPES.

    Only emits pantry SKUs so stock still deducts from branded packs.
    """
    n = dish_name.lower()
    picked: list[tuple[str, float, str]] = []

    def add(sku: str, qty: float, unit: str) -> None:
        if sku in pantry_names and all(row[0] != sku for row in picked):
            picked.append((sku, qty, unit))

    if "paneer" in n:
        add("Paneer", 120, "g")
        add("Garam Masala", 6, "g")
        add("Yogurt", 30, "g")
    if "palak" in n or "spinach" in n:
        add("Spinach", 150, "g")
        add("Paneer", 80, "g")
    if "chicken" in n:
        add("Chicken", 160, "g")
        add("Garam Masala", 6, "g")
    if "mutton" in n or "keema" in n:
        add("Mutton", 160, "g")
        add("Garam Masala", 8, "g")
    if "egg" in n:
        add("Eggs", 2, "pcs")
    if "tofu" in n:
        add("Tofu", 120, "g")
    if "chole" in n or "chana" in n:
        add("Chickpeas", 140, "g")
    if "dal" in n:
        add("Lentils", 120, "g")
        add("Haldi", 3, "g")
    if "gobi" in n:
        add("Cauliflower", 120, "g")
        add("Potato", 80, "g")
    if "biryani" in n or "rice" in n or "jeera" in n:
        add("Basmati Rice", 160, "g")
    if "pav" in n or "vada" in n or "misal" in n:
        add("Pav Bread", 2, "pcs")
        add("Potato", 80, "g")
        add("Butter", 15, "g")
    if "dosa" in n or "idli" in n:
        add("Rice Flour", 80, "g")
        add("Potato", 80, "g")
    if "roti" in n or "naan" in n or "thepla" in n:
        add("Wheat Flour", 80, "g")
    if "lassi" in n or "chaas" in n or "buttermilk" in n:
        add("Yogurt", 180, "g")
        add("Milk", 50, "ml")
        add("Sugar", 10, "g")
    if "mango" in n:
        add("Mango Pulp", 80, "ml")
    if "chai" in n or "tea" in n:
        add("Tea Leaves", 5, "g")
        add("Milk", 150, "ml")
        add("Sugar", 10, "g")
    if "coffee" in n or "hot chocolate" in n:
        add("Coffee Powder", 8, "g")
        add("Milk", 180, "ml")
        add("Sugar", 12, "g")
    if "fries" in n or "aloo" in n or "samosa" in n or "pakora" in n or "bhel" in n:
        add("Potato", 120, "g")
        add("Garam Masala", 4, "g")
    if "thali" in n or "feast" in n or "lunch" in n or "brunch" in n or "combo" in n or "box" in n:
        add("Mixed Vegetables", 180, "g")
        add("Basmati Rice", 120, "g")
        add("Wheat Flour", 80, "g")
    if any(w in n for w in ("jamun", "kheer", "halwa", "rasmalai", "brownie", "sweet")):
        add("Sugar", 40, "g")
        add("Khoya", 40, "g")
        add("Milk", 80, "ml")
    if "juice" in n or "soda" in n or "watermelon" in n:
        add("Mango Pulp", 60, "ml")
        add("Sugar", 10, "g")
    if "curry" in n or "masala" in n:
        add("Tomato", 80, "g")
        add("Onion", 50, "g")
        add("Garam Masala", 6, "g")

    if not picked:
        add("Mixed Vegetables", 120, "g")
        add("Garam Masala", 4, "g")
        add("Onion", 40, "g")
    return picked

DISH_PREP_STEPS: dict[str, list[dict]] = {
    "Paneer Tikka": [
        {
            "step_order": 1,
            "title": "Marinate paneer",
            "body_html": "<p>Coat paneer cubes with yogurt, garam masala, and lal mirch. Rest <strong>20 minutes</strong>.</p>",
            "photo_url": _PANEER,
            "duration_min": 20,
        },
        {
            "step_order": 2,
            "title": "Char-grill",
            "body_html": "<p>Grill on medium heat until edges char — quality-first, no rushing.</p>",
            "duration_min": 10,
        },
    ],
    "Chicken Biryani": [
        {
            "step_order": 1,
            "title": "Par-cook rice",
            "body_html": "<p>Boil basmati to 70% doneness with whole spices.</p>",
            "duration_min": 12,
        },
        {
            "step_order": 2,
            "title": "Layer & dum",
            "body_html": "<p>Layer chicken masala and rice; seal and cook on low <strong>25 min</strong>.</p>",
            "photo_url": _RICE,
            "duration_min": 25,
        },
    ],
    "Palak Paneer": [
        {
            "step_order": 1,
            "title": "Blanch spinach",
            "body_html": "<p>Blanch spinach, shock in cold water, and blend to a smooth puree.</p>",
            "photo_url": _SPINACH,
            "duration_min": 8,
        },
        {
            "step_order": 2,
            "title": "Finish with paneer",
            "body_html": "<p>Simmer puree with garam masala; fold in paneer cubes and a knob of butter.</p>",
            "photo_url": _PANEER,
            "duration_min": 12,
        },
    ],
}
