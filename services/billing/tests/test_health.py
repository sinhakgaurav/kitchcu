import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "billing"


@pytest.mark.asyncio
async def test_subscription_plans_public(client: AsyncClient):
    response = await client.get("/api/v1/billing/subscriptions/plans")
    assert response.status_code == 200
    plans = {p["tier"]: p for p in response.json()["plans"]}
    assert "starter" in plans
    assert plans["starter"]["monthly_amount"] == 499.0
