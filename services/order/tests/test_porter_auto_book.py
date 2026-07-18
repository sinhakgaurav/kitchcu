"""API tests — customer ETA + Porter delayed auto-book (P35)."""

from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, _make_token


def _set_kitchen_porter(kitchen_id, *, enabled=True, delay_min=15):
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ckac_identity.kitchens
            SET porter_auto_book_enabled = %s,
                porter_auto_book_delay_min = %s
            WHERE id = %s::uuid
            """,
            (enabled, delay_min, str(kitchen_id)),
        )
    conn.close()


def _order_porter_cols(order_id: str) -> dict:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT estimated_prep_min, estimated_delivery_min,
                   estimated_ready_at, estimated_delivery_at,
                   porter_auto_book_at, courier_job_id
            FROM ckac_orders.orders WHERE id = %s::uuid
            """,
            (order_id,),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    return {
        "estimated_prep_min": row[0],
        "estimated_delivery_min": row[1],
        "estimated_ready_at": row[2],
        "estimated_delivery_at": row[3],
        "porter_auto_book_at": row[4],
        "courier_job_id": row[5],
    }


@pytest.mark.asyncio
async def test_customer_delivery_order_stores_prep_plus_delivery_eta(client: AsyncClient, order_ctx):
    owner_id, kitchen_id, dish_id, _code, token = order_ctx
    # dish seeded: prep 25, delivery 20
    payload = {
        "items": [{"dish_id": str(dish_id), "quantity": 1}],
        "delivery_type": "delivery",
        "delivery_mode": "self",
        "payment_method": "cod",
        "delivery_fee": 0,
        "delivery_fee_accepted": True,
        "customer_name": "ETA Tester",
        "customer_phone": "+919911122233",
        "customer_latitude": 18.5362,
        "customer_longitude": 73.8958,
        "distance_km": 1.0,
    }
    # manual create as owner for simplicity
    res = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["estimated_prep_min"] == 25
    assert data["estimated_delivery_min"] == 20
    assert data["estimated_ready_at"] is not None
    assert data["estimated_delivery_at"] is not None
    ready = datetime.fromisoformat(data["estimated_ready_at"].replace("Z", "+00:00"))
    door = datetime.fromisoformat(data["estimated_delivery_at"].replace("Z", "+00:00"))
    assert door - ready == timedelta(minutes=20)
    _ = owner_id


@pytest.mark.asyncio
async def test_accept_schedules_porter_auto_book_when_enabled(client: AsyncClient, order_ctx):
    owner_id, kitchen_id, dish_id, _code, token = order_ctx
    _set_kitchen_porter(kitchen_id, enabled=True, delay_min=15)
    payload = {
        "items": [{"dish_id": str(dish_id), "quantity": 1}],
        "delivery_type": "delivery",
        "delivery_mode": "platform",
        "payment_method": "cod",
        "delivery_fee": 0,
        "delivery_fee_accepted": True,
        "customer_name": "Auto Book",
        "customer_phone": "+919911122244",
        "customer_latitude": 18.54,
        "customer_longitude": 73.90,
        "distance_km": 2.0,
    }
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 201, create.text
    order_id = create.json()["id"]

    before = datetime.now(UTC)
    accept = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accept.status_code == 200, accept.text
    body = accept.json()
    assert body["porter_auto_book_at"] is not None
    assert body.get("courier_job_id") in (None, "")
    cols = _order_porter_cols(order_id)
    assert cols["courier_job_id"] is None
    assert cols["porter_auto_book_at"] is not None
    # ~15 min from accept
    delta = cols["porter_auto_book_at"].astimezone(UTC) - before
    assert timedelta(minutes=14) <= delta <= timedelta(minutes=16)
    _ = owner_id


@pytest.mark.asyncio
async def test_accept_immediate_when_auto_book_disabled(client: AsyncClient, order_ctx, monkeypatch):
    owner_id, kitchen_id, dish_id, _code, token = order_ctx
    _set_kitchen_porter(kitchen_id, enabled=False, delay_min=15)

    async def fake_book(session, order, pickup_time=None):
        return {"fee": 40.0, "job_id": "porter-test-job", "partner": "porter"}

    monkeypatch.setenv("DELIVERY_PARTNER", "porter")
    monkeypatch.setenv("PORTER_API_KEY", "test-key")
    monkeypatch.setattr("app.porter_client.quote_and_book_porter", fake_book)

    payload = {
        "items": [{"dish_id": str(dish_id), "quantity": 1}],
        "delivery_type": "delivery",
        "delivery_mode": "platform",
        "payment_method": "cod",
        "delivery_fee": 0,
        "delivery_fee_accepted": True,
        "customer_name": "Immediate",
        "customer_phone": "+919911122255",
        "customer_latitude": 18.54,
        "customer_longitude": 73.90,
        "distance_km": 2.0,
    }
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 201, create.text
    order_id = create.json()["id"]

    accept = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accept.status_code == 200, accept.text
    cols = _order_porter_cols(order_id)
    assert cols["porter_auto_book_at"] is None
    assert cols["courier_job_id"] == "porter-test-job"
    _ = owner_id
    _ = _make_token


@pytest.mark.asyncio
async def test_porter_auto_book_tick_books_due_order(client: AsyncClient, order_ctx, monkeypatch):
    owner_id, kitchen_id, dish_id, _code, token = order_ctx
    _set_kitchen_porter(kitchen_id, enabled=True, delay_min=15)

    async def fake_book(session, order, pickup_time=None):
        return {"fee": 55.0, "job_id": "porter-tick-job", "partner": "porter"}

    monkeypatch.setenv("DELIVERY_PARTNER", "porter")
    monkeypatch.setenv("PORTER_API_KEY", "test-key")
    monkeypatch.setattr("app.porter_client.quote_and_book_porter", fake_book)

    payload = {
        "items": [{"dish_id": str(dish_id), "quantity": 1}],
        "delivery_type": "delivery",
        "delivery_mode": "platform",
        "payment_method": "cod",
        "delivery_fee": 0,
        "delivery_fee_accepted": True,
        "customer_name": "Tick",
        "customer_phone": "+919911122266",
        "customer_latitude": 18.54,
        "customer_longitude": 73.90,
        "distance_km": 2.0,
    }
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = create.json()["id"]
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Force due
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ckac_orders.orders
            SET porter_auto_book_at = NOW() - INTERVAL '1 minute'
            WHERE id = %s::uuid
            """,
            (order_id,),
        )
    conn.close()

    tick = await client.post(
        "/api/v1/internal/orders/porter-auto-book/tick",
        headers={"X-Internal-Key": "test-internal-key-for-pytest"},
    )
    assert tick.status_code == 200, tick.text
    assert tick.json()["booked"] >= 1
    cols = _order_porter_cols(order_id)
    assert cols["courier_job_id"] == "porter-tick-job"
    assert cols["porter_auto_book_at"] is None
    _ = owner_id
