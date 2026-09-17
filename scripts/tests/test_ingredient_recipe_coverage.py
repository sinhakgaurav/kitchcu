"""Every seeded dish must map to pantry SKUs with brand, pack, and photo."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from bulk_demo_data import BULK_DISHES  # noqa: E402
from demo_data import DEMO_DISHES  # noqa: E402
from ingredient_demo_data import DEMO_PANTRY, DISH_RECIPES  # noqa: E402


def _pantry_by_name() -> dict[str, dict]:
    return {item["name"]: item for item in DEMO_PANTRY}


def test_pantry_skus_carry_brand_pack_photo_and_stock() -> None:
    assert DEMO_PANTRY
    seen: set[str] = set()
    for item in DEMO_PANTRY:
        name = item["name"]
        assert name not in seen, name
        seen.add(name)
        assert item["unit"] in {"g", "ml", "pcs"}, name
        assert item["current_stock"] > 0, name
        assert item["low_stock_threshold"] >= 0, name
        assert item.get("brand"), name
        assert item.get("photo_url"), name
        pack_size = float(item["pack_size"])
        assert pack_size > 0, name
        assert item.get("pack_label"), name
        assert item["unit"] in item["pack_label"] or item["unit"] == "pcs"
        packs = item["current_stock"] / pack_size
        assert packs >= 1, f"{name} stock must cover at least one pack"
        kcal = item.get("kcal_per_100")
        assert kcal is not None, name
        assert 0 <= float(kcal) <= 2000, name


def test_every_bulk_and_demo_dish_has_a_recipe_on_pantry_stock() -> None:
    pantry = _pantry_by_name()
    required = {d["name"] for d in BULK_DISHES} | {d["name"] for d in DEMO_DISHES}
    missing_recipes = sorted(required - set(DISH_RECIPES))
    assert not missing_recipes, f"Dishes without recipes: {missing_recipes}"

    missing_skus: list[str] = []
    empty: list[str] = []
    for dish_name in sorted(required):
        lines = DISH_RECIPES[dish_name]
        if not lines:
            empty.append(dish_name)
            continue
        for entry in lines:
            sku = entry[0]
            qty = entry[1]
            unit = entry[2]
            if sku not in pantry:
                missing_skus.append(f"{dish_name} -> {sku}")
                continue
            assert qty > 0, f"{dish_name} {sku}"
            assert unit == pantry[sku]["unit"], f"{dish_name} {sku} unit {unit} != pantry"
    assert not empty, empty
    assert not missing_skus, missing_skus


def test_infer_recipe_only_uses_pantry_skus() -> None:
    pantry = {item["name"] for item in DEMO_PANTRY}
    from ingredient_demo_data import infer_recipe

    for name in ("Bhel Puri", "Office Lunch Box", "Filter Coffee", "Unknown Special"):
        lines = infer_recipe(name, pantry)
        assert lines, name
        for sku, qty, unit in lines:
            assert sku in pantry, f"{name} -> {sku}"
            assert qty > 0
            assert unit in {"g", "ml", "pcs"}
