"""Feature flag enforcement + OTP gating for identity."""

import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


@pytest.mark.asyncio
async def test_owner_register_blocked_when_flag_disabled(client: AsyncClient):
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'owner_registrations'"
    )
    cur.close()
    conn.close()
    try:
        phone = str(uuid.uuid4().int % 9000000000 + 1000000000)
        res = await client.post(
            "/api/v1/owners/register",
            json={"phone": phone, "name": "Blocked Owner"},
        )
        assert res.status_code == 403, res.text
        assert "owner_registrations" in res.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'owner_registrations'"
        )
        cur.close()
        conn.close()


@pytest.mark.asyncio
async def test_dev_otp_hint_returned_in_test_env(client: AsyncClient):
    # APP_ENV=test in conftest → fixed demo OTP allowed
    phone = "9876500099"
    await client.post("/api/v1/owners/register", json={"phone": phone, "name": "OTP Owner"})
    req = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req.status_code == 202
    body = req.json()
    assert "dev_hint" in body
    assert "123456" in body["dev_hint"]
