from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_promotions(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    dish_id = marketing_ctx["dish_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    now = datetime.now(UTC)

    create = await client.post(
        f"/api/v1/kitchens/{kid}/promotions",
        json={
            "name": "VIP Paneer deal",
            "dish_id": str(dish_id),
            "special_price": 149,
            "segment": "vip",
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
        },
        headers=headers,
    )
    assert create.status_code == 201
    assert create.json()["dish_name"] == "Paneer Tikka"

    listed = await client.get(f"/api/v1/kitchens/{kid}/promotions", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_active_promotions_for_all_segment(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    dish_id = marketing_ctx["dish_id"]
    owner_headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    now = datetime.now(UTC)

    await client.post(
        f"/api/v1/kitchens/{kid}/promotions",
        json={
            "name": "Everyone deal",
            "dish_id": str(dish_id),
            "special_price": 179,
            "segment": "all",
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(days=3)).isoformat(),
        },
        headers=owner_headers,
    )

    active = await client.get(f"/api/v1/kitchens/{kid}/promotions/active")
    assert active.status_code == 200
    assert len(active.json()["promotions"]) == 1


@pytest.mark.asyncio
async def test_deactivate_promotion(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    dish_id = marketing_ctx["dish_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    now = datetime.now(UTC)

    created = await client.post(
        f"/api/v1/kitchens/{kid}/promotions",
        json={
            "name": "End me",
            "dish_id": str(dish_id),
            "special_price": 99,
            "segment": "all",
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(days=2)).isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    promo_id = created.json()["id"]

    ended = await client.patch(
        f"/api/v1/kitchens/{kid}/promotions/{promo_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert ended.status_code == 200
    assert ended.json()["is_active"] is False

    active = await client.get(f"/api/v1/kitchens/{kid}/promotions/active")
    assert active.status_code == 200
    assert active.json()["promotions"] == []
