"""Customer checkout order tests — Sprint 5."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL, _make_token

CUSTOMER_ORDER_PAYLOAD = {
    "items": [{"dish_id": None, "quantity": 1}],
    "delivery_type": "pickup",
    "payment_method": "cod",
    "delivery_fee": 0,
}


def _make_customer_token(customer_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(customer_id), "type": "customer", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_customer(*, phone: str = "+919988776655", name: str = "Test Customer") -> uuid.UUID:
    customer_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status)
            VALUES (%s::uuid, %s, %s, 'active')
            """,
            (str(customer_id), name, phone),
        )
    conn.close()
    return customer_id


@pytest.mark.asyncio
async def test_customer_order_requires_auth(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, dish_id, _, _ = order_ctx
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
    )
    assert response.status_code == 401


def _seed_coupon(kitchen_id: uuid.UUID, code: str = "SAVE10", *, percent: float = 10) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_marketing.coupons
            (id, kitchen_id, code, discount_type, discount_value, min_order_amount, is_active, used_count)
            VALUES (%s::uuid, %s::uuid, %s, 'percent', %s, 0, true, 0)
            """,
            (str(uuid.uuid4()), str(kitchen_id), code, percent),
        )
    conn.close()


@pytest.mark.asyncio
async def test_customer_order_success(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, kitchen_code, _ = order_ctx
    customer_id = _seed_customer()
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 2}]

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "customer_pwa"
    assert data["payment_method"] == "cod"
    assert data["customer_phone"] == "+919988776655"
    assert data["customer_name"] == "Test Customer"
    assert data["subtotal"] == 398.0
    assert kitchen_code in data["order_code"]


@pytest.mark.asyncio
async def test_customer_order_applies_coupon(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, _ = order_ctx
    _seed_coupon(kitchen_id, "SAVE10", percent=10)
    customer_id = _seed_customer(phone="+919900112233")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 2}]
    payload["coupon_code"] = "save10"

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["subtotal"] == 398.0
    assert data["coupon_code"] == "SAVE10"
    assert data["discount_amount"] == 39.8
    assert data["total"] == 358.2


@pytest.mark.asyncio
async def test_customer_order_rejects_invalid_coupon(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, _ = order_ctx
    customer_id = _seed_customer(phone="+919900112244")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]
    payload["coupon_code"] = "NOPE"

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "coupon" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_customer_orders_list(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, owner_token = order_ctx
    customer_id = _seed_customer(phone="+919911122233")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]

    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 201

    listing = await client.get(
        "/api/v1/customers/me/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert data["orders"][0]["source"] == "customer_pwa"

    owner_list = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_list.status_code == 200
    assert owner_list.json()["total"] >= 1


@pytest.mark.asyncio
async def test_owner_cannot_use_customer_order_endpoint(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, owner_token = order_ctx
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_customer_order_idempotency_key_replay_returns_same_order(
    client: AsyncClient, order_ctx
):
    """A retried checkout (network timeout / double-tap) with the same Idempotency-Key
    must never create a second order or double-charge the customer."""
    _, kitchen_id, dish_id, _, _ = order_ctx
    customer_id = _seed_customer(phone="+919944455566")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 3}]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "checkout-retry-key-001"}

    first = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer", json=payload, headers=headers
    )
    assert first.status_code == 201
    order_id = first.json()["id"]

    replay = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer", json=payload, headers=headers
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == order_id

    listing = await client.get(
        "/api/v1/customers/me/orders", headers={"Authorization": f"Bearer {token}"}
    )
    assert listing.json()["total"] == 1


@pytest.mark.asyncio
async def test_customer_order_different_idempotency_key_creates_new_order(
    client: AsyncClient, order_ctx
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    customer_id = _seed_customer(phone="+919944455577")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={**headers, "Idempotency-Key": "checkout-key-A"},
    )
    second = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={**headers, "Idempotency-Key": "checkout-key-B"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


@pytest.mark.asyncio
async def test_customer_order_platform_mode_beyond_range_shared_subsidy(
    client: AsyncClient, order_ctx
):
    """Checkout Porter/platform fee must persist with kitchen cost-share rules."""
    import math

    _, kitchen_id, dish_id, _, _ = order_ctx
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ckac_identity.kitchens
            SET max_delivery_radius_km = 5,
                min_order_for_free_delivery = 300,
                delivery_subsidy_percent = 50
            WHERE id = %s::uuid
            """,
            (str(kitchen_id),),
        )
    conn.close()

    # ~18+ km from kitchen pin (18.5362, 73.8958) — beyond 5 km max.
    far_lat, far_lng = 18.70, 74.10
    # Distance via PostGIS would be authoritative; approximate for fee formula after place.
    # Order service recomputes distance — we only need a fee that matches server quote.
    # First place with a probe to learn expected fee, or compute with same formula after
    # fetching distance from a failed mismatch. Use delivery quote path via formula with
    # known env defaults after measuring distance in SQL.
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ST_Distance(
                location,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            ) / 1000.0
            FROM ckac_identity.kitchens WHERE id = %s::uuid
            """,
            (far_lng, far_lat, str(kitchen_id)),
        )
        dist = float(cur.fetchone()[0])
    conn.close()
    assert dist > 5
    platform_gross = round(25 + math.ceil(dist) * 12, 2)
    customer_fee = round(platform_gross * 0.5, 2)
    owner_fee = round(platform_gross - customer_fee, 2)

    customer_id = _seed_customer(phone="+919922233344")
    token = _make_customer_token(customer_id)
    # qty 2 → subtotal 398 ≥ 300 min order
    payload = {
        "items": [{"dish_id": str(dish_id), "quantity": 2}],
        "delivery_type": "delivery",
        "delivery_mode": "platform",
        "payment_method": "upi",
        "delivery_fee": customer_fee,
        "delivery_fee_accepted": True,
        "delivery_fee_payment": "prepaid",
        "customer_latitude": far_lat,
        "customer_longitude": far_lng,
    }
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["delivery_mode"] == "platform"
    assert data["delivery_payer"] == "shared"
    assert data["delivery_fee"] == customer_fee
    assert data["owner_delivery_cost"] == owner_fee
    assert data["courier_partner"] == "porter"


@pytest.mark.asyncio
async def test_customer_order_repeat(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, _ = order_ctx
    customer_id = _seed_customer(phone="+919933344455")
    token = _make_customer_token(customer_id)
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 2}]

    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 201
    order_id = create.json()["id"]

    repeat = await client.post(
        f"/api/v1/customers/me/orders/{order_id}/repeat",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert repeat.status_code == 201
    data = repeat.json()
    assert data["id"] != order_id
    assert data["source"] == "customer_pwa"
    assert data["subtotal"] == 398.0
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2

    listing = await client.get(
        "/api/v1/customers/me/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["total"] == 2
