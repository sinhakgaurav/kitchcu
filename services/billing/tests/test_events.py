import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_capture_publishes_event(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:payment")

    create = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    payment_id = create.json()["id"]

    capture = await client.post(
        f"/api/v1/billing/payments/{payment_id}/capture",
        headers=headers,
    )
    assert capture.status_code == 200

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:billing:payment": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    event_types = {e["event_type"] for e in events}
    assert "payment.created" in event_types
    assert "payment.captured" in event_types

    captured = next(e for e in events if e["event_type"] == "payment.captured")
    assert captured["aggregate_id"] == payment_id

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT published FROM ckac_events.outbox WHERE event_id = %s::uuid",
            (captured["event_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] is True


@pytest.mark.asyncio
async def test_subscription_created_publishes_event(client: AsyncClient, billing_ctx):
    _, _, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:subscription")

    response = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "starter", "billing_cycle": "monthly"},
        headers=headers,
    )
    assert response.status_code == 201

    messages = await redis_client.xread({"ckac:billing:subscription": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "subscription.created"
