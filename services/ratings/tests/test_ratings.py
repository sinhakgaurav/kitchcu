import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_rating_for_delivered_order(client: AsyncClient, ratings_ctx):
    order_id = ratings_ctx["order_id"]
    dish_id = ratings_ctx["dish_id"]
    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}

    response = await client.post(
        f"/api/v1/customers/me/orders/{order_id}/ratings",
        json={
            "ratings": [
                {
                    "dish_id": str(dish_id),
                    "home_taste_score": 5,
                    "quality_score": 4,
                    "media_url": "https://cdn.example/review.mp4",
                    "media_type": "video",
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["ratings"]) == 1
    assert body["ratings"][0]["home_taste_score"] == 5
    assert "health_nudge" in body
    assert body["health_nudge"]["walk_minutes"] >= 5
    assert "Hope you loved the meal" in body["health_nudge"]["message"]


@pytest.mark.asyncio
async def test_rejects_non_delivered_order(client: AsyncClient, preparing_ctx):
    headers = {"Authorization": f"Bearer {preparing_ctx['customer_token']}"}

    response = await client.post(
        f"/api/v1/customers/me/orders/{preparing_ctx['order_id']}/ratings",
        json={
            "ratings": [
                {
                    "dish_id": str(preparing_ctx["dish_id"]),
                    "home_taste_score": 4,
                    "quality_score": 4,
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert "delivered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rejects_duplicate_rating(client: AsyncClient, ratings_ctx):
    order_id = ratings_ctx["order_id"]
    dish_id = ratings_ctx["dish_id"]
    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}
    payload = {
        "ratings": [{"dish_id": str(dish_id), "home_taste_score": 5, "quality_score": 5}]
    }

    first = await client.post(
        f"/api/v1/customers/me/orders/{order_id}/ratings",
        json=payload,
        headers=headers,
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/customers/me/orders/{order_id}/ratings",
        json=payload,
        headers=headers,
    )
    assert second.status_code == 400
