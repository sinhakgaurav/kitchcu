import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_aggregate_formula(client: AsyncClient, ratings_ctx):
    order_id = ratings_ctx["order_id"]
    dish_id = ratings_ctx["dish_id"]
    kitchen_id = ratings_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}

    await client.post(
        f"/api/v1/customers/me/orders/{order_id}/ratings",
        json={
            "ratings": [{"dish_id": str(dish_id), "home_taste_score": 5, "quality_score": 3}]
        },
        headers=headers,
    )

    summary = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/ratings/summary"
    )
    assert summary.status_code == 200
    data = summary.json()
    assert data["rating_count"] == 1
    assert data["avg_home_taste"] == 5.0
    assert data["avg_quality"] == 3.0
    assert data["overall_rating"] == 4.2  # 0.6*5 + 0.4*3

    batch = await client.get(f"/api/v1/kitchens/{kitchen_id}/ratings/summaries")
    assert batch.status_code == 200
    assert len(batch.json()["summaries"]) == 1


@pytest.mark.asyncio
async def test_anonymous_reviews_no_pii(client: AsyncClient, ratings_ctx):
    order_id = ratings_ctx["order_id"]
    dish_id = ratings_ctx["dish_id"]
    kitchen_id = ratings_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}

    await client.post(
        f"/api/v1/customers/me/orders/{order_id}/ratings",
        json={
            "ratings": [
                {
                    "dish_id": str(dish_id),
                    "home_taste_score": 4,
                    "quality_score": 5,
                    "media_url": "https://cdn.example/audio.mp3",
                    "media_type": "audio",
                }
            ]
        },
        headers=headers,
    )

    reviews = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/ratings/reviews"
    )
    assert reviews.status_code == 200
    item = reviews.json()["reviews"][0]
    assert "customer_id" not in item
    assert "customer_phone" not in item
    assert item["media_type"] == "audio"
