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


@pytest.mark.asyncio
async def test_branded_page_logo_and_background_urls(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]
    code = created.json()["code"]

    updated = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={
            "enabled": True,
            "logo_url": "https://cdn.example.com/kitchens/logo.png",
            "background_url": "https://cdn.example.com/kitchens/hero.jpg",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    bp = updated.json()["branded_page"]
    assert bp["logo_url"] == "https://cdn.example.com/kitchens/logo.png"
    assert bp["background_url"] == "https://cdn.example.com/kitchens/hero.jpg"

    public = await client.get(f"/api/v1/kitchens/public/by-code/{code}")
    assert public.status_code == 200
    pub_bp = public.json()["branded_page"]
    assert pub_bp["logo_url"] == "https://cdn.example.com/kitchens/logo.png"
    assert pub_bp["background_url"] == "https://cdn.example.com/kitchens/hero.jpg"

    cleared = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={"logo_url": "", "background_url": ""},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["branded_page"]["logo_url"] is None
    assert cleared.json()["branded_page"]["background_url"] is None


@pytest.mark.asyncio
async def test_branded_page_rejects_invalid_media_url(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]

    bad = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        json={"logo_url": "javascript:alert(1)"},
        headers=auth_headers,
    )
    assert bad.status_code == 422
