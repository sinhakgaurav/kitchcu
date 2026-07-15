"""Platform API keys — super-admin Control (TDD)."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
from jose import jwt

from tests.conftest import SYNC_DB_URL

JWT_SECRET = "test-secret-key-for-pytest"
ADMIN_EMAIL = "admin@test.ckac"
ADMIN_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _seed_admin() -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Test Admin', 'superadmin', true)
            ON CONFLICT (id) DO NOTHING
            """,
            (ADMIN_ID, ADMIN_EMAIL),
        )
    conn.close()


def _admin_token() -> str:
    return jwt.encode(
        {
            "sub": ADMIN_ID,
            "email": ADMIN_EMAIL,
            "type": "admin",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


async def test_admin_api_keys_list_and_upsert_masks_secret(client):
    _seed_admin()
    headers = {"Authorization": f"Bearer {_admin_token()}"}

    listed = await client.get("/api/v1/admin/api-keys", headers=headers)
    assert listed.status_code == 200, listed.text
    keys = listed.json()
    assert any(k["key"] == "razorpay_key_secret" for k in keys)
    rz = next(k for k in keys if k["key"] == "razorpay_key_secret")
    assert rz["configured"] is False
    assert rz["is_secret"] is True

    put = await client.put(
        "/api/v1/admin/api-keys/razorpay_key_secret",
        headers=headers,
        json={"value": "sk_test_super_secret_value_1234"},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["configured"] is True
    assert body["value_masked"] is not None
    assert "super_secret" not in (body["value_masked"] or "")
    assert body["value_masked"].endswith("1234")

    listed2 = await client.get("/api/v1/admin/api-keys", headers=headers)
    rz2 = next(k for k in listed2.json() if k["key"] == "razorpay_key_secret")
    assert rz2["configured"] is True

    cleared = await client.delete(
        "/api/v1/admin/api-keys/razorpay_key_secret",
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["configured"] is False


async def test_admin_api_key_unknown_slot_404(client):
    _seed_admin()
    headers = {"Authorization": f"Bearer {_admin_token()}"}
    res = await client.put(
        f"/api/v1/admin/api-keys/not_a_real_key_{uuid.uuid4().hex[:8]}",
        headers=headers,
        json={"value": "x"},
    )
    assert res.status_code == 404
