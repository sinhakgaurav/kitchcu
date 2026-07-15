"""F06 multi-kitchen checkout API tests."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL


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


def _seed_customer(phone: str) -> tuple[uuid.UUID, dict[str, str]]:
    customer_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status)
            VALUES (%s::uuid, 'Multi Cart Customer', %s, 'active')
            """,
            (str(customer_id), phone),
        )
    conn.close()
    return customer_id, {"Authorization": f"Bearer {_customer_token(customer_id)}"}


def _seed_second_kitchen() -> tuple[uuid.UUID, uuid.UUID]:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    category_id = uuid.uuid4()
    dish_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners
                (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Second Owner', 'starter', 'trial')
            """,
            (str(owner_id), f"+91{owner_id.int % 9000000000 + 1000000000}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
                (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Second Kitchen',
                ST_SetSRID(ST_MakePoint(73.90, 18.54), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKMUL{owner_id.hex[:4].upper()}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order)
            VALUES (%s::uuid, %s::uuid, 'Veg', 'veg', 0)
            """,
            (str(category_id), str(kitchen_id)),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.dishes
                (id, kitchen_id, category_id, name, price, prep_time_min, delivery_time_min, max_time_min, is_active)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'Dal Rice', 151.00, 20, 15, 35, true)
            """,
            (str(dish_id), str(kitchen_id), str(category_id)),
        )
    conn.close()
    return kitchen_id, dish_id


def _payload(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    second_kitchen_id: uuid.UUID,
    second_dish_id: uuid.UUID,
    *,
    payment_method: str = "cod",
) -> dict:
    return {
        "payment_method": payment_method,
        "groups": [
            {
                "kitchen_id": str(kitchen_id),
                "items": [{"dish_id": str(dish_id), "quantity": 2}],
                "delivery_type": "pickup",
                "delivery_fee": 0,
            },
            {
                "kitchen_id": str(second_kitchen_id),
                "items": [{"dish_id": str(second_dish_id), "quantity": 1}],
                "delivery_type": "delivery",
                "delivery_fee": 40,
                "delivery_fee_accepted": True,
            },
        ],
    }


@pytest.mark.asyncio
async def test_master_checkout_requires_customer_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/customers/me/master-orders",
        json={"payment_method": "cod", "groups": []},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_master_checkout_requires_idempotency_key(
    client: AsyncClient,
    order_ctx,
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, headers = _seed_customer("+919900001111")
    response = await client.post(
        "/api/v1/customers/me/master-orders",
        json=_payload(kitchen_id, dish_id, second_kitchen_id, second_dish_id),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_master_checkout_creates_grouped_orders_and_is_idempotent(
    client: AsyncClient,
    order_ctx,
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, headers = _seed_customer("+919900002222")
    headers["Idempotency-Key"] = str(uuid.uuid4())
    payload = _payload(kitchen_id, dish_id, second_kitchen_id, second_dish_id)

    first = await client.post(
        "/api/v1/customers/me/master-orders",
        json=payload,
        headers=headers,
    )
    assert first.status_code == 201
    data = first.json()
    assert data["master_order_code"].startswith("MORD-")
    assert data["payment_method"] == "cod"
    assert data["subtotal"] == 549.0
    assert data["delivery_fee"] == 40.0
    assert data["total"] == 589.0
    assert len(data["orders"]) == 2
    assert {o["kitchen_id"] for o in data["orders"]} == {
        str(kitchen_id),
        str(second_kitchen_id),
    }
    assert all(o["master_order_id"] == data["id"] for o in data["orders"])
    assert len({o["order_code"] for o in data["orders"]}) == 2

    retry = await client.post(
        "/api/v1/customers/me/master-orders",
        json=payload,
        headers=headers,
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == data["id"]

    receipt = await client.get(
        f"/api/v1/customers/me/master-orders/{data['id']}",
        headers={"Authorization": headers["Authorization"]},
    )
    assert receipt.status_code == 200
    assert receipt.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_master_checkout_accepts_online_payment_method(
    client: AsyncClient,
    order_ctx,
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, headers = _seed_customer("+919900003333")
    headers["Idempotency-Key"] = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/customers/me/master-orders",
        json=_payload(
            kitchen_id,
            dish_id,
            second_kitchen_id,
            second_dish_id,
            payment_method="online",
        ),
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["payment_method"] == "online"


@pytest.mark.asyncio
async def test_master_receipt_is_customer_scoped(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, owner_headers = _seed_customer("+919900004444")
    owner_headers["Idempotency-Key"] = str(uuid.uuid4())
    created = await client.post(
        "/api/v1/customers/me/master-orders",
        json=_payload(kitchen_id, dish_id, second_kitchen_id, second_dish_id),
        headers=owner_headers,
    )
    assert created.status_code == 201

    _, other_headers = _seed_customer("+919900005555")
    forbidden = await client.get(
        f"/api/v1/customers/me/master-orders/{created.json()['id']}",
        headers=other_headers,
    )
    assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_master_checkout_is_atomic_when_a_dish_is_inactive(
    client: AsyncClient,
    order_ctx,
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, headers = _seed_customer("+919900006666")
    headers["Idempotency-Key"] = str(uuid.uuid4())

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_catalog.dishes SET is_active = false WHERE id = %s::uuid",
            (str(second_dish_id),),
        )
    conn.close()

    response = await client.post(
        "/api/v1/customers/me/master-orders",
        json=_payload(kitchen_id, dish_id, second_kitchen_id, second_dish_id),
        headers=headers,
    )
    assert response.status_code == 400

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM ckac_orders.orders WHERE source = 'customer_pwa_multi'"
        )
        assert cur.fetchone()[0] == 0
    conn.close()


@pytest.mark.asyncio
async def test_master_checkout_publishes_master_and_sub_order_events(
    client: AsyncClient,
    order_ctx,
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    second_kitchen_id, second_dish_id = _seed_second_kitchen()
    _, headers = _seed_customer("+919900007777")
    headers["Idempotency-Key"] = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/customers/me/master-orders",
        json=_payload(kitchen_id, dish_id, second_kitchen_id, second_dish_id),
        headers=headers,
    )
    assert response.status_code == 201
    master_id = response.json()["id"]

    from app.main import redis_client

    assert redis_client is not None
    master_messages = await redis_client.xread(
        {"ckac:orders:master_order": "0-0"},
        count=10,
    )
    order_messages = await redis_client.xread(
        {"ckac:orders:order": "0-0"},
        count=10,
    )
    assert len(master_messages) == 1
    master_event = json.loads(master_messages[0][1][-1][1]["data"])
    assert master_event["event_type"] == "master_order.created"
    assert master_event["aggregate_id"] == master_id
    assert len(master_event["payload"]["order_ids"]) == 2

    order_events = [
        json.loads(entry[1]["data"])
        for entry in order_messages[0][1]
    ]
    assert len([event for event in order_events if event["event_type"] == "order.placed"]) == 2

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM ckac_events.outbox
            WHERE aggregate_id = %s
              AND event_type = 'master_order.created'
              AND published = true
            """,
            (master_id,),
        )
        assert cur.fetchone()[0] == 1
    conn.close()
