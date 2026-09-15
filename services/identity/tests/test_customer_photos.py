"""Customer profile photo + live-capture photo uploads."""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from app.admin_routes import hash_password
from tests.conftest import SYNC_DB_URL

JWT_SECRET = os.environ.get("JWT_SECRET", "test-secret-key-for-pytest")

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)


async def _login(client: AsyncClient, phone: str = "+919611222333") -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    ok = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert ok.status_code == 200
    return ok.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_me_exposes_empty_photo_fields(client: AsyncClient):
    token = await _login(client, "+919611222001")
    me = await client.get("/api/v1/customers/me", headers=_auth(token))
    assert me.status_code == 200
    body = me.json()
    assert body["avatar_url"] is None
    assert body["live_photo_url"] is None
    assert body["live_photo_captured_at"] is None
    assert body["has_live_photo"] is False


@pytest.mark.asyncio
async def test_avatar_upload_sets_profile_photo(client: AsyncClient):
    token = await _login(client, "+919611222002")
    res = await client.post(
        "/api/v1/customers/me/avatar",
        headers=_auth(token),
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["avatar_url"]
    assert "customer-" in body["avatar_url"]
    assert "avatar" in body["avatar_url"]
    assert body["has_live_photo"] is False
    assert body["live_photo_url"] is None


@pytest.mark.asyncio
async def test_live_photo_rejected_without_live_flag(client: AsyncClient):
    token = await _login(client, "+919611222003")
    res = await client.post(
        "/api/v1/customers/me/live-photo",
        headers=_auth(token),
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "false"},
    )
    assert res.status_code == 400, res.text
    assert "live" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_live_photo_upload_requires_camera_flag(client: AsyncClient):
    token = await _login(client, "+919611222004")
    captured = "2026-09-15T08:30:00+00:00"
    res = await client.post(
        "/api/v1/customers/me/live-photo",
        headers=_auth(token),
        files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "true", "captured_at": captured},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["live_photo_url"]
    assert "live-photo" in body["live_photo_url"] or "live_photo" in body["live_photo_url"]
    assert body["has_live_photo"] is True
    assert body["live_photo_captured_at"]
    assert body["avatar_url"] is None


@pytest.mark.asyncio
async def test_patch_cannot_set_live_photo_url(client: AsyncClient):
    token = await _login(client, "+919611222005")
    res = await client.patch(
        "/api/v1/customers/me",
        headers=_auth(token),
        json={"live_photo_url": "https://evil.example/stock.jpg", "name": "Patched"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["name"] == "Patched"
    assert body["live_photo_url"] is None
    assert body["has_live_photo"] is False


@pytest.mark.asyncio
async def test_photo_uploads_blocked_when_flag_disabled(client: AsyncClient):
    token = await _login(client, "+919611222006")
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false "
            "WHERE key = 'customer_profile_photos'"
        )
    conn.close()
    try:
        avatar = await client.post(
            "/api/v1/customers/me/avatar",
            headers=_auth(token),
            files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
        )
        live = await client.post(
            "/api/v1/customers/me/live-photo",
            headers=_auth(token),
            files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
            data={"is_live_capture": "true"},
        )
        assert avatar.status_code == 403, avatar.text
        assert live.status_code == 403, live.text
        assert "customer_profile_photos" in avatar.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true "
                "WHERE key = 'customer_profile_photos'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_live_photo_upload_publishes_customer_updated(client: AsyncClient):
    from app.main import redis_client

    token = await _login(client, "+919611222007")
    if redis_client:
        await redis_client.delete("ckac:identity:customer")

    res = await client.post(
        "/api/v1/customers/me/live-photo",
        headers=_auth(token),
        files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "true"},
    )
    assert res.status_code == 200, res.text
    customer_id = res.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:customer": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "customer.updated"
    assert event_data["aggregate_id"] == customer_id
    assert event_data["payload"]["photo_kind"] == "live_photo"
    assert event_data["payload"]["has_live_photo"] is True
    assert "live_photo_url" not in event_data["payload"]


@pytest.mark.asyncio
async def test_admin_customer_detail_includes_photos(client: AsyncClient):
    token = await _login(client, "+919611222008")
    uploaded = await client.post(
        "/api/v1/customers/me/avatar",
        headers=_auth(token),
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    await client.post(
        "/api/v1/customers/me/live-photo",
        headers=_auth(token),
        files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "true"},
    )
    customer_id = uploaded.json()["id"]

    admin_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Photo Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, is_active = true
            RETURNING id
            """,
            (str(admin_id), "admin-photos@test.ckac", hash_password("admin123456")),
        )
        row = cur.fetchone()
        if row:
            admin_id = row[0]
        cur.execute(
            """
            INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
            VALUES ('superadmin', '*')
            ON CONFLICT DO NOTHING
            """
        )
    conn.close()
    admin_jwt = jwt.encode(
        {
            "sub": str(admin_id),
            "email": "admin-photos@test.ckac",
            "type": "admin",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    detail = await client.get(
        f"/api/v1/admin/customers/{customer_id}",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["avatar_url"]
    assert body["live_photo_url"]
    assert body["has_live_photo"] is True

    listing = await client.get(
        "/api/v1/admin/customers",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert listing.status_code == 200, listing.text
    row = next(r for r in listing.json() if r["id"] == customer_id)
    assert row["has_avatar"] is True
    assert row["has_live_photo"] is True
