"""Admin kitchen stream summary — JWT, RBAC, no publisher_token leak."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL


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


def _seed_admin(role: str, *, grants: list[str] | None = None) -> str:
    admin_id = uuid.uuid4()
    email = f"stream-{role}-{admin_id.hex[:8]}@kitchcu.dev"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', %s, %s, true)
            """,
            (str(admin_id), email, f"{role} Stream Admin", role),
        )
        if grants is not None:
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
    return _admin_token(admin_id, email)


@pytest.mark.asyncio
async def test_admin_stream_summary_requires_auth(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    resp = await client.get(f"/api/v1/admin/kitchens/{kid}/stream/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_stream_summary_forbidden_without_permission(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    token = _seed_admin("auditor", grants=["refunds:read"])
    resp = await client.get(
        f"/api/v1/admin/kitchens/{kid}/stream/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "streaming:read" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_stream_summary_omits_publisher_token(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {stream_ctx['owner_token']}"}
    await client.patch(
        f"/api/v1/kitchens/{kid}/stream/settings",
        json={"live_sharing_enabled": True},
        headers=owner_headers,
    )
    live = await client.post(
        f"/api/v1/kitchens/{kid}/stream/go-live",
        json={"title": "Admin watch"},
        headers=owner_headers,
    )
    assert live.status_code == 200, live.text

    token = _seed_admin("superadmin", grants=["*"])
    summary = await client.get(
        f"/api/v1/admin/kitchens/{kid}/stream/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    dumped = str(body)
    assert "publisher_token" not in dumped
    assert body["settings"]["kitchen_id"] == str(kid)
    assert body["settings"]["is_live"] is True
    assert body["current_session"] is not None
    assert body["current_session"]["id"] == live.json()["id"]
    assert "publisher_token" not in body["current_session"]
