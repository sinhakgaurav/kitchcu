import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment_for_online_order(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["order_id"] == str(order_id)
    assert data["status"] == "created"
    assert data["method"] == "online"
    assert data["razorpay_order_id"].startswith("order_dev_")


@pytest.mark.asyncio
async def test_create_payment_rejects_cod_order(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_orders.orders SET payment_method = 'cod' WHERE id = %s::uuid",
            (str(order_id),),
        )
    conn.close()

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "COD" in response.json()["detail"]


@pytest.mark.asyncio
async def test_capture_payment(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    payment_id = create.json()["id"]

    capture = await client.post(
        f"/api/v1/billing/payments/{payment_id}/capture",
        headers=headers,
    )
    assert capture.status_code == 200
    assert capture.json()["status"] == "captured"
    assert capture.json()["razorpay_payment_id"].startswith("pay_dev_")


@pytest.mark.asyncio
async def test_upi_intent_returns_uri(client: AsyncClient, billing_ctx):
    _, _, order_id, code, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/billing/payments/upi-intent",
        json={"order_id": str(order_id)},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert "upi://pay?" in data["upi_uri"]
    assert code.lower() in data["upi_uri"].lower()


@pytest.mark.asyncio
async def test_get_payment_requires_auth(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    payment_id = create.json()["id"]

    get_resp = await client.get(f"/api/v1/billing/payments/{payment_id}", headers=headers)
    assert get_resp.status_code == 200

    unauth = await client.get(f"/api/v1/billing/payments/{payment_id}")
    assert unauth.status_code == 401
