"""Owner messaging wallet balance read."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_owner_can_read_messaging_wallet_after_enterprise(client: AsyncClient, billing_ctx):
    _, kitchen_id, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    empty = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_id}/messaging-wallet",
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["balance_inr"] == 0.0
    assert empty.json()["kitchen_id"] == str(kitchen_id)

    create = await client.post(
        "/api/v1/billing/subscriptions",
        json={"plan_tier": "enterprise", "billing_cycle": "monthly"},
        headers=headers,
    )
    sub_id = create.json()["id"]
    await client.post(f"/api/v1/billing/subscriptions/{sub_id}/activate", headers=headers)

    funded = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_id}/messaging-wallet",
        headers=headers,
    )
    assert funded.status_code == 200
    assert funded.json()["balance_inr"] == 500.0
    assert funded.json()["low_balance"] is False
