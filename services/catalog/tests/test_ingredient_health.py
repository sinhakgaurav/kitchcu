"""P50 — ingredient health scores from F19 recipes."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.ingredient_health import (
    aggregate_order_health,
    health_label,
    lookup_health_profile,
    normalize_ingredient_name,
    score_ingredient_lines,
)
from tests.conftest import build_dish_payload


def test_normalize_and_alias_lookup():
    assert normalize_ingredient_name("  Garam  Masala ") == "garam masala"
    assert lookup_health_profile("Haldi").name == "Haldi"
    assert lookup_health_profile("turmeric").name == "Haldi"
    assert lookup_health_profile("Amul Paneer").name == "Paneer"
    assert lookup_health_profile("unknown starch") is None


def test_score_weights_main_ingredient_over_pinch_of_spice():
    light = score_ingredient_lines(
        [
            ("Spinach", 150, "g"),
            ("Paneer", 40, "g"),
            ("Haldi", 2, "g"),
        ]
    )
    rich = score_ingredient_lines(
        [
            ("Butter", 80, "g"),
            ("Sugar", 40, "g"),
            ("Khoya", 30, "g"),
        ]
    )
    assert light.score is not None and rich.score is not None
    assert light.score > rich.score
    assert light.label == "Produce-forward" or light.score >= 65
    names = {i.name for i in light.ingredients}
    assert "Spinach" in names
    assert all(i.benefits and i.disadvantages for i in light.ingredients)


def test_unmapped_recipe_has_null_score():
    snap = score_ingredient_lines([("Mystery Powder", 10, "g")])
    assert snap.score is None
    assert snap.label == health_label(None)
    assert snap.mapped == 0
    assert snap.total == 1


def test_aggregate_order_health_quantity_weighted():
    a = score_ingredient_lines([("Spinach", 150, "g")])
    b = score_ingredient_lines([("Sugar", 40, "g")])
    overall = aggregate_order_health([(a, 3), (b, 1)])
    assert overall.score is not None
    assert overall.score > b.score


@pytest.mark.asyncio
async def test_menu_includes_health_from_recipe(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Spinach", "unit": "g", "current_stock": 500, "low_stock_threshold": 50},
        headers=headers,
    )
    assert ing.status_code == 201, ing.text
    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=dish_payload,
        headers=headers,
    )
    dish_id = dish.json()["id"]
    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={"lines": [{"ingredient_id": ing.json()["id"], "quantity": 120, "unit": "g"}]},
        headers=headers,
    )
    assert recipe.status_code == 200, recipe.text

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert menu.status_code == 200, menu.text
    row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
    assert row["health"]["score"] is not None
    assert row["health"]["score"] >= 80
    assert row["health"]["ingredients"][0]["name"] == "Spinach"
    assert "benefits" in row["health"]["ingredients"][0]
    assert "current_stock" not in row["health"]["ingredients"][0]


@pytest.mark.asyncio
async def test_dishes_health_batch_and_tenant_isolation(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Butter", "unit": "g", "current_stock": 200, "low_stock_threshold": 20},
        headers=headers,
    )
    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json={**dish_payload, "name": "Health Butter Dish"},
        headers=headers,
    )
    dish_id = dish.json()["id"]
    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={"lines": [{"ingredient_id": ing.json()["id"], "quantity": 25, "unit": "g"}]},
        headers=headers,
    )

    missing = uuid.uuid4()
    batch = await client.get(f"/api/v1/dishes/health?ids={dish_id},{missing}")
    assert batch.status_code == 200, batch.text
    body = batch.json()
    assert body["total"] == 1
    assert body["dishes"][0]["dish_id"] == dish_id
    assert body["dishes"][0]["score"] is not None
    assert "current_stock" not in batch.text

    empty = await client.get("/api/v1/dishes/health")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0


@pytest.mark.asyncio
async def test_ingredient_list_includes_health_profile(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Lentils", "unit": "g", "current_stock": 200, "low_stock_threshold": 20},
        headers=headers,
    )
    assert ing.status_code == 201
    assert ing.json()["health_score"] == 84
    assert "protein" in ing.json()["health_benefits"].lower() or "fibre" in ing.json()["health_benefits"].lower()
    listing = await client.get(f"/api/v1/kitchens/{kitchen_id}/ingredients", headers=headers)
    row = listing.json()["ingredients"][0]
    assert row["health_disadvantages"]
