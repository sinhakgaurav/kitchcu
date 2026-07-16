"""Messaging wallet deduct + low-balance alert (M10)."""

import json

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


@pytest.mark.asyncio
async def test_wallet_deduct_and_low_balance_event(client: AsyncClient, billing_ctx):
    owner_id, kitchen_id, _, _, owner_token = billing_ctx
    headers = {"Authorization": f"Bearer {owner_token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:wallet")

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "enterprise", "billing_cycle": "monthly"},
        headers=headers,
    )
    sub_id = create.json()["id"]
    await client.post(f"/api/v1/billing/subscriptions/{sub_id}/activate", headers=headers)

    deduct = await client.post(
        f"/api/v1/internal/wallets/{kitchen_id}/deduct",
        json={
            "amount_inr": 460.0,
            "reason": "test_broadcast",
            "recipient_count": 460,
        },
        headers={"X-Internal-Key": "test-internal-key-for-pytest"},
    )
    assert deduct.status_code == 200
    assert deduct.json()["balance_inr"] == 40.0

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:billing:wallet": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    types = {e["event_type"] for e in events}
    assert "wallet.debited" in types
    assert "wallet.low_balance" in types

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT balance_inr FROM ckac_billing.kitchen_messaging_wallets WHERE kitchen_id = %s::uuid",
            (str(kitchen_id),),
        )
        assert float(cur.fetchone()[0]) == 40.0
    conn.close()
