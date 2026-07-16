"""Enterprise tier — ₹1,799 bifurcation (₹1,299 platform + ₹500 messaging wallet)."""

import json

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


@pytest.mark.asyncio
async def test_enterprise_activate_splits_ledger_and_credits_wallet(
    client: AsyncClient, billing_ctx
):
    owner_id, kitchen_id, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:subscription", "ckac:billing:wallet")

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "enterprise", "billing_cycle": "monthly"},
        headers=headers,
    )
    assert create.status_code == 201
    sub = create.json()
    assert sub["plan_tier"] == "enterprise"
    assert sub["amount"] == 1799.0

    activate = await client.post(
        f"/api/v1/billing/subscriptions/{sub['id']}/activate",
        headers=headers,
    )
    assert activate.status_code == 200
    assert activate.json()["status"] == "active"

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT platform_revenue_amount, wallet_credit_amount, total_amount, kitchen_id
            FROM ckac_billing.subscription_ledger_entries
            WHERE subscription_id = %s::uuid
            """,
            (sub["id"],),
        )
        ledger = cur.fetchone()
        assert ledger is not None
        platform, wallet_credit, total, ledger_kitchen = ledger
        assert float(platform) == 1299.0
        assert float(wallet_credit) == 500.0
        assert float(total) == 1799.0
        assert str(ledger_kitchen) == str(kitchen_id)

        cur.execute(
            "SELECT balance_inr FROM ckac_billing.kitchen_messaging_wallets WHERE kitchen_id = %s::uuid",
            (str(kitchen_id),),
        )
        row = cur.fetchone()
        assert row is not None
        assert float(row[0]) == 500.0

        cur.execute(
            "SELECT subscription_tier FROM ckac_identity.owners WHERE id = %s::uuid",
            (str(owner_id),),
        )
        assert cur.fetchone()[0] == "enterprise"
    conn.close()

    assert redis_client is not None
    wallet_msgs = await redis_client.xread({"ckac:billing:wallet": "0-0"}, count=10)
    assert len(wallet_msgs) >= 1
    wallet_events = [
        json.loads(entry[1]["data"]) for _, entries in wallet_msgs for entry in entries
    ]
    credited = next(e for e in wallet_events if e["event_type"] == "wallet.credits.added")
    assert credited["payload"]["kitchen_id"] == str(kitchen_id)
    assert credited["payload"]["amount_inr"] == 500.0
    assert credited["payload"]["owner_id"] == str(owner_id)


@pytest.mark.asyncio
async def test_starter_activate_does_not_credit_wallet(client: AsyncClient, billing_ctx):
    _, kitchen_id, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "starter", "billing_cycle": "monthly"},
        headers=headers,
    )
    sub_id = create.json()["id"]
    await client.post(f"/api/v1/billing/subscriptions/{sub_id}/activate", headers=headers)

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM ckac_billing.subscription_ledger_entries")
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT balance_inr FROM ckac_billing.kitchen_messaging_wallets WHERE kitchen_id = %s::uuid",
            (str(kitchen_id),),
        )
        assert cur.fetchone() is None
    conn.close()
