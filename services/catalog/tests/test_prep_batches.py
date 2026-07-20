"""F19b — bulk prep batches + prep_batch_only stock mode."""

import json
import os
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import build_dish_payload

INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "test-internal-key-for-pytest")


async def _setup_dish_with_recipe(client: AsyncClient, kitchen_id: str, token: str, *, name: str = "Dal"):
    headers = {"Authorization": f"Bearer {token}"}
    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={"name": f"{name} Stock {uuid.uuid4().hex[:6]}", "unit": "g", "current_stock": 1000, "low_stock_threshold": 50},
        headers=headers,
    )
    assert ing.status_code == 201, ing.text
    ingredient_id = ing.json()["id"]

    dish_payload = await build_dish_payload(client, kitchen_id, token)
    dish_payload["name"] = f"{name} {uuid.uuid4().hex[:4]}"
    dish = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=dish_payload,
        headers=headers,
    )
    assert dish.status_code == 201, dish.text
    dish_id = dish.json()["id"]

    recipe = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
        json={"lines": [{"ingredient_id": ingredient_id, "quantity": 10, "unit": "g"}]},
        headers=headers,
    )
    assert recipe.status_code == 200, recipe.text
    return ingredient_id, dish_id, headers


@pytest.mark.asyncio
async def test_bulk_prep_combo_mark_prepared_deducts_stock(client: AsyncClient, kitchen_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:ingredient")

    _, kitchen_id, token = kitchen_ctx
    ing_a, dish_a, headers = await _setup_dish_with_recipe(client, kitchen_id, token, name="Rice")
    ing_b, dish_b, _ = await _setup_dish_with_recipe(client, kitchen_id, token, name="Dal")

    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/prep-batches",
        json={
            "name": "Morning thali cook",
            "batch_type": "combo",
            "portions": 10,
            "dishes": [
                {"dish_id": dish_a, "quantity_per_portion": 1},
                {"dish_id": dish_b, "quantity_per_portion": 1},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert len(body["dishes"]) == 2
    assert len(body["ingredient_lines"]) == 2
    # 10g * 10 portions each
    by_ing = {line["ingredient_id"]: line["quantity"] for line in body["ingredient_lines"]}
    assert by_ing[ing_a] == 100
    assert by_ing[ing_b] == 100

    # Explicit override: use less dal
    patched = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/prep-batches/{body['id']}",
        json={
            "ingredient_lines": [
                {"ingredient_id": ing_a, "quantity": 100, "unit": "g", "sort_order": 0},
                {"ingredient_id": ing_b, "quantity": 80, "unit": "g", "sort_order": 1},
            ]
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    prepared = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/prep-batches/{body['id']}/mark-prepared",
        headers=headers,
    )
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "prepared"

    listing = await client.get(f"/api/v1/kitchens/{kitchen_id}/ingredients", headers=headers)
    stocks = {i["id"]: i["current_stock"] for i in listing.json()["ingredients"]}
    assert stocks[ing_a] == 900
    assert stocks[ing_b] == 920

    again = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/prep-batches/{body['id']}/mark-prepared",
        headers=headers,
    )
    assert again.status_code == 200
    listing2 = await client.get(f"/api/v1/kitchens/{kitchen_id}/ingredients", headers=headers)
    stocks2 = {i["id"]: i["current_stock"] for i in listing2.json()["ingredients"]}
    assert stocks2[ing_a] == 900
    assert stocks2[ing_b] == 920

    messages = await redis_client.xread({"ckac:catalog:ingredient": "0-0"}, count=40)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    assert any(e["event_type"] == "prep_batch.prepared" for e in events)
    assert any(e["event_type"] == "ingredient.stock.deducted" for e in events)


@pytest.mark.asyncio
async def test_prep_batch_only_skips_order_deduct(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    ingredient_id, dish_id, headers = await _setup_dish_with_recipe(client, kitchen_id, token)

    mode = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/stock-settings",
        json={"deduct_mode": "prep_batch_only"},
        headers=headers,
    )
    assert mode.status_code == 200
    assert mode.json()["deduct_mode"] == "prep_batch_only"

    deduct = await client.post(
        f"/api/v1/internal/kitchens/{kitchen_id}/stock/deduct-order",
        json={
            "order_id": str(uuid.uuid4()),
            "items": [{"dish_id": dish_id, "quantity": 2}],
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert deduct.status_code == 200
    assert deduct.json()["deducted"] == []

    listing = await client.get(f"/api/v1/kitchens/{kitchen_id}/ingredients", headers=headers)
    stock = next(i for i in listing.json()["ingredients"] if i["id"] == ingredient_id)
    assert stock["current_stock"] == 1000
