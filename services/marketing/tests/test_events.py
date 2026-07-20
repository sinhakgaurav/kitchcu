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


@pytest.mark.asyncio
async def test_subscription_plan_created_publishes_event(client: AsyncClient, marketing_ctx):
    """EDD: combo plan create emits subscription.plan.created."""
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:marketing:subscription")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/subscription-plans",
        headers=headers,
        json={
            "name": "Event Combo",
            "plan_type": "combo",
            "price_monthly": 2999,
            "dishes_config": {
                "dish_ids": [str(marketing_ctx["dish_id"]), str(marketing_ctx["dish_id_2"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        },
    )
    assert response.status_code == 201, response.text
    plan_id = response.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:marketing:subscription": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    created = [
        e
        for e in events
        if e["event_type"] == "subscription.plan.created" and e["aggregate_id"] == plan_id
    ]
    assert len(created) == 1
    assert created[0]["payload"]["plan_type"] == "combo"
    assert created[0]["payload"]["kitchen_id"] == str(kid)
