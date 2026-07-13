import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_suggestion_generated_publishes_event(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:growth:suggestion")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/growth/suggestions/generate?days=90",
        headers=headers,
    )
    assert response.status_code == 201

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:growth:suggestion": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    assert any(e["event_type"] == "suggestion.generated" for e in events)

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    created = next(e for e in events if e["event_type"] == "suggestion.generated")
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
async def test_daily_menu_push_publishes_event(client: AsyncClient, growth_ctx):
    kid = growth_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {growth_ctx['owner_token']}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:growth:daily_menu")

    response = await client.post(
        f"/api/v1/kitchens/{kid}/growth/daily-menu/push",
        json={"dish_ids": [str(growth_ctx["dish_a"])]},
        headers=headers,
    )
    assert response.status_code == 202

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:growth:daily_menu": "0-0"}, count=10)
    assert len(messages) >= 1
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    blast = next(e for e in events if e["event_type"] == "daily_menu.blast_requested")
    assert blast["payload"]["kitchen_id"] == str(kid)
