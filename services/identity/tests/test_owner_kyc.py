"""Owner KYC — profile photo, live photo, Aadhaar, PAN."""

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
from app.owner_kyc import mask_aadhaar, mask_pan, normalize_aadhaar, normalize_pan
from tests.conftest import SYNC_DB_URL

JWT_SECRET = os.environ.get("JWT_SECRET", "test-secret-key-for-pytest")

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)

AADHAAR = "234123412347"
PAN = "ABCDE1234F"


def test_normalize_and_mask_ids():
    assert normalize_aadhaar("2341 2341 2347") == AADHAAR
    assert mask_aadhaar(AADHAAR) == "XXXX-XXXX-2347"
    assert normalize_pan("abcde1234f") == PAN
    assert mask_pan(PAN) == "XXXXX1234F"
    with pytest.raises(ValueError):
        normalize_aadhaar("123412341234")
    with pytest.raises(ValueError):
        normalize_pan("ABCDE12345")


@pytest.mark.asyncio
async def test_owner_me_exposes_empty_kyc(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/v1/owners/me", headers=auth_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["avatar_url"] is None
    assert body["live_photo_url"] is None
    assert body["aadhaar_masked"] is None
    assert body["pan_masked"] is None
    assert body["has_live_photo"] is False
    assert body["kyc_complete"] is False
    assert "aadhaar_number" not in body
    assert "pan_number" not in body


@pytest.mark.asyncio
async def test_owner_kyc_ids_masked_on_read(client: AsyncClient, auth_headers: dict):
    res = await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"aadhaar_number": AADHAAR, "pan_number": PAN},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["aadhaar_masked"] == "XXXX-XXXX-2347"
    assert body["pan_masked"] == "XXXXX1234F"
    assert AADHAAR not in res.text
    assert PAN not in res.text
    assert body["kyc_complete"] is False


@pytest.mark.asyncio
async def test_owner_kyc_rejects_invalid_ids(client: AsyncClient, auth_headers: dict):
    bad_a = await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"aadhaar_number": "000000000000"},
    )
    bad_p = await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"pan_number": "12345ABCDE"},
    )
    assert bad_a.status_code == 400
    assert bad_p.status_code == 400


@pytest.mark.asyncio
async def test_owner_avatar_and_live_photo(client: AsyncClient, auth_headers: dict):
    avatar = await client.post(
        "/api/v1/owners/me/avatar",
        headers=auth_headers,
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
    )
    assert avatar.status_code == 200, avatar.text
    assert avatar.json()["avatar_url"]
    assert "owner-" in avatar.json()["avatar_url"]

    rejected = await client.post(
        "/api/v1/owners/me/live-photo",
        headers=auth_headers,
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "false"},
    )
    assert rejected.status_code == 400

    live = await client.post(
        "/api/v1/owners/me/live-photo",
        headers=auth_headers,
        files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "true"},
    )
    assert live.status_code == 200, live.text
    assert live.json()["has_live_photo"] is True
    assert live.json()["live_photo_url"]


@pytest.mark.asyncio
async def test_owner_kyc_complete_after_photos_and_ids(client: AsyncClient, auth_headers: dict):
    await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"aadhaar_number": AADHAAR, "pan_number": PAN},
    )
    await client.post(
        "/api/v1/owners/me/avatar",
        headers=auth_headers,
        files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
    )
    live = await client.post(
        "/api/v1/owners/me/live-photo",
        headers=auth_headers,
        files={"file": ("live.png", io.BytesIO(PNG), "image/png")},
        data={"is_live_capture": "true"},
    )
    assert live.status_code == 200
    assert live.json()["kyc_complete"] is True


@pytest.mark.asyncio
async def test_owner_kyc_blocked_when_flag_disabled(client: AsyncClient, auth_headers: dict):
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'owner_kyc'"
        )
    conn.close()
    try:
        patch = await client.patch(
            "/api/v1/owners/me",
            headers=auth_headers,
            json={"pan_number": PAN},
        )
        upload = await client.post(
            "/api/v1/owners/me/avatar",
            headers=auth_headers,
            files={"file": ("face.png", io.BytesIO(PNG), "image/png")},
        )
        assert patch.status_code == 403, patch.text
        assert upload.status_code == 403, upload.text
        assert "owner_kyc" in patch.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'owner_kyc'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_owner_kyc_publishes_owner_updated(client: AsyncClient, auth_headers: dict):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:identity:owner")

    res = await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"aadhaar_number": AADHAAR, "pan_number": PAN},
    )
    assert res.status_code == 200
    owner_id = res.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:owner": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "owner.updated"
    assert event_data["aggregate_id"] == owner_id
    assert event_data["payload"]["has_aadhaar"] is True
    assert "aadhaar_number" not in event_data["payload"]
    assert AADHAAR not in json.dumps(event_data)


@pytest.mark.asyncio
async def test_admin_kitchen_kyc_is_masked(
    client: AsyncClient, auth_headers: dict, registered_owner: dict
):
    await client.patch(
        "/api/v1/owners/me",
        headers=auth_headers,
        json={"aadhaar_number": AADHAAR, "pan_number": PAN},
    )
    kitchen = await client.post(
        "/api/v1/kitchens",
        headers=auth_headers,
        json={
            "name": "KYC Kitchen",
            "address_line": "Koregaon Park",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
            "latitude": 18.5362,
            "longitude": 73.8958,
        },
    )
    assert kitchen.status_code == 201, kitchen.text
    kitchen_id = kitchen.json()["id"]

    admin_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'KYC Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, is_active = true
            RETURNING id
            """,
            (str(admin_id), "admin-owner-kyc@test.ckac", hash_password("admin123456")),
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
            "email": "admin-owner-kyc@test.ckac",
            "type": "admin",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    detail = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["owner_aadhaar_masked"] == "XXXX-XXXX-2347"
    assert body["owner_pan_masked"] == "XXXXX1234F"
    assert AADHAAR not in detail.text
    assert PAN not in detail.text
    assert registered_owner["id"] == body["owner_id"]
