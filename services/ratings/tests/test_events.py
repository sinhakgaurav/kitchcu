import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rating_created_publishes_event(client: AsyncClient, ratings_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:ratings:rating", "ckac:ratings:dish")

    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}
    response = await client.post(
        f"/api/v1/customers/me/orders/{ratings_ctx['order_id']}/ratings",
        json={
            "ratings": [
                {
                    "dish_id": str(ratings_ctx["dish_id"]),
                    "home_taste_score": 4,
                    "quality_score": 4,
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 201
    rating_id = response.json()["ratings"][0]["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:ratings:rating": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    created = next(e for e in events if e["event_type"] == "rating.created")
    assert created["aggregate_id"] == rating_id

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
