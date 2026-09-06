"""Super-admin kitchen profile correction — address and map pin."""

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-kitchen-profile@test.ckac"


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
            VALUES (%s::uuid, %s, 'hash', 'Profile Admin', 'superadmin', true)
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
            VALUES (%s::uuid, %s, 'Profile Owner', 'starter', 'trial')
            """,
            (str(owner_id), f"+9198{owner_id.int % 900000000 + 100000000}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, address_line, city, state, pincode, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Wrong Pin Kitchen', 'Old Street', 'Pune',
                'Maharashtra', '411001',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKP{owner_id.hex[:4].upper()}"),
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
async def test_admin_kitchen_profile_patch_requires_auth(client: AsyncClient):
    response = await client.patch(
        f"/api/v1/admin/kitchens/{uuid.uuid4()}/profile",
        json={"name": "Ops Fix"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_kitchen_profile_can_correct_address_and_pin(client: AsyncClient):
    kitchen_id, admin_id = _seed()
    headers = {"Authorization": f"Bearer {_admin_token(admin_id)}"}

    response = await client.patch(
        f"/api/v1/admin/kitchens/{kitchen_id}/profile",
        json={
            "name": "Corrected Kitchen",
            "address_line": "New Lane",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411014",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Corrected Kitchen"
    assert data["address_line"] == "New Lane"
    assert data["pincode"] == "411014"
    assert data["latitude"] == pytest.approx(18.5204, rel=1e-4)
    assert data["longitude"] == pytest.approx(73.8567, rel=1e-4)

    detail = await client.get(f"/api/v1/admin/kitchens/{kitchen_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"] == "Corrected Kitchen"
    assert body["latitude"] == pytest.approx(18.5204, rel=1e-4)
