"""Order bill PDF receipts — owner + customer download."""

import pytest
from httpx import AsyncClient

from tests.conftest import _make_token
from tests.test_customer_orders import _make_customer_token, _seed_customer


@pytest.mark.asyncio
async def test_owner_order_bill_pdf(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert create.status_code == 201
    order = create.json()

    response = await client.get(
        f"/api/v1/orders/{order['id']}/bill.pdf",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert order["order_code"] in response.headers.get("content-disposition", "")
    assert response.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_owner_bill_pdf_requires_auth(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    response = await client.get(f"/api/v1/orders/{order_id}/bill.pdf")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_bill_pdf_wrong_kitchen_denied(
    client: AsyncClient, order_ctx, manual_order_payload
):
    owner_id, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]

    other_owner = __import__("uuid").uuid4()
    other_token = _make_token(other_owner)
    response = await client.get(
        f"/api/v1/orders/{order_id}/bill.pdf",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_customer_order_bill_pdf(client: AsyncClient, order_ctx):
    from tests.test_customer_orders import CUSTOMER_ORDER_PAYLOAD

    _, kitchen_id, dish_id, _, _ = order_ctx
    customer_id = _seed_customer()
    token = _make_customer_token(customer_id)
    headers = {"Authorization": f"Bearer {token}"}
    payload = CUSTOMER_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]

    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json=payload,
        headers=headers,
    )
    assert create.status_code == 201
    order_id = create.json()["id"]

    response = await client.get(
        f"/api/v1/customers/me/orders/{order_id}/bill.pdf",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"
