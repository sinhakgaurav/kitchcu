"""Customer social login and WhatsApp OTP tests."""

import json

import pytest
from httpx import AsyncClient

from app.oauth import DEV_OAUTH_CODE

REDIRECT_URI = "http://localhost:13001/oauth/callback"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "facebook", "instagram", "twitter"])
async def test_customer_oauth_dev_login(client: AsyncClient, provider: str):
    start = await client.get(
        f"/api/v1/auth/customer/oauth/{provider}/start",
        params={"redirect_uri": REDIRECT_URI},
    )
    assert start.status_code == 200
    data = start.json()
    assert data["provider"] == provider
    assert data["dev_mode"] is True
    assert data["state"]

    complete = await client.post(
        f"/api/v1/auth/customer/oauth/{provider}/complete",
        json={"code": DEV_OAUTH_CODE, "state": data["state"], "redirect_uri": REDIRECT_URI},
    )
    assert complete.status_code == 200
    body = complete.json()
    assert body["access_token"]
    assert body["customer"]["name"]
    assert body["customer"]["email"]

    me = await client.get(
        "/api/v1/customers/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == body["customer"]["id"]


@pytest.mark.asyncio
async def test_customer_oauth_dev_login_idempotent(client: AsyncClient):
    start = await client.get(
        "/api/v1/auth/customer/oauth/google/start",
        params={"redirect_uri": REDIRECT_URI},
    )
    state = start.json()["state"]
    payload = {"code": DEV_OAUTH_CODE, "state": state, "redirect_uri": REDIRECT_URI}

    first = await client.post("/api/v1/auth/customer/oauth/google/complete", json=payload)
    second = await client.post("/api/v1/auth/customer/oauth/google/complete", json=payload)
    assert first.status_code == 200
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_customer_whatsapp_otp_login(client: AsyncClient):
    phone = "+919876543210"
    req = await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    assert req.status_code == 202

    bad = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "000000"},
    )
    assert bad.status_code == 401

    ok = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert ok.status_code == 200
    assert ok.json()["customer"]["phone"] == phone


@pytest.mark.asyncio
async def test_customer_created_event_on_oauth(client: AsyncClient):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:identity:customer")

    start = await client.get(
        "/api/v1/auth/customer/oauth/google/start",
        params={"redirect_uri": REDIRECT_URI},
    )
    state = start.json()["state"]
    response = await client.post(
        "/api/v1/auth/customer/oauth/google/complete",
        json={"code": DEV_OAUTH_CODE, "state": state, "redirect_uri": REDIRECT_URI},
    )
    assert response.status_code == 200
    customer_id = response.json()["customer"]["id"]

    from app.main import redis_client

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:customer": "0-0"}, count=5)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "customer.created"
    assert event_data["aggregate_id"] == customer_id


@pytest.mark.asyncio
async def test_list_oauth_providers(client: AsyncClient):
    response = await client.get("/api/v1/auth/customer/oauth/providers")
    assert response.status_code == 200
    ids = {p["id"] for p in response.json()["providers"]}
    assert ids == {"google", "facebook", "instagram", "twitter", "whatsapp"}
