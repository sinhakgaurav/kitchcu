"""P50 — ingredient health scores from F19 recipes. P53 — recipe kcal + healthy tag."""

from __future__ import annotations

import json
import os
import uuid

import psycopg2
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


@pytest.mark.asyncio
async def test_recipe_sums_ingredient_kcal_and_sets_healthy_tag(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    spinach = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Spinach",
            "unit": "g",
            "current_stock": 500,
            "low_stock_threshold": 50,
            "kcal_per_100": 23,
        },
        headers=headers,
    )
    dal = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Lentils",
            "unit": "g",
            "current_stock": 500,
            "low_stock_threshold": 50,
            "kcal_per_100": 116,
        },
        headers=headers,
    )
    assert spinach.status_code == 201, spinach.text
    assert spinach.json()["kcal_per_100"] == 23
    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json={
            **dish_payload,
            "name": "Palak Dal Bowl",
            "calories_description": "Light lunch bowl — dal + greens.",
        },
        headers=headers,
    )
    assert dish.status_code == 201, dish.text
    assert dish.json()["calories_description"] == "Light lunch bowl — dal + greens."
    dish_id = dish.json()["id"]

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:ingredient")

    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={
            "lines": [
                {"ingredient_id": spinach.json()["id"], "quantity": 150, "unit": "g"},
                {"ingredient_id": dal.json()["id"], "quantity": 80, "unit": "g"},
            ]
        },
        headers=headers,
    )
    assert recipe.status_code == 200, recipe.text
    body = recipe.json()
    assert body["calories_kcal"] == 127  # 34.5 + 92.8
    assert body["calories_incomplete"] is False
    assert body["healthy_tag"] is True
    assert body["lines"][0]["line_kcal"] is not None

    messages = await redis_client.xread({"ckac:catalog:ingredient": "0-0"}, count=40)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    recipe_events = [e for e in events if e["event_type"] == "ingredient.recipe.updated"]
    assert recipe_events
    assert recipe_events[-1]["payload"]["calories_kcal"] == 127
    assert recipe_events[-1]["payload"]["healthy_tag"] is True

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
    assert row["calories_description"].startswith("Light lunch")
    assert row["health"]["calories_kcal"] == 127
    assert row["health"]["healthy_tag"] is True
    assert row["health"]["calories_incomplete"] is False
    spinach_line = next(i for i in row["health"]["ingredients"] if i["name"] == "Spinach")
    assert spinach_line["kcal"] == 34.5


@pytest.mark.asyncio
async def test_incomplete_kcal_map_is_not_healthy(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    spinach = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Spinach", "unit": "g", "current_stock": 200, "kcal_per_100": 23},
        headers=headers,
    )
    mystery = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "House Mix", "unit": "g", "current_stock": 200},
        headers=headers,
    )
    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json={**dish_payload, "name": "Partial Kcal Plate"},
        headers=headers,
    )
    dish_id = dish.json()["id"]
    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={
            "lines": [
                {"ingredient_id": spinach.json()["id"], "quantity": 100, "unit": "g"},
                {"ingredient_id": mystery.json()["id"], "quantity": 40, "unit": "g"},
            ]
        },
        headers=headers,
    )
    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
    assert row["health"]["calories_kcal"] == 23
    assert row["health"]["calories_incomplete"] is True
    assert row["health"]["healthy_tag"] is False
    mystery_line = next(i for i in row["health"]["ingredients"] if i["name"] == "House Mix")
    assert mystery_line["kcal"] is None


@pytest.mark.asyncio
async def test_patch_ingredient_kcal_publishes_event(client: AsyncClient, kitchen_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:ingredient")

    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Onion", "unit": "g", "current_stock": 500},
        headers=headers,
    )
    assert created.status_code == 201
    ingredient_id = created.json()["id"]
    patched = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/ingredients/{ingredient_id}",
        json={"kcal_per_100": 40},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["kcal_per_100"] == 40

    messages = await redis_client.xread({"ckac:catalog:ingredient": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    updated = [e for e in events if e["event_type"] == "ingredient.updated"]
    assert updated
    assert updated[-1]["payload"]["kcal_per_100"] == 40


def _set_identity_flag(key: str, enabled: bool) -> None:
    conn = psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
            VALUES (%s, %s, 'kitchen', %s)
            ON CONFLICT (key) DO UPDATE SET enabled = EXCLUDED.enabled
            """,
            (key, enabled, key),
        )
    conn.close()


def _set_healthy_max_kcal(value: int) -> None:
    conn = psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.healthy_food_settings
              (id, healthy_max_kcal, healthy_min_score)
            VALUES (1, %s, 65)
            ON CONFLICT (id) DO UPDATE SET healthy_max_kcal = EXCLUDED.healthy_max_kcal
            """,
            (value,),
        )
    conn.close()


def _restore_calorie_controls() -> None:
    _set_identity_flag("dish_calories", True)
    _set_identity_flag("dish_healthy_tag", True)
    _set_healthy_max_kcal(500)


async def _palak_dal_dish(client: AsyncClient, kitchen_id, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    spinach = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Spinach",
            "unit": "g",
            "current_stock": 500,
            "kcal_per_100": 23,
        },
        headers=headers,
    )
    dal = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Lentils",
            "unit": "g",
            "current_stock": 500,
            "kcal_per_100": 116,
        },
        headers=headers,
    )
    assert spinach.status_code == 201, spinach.text
    assert dal.status_code == 201, dal.text
    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json={
            **dish_payload,
            "name": f"Palak Dal {uuid.uuid4().hex[:6]}",
            "calories_description": "Light lunch bowl — dal + greens.",
        },
        headers=headers,
    )
    assert dish.status_code == 201, dish.text
    dish_id = dish.json()["id"]
    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={
            "lines": [
                {"ingredient_id": spinach.json()["id"], "quantity": 150, "unit": "g"},
                {"ingredient_id": dal.json()["id"], "quantity": 80, "unit": "g"},
            ]
        },
        headers=headers,
    )
    assert recipe.status_code == 200, recipe.text
    return dish_id


@pytest.mark.asyncio
async def test_admin_kcal_cap_controls_public_healthy_tag(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    try:
        dish_id = await _palak_dal_dish(client, kitchen_id, token)
        menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
        row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
        assert row["health"]["calories_kcal"] == 127
        assert row["health"]["healthy_tag"] is True

        _set_healthy_max_kcal(100)
        menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
        row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
        assert row["health"]["calories_kcal"] == 127
        assert row["health"]["healthy_tag"] is False

        recipe = await client.get(
            f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recipe.status_code == 200, recipe.text
        assert recipe.json()["healthy_max_kcal"] == 100
        assert recipe.json()["healthy_tag"] is False
    finally:
        _restore_calorie_controls()


@pytest.mark.asyncio
async def test_dish_calories_flag_strips_public_kcal(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    try:
        dish_id = await _palak_dal_dish(client, kitchen_id, token)
        _set_identity_flag("dish_calories", False)
        menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
        row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
        assert row["health"]["calories_kcal"] is None
        assert row["health"]["healthy_tag"] is False
        spinach_line = next(i for i in row["health"]["ingredients"] if i["name"] == "Spinach")
        assert spinach_line["kcal"] is None

        recipe = await client.get(
            f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recipe.json()["calories_kcal"] == 127
    finally:
        _restore_calorie_controls()


@pytest.mark.asyncio
async def test_healthy_tag_flag_hides_badge_keeps_kcal(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    try:
        dish_id = await _palak_dal_dish(client, kitchen_id, token)
        _set_identity_flag("dish_healthy_tag", False)
        menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
        row = next(d for d in menu.json()["dishes"] if d["id"] == dish_id)
        assert row["health"]["calories_kcal"] == 127
        assert row["health"]["healthy_tag"] is False
    finally:
        _restore_calorie_controls()
