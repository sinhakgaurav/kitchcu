import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_manual_order_publishes_order_placed(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:orders:order")

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert response.status_code == 201
    order_id = response.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:orders:order": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "order.placed"
    assert event_data["aggregate_id"] == order_id

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT published FROM ckac_events.outbox WHERE event_id = %s::uuid",
            (event_data["event_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] is True


@pytest.mark.asyncio
async def test_parse_message_publishes_draft_created(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:orders:draft")

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json={"message_text": "2 Paneer Tikka", "source": "manual_message"},
        headers=headers,
    )
    assert response.status_code == 201

    messages = await redis_client.xread({"ckac:orders:draft": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "order.draft.created"


@pytest.mark.asyncio
async def test_patch_draft_publishes_draft_updated(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json={"message_text": "2 Mystery Stew", "source": "manual_message"},
        headers=headers,
    )
    assert create.status_code == 201
    draft_id = create.json()["id"]

    if redis_client:
        await redis_client.delete("ckac:orders:draft")

    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/orders/drafts/{draft_id}",
        json={
            "parsed_items": [
                {"raw": "2 Mystery Stew", "dish_id": str(dish_id), "quantity": 2},
            ]
        },
        headers=headers,
    )
    assert response.status_code == 200

    messages = await redis_client.xread({"ckac:orders:draft": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    updated = [e for e in events if e["event_type"] == "order.draft.updated" and e["aggregate_id"] == draft_id]
    assert len(updated) >= 1
    assert updated[0]["payload"]["draft_id"] == draft_id

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT published FROM ckac_events.outbox WHERE event_id = %s::uuid",
            (updated[0]["event_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] is True
