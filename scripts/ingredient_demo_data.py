"""Ingredient pantry + dish recipes for demo/bulk seed (F19)."""

from __future__ import annotations

from demo_data import unsplash

_SPICE = unsplash("photo-1596040033229-a0b710c43606", 600)
_PANEER = unsplash("photo-1563379927098-05c457674dd8", 600)
_RICE = unsplash("photo-1585937421612-70a008592f82", 600)

# Standard cloud-kitchen pantry (name -> unit, stock, threshold, optional photo)
DEMO_PANTRY: list[dict] = [
    {"name": "Garam Masala", "unit": "g", "current_stock": 500, "low_stock_threshold": 80, "photo_url": _SPICE},
    {"name": "Lal Mirch", "unit": "g", "current_stock": 400, "low_stock_threshold": 60, "photo_url": _SPICE},
    {"name": "Haldi", "unit": "g", "current_stock": 350, "low_stock_threshold": 50, "photo_url": _SPICE},
    {"name": "Paneer", "unit": "g", "current_stock": 2000, "low_stock_threshold": 400, "photo_url": _PANEER},
    {"name": "Chicken", "unit": "g", "current_stock": 3000, "low_stock_threshold": 600},
    {"name": "Basmati Rice", "unit": "g", "current_stock": 5000, "low_stock_threshold": 800, "photo_url": _RICE},
    {"name": "Yogurt", "unit": "g", "current_stock": 1500, "low_stock_threshold": 300},
    {"name": "Butter", "unit": "g", "current_stock": 800, "low_stock_threshold": 150},
    {"name": "Tomato", "unit": "g", "current_stock": 2000, "low_stock_threshold": 400},
    {"name": "Potato", "unit": "g", "current_stock": 2500, "low_stock_threshold": 500},
    {"name": "Wheat Flour", "unit": "g", "current_stock": 4000, "low_stock_threshold": 700},
    {"name": "Mango Pulp", "unit": "ml", "current_stock": 1200, "low_stock_threshold": 200},
    {"name": "Khoya", "unit": "g", "current_stock": 600, "low_stock_threshold": 120},
    {"name": "Mixed Vegetables", "unit": "g", "current_stock": 1800, "low_stock_threshold": 350},
    {"name": "Pav Bread", "unit": "pcs", "current_stock": 120, "low_stock_threshold": 24},
]

# Per-dish recipe: dish name -> list of (ingredient name, qty, unit, optional line photo)
DISH_RECIPES: dict[str, list[tuple[str, float, str] | tuple[str, float, str, str]]] = {
    "Paneer Tikka": [
        ("Paneer", 150, "g", _PANEER),
        ("Garam Masala", 8, "g"),
        ("Lal Mirch", 4, "g"),
        ("Yogurt", 40, "g"),
    ],
    "Chicken Biryani": [
        ("Chicken", 200, "g"),
        ("Basmati Rice", 180, "g", _RICE),
        ("Garam Masala", 10, "g"),
        ("Haldi", 3, "g"),
    ],
    "Masala Dosa": [
        ("Potato", 120, "g"),
        ("Garam Masala", 5, "g"),
        ("Haldi", 2, "g"),
    ],
    "Butter Chicken": [
        ("Chicken", 180, "g"),
        ("Tomato", 100, "g"),
        ("Butter", 30, "g"),
        ("Garam Masala", 6, "g"),
    ],
    "Mango Lassi": [
        ("Yogurt", 200, "ml"),
        ("Mango Pulp", 80, "ml"),
    ],
    "Gulab Jamun": [
        ("Khoya", 80, "g"),
        ("Wheat Flour", 15, "g"),
        ("Garam Masala", 1, "g"),
    ],
    "Veg Thali Combo": [
        ("Mixed Vegetables", 200, "g"),
        ("Wheat Flour", 100, "g"),
        ("Basmati Rice", 150, "g"),
        ("Haldi", 4, "g"),
    ],
    "Pav Bhaji": [
        ("Mixed Vegetables", 250, "g"),
        ("Pav Bread", 2, "pcs"),
        ("Butter", 20, "g"),
        ("Lal Mirch", 5, "g"),
    ],
}

# Per-dish prep steps for seed scripts
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
}
