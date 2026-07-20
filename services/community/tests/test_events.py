import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recipe_shared_publishes_event(client: AsyncClient, community_ctx):
    kid = community_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {community_ctx['owner_token']}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:community:recipe")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/community/recipes",
        json={
            "title": "Event Recipe",
            "recipe_html": "<p>Test event publish</p>",
            "cover_url": "https://cdn.example/community/cover.jpg",
        },
        headers=headers,
    )
    assert response.status_code == 201
    recipe_id = response.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:community:recipe": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    shared = [e for e in events if e["event_type"] == "recipe.shared"]
    assert len(shared) >= 1
    assert shared[-1]["aggregate_id"] == recipe_id
    assert shared[-1]["payload"]["cover_url"] == "https://cdn.example/community/cover.jpg"
