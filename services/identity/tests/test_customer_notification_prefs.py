"""Customer notification preferences — order updates, offers, channel (ID-10)."""

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, phone: str) -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    ok = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert ok.status_code == 200
    return ok.json()["access_token"]


@pytest.mark.asyncio
async def test_defaults_order_updates_on_offers_off(client: AsyncClient):
    token = await _login(client, "+919611000001")
    me = await client.get("/api/v1/customers/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["notify_order_updates"] is True
    assert body["notify_offers"] is False
    assert body["notify_channel"] == "whatsapp"


@pytest.mark.asyncio
async def test_update_prefs_persists(client: AsyncClient):
    token = await _login(client, "+919611000002")
    headers = {"Authorization": f"Bearer {token}"}

    updated = await client.patch(
        "/api/v1/customers/me/notifications",
        json={"notify_offers": True, "notify_channel": "whatsapp"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["notify_offers"] is True
    assert body["notify_channel"] == "whatsapp"
    # Omitted field stays unchanged.
    assert body["notify_order_updates"] is True

    me = await client.get("/api/v1/customers/me", headers=headers)
    assert me.json()["notify_offers"] is True


@pytest.mark.asyncio
async def test_channel_none_silences_everything(client: AsyncClient):
    token = await _login(client, "+919611000003")
    headers = {"Authorization": f"Bearer {token}"}

    await client.patch(
        "/api/v1/customers/me/notifications",
        json={"notify_offers": True},
        headers=headers,
    )
    silenced = await client.patch(
        "/api/v1/customers/me/notifications",
        json={"notify_channel": "none"},
        headers=headers,
    )
    assert silenced.status_code == 200, silenced.text
    body = silenced.json()
    assert body["notify_channel"] == "none"
    assert body["notify_order_updates"] is False
    assert body["notify_offers"] is False


@pytest.mark.asyncio
async def test_invalid_channel_rejected(client: AsyncClient):
    token = await _login(client, "+919611000004")
    bad = await client.patch(
        "/api/v1/customers/me/notifications",
        json={"notify_channel": "sms"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_prefs_require_customer_auth(client: AsyncClient):
    anon = await client.patch(
        "/api/v1/customers/me/notifications",
        json={"notify_offers": True},
    )
    assert anon.status_code in (401, 403)
