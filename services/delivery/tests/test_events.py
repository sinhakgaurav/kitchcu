import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quote_publishes_event(client: AsyncClient, delivery_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:delivery:quote")

    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["lat"],
            "longitude": delivery_ctx["lng"],
            "subtotal": 100,
        },
    )
    assert response.status_code == 200

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:delivery:quote": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    assert any(e["event_type"] == "delivery.fee_quoted" for e in events)
