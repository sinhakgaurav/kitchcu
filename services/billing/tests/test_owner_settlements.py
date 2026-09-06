"""Owner kitchen settlements list — TDD."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET
from tests.test_master_payments import _seed_master_order_context


def _owner_headers(owner_id: uuid.UUID) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(owner_id),
            "type": "owner",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _owner_ids_for_master(master_id: uuid.UUID) -> list[tuple[uuid.UUID, uuid.UUID]]:
    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.kitchen_id, k.owner_id
            FROM ckac_orders.orders o
            JOIN ckac_identity.kitchens k ON k.id = o.kitchen_id
            WHERE o.master_order_id = %s::uuid
            ORDER BY o.kitchen_id
            """,
            (str(master_id),),
        )
        rows = [(uuid.UUID(str(r[0])), uuid.UUID(str(r[1]))) for r in cur.fetchall()]
    conn.close()
    return rows


@pytest.mark.asyncio
async def test_owner_settlements_requires_auth(client: AsyncClient):
    kid = uuid.uuid4()
    resp = await client.get(f"/api/v1/billing/kitchens/{kid}/settlements")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_owner_sees_own_kitchen_settlements_only(client: AsyncClient):
    master_id, _, customer_headers = _seed_master_order_context()
    kitchen_owners = _owner_ids_for_master(master_id)
    assert len(kitchen_owners) == 2
    kitchen_a, owner_a = kitchen_owners[0]
    kitchen_b, owner_b = kitchen_owners[1]

    created = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=customer_headers,
    )
    assert created.status_code == 201, created.text
    payment_id = created.json()["id"]
    captured = await client.post(
        f"/api/v1/billing/payments/customer/master/{payment_id}/capture",
        headers=customer_headers,
    )
    assert captured.status_code == 200, captured.text
    assert len(captured.json()["settlements"]) == 2

    own = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_a}/settlements",
        headers=_owner_headers(owner_a),
    )
    assert own.status_code == 200, own.text
    rows = own.json()
    assert len(rows) == 1
    assert rows[0]["kitchen_id"] == str(kitchen_a)
    assert rows[0]["kitchen_id"] != str(kitchen_b)
    assert "net_to_owner" in rows[0]
    assert "settlement_status" in rows[0]


@pytest.mark.asyncio
async def test_owner_settlements_tenant_isolation(client: AsyncClient):
    master_id, _, customer_headers = _seed_master_order_context()
    kitchen_owners = _owner_ids_for_master(master_id)
    kitchen_a, _owner_a = kitchen_owners[0]
    _kitchen_b, owner_b = kitchen_owners[1]

    created = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=customer_headers,
    )
    payment_id = created.json()["id"]
    await client.post(
        f"/api/v1/billing/payments/customer/master/{payment_id}/capture",
        headers=customer_headers,
    )

    cross = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_a}/settlements",
        headers=_owner_headers(owner_b),
    )
    assert cross.status_code == 403
