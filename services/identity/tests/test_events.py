import json

import pytest
from httpx import AsyncClient

KITCHEN_PAYLOAD = {
    "name": "Event Test Kitchen",
    "address_line": "Koregaon Park",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "latitude": 18.5362,
    "longitude": 73.8958,
}


@pytest.mark.asyncio
async def test_kitchen_created_publishes_redis_event(client: AsyncClient, auth_headers: dict):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:identity:kitchen")

    response = await client.post(
        "/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 201
    kitchen_id = response.json()["id"]

    from app.main import redis_client

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:kitchen": "0-0"}, count=10)
    assert len(messages) >= 1
    stream_name, entries = messages[0]
    assert stream_name == "ckac:identity:kitchen"
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "kitchen.created"
    assert event_data["aggregate_id"] == kitchen_id
    assert event_data["producer"] == "identity-service"
    assert event_data["payload"]["city"] == "Pune"


@pytest.mark.asyncio
async def test_kitchen_created_writes_outbox(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers
    )
    assert response.status_code == 201

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_type, published FROM ckac_events.outbox "
            "WHERE event_type = 'kitchen.created' ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "kitchen.created"
    assert row[1] is True


@pytest.mark.asyncio
async def test_kitchen_whatsapp_updated_publishes_event(client: AsyncClient, auth_headers: dict):
    from app.main import redis_client

    create = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert create.status_code == 201
    kitchen_id = create.json()["id"]

    if redis_client:
        await redis_client.delete("ckac:identity:kitchen")

    put = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration",
        json={"whatsapp_phone_id": "PHONE_EVENT_99", "whatsapp_display_phone": "+919999999999"},
        headers=auth_headers,
    )
    assert put.status_code == 200

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:kitchen": "0-0"}, count=10)
    assert len(messages) >= 1
    _, entries = messages[0]
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "kitchen.whatsapp.updated"
    assert event_data["aggregate_id"] == kitchen_id
    assert event_data["payload"]["connected"] is True
    assert event_data["payload"]["whatsapp_phone_id"] == "PHONE_EVENT_99"
