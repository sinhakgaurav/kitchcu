"""Kitchen branded storefront settings — owner publish + public by-code payload."""

import pytest
from httpx import AsyncClient

from tests.test_kitchens import KITCHEN_PAYLOAD


@pytest.mark.asyncio
async def test_branded_page_defaults_disabled(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["branded_page"]["enabled"] is False
    assert body["branded_page"]["tagline"] is None


@pytest.mark.asyncio
async def test_owner_can_publish_branded_page(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]
    code = created.json()["code"]

    updated = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={
            "enabled": True,
            "tagline": "Home-style thalis",
            "accent_color": "#0f766e",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    bp = updated.json()["branded_page"]
    assert bp["enabled"] is True
    assert bp["tagline"] == "Home-style thalis"
    assert bp["accent_color"] == "#0F766E"

    public = await client.get(f"/api/v1/kitchens/public/by-code/{code}")
    assert public.status_code == 200
    data = public.json()
    assert data["branded_page"]["enabled"] is True
    assert data["branded_page"]["tagline"] == "Home-style thalis"
    assert data["name"] == KITCHEN_PAYLOAD["name"]


@pytest.mark.asyncio
async def test_branded_page_rejects_invalid_accent(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]

    bad = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={"accent_color": "teal"},
        headers=auth_headers,
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_branded_page_requires_owner(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]

    anon = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={"enabled": True},
    )
    assert anon.status_code == 401
