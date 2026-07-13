import json

import pytest
from httpx import AsyncClient


PARSE_PAYLOAD = {
    "message_text": "2 Paneer Tikka\nno onion",
    "source": "manual_message",
    "customer_phone": "+919876543210",
}


@pytest.mark.asyncio
async def test_parse_message_creates_draft(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, dish_id, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json=PARSE_PAYLOAD,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["source"] == "manual_message"
    assert len(data["parsed_items"]) >= 1
    assert data["parsed_items"][0]["matched"] is True
    assert data["parsed_items"][0]["dish_name"] == "Paneer Tikka"
    assert "no onion" in data["special_notes"][0]


@pytest.mark.asyncio
async def test_list_drafts(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json=PARSE_PAYLOAD,
        headers=headers,
    )
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/drafts",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_confirm_draft_creates_order(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json=PARSE_PAYLOAD,
        headers=headers,
    )
    draft_id = create.json()["id"]
    confirm = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/drafts/{draft_id}/confirm",
        headers=headers,
    )
    assert confirm.status_code == 201
    assert confirm.json()["source"] == "manual_message"
    assert confirm.json()["subtotal"] == 398.0


@pytest.mark.asyncio
async def test_draft_created_publishes_event(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, token = order_ctx
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json=PARSE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    draft_id = response.json()["id"]

    from app.main import redis_client

    messages = await redis_client.xread({"ckac:orders:draft": "0-0"}, count=10)
    events = [json.loads(e[1]["data"]) for _, entries in messages for e in entries]
    draft_events = [e for e in events if e["aggregate_id"] == draft_id]
    assert draft_events[0]["event_type"] == "order.draft.created"


@pytest.mark.asyncio
async def test_whatsapp_internal_intake(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, _ = order_ctx
    import os

    key = os.environ.get("INTERNAL_API_KEY", "test-internal-key-for-pytest")
    response = await client.post(
        f"/api/v1/internal/kitchens/{kitchen_id}/orders/from-whatsapp",
        json={"message_text": "2 Paneer Tikka", "customer_phone": "+919999999999"},
        headers={"X-Internal-Key": key},
    )
    assert response.status_code == 201
    assert response.json()["source"] == "whatsapp"
