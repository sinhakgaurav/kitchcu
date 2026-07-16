"""Per-kitchen module kill-switches (admin + enforcement)."""

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]

ADMIN_EMAIL = "admin-modules@test.ckac"


def _sync_db_url() -> str:
    return os.environ["DATABASE_SYNC_URL"]


def _seed_admin_and_kitchen() -> tuple[uuid.UUID, str]:
    kitchen_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    conn = psycopg2.connect(_sync_db_url())
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Module Admin', 'superadmin', true)
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
            VALUES (%s::uuid, %s, 'Module Owner', 'starter', 'trial')
            """,
            (str(owner_id), f"+9199{owner_id.int % 900000000 + 100000000}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Module Test Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKM{owner_id.hex[:4].upper()}"),
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
async def test_admin_can_disable_kitchen_module(client: AsyncClient):
    kitchen_id, admin_id = _seed_admin_and_kitchen()
    admin_headers = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    listed = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/module-flags",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    modules = {m["module_key"]: m for m in listed.json()["modules"]}
    assert "marketing_broadcast" in modules

    patch = await client.patch(
        f"/api/v1/admin/kitchens/{kitchen_id}/module-flags/marketing_broadcast",
        json={"enabled": False},
        headers=admin_headers,
    )
    assert patch.status_code == 200
    assert patch.json()["enabled"] is False

    conn = psycopg2.connect(_sync_db_url())
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT enabled FROM ckac_identity.kitchen_module_flags
            WHERE kitchen_id = %s::uuid AND module_key = 'marketing_broadcast'
            """,
            (str(kitchen_id),),
        )
        assert cur.fetchone()[0] is False
    conn.close()
