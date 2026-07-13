import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quote_free_within_radius(client: AsyncClient, delivery_ctx):
    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["lat"],
            "longitude": delivery_ctx["lng"],
            "subtotal": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["fee"] == 0.0
    assert data["within_free_radius"] is True


@pytest.mark.asyncio
async def test_quote_per_km_beyond_free(client: AsyncClient, delivery_ctx):
    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["near_lat"],
            "longitude": delivery_ctx["near_lng"],
            "subtotal": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["fee"] > 0


@pytest.mark.asyncio
async def test_quote_out_of_range(client: AsyncClient, delivery_ctx):
    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["far_lat"],
            "longitude": delivery_ctx["far_lng"],
            "subtotal": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "out_of_range"
    assert data["fee"] == 0.0


@pytest.mark.asyncio
async def test_track_by_token(client: AsyncClient, delivery_ctx):
    import psycopg2

    order_id = __import__("uuid").uuid4()
    token = "track-test-token-abc"
    conn = psycopg2.connect(__import__("os").environ["DATABASE_SYNC_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
            (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
             payment_method, subtotal, delivery_fee, total, tracking_token, distance_km)
            VALUES (
                %s::uuid, %s::uuid, 'BILL-DEL-0001', 'CKDEL-BILL-DEL-0001',
                'preparing', 'customer_pwa', 'delivery', 'cod',
                199.00, 30.00, 229.00, %s, 4.5
            )
            """,
            (str(order_id), str(delivery_ctx["kitchen_id"]), token),
        )
    conn.close()

    response = await client.get(f"/api/v1/delivery/track/{token}")
    assert response.status_code == 200
    data = response.json()
    assert data["order_code"] == "CKDEL-BILL-DEL-0001"
    assert data["status"] == "preparing"
    assert data["distance_km"] == 4.5
