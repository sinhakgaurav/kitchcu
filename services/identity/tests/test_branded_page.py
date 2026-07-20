"""Kitchen branded storefront settings — owner publish + public by-code payload."""

import io
import os

import pytest
from httpx import AsyncClient

from ckac_common.storage import reset_media_storage
from tests.test_kitchens import KITCHEN_PAYLOAD

os.environ.setdefault("MEDIA_STORAGE_BACKEND", "local")


def _jpeg_bytes() -> bytes:
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\x7f\xff\xd9"
    )


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


@pytest.mark.asyncio
async def test_owner_branded_page_media_upload_logo_and_background(
    client: AsyncClient, auth_headers: dict
):
    os.environ["MEDIA_STORAGE_BACKEND"] = "local"
    reset_media_storage()
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]

    logo = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/branded-page/upload",
        headers=auth_headers,
        files={"file": ("logo.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        data={"slot": "logo"},
    )
    assert logo.status_code == 200, logo.text
    bp = logo.json()["branded_page"]
    assert bp["logo_url"]
    assert bp["logo_url"].startswith("file://") or bp["logo_url"].startswith("http")

    bg = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/branded-page/upload",
        headers=auth_headers,
        files={"file": ("hero.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        data={"slot": "background"},
    )
    assert bg.status_code == 200, bg.text
    bp2 = bg.json()["branded_page"]
    assert bp2["background_url"]
    assert bp2["logo_url"] == bp["logo_url"]


@pytest.mark.asyncio
async def test_owner_branded_page_upload_requires_auth(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]
    anon = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/branded-page/upload",
        files={"file": ("logo.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        data={"slot": "logo"},
    )
    assert anon.status_code == 401
