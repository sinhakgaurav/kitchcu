import json

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_recipe_learned_publishes_event(client: AsyncClient, learning_ctx, monkeypatch):
    kid = learning_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {learning_ctx['owner_token']}"}
    monkeypatch.setattr(
        "app.schemas.create_trial_dish",
        AsyncMock(return_value=learning_ctx["trial_dish_id"]),
    )

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:learning:trial")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/learning/learn",
        json={"recipe_id": str(learning_ctx["recipe_id"]), "price": 99},
        headers=headers,
    )
    assert response.status_code == 201

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:learning:trial": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    assert any(e["event_type"] == "recipe.learned" for e in events)
