"""Customer_* feature flag enforcement."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import SYNC_DB_URL

JWT_SECRET = os.environ.get("JWT_SECRET", "test-secret-key-for-pytest")


def _customer_token(customer_id: uuid.UUID) -> str:
    return jwt.encode(
        {
            "sub": str(customer_id),
            "type": "customer",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_customer() -> uuid.UUID:
    customer_id = uuid.uuid4()
    phone = f"+919{customer_id.int % 900000000 + 100000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ckac_identity.customers (id, name, phone, status) "
            "VALUES (%s::uuid, 'Flag Cust', %s, 'active')",
            (str(customer_id), phone),
        )
    conn.close()
    return customer_id


@pytest.mark.asyncio
async def test_addresses_blocked_when_flag_disabled(client: AsyncClient):
    customer_id = _seed_customer()
    headers = {"Authorization": f"Bearer {_customer_token(customer_id)}"}
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'customer_addresses'"
        )
    conn.close()
    try:
        res = await client.get("/api/v1/customers/me/addresses", headers=headers)
        assert res.status_code == 403, res.text
        assert "customer_addresses" in res.json()["detail"]

        addr_id = uuid.uuid4()
        upd = await client.put(
            f"/api/v1/customers/me/addresses/{addr_id}",
            headers=headers,
            json={
                "label": "Home",
                "address_line": "1 Main St",
                "city": "Pune",
                "pincode": "411001",
                "latitude": 18.52,
                "longitude": 73.85,
            },
        )
        assert upd.status_code == 403, upd.text

        deleted = await client.delete(
            f"/api/v1/customers/me/addresses/{addr_id}",
            headers=headers,
        )
        assert deleted.status_code == 403, deleted.text
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'customer_addresses'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_payout_qr_blocked_when_flag_disabled(client: AsyncClient):
    customer_id = _seed_customer()
    headers = {"Authorization": f"Bearer {_customer_token(customer_id)}"}
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'customer_payout_profile'"
        )
    conn.close()
    try:
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        res = await client.post(
            "/api/v1/customers/me/payout/qr",
            headers=headers,
            files={"file": ("qr.png", png, "image/png")},
        )
        assert res.status_code == 403, res.text
        assert "customer_payout_profile" in res.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'customer_payout_profile'"
            )
        conn.close()
