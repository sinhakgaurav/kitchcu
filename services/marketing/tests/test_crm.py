import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crm_sync_from_orders(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    response = await client.get(
        f"/api/v1/kitchens/{kid}/crm/customers?refresh=true",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["synced_at"] is not None
    customer = data["customers"][0]
    assert customer["customer_phone"] == marketing_ctx["customer_phone"]
    assert customer["order_count"] == 1
    assert customer["total_spend"] == 398.0
    assert len(customer["favorite_dishes"]) == 1
    assert customer["favorite_dishes"][0]["dish_name"] == "Paneer Tikka"


@pytest.mark.asyncio
async def test_crm_update_tags(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    listed = await client.get(
        f"/api/v1/kitchens/{kid}/crm/customers?refresh=true",
        headers=headers,
    )
    customer_id = listed.json()["customers"][0]["id"]

    updated = await client.patch(
        f"/api/v1/kitchens/{kid}/crm/customers/{customer_id}",
        json={"tags": ["vip", "weekend"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["tags"] == ["vip", "weekend"]
