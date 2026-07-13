import json

import pytest
from httpx import AsyncClient

from tests.conftest import build_dish_payload


@pytest.mark.asyncio
async def test_dish_created_publishes_redis_event(client: AsyncClient, kitchen_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:dish")

    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    dish_id = response.json()["id"]

    from app.main import redis_client

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:catalog:dish": "0-0"}, count=10)
    assert len(messages) >= 1
    stream_name, entries = messages[0]
    assert stream_name == "ckac:catalog:dish"
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "dish.created"
    assert event_data["aggregate_id"] == dish_id
    assert event_data["producer"] == "catalog-service"
    assert event_data["payload"]["kitchen_id"] == str(kitchen_id)


@pytest.mark.asyncio
async def test_dish_updated_publishes_event(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    payload = await build_dish_payload(client, kitchen_id, token)
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers=headers,
    )
    dish_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"price": 249.0},
        headers=headers,
    )
    assert response.status_code == 200

    from app.main import redis_client

    messages = await redis_client.xread({"ckac:catalog:dish": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    updated = [e for e in events if e["event_type"] == "dish.updated"]
    assert len(updated) >= 1
    assert updated[-1]["aggregate_id"] == dish_id
    assert "price" in updated[-1]["payload"]["changes"]
