import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_coupon_created_publishes_event(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:marketing:coupon")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/coupons",
        json={"code": "EVENT10", "discount_type": "percent", "discount_value": 10},
        headers=headers,
    )
    assert response.status_code == 201
    coupon_id = response.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:marketing:coupon": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    created = next(e for e in events if e["event_type"] == "coupon.created")
    assert created["aggregate_id"] == coupon_id

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT published FROM ckac_events.outbox WHERE event_id = %s::uuid",
            (created["event_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] is True
