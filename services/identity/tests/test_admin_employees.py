"""Admin employees CRUD + RBAC gate — API tests."""

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
SUPER_EMAIL = "super-emp@test.ckac"
SUPPORT_EMAIL = "support-emp@test.ckac"


def _seed_admins() -> tuple[str, str]:
    super_id = uuid.uuid4()
    support_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Super', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET role = 'superadmin', is_active = true
            RETURNING id
            """,
            (str(super_id), SUPER_EMAIL),
        )
        row = cur.fetchone()
        super_id = row[0] if row else super_id
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Support', 'support', true)
            ON CONFLICT (email) DO UPDATE SET role = 'support', is_active = true
            RETURNING id
            """,
            (str(support_id), SUPPORT_EMAIL),
        )
        row = cur.fetchone()
        support_id = row[0] if row else support_id
        # Ensure support lacks employees:write if role grants exist
        cur.execute(
            """
            DELETE FROM ckac_identity.admin_role_permissions
            WHERE role = 'support' AND permission_code LIKE 'employees%%'
            """
        )
    conn.close()
    return str(super_id), str(support_id)


def _token(admin_id: str, email: str) -> str:
    return jwt.encode(
        {"sub": admin_id, "type": "admin", "email": email},
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_superadmin_employees_crud(client: AsyncClient):
    super_id, _ = _seed_admins()
    headers = {"Authorization": f"Bearer {_token(super_id, SUPER_EMAIL)}"}

    roles = await client.get("/api/v1/admin/employees/roles", headers=headers)
    assert roles.status_code == 200, roles.text
    assert "superadmin" in roles.json()
    assert "support" in roles.json()

    email = f"new-{uuid.uuid4().hex[:8]}@test.ckac"
    created = await client.post(
        "/api/v1/admin/employees",
        headers=headers,
        json={
            "email": email,
            "name": "Ops Hire",
            "password": "securepass99",
            "role": "ops",
        },
    )
    assert created.status_code == 201, created.text
    emp = created.json()
    assert emp["email"] == email
    assert emp["role"] == "ops"
    assert emp["is_active"] is True

    listed = await client.get("/api/v1/admin/employees", headers=headers)
    assert listed.status_code == 200
    assert any(r["id"] == emp["id"] for r in listed.json())

    patched = await client.patch(
        f"/api/v1/admin/employees/{emp['id']}",
        headers=headers,
        json={"role": "finance", "name": "Finance Hire"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["role"] == "finance"
    assert patched.json()["name"] == "Finance Hire"

    deactivated = await client.post(
        f"/api/v1/admin/employees/{emp['id']}/deactivate",
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False


@pytest.mark.asyncio
async def test_support_cannot_create_employees(client: AsyncClient):
    _, support_id = _seed_admins()
    headers = {"Authorization": f"Bearer {_token(support_id, SUPPORT_EMAIL)}"}

    # If RBAC tables empty, support may get empty grants → 403
    res = await client.post(
        "/api/v1/admin/employees",
        headers=headers,
        json={
            "email": f"blocked-{uuid.uuid4().hex[:6]}@test.ckac",
            "name": "Blocked",
            "password": "securepass99",
            "role": "ops",
        },
    )
    assert res.status_code == 403, res.text
