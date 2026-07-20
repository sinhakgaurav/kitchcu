"""Super-admin kitchen branded storefront — list flag + PATCH workspace."""

import io
import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from ckac_common.storage import reset_media_storage

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-brand-page@test.ckac"
os.environ.setdefault("MEDIA_STORAGE_BACKEND", "local")


def _jpeg_bytes() -> bytes:
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\x7f\xff\xd9"
    )


def _seed() -> tuple[uuid.UUID, str]:
    kitchen_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Brand Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET is_active = true
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL),
        )
        row = cur.fetchone()
        admin_id = row[0] if row else admin_id
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Brand Owner', 'starter', 'trial')
            """,
            (str(owner_id), f"+9198{owner_id.int % 900000000 + 100000000}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status, city)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Brand Test Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active', 'Pune'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKB{owner_id.hex[:4].upper()}"),
        )
    conn.close()
    return kitchen_id, str(admin_id)


def _admin_token(admin_id: str) -> str:
    return jwt.encode(
        {"sub": admin_id, "type": "admin", "email": ADMIN_EMAIL},
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_admin_kitchen_branded_page_publish(client: AsyncClient):
    kitchen_id, admin_id = _seed()
    headers = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    detail = await client.get(f"/api/v1/admin/kitchens/{kitchen_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["branded_page_enabled"] is False
    assert body["branded_page"]["enabled"] is False

    patched = await client.patch(
        f"/api/v1/admin/kitchens/{kitchen_id}/branded-page",
        headers=headers,
        json={
            "enabled": True,
            "tagline": "Ops published storefront",
            "accent_color": "#0F766E",
        },
    )
    assert patched.status_code == 200, patched.text
    next_body = patched.json()
    assert next_body["branded_page_enabled"] is True
    assert next_body["branded_page"]["enabled"] is True
    assert next_body["branded_page"]["tagline"] == "Ops published storefront"
    assert next_body["branded_page"]["accent_color"] == "#0F766E"

    listed = await client.get("/api/v1/admin/kitchens", headers=headers)
    assert listed.status_code == 200
    row = next(k for k in listed.json() if k["id"] == str(kitchen_id))
    assert row["branded_page_enabled"] is True


@pytest.mark.asyncio
async def test_admin_kitchen_branded_page_media_urls(client: AsyncClient):
    kitchen_id, admin_id = _seed()
    headers = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    patched = await client.patch(
        f"/api/v1/admin/kitchens/{kitchen_id}/branded-page",
        headers=headers,
        json={
            "enabled": True,
            "logo_url": "https://cdn.example.com/admin-logo.png",
            "background_url": "https://cdn.example.com/admin-bg.jpg",
            "tagline": "Ops brand art",
        },
    )
    assert patched.status_code == 200, patched.text
    bp = patched.json()["branded_page"]
    assert bp["logo_url"] == "https://cdn.example.com/admin-logo.png"
    assert bp["background_url"] == "https://cdn.example.com/admin-bg.jpg"
    assert bp["tagline"] == "Ops brand art"


@pytest.mark.asyncio
async def test_admin_kitchen_branded_page_media_upload(client: AsyncClient):
    os.environ["MEDIA_STORAGE_BACKEND"] = "local"
    reset_media_storage()
    kitchen_id, admin_id = _seed()
    headers = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    uploaded = await client.post(
        f"/api/v1/admin/kitchens/{kitchen_id}/branded-page/media",
        headers=headers,
        files={"file": ("logo.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")},
        data={"slot": "logo"},
    )
    assert uploaded.status_code == 200, uploaded.text
    bp = uploaded.json()["branded_page"]
    assert bp["logo_url"]
    assert bp["logo_url"].startswith("file://") or bp["logo_url"].startswith("http")
