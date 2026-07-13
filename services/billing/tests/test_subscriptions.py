import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_activate_subscription(client: AsyncClient, billing_ctx):
    _, _, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "growth", "billing_cycle": "monthly"},
        headers=headers,
    )
    assert create.status_code == 201
    sub = create.json()
    assert sub["plan_tier"] == "growth"
    assert sub["status"] == "trial"
    assert sub["amount"] == 999.0

    activate = await client.post(
        f"/api/v1/billing/subscriptions/{sub['id']}/activate",
        headers=headers,
    )
    assert activate.status_code == 200
    activated = activate.json()
    assert activated["status"] == "active"
    assert activated["current_period_end"] is not None

    me = await client.get("/api/v1/billing/subscriptions/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["id"] == sub["id"]


@pytest.mark.asyncio
async def test_activate_updates_identity_owner(client: AsyncClient, billing_ctx):
    owner_id, _, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "pro", "billing_cycle": "yearly"},
        headers=headers,
    )
    sub_id = create.json()["id"]
    await client.post(f"/api/v1/billing/subscriptions/{sub_id}/activate", headers=headers)

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT subscription_tier, subscription_status FROM ckac_identity.owners WHERE id = %s::uuid",
            (str(owner_id),),
        )
        tier, status = cur.fetchone()
    conn.close()
    assert tier == "pro"
    assert status == "active"
