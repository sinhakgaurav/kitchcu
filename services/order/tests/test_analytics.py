"""Owner growth analytics tests — revenue, dishes, peak hours, retention."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, _make_token


def _insert_order(
    kitchen_id: uuid.UUID,
    *,
    total: float,
    status: str,
    created_at: datetime,
    customer_phone: str | None = None,
    customer_name: str | None = None,
    dish_id: uuid.UUID | None = None,
    dish_name: str = "Paneer Tikka",
    quantity: int = 1,
    unit_price: float = 199.0,
) -> uuid.UUID:
    order_id = uuid.uuid4()
    order_code = f"CKTST-BILL-{order_id.hex[:8].upper()}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
                (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
                 payment_method, customer_name, customer_phone, subtotal, delivery_fee,
                 total, created_at, updated_at)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, 'manual', 'pickup', 'cod',
                    %s, %s, %s, 0, %s, %s, %s)
            """,
            (
                str(order_id), str(kitchen_id), order_code[:32], order_code, status,
                customer_name, customer_phone, total, total, created_at, created_at,
            ),
        )
        cur.execute(
            """
            INSERT INTO ckac_orders.order_items
                (id, order_id, dish_id, dish_name, quantity, unit_price, prep_time_min)
            VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, 25)
            """,
            (
                str(uuid.uuid4()), str(order_id), str(dish_id or uuid.uuid4()),
                dish_name, quantity, unit_price,
            ),
        )
    conn.close()
    return order_id


@pytest.mark.asyncio
async def test_summary_requires_auth(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, _ = order_ctx
    r = await client.get(f"/api/v1/kitchens/{kitchen_id}/analytics/summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_summary_forbidden_for_non_owner(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, _ = order_ctx
    stranger = _make_token(uuid.uuid4())
    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/summary",
        headers={"Authorization": f"Bearer {stranger}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_summary_excludes_cancelled_and_computes_repeat_rate(
    client: AsyncClient, order_ctx
):
    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    # Customer A: two delivered orders (repeat buyer)
    _insert_order(kitchen_id, total=200, status="delivered", created_at=now - timedelta(days=1),
                  customer_phone="+919000000001", dish_id=dish_id)
    _insert_order(kitchen_id, total=300, status="delivered", created_at=now - timedelta(days=2),
                  customer_phone="+919000000001", dish_id=dish_id)
    # Customer B: one order (new buyer)
    _insert_order(kitchen_id, total=500, status="preparing", created_at=now - timedelta(days=1),
                  customer_phone="+919000000002", dish_id=dish_id)
    # Cancelled order — must be excluded from revenue
    _insert_order(kitchen_id, total=999, status="cancelled", created_at=now - timedelta(days=1),
                  customer_phone="+919000000003", dish_id=dish_id)

    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/summary?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total_orders"] == 4
    assert data["completed_orders"] == 3
    assert data["cancelled_orders"] == 1
    assert data["gross_revenue"] == 1000.0
    assert data["avg_order_value"] == pytest.approx(333.33, abs=0.01)
    assert data["unique_customers"] == 2
    assert data["repeat_customers"] == 1
    assert data["repeat_rate"] == 0.5


@pytest.mark.asyncio
async def test_top_dishes_ranks_by_revenue(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    other_dish = uuid.uuid4()
    _insert_order(kitchen_id, total=400, status="delivered", created_at=now - timedelta(days=1),
                  dish_id=dish_id, dish_name="Paneer Tikka", quantity=2, unit_price=200)
    _insert_order(kitchen_id, total=100, status="delivered", created_at=now - timedelta(days=1),
                  dish_id=other_dish, dish_name="Masala Chai", quantity=2, unit_price=50)

    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/top-dishes?days=30&limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    dishes = r.json()["dishes"]
    assert len(dishes) == 2
    assert dishes[0]["dish_name"] == "Paneer Tikka"
    assert dishes[0]["revenue"] == 400.0
    assert dishes[0]["quantity"] == 2


@pytest.mark.asyncio
async def test_peak_hours_returns_24_buckets(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    _insert_order(kitchen_id, total=200, status="delivered",
                  created_at=datetime.now(UTC) - timedelta(days=1), dish_id=dish_id)
    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/peak-hours?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    hours = r.json()["hours"]
    assert len(hours) == 24
    assert sum(h["orders"] for h in hours) == 1


@pytest.mark.asyncio
async def test_revenue_timeseries_fills_missing_days(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    _insert_order(kitchen_id, total=250, status="delivered",
                  created_at=datetime.now(UTC), dish_id=dish_id)
    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/revenue-timeseries?days=7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 7
    assert sum(p["revenue"] for p in points) == 250.0


@pytest.mark.asyncio
async def test_customers_segments_and_churn_risk(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    # VIP: 5 orders
    for i in range(5):
        _insert_order(kitchen_id, total=200, status="delivered",
                      created_at=now - timedelta(days=i + 1),
                      customer_phone="+919111111111", customer_name="VIP", dish_id=dish_id)
    # Churn risk: 2 orders, both older than 21 days
    _insert_order(kitchen_id, total=300, status="delivered", created_at=now - timedelta(days=40),
                  customer_phone="+919222222222", customer_name="Lapsed", dish_id=dish_id)
    _insert_order(kitchen_id, total=300, status="delivered", created_at=now - timedelta(days=35),
                  customer_phone="+919222222222", customer_name="Lapsed", dish_id=dish_id)

    r = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/analytics/customers?days=365&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["vip_customers"] == 1
    assert data["repeat_customers"] == 1  # the lapsed customer has 2 orders
    phones = [c["customer_phone"] for c in data["churn_risk"]]
    assert "+919222222222" in phones
    assert "+919111111111" not in phones
