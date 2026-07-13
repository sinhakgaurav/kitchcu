import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, Request, Response

from tests.conftest import SYNC_DB_URL, WEBHOOK_PAYLOAD, _seed_kitchen


@pytest.mark.asyncio
async def test_whatsapp_webhook_publishes_event(client: AsyncClient):
    kitchen_id = _seed_kitchen()
    draft_id = uuid.uuid4()

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:notify:whatsapp")

    mock_response = Response(
        201,
        json={
            "id": str(draft_id),
            "kitchen_id": str(kitchen_id),
            "status": "draft",
            "source": "whatsapp",
            "raw_message": "2 Paneer Tikka",
            "parsed_items": [],
            "unmatched_lines": [],
            "special_notes": [],
            "order_id": None,
            "created_at": "2026-07-12T00:00:00Z",
        },
        request=Request("POST", "http://test/internal"),
    )

    import app.routes as routes_mod

    assert routes_mod.http_client is not None
    with patch.object(routes_mod.http_client, "post", AsyncMock(return_value=mock_response)):
        response = await client.post("/api/v1/webhooks/whatsapp", json=WEBHOOK_PAYLOAD)

    assert response.status_code == 200

    messages = await redis_client.xread({"ckac:notify:whatsapp": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "whatsapp.message.received"
    assert event_data["payload"]["kitchen_id"] == str(kitchen_id)

    import psycopg2

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
