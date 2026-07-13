"""Support chat API tests — owner & customer audiences."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_support_chat_owner_pricing(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "owner", "message": "What are your pricing plans?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["audience"] == "owner"
    assert "499" in data["reply"]
    assert data["source"] in ("knowledge", "ai")
    assert "commission" in data["reply"].lower()


@pytest.mark.asyncio
async def test_support_chat_customer_find_kitchen(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "customer", "message": "How do I find a nearby kitchen?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["audience"] == "customer"
    assert "customer.kitchcu.in" in data["reply"] or "nearby" in data["reply"].lower()


@pytest.mark.asyncio
async def test_support_chat_invalid_audience(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "admin", "message": "hello"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_support_chat_empty_message(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "owner", "message": ""},
    )
    assert r.status_code == 422
