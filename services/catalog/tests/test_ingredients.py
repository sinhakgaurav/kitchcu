"""F19 ingredient balance mapper tests."""

import json
import os
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import build_dish_payload

INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "test-internal-key-for-pytest")


@pytest.mark.asyncio
async def test_create_ingredient(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Garam Masala",
            "unit": "g",
            "current_stock": 500,
            "low_stock_threshold": 50,
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Garam Masala"
    assert data["current_stock"] == 500
    assert data["is_low"] is False


@pytest.mark.asyncio
async def test_set_recipe_and_deduct_on_order(client: AsyncClient, kitchen_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:ingredient")

    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}

    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Lal Mirch", "unit": "g", "current_stock": 100, "low_stock_threshold": 20},
        headers=headers,
    )
    ingredient_id = ing.json()["id"]

    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=dish_payload,
        headers=headers,
    )
    dish_id = dish.json()["id"]

    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={"lines": [{"ingredient_id": ingredient_id, "quantity": 10, "unit": "g"}]},
        headers=headers,
    )
    assert recipe.status_code == 200
    assert len(recipe.json()["lines"]) == 1

    deduct = await client.post(
        f"/api/v1/internal/kitchens/{kitchen_id}/stock/deduct-order",
        json={
            "order_id": str(uuid.uuid4()),
            "items": [{"dish_id": dish_id, "quantity": 2}],
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert deduct.status_code == 200
    assert deduct.json()["deducted"][0]["deducted"] == 20

    listing = await client.get(f"/api/v1/kitchens/{kitchen_id}/ingredients", headers=headers)
    stock = next(i for i in listing.json()["ingredients"] if i["id"] == ingredient_id)
    assert stock["current_stock"] == 80

    messages = await redis_client.xread({"ckac:catalog:ingredient": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    assert any(e["event_type"] == "ingredient.stock.deducted" for e in events)


@pytest.mark.asyncio
async def test_low_stock_check(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}

    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Haldi", "unit": "g", "current_stock": 5, "low_stock_threshold": 10},
        headers=headers,
    )
    ingredient_id = ing.json()["id"]

    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish_id = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/dishes",
            json=dish_payload,
            headers=headers,
        )
    ).json()["id"]

    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={"lines": [{"ingredient_id": ingredient_id, "quantity": 8, "unit": "g"}]},
        headers=headers,
    )

    check = await client.post(
        f"/api/v1/internal/kitchens/{kitchen_id}/stock/low-stock-check",
        json={"items": [{"dish_id": dish_id, "quantity": 1}]},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert check.status_code == 200
    body = check.json()
    assert body["has_shortfall"] is True
    assert body["warnings"][0]["shortfall"] == 3


@pytest.mark.asyncio
async def test_manual_stock_adjust(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": "Paneer", "unit": "g", "current_stock": 200, "low_stock_threshold": 100},
        headers=headers,
    )
    ingredient_id = ing.json()["id"]

    adjusted = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients/{ingredient_id}/adjust-stock",
        json={"delta": -50, "reason": "Spoilage write-off"},
        headers=headers,
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["current_stock"] == 150


@pytest.mark.asyncio
async def test_recipe_prep_steps_and_photos(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}

    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Paneer",
            "unit": "g",
            "current_stock": 500,
            "low_stock_threshold": 50,
            "photo_url": "https://example.com/paneer.jpg",
        },
        headers=headers,
    )
    ingredient_id = ing.json()["id"]

    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish_id = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/dishes",
            json=dish_payload,
            headers=headers,
        )
    ).json()["id"]

    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={
            "lines": [
                {
                    "ingredient_id": ingredient_id,
                    "quantity": 150,
                    "unit": "g",
                    "photo_url": "https://example.com/paneer-cube.jpg",
                    "sort_order": 0,
                }
            ],
            "prep_steps": [
                {
                    "step_order": 1,
                    "title": "Marinate",
                    "body_html": "<p>Coat paneer with <strong>yogurt</strong> and spices.</p>",
                    "photo_url": "https://example.com/marinate.jpg",
                    "duration_min": 20,
                },
                {
                    "step_order": 2,
                    "title": "Grill",
                    "body_html": "<p>Grill on medium heat until charred.</p>",
                    "duration_min": 8,
                },
            ],
        },
        headers=headers,
    )
    assert recipe.status_code == 200
    body = recipe.json()
    assert len(body["lines"]) == 1
    assert body["lines"][0]["photo_url"] == "https://example.com/paneer-cube.jpg"
    assert len(body["prep_steps"]) == 2
    assert "yogurt" in body["prep_steps"][0]["body_html"]
    assert body["prep_steps"][0]["duration_min"] == 20
