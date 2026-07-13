import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_customer_suggestion_and_owner_response(client: AsyncClient, ratings_ctx):
    kid = ratings_ctx["kitchen_id"]
    dish_id = ratings_ctx["dish_id"]
    customer_headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}
    owner_headers = {"Authorization": f"Bearer {ratings_ctx['owner_token']}"}

    created = await client.post(
        f"/api/v1/kitchens/{kid}/dishes/{dish_id}/suggestions",
        json={"suggestion_text": "Please offer a mild spice option for kids."},
        headers=customer_headers,
    )
    assert created.status_code == 201
    suggestion_id = created.json()["id"]

    listed = await client.get(
        f"/api/v1/kitchens/{kid}/suggestions?status=pending",
        headers=owner_headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = await client.patch(
        f"/api/v1/kitchens/{kid}/suggestions/{suggestion_id}",
        json={"status": "accepted", "owner_response": "Added mild option on request."},
        headers=owner_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "accepted"
