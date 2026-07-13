import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_curated_recipes(client: AsyncClient, learning_ctx):
    res = await client.get("/api/v1/learning/recipes")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(r["slug"] == "test-korma" for r in body["recipes"])


@pytest.mark.asyncio
async def test_learn_recipe_creates_trial(client: AsyncClient, learning_ctx, monkeypatch):
    kid = learning_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {learning_ctx['owner_token']}"}
    dish_id = learning_ctx["trial_dish_id"]

    monkeypatch.setattr(
        "app.schemas.create_trial_dish",
        AsyncMock(return_value=dish_id),
    )

    res = await client.post(
        f"/api/v1/kitchens/{kid}/learning/learn",
        json={"recipe_id": str(learning_ctx["recipe_id"]), "price": 149},
        headers=headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["catalog_dish_id"] == str(dish_id)
    assert body["status"] == "draft"
    assert body["dish_name"] == "Test Korma"


@pytest.mark.asyncio
async def test_trial_workflow_invite_send_rate_promote(client: AsyncClient, learning_ctx, monkeypatch):
    kid = learning_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {learning_ctx['owner_token']}"}
    dish_id = learning_ctx["trial_dish_id"]

    monkeypatch.setattr("app.schemas.create_trial_dish", AsyncMock(return_value=dish_id))
    monkeypatch.setattr("app.schemas.notify_trial_sample_blast", AsyncMock(return_value=None))
    monkeypatch.setattr("app.schemas.activate_dish", AsyncMock(return_value=None))

    learn = await client.post(
        f"/api/v1/kitchens/{kid}/learning/learn",
        json={"recipe_id": str(learning_ctx["recipe_id"]), "price": 120},
        headers=headers,
    )
    trial_id = learn.json()["id"]

    invites = await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/invites",
        json={"customer_ids": [str(c) for c in learning_ctx["customer_ids"]], "promo_type": "free"},
        headers=headers,
    )
    assert invites.status_code == 200
    assert invites.json()["invite_count"] == 6

    sent = await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/send-samples",
        headers=headers,
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "collecting_ratings"

    detail = await client.get(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}",
        headers=headers,
    )
    invites_list = detail.json()["invites"]

    for inv in invites_list:
        res = await client.post(
            f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/ratings",
            json={"invite_id": inv["id"], "home_taste_score": 5, "quality_score": 4},
            headers=headers,
        )
        assert res.status_code == 200

    rated = await client.get(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}",
        headers=headers,
    )
    assert rated.json()["avg_rating"] is not None
    assert rated.json()["avg_rating"] >= 4.0

    promoted = await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/promote",
        headers=headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "promoted"
    assert promoted.json()["promoted_at"] is not None


@pytest.mark.asyncio
async def test_promote_rejects_low_rating(client: AsyncClient, learning_ctx, monkeypatch):
    kid = learning_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {learning_ctx['owner_token']}"}
    dish_id = learning_ctx["trial_dish_id"]

    monkeypatch.setattr("app.schemas.create_trial_dish", AsyncMock(return_value=dish_id))
    monkeypatch.setattr("app.schemas.notify_trial_sample_blast", AsyncMock(return_value=None))

    learn = await client.post(
        f"/api/v1/kitchens/{kid}/learning/learn",
        json={"recipe_id": str(learning_ctx["recipe_id"])},
        headers=headers,
    )
    trial_id = learn.json()["id"]
    await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/invites",
        json={"customer_ids": [str(c) for c in learning_ctx["customer_ids"]]},
        headers=headers,
    )
    await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/send-samples",
        headers=headers,
    )
    detail = (await client.get(f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}", headers=headers)).json()
    await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/ratings",
        json={"invite_id": detail["invites"][0]["id"], "home_taste_score": 2, "quality_score": 2},
        headers=headers,
    )
    bad = await client.post(
        f"/api/v1/kitchens/{kid}/learning/trials/{trial_id}/promote",
        headers=headers,
    )
    assert bad.status_code == 400
