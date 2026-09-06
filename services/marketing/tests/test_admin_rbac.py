"""Marketing admin must use shared RBAC so superadmin '*' fallback works."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL, _seed_marketing_ctx


def _admin_token(admin_id: uuid.UUID, email: str) -> str:
    return jwt.encode(
        {
            "sub": str(admin_id),
            "type": "admin",
            "email": email,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_admin(role: str) -> str:
    admin_id = uuid.uuid4()
    email = f"{role}-{admin_id.hex[:8]}@kitchcu.dev"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', %s, %s, true)
            """,
            (str(admin_id), email, f"{role} Admin", role),
        )
    conn.close()
    return _admin_token(admin_id, email)


def _replace_role_grants(role: str, grants: list[str]) -> list[str]:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT permission_code FROM ckac_identity.admin_role_permissions WHERE role = %s",
            (role,),
        )
        previous = [str(r[0]) for r in cur.fetchall()]
        cur.execute("DELETE FROM ckac_identity.admin_role_permissions WHERE role = %s", (role,))
        for code in grants:
            cur.execute(
                """
                INSERT INTO ckac_identity.admin_permissions (code, description)
                VALUES (%s, %s)
                ON CONFLICT (code) DO NOTHING
                """,
                (code, code),
            )
            cur.execute(
                """
                INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (role, code),
            )
    conn.close()
    return previous


def _restore_role_grants(role: str, grants: list[str]) -> None:
    _replace_role_grants(role, grants)


@pytest.mark.asyncio
async def test_superadmin_without_db_grants_can_read_templates(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    token = _seed_admin("superadmin")
    previous = _replace_role_grants("superadmin", [])
    headers = {"Authorization": f"Bearer {token}"}
    try:
        listed = await client.get(
            f"/api/v1/admin/kitchens/{kitchen_id}/templates",
            headers=headers,
        )
        assert listed.status_code == 200, listed.text
    finally:
        _restore_role_grants("superadmin", previous or ["*"])


@pytest.mark.asyncio
async def test_admin_without_marketing_read_is_forbidden(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    token = _seed_admin("finance")
    previous = _replace_role_grants("finance", ["refunds:read"])
    headers = {"Authorization": f"Bearer {token}"}
    try:
        listed = await client.get(
            f"/api/v1/admin/kitchens/{kitchen_id}/templates",
            headers=headers,
        )
        assert listed.status_code == 403
        assert "marketing:read" in listed.json()["detail"]
    finally:
        _restore_role_grants("finance", previous)
