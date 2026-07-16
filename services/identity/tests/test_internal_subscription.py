"""Internal subscription sync — billing → identity boundary."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import SYNC_DB_URL


@pytest.mark.asyncio
async def test_internal_subscription_sync_updates_owner():
    import sys
    from pathlib import Path

    identity_root = Path(__file__).resolve().parents[2] / "identity"
    if str(identity_root) not in sys.path:
        sys.path.insert(0, str(identity_root))

    from app.main import app as identity_app

    owner_id = uuid.uuid4()
    phone = f"+91{owner_id.int % 9000000000 + 1000000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status) "
            "VALUES (%s::uuid, %s, 'Internal Sync', 'starter', 'trial')",
            (str(owner_id), phone),
        )
    conn.close()

    expires = datetime.now(UTC) + timedelta(days=30)
    transport = ASGITransport(app=identity_app)
    async with AsyncClient(transport=transport, base_url="http://identity") as client:
        res = await client.patch(
            f"/api/v1/internal/owners/{owner_id}/subscription",
            json={
                "plan_tier": "growth",
                "subscription_status": "active",
                "subscription_expires_at": expires.isoformat(),
            },
            headers={"X-Internal-Key": os.environ.get("INTERNAL_API_KEY", "test-internal-key-for-pytest")},
        )
    assert res.status_code == 204, res.text

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT subscription_tier, subscription_status FROM ckac_identity.owners WHERE id = %s::uuid",
            (str(owner_id),),
        )
        tier, status = cur.fetchone()
    conn.close()
    assert tier == "growth"
    assert status == "active"


@pytest.mark.asyncio
async def test_internal_subscription_sync_rejects_bad_key():
    import sys
    from pathlib import Path

    identity_root = Path(__file__).resolve().parents[2] / "identity"
    if str(identity_root) not in sys.path:
        sys.path.insert(0, str(identity_root))

    from app.main import app as identity_app

    transport = ASGITransport(app=identity_app)
    async with AsyncClient(transport=transport, base_url="http://identity") as client:
        res = await client.patch(
            f"/api/v1/internal/owners/{uuid.uuid4()}/subscription",
            json={
                "plan_tier": "starter",
                "subscription_status": "active",
                "subscription_expires_at": datetime.now(UTC).isoformat(),
            },
            headers={"X-Internal-Key": "wrong-key"},
        )
    assert res.status_code == 403
