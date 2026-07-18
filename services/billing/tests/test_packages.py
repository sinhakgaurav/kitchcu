"""Admin package mapper — features → packages → plans → kitchen."""

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-pkg@test.ckac"


def _admin_token() -> str:
    admin_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Pkg Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET is_active = true, role = 'superadmin'
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL),
        )
        row = cur.fetchone()
        admin_id = row[0] if row else admin_id
    conn.close()
    return jwt.encode(
        {"sub": str(admin_id), "type": "admin", "email": ADMIN_EMAIL},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_kitchen() -> uuid.UUID:
    kitchen_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Pkg Owner', 'starter', 'trial')
            """,
            (str(owner_id), f"+9198{owner_id.int % 900000000 + 100000000}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status, city)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Pkg Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active', 'Pune'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKP{owner_id.hex[:4].upper()}"),
        )
    conn.close()
    return kitchen_id


@pytest.mark.asyncio
async def test_package_mapper_crud_and_kitchen_assign(client: AsyncClient):
    headers = {"Authorization": f"Bearer {_admin_token()}"}
    kitchen_id = _seed_kitchen()

    features = await client.get("/api/v1/admin/features", headers=headers)
    assert features.status_code == 200, features.text
    keys = [f["key"] for f in features.json()]
    assert "whatsapp" in keys or len(keys) >= 1

    code = f"test-{uuid.uuid4().hex[:8]}"
    feature_keys = keys[:2] if len(keys) >= 2 else keys
    created = await client.post(
        "/api/v1/admin/packages",
        headers=headers,
        json={
            "code": code,
            "name": "Test Bundle",
            "audience": "owner",
            "description": "pytest package",
            "is_active": True,
            "feature_keys": feature_keys,
            "plan_tiers": ["starter"],
        },
    )
    assert created.status_code in (200, 201), created.text
    pkg = created.json()
    assert pkg["code"] == code
    assert set(pkg["feature_keys"]) == set(feature_keys)

    listed = await client.get("/api/v1/admin/packages", headers=headers)
    assert listed.status_code == 200
    assert any(p["id"] == pkg["id"] for p in listed.json())

    assigned = await client.put(
        f"/api/v1/admin/kitchens/{kitchen_id}/package",
        headers=headers,
        json={"package_id": pkg["id"], "notes": "pytest", "sync_module_flags": False},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["package"]["id"] == pkg["id"]
    assert body["source"] in ("assigned", "plan_default")

    got = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/package",
        headers=headers,
    )
    assert got.status_code == 200
    assert got.json()["package"]["code"] == code
