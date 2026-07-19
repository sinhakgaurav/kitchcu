"""Super-admin kitchen branded storefront — list flag + PATCH workspace."""

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-brand-page@test.ckac"


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
