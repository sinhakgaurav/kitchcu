import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_growth_combos(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    response = await client.get(f"/api/v1/kitchens/{kid}/growth/combos?days=90", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["multi_item_orders"] == 4
    assert len(data["combos"]) >= 1
    top = data["combos"][0]
    assert top["support_pct"] == 100.0
    assert "Butter Naan" in (top["dish_a_name"], top["dish_b_name"])
    assert "Dal Makhani" in (top["dish_a_name"], top["dish_b_name"])


@pytest.mark.asyncio
async def test_growth_patterns(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    response = await client.get(f"/api/v1/kitchens/{kid}/growth/patterns?days=90", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["window_days"] == 90
    assert len(data["days"]) >= 1
    assert "insight" in data
    assert len(data["insight"]) > 10


@pytest.mark.asyncio
async def test_generate_suggestions(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    response = await client.post(
        f"/api/v1/kitchens/{kid}/growth/suggestions/generate?days=90",
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total"] >= 2
    types = {s["suggestion_type"] for s in data["suggestions"]}
    assert "combo_opportunity" in types
    assert "seasonal" in types


@pytest.mark.asyncio
async def test_dismiss_suggestion(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    gen = await client.post(
        f"/api/v1/kitchens/{kid}/growth/suggestions/generate?days=90",
        headers=headers,
    )
    sid = gen.json()["suggestions"][0]["id"]

    response = await client.patch(
        f"/api/v1/kitchens/{kid}/growth/suggestions/{sid}",
        json={"dismissed": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["dismissed"] is True

    listed = await client.get(f"/api/v1/kitchens/{kid}/growth/suggestions", headers=headers)
    assert all(s["id"] != sid for s in listed.json()["suggestions"])


@pytest.mark.asyncio
async def test_seasonal_patterns(client: AsyncClient, growth_ctx):
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    response = await client.get("/api/v1/growth/seasonal-patterns?region=india", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["patterns"][0]["season_event"] == "diwali"


@pytest.mark.asyncio
async def test_daily_menu_push(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}
    dish_ids = [str(growth_ctx["dish_a"]), str(growth_ctx["dish_b"])]

    response = await client.post(
        f"/api/v1/kitchens/{kid}/growth/daily-menu/push",
        json={"dish_ids": dish_ids},
        headers=headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["recipient_count"] == 1
    assert "Butter Naan" in data["message"]
    assert "Dal Makhani" in data["message"]


@pytest.mark.asyncio
async def test_daily_menu_push_invalid_dish(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    response = await client.post(
        f"/api/v1/kitchens/{kid}/growth/daily-menu/push",
        json={"dish_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_golden_performance_day_suggestion_and_save(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    dish_c = str(growth_ctx["dish_c"])
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    gen = await client.post(
        f"/api/v1/kitchens/{kid}/growth/suggestions/generate?days=90",
        headers=headers,
    )
    assert gen.status_code == 201
    suggestions = gen.json()["suggestions"]
    golden = [s for s in suggestions if s["suggestion_type"] == "golden_performance_day"]
    assert len(golden) >= 1
    g = golden[0]
    assert g["action_payload"]["dish_id"] == dish_c
    assert g["action_payload"]["order_qty"] >= 10
    assert g["action_payload"]["recipe_snapshot"]["lines"]
    assert g["priority"] >= 90

    save = await client.post(
        f"/api/v1/kitchens/{kid}/growth/suggestions/{g['id']}/save-golden-recipe",
        headers=headers,
    )
    assert save.status_code == 201
    pin = save.json()
    assert pin["dish_id"] == dish_c
    assert pin["recipe_snapshot"]["lines"][0]["ingredient_name"] == "Paneer"

    listed = await client.get(
        f"/api/v1/kitchens/{kid}/growth/golden-recipes?dish_id={dish_c}",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert listed.json()["pins"][0]["id"] == pin["id"]
