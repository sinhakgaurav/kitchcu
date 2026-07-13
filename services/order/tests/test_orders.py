import json
import re

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_manual_order_requires_auth(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, _ = order_ctx
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_manual_order_success(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, dish_id, kitchen_code, token = order_ctx
    manual_order_payload["items"] = [{"dish_id": str(dish_id), "quantity": 2}]
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert data["source"] == "manual"
    assert data["subtotal"] == 398.0
    assert data["total"] == 398.0
    assert len(data["items"]) == 1
    assert data["items"][0]["dish_name"] == "Paneer Tikka"
    assert re.match(rf"^{kitchen_code}-BILL-\d{{8}}-\d{{4}}$", data["order_code"])


@pytest.mark.asyncio
async def test_order_code_increments_per_day(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, dish_id, kitchen_code, token = order_ctx
    manual_order_payload["items"] = [{"dish_id": str(dish_id), "quantity": 1}]
    headers = {"Authorization": f"Bearer {token}"}
    r1 = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    r2 = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["bill_id"] != r2.json()["bill_id"]
    assert r1.json()["order_code"].endswith("-0001")
    assert r2.json()["order_code"].endswith("-0002")


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    response = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_valid_status_lifecycle(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    for status in ("accepted", "preparing", "ready", "delivered"):
        response = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": status, "note": f"Moving to {status}"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == status
    assert len(response.json()["status_events"]) == 5


@pytest.mark.asyncio
async def test_cancel_requires_reason(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=headers,
    )
    response = await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_orders_by_kitchen(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["orders"][0]["source"] == "manual"


@pytest.mark.asyncio
async def test_get_order_detail(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    response = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == order_id


@pytest.mark.asyncio
async def test_order_placed_publishes_event(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    order_id = response.json()["id"]

    from app.main import redis_client

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:orders:order": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "order.placed"
    assert event_data["aggregate_id"] == order_id


@pytest.mark.asyncio
async def test_status_changed_publishes_event(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    order_id = create.json()["id"]
    await client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=headers,
    )

    from app.main import redis_client

    messages = await redis_client.xread({"ckac:orders:order": "0-0"}, count=10)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    status_events = [
        e for e in events if e["event_type"] == "order.status.changed" and e["aggregate_id"] == order_id
    ]
    assert len(status_events) >= 1
    assert status_events[-1]["payload"]["to_status"] == "accepted"
