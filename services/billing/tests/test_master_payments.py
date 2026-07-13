"""F44 master order split payment tests."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL

PLATFORM_FEE = 0.0


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


def _seed_master_order_context() -> tuple[uuid.UUID, uuid.UUID, dict[str, str]]:
    customer_id = uuid.uuid4()
    master_id = uuid.uuid4()
    order_a = uuid.uuid4()
    order_b = uuid.uuid4()
    kitchen_a = uuid.uuid4()
    kitchen_b = uuid.uuid4()
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    phone = "+919911223344"

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status)
            VALUES (%s::uuid, 'Split Customer', %s, 'active')
            """,
            (str(customer_id), phone),
        )
        for owner_id, kitchen_id, code, total in (
            (owner_a, kitchen_a, "CKSPL001", 398.0),
            (owner_b, kitchen_b, "CKSPL002", 191.0),
        ):
            cur.execute(
                """
                INSERT INTO ckac_identity.owners
                    (id, phone, name, subscription_tier, subscription_status)
                VALUES (%s::uuid, %s, 'Owner', 'starter', 'trial')
                """,
                (str(owner_id), f"+91{owner_id.int % 9000000000 + 1000000000}"),
            )
            cur.execute(
                """
                INSERT INTO ckac_identity.kitchens
                    (id, owner_id, code, name, location, status, settings)
                VALUES (
                    %s::uuid, %s::uuid, %s, %s,
                    ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                    'active',
                    %s::jsonb
                )
                """,
                (
                    str(kitchen_id),
                    str(owner_id),
                    code,
                    f"Kitchen {code}",
                    json.dumps({"razorpay_linked_account_id": f"acc_dev_{code.lower()}"}),
                ),
            )

        cur.execute(
            """
            INSERT INTO ckac_orders.master_orders
                (id, master_order_code, customer_id, customer_name, customer_phone,
                 idempotency_key, status, payment_method, subtotal, delivery_fee, total)
            VALUES (
                %s::uuid, 'MORD-20260713-ABCD', %s::uuid, 'Split Customer', %s,
                'idem-split-001', 'created', 'online', 549.0, 40.0, 589.0
            )
            """,
            (str(master_id), str(customer_id), phone),
        )
        for order_id, kitchen_id, code, subtotal, delivery, total in (
            (order_a, kitchen_a, "CKSPL001-BILL-20260713-0001", 398.0, 0.0, 398.0),
            (order_b, kitchen_b, "CKSPL002-BILL-20260713-0001", 151.0, 40.0, 191.0),
        ):
            cur.execute(
                """
                INSERT INTO ckac_orders.orders
                    (id, kitchen_id, master_order_id, bill_id, order_code, status, source,
                     delivery_type, payment_method, customer_phone, subtotal, delivery_fee, total)
                VALUES (
                    %s::uuid, %s::uuid, %s::uuid, 'BILL-20260713-0001', %s,
                    'received', 'customer_pwa_multi', 'delivery', 'online', %s,
                    %s, %s, %s
                )
                """,
                (
                    str(order_id),
                    str(kitchen_id),
                    str(master_id),
                    code,
                    phone,
                    subtotal,
                    delivery,
                    total,
                ),
            )
    conn.close()
    headers = {
        "Authorization": f"Bearer {_customer_token(customer_id)}",
    }
    return master_id, customer_id, headers


@pytest.mark.asyncio
async def test_create_master_payment(client: AsyncClient):
    master_id, _, headers = _seed_master_order_context()
    response = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["master_order_id"] == str(master_id)
    assert data["amount"] == 589.0
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_master_payment_rejects_cod_master_order(client: AsyncClient):
    master_id, _, headers = _seed_master_order_context()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_orders.master_orders SET payment_method = 'cod' WHERE id = %s::uuid",
            (str(master_id),),
        )
    conn.close()

    response = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "COD" in response.json()["detail"]


@pytest.mark.asyncio
async def test_capture_master_payment_creates_settlements_and_events(client: AsyncClient):
    master_id, _, headers = _seed_master_order_context()

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:payment", "ckac:billing:settlement")

    create = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=headers,
    )
    payment_id = create.json()["id"]

    capture = await client.post(
        f"/api/v1/billing/payments/customer/master/{payment_id}/capture",
        headers=headers,
    )
    assert capture.status_code == 200
    body = capture.json()
    assert body["payment"]["status"] == "captured"
    assert len(body["settlements"]) == 2
    assert sum(s["net_to_owner"] for s in body["settlements"]) == pytest.approx(589.0)
    assert all(s["settlement_status"] == "transferred" for s in body["settlements"])
    assert all(s["razorpay_transfer_id"].startswith("trf_dev_") for s in body["settlements"])

    assert redis_client is not None
    payment_messages = await redis_client.xread({"ckac:billing:payment": "0-0"}, count=20)
    settlement_messages = await redis_client.xread({"ckac:billing:settlement": "0-0"}, count=20)
    payment_events = [
        json.loads(entry[1]["data"])
        for _, entries in payment_messages
        for entry in entries
    ]
    split_events = [
        json.loads(entry[1]["data"])
        for _, entries in settlement_messages
        for entry in entries
    ]
    assert "payment.captured" in {event["event_type"] for event in payment_events}
    split = next(event for event in split_events if event["event_type"] == "payment.split.completed")
    assert split["aggregate_id"] == str(master_id)
    assert len(split["payload"]["transfers"]) == 2

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM ckac_billing.settlements WHERE master_order_id = %s::uuid",
            (str(master_id),),
        )
        assert cur.fetchone()[0] == 2
    conn.close()


@pytest.mark.asyncio
async def test_master_payment_capture_is_idempotent(client: AsyncClient):
    master_id, _, headers = _seed_master_order_context()
    create = await client.post(
        "/api/v1/billing/payments/customer/master",
        json={"master_order_id": str(master_id), "method": "online"},
        headers=headers,
    )
    payment_id = create.json()["id"]

    first = await client.post(
        f"/api/v1/billing/payments/customer/master/{payment_id}/capture",
        headers=headers,
    )
    second = await client.post(
        f"/api/v1/billing/payments/customer/master/{payment_id}/capture",
        headers=headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["settlements"]) == len(second.json()["settlements"])
