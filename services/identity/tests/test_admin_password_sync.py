"""Bootstrap admin password stays aligned with ADMIN_EMAIL / ADMIN_PASSWORD env."""

import os
import uuid

import bcrypt
import psycopg2
import pytest
from httpx import AsyncClient

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]


@pytest.mark.asyncio
async def test_admin_login_resyncs_password_from_env(client: AsyncClient, monkeypatch):
    email = "admin-sync@test.ckac"
    stale_hash = bcrypt.hashpw(b"old-password-999999", bcrypt.gensalt()).decode()
    admin_id = uuid.uuid4()

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins
            (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Sync Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE
              SET password_hash = EXCLUDED.password_hash, is_active = true
            """,
            (str(admin_id), email, stale_hash),
        )
    conn.close()

    monkeypatch.setattr("app.admin_routes.settings.admin_email", email)
    monkeypatch.setattr("app.admin_routes.settings.admin_password", "new-password-123456")

    # ensure_default_admin runs on login and rewrites hash from ADMIN_PASSWORD env
    fresh = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": email, "password": "new-password-123456"},
    )
    assert fresh.status_code == 200, fresh.text
    assert "access_token" in fresh.json()

    stale = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": email, "password": "old-password-999999"},
    )
    assert stale.status_code == 401
