"""Support chat API tests — owner & customer audiences (FAQ pack + options)."""

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
    assert data.get("options")
    assert data.get("answer_id") in (None, "owner.pricing.plans", "owner.pricing.why_charge")


@pytest.mark.asyncio
async def test_support_chat_owner_menu_option(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "owner", "message": "1", "selected_option_id": "1"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "499" in data["reply"] or "subscription" in data["reply"].lower()
    assert isinstance(data.get("options"), list)


@pytest.mark.asyncio
async def test_support_chat_owner_refunds(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "owner", "message": "How do customer refunds work?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "refund" in data["reply"].lower()
    assert data.get("answer_id") == "owner.billing.refunds"


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
    assert data.get("options")


@pytest.mark.asyncio
async def test_support_chat_customer_checkout_current(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "customer", "message": "Can I checkout and pay with UPI?"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "coming in the next release" not in data["reply"].lower()
    assert "upi" in data["reply"].lower() or "checkout" in data["reply"].lower()


@pytest.mark.asyncio
async def test_support_chat_customer_track_order(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "customer", "message": "Track my order status"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("answer_id") == "customer.order.track"
    assert "my orders" in data["reply"].lower() or "status" in data["reply"].lower()


@pytest.mark.asyncio
async def test_support_chat_greeting_returns_menu(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "owner", "message": "hi"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("options")
    assert len(data["options"]) >= 5


@pytest.mark.asyncio
async def test_support_chat_invalid_audience(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "admin", "message": "hello"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_support_chat_empty_opens_menu(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={"audience": "customer", "message": ""},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("options")
