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
async def test_list_orders_defaults_to_a_bounded_page(client: AsyncClient, order_ctx):
    from datetime import UTC, datetime, timedelta

    from tests.test_analytics import _insert_order

    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    for i in range(3):
        _insert_order(
            kitchen_id,
            total=199,
            status="delivered",
            created_at=now - timedelta(minutes=i),
            dish_id=dish_id,
        )
    headers = {"Authorization": f"Bearer {token}"}
    capped = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"limit": 2},
        headers=headers,
    )
    assert capped.status_code == 200
    body = capped.json()
    assert body["total"] == 2
    assert len(body["orders"]) == 2

    too_big = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"limit": 500},
        headers=headers,
    )
    assert too_big.status_code == 422


@pytest.mark.asyncio
async def test_list_open_orders_skips_terminal_states(client: AsyncClient, order_ctx):
    from datetime import UTC, datetime, timedelta

    from tests.test_analytics import _insert_order

    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    live_id = _insert_order(
        kitchen_id,
        total=199,
        status="received",
        created_at=now,
        dish_id=dish_id,
    )
    _insert_order(
        kitchen_id,
        total=199,
        status="delivered",
        created_at=now - timedelta(hours=1),
        dish_id=dish_id,
    )
    _insert_order(
        kitchen_id,
        total=50,
        status="cancelled",
        created_at=now - timedelta(hours=2),
        dish_id=dish_id,
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"open": "true"},
        headers=headers,
    )
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["orders"]}
    assert str(live_id) in ids
    assert response.json()["total"] == 1
    assert response.json()["lane_counts"] == {"received": 1}
    assert all(row["status"] not in {"delivered", "cancelled"} for row in response.json()["orders"])


@pytest.mark.asyncio
async def test_open_order_lane_counts_cover_the_full_rush(client: AsyncClient, order_ctx):
    from datetime import UTC, datetime, timedelta

    from tests.test_analytics import _insert_order

    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    for i in range(3):
        _insert_order(
            kitchen_id,
            total=199,
            status="received",
            created_at=now - timedelta(minutes=i),
            dish_id=dish_id,
        )
    _insert_order(
        kitchen_id,
        total=249,
        status="ready",
        created_at=now - timedelta(minutes=30),
        dish_id=dish_id,
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"open": "true", "limit": 1},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["orders"]) == 1
    assert body["lane_counts"] == {"received": 3, "ready": 1}


@pytest.mark.asyncio
async def test_list_orders_date_filters(client: AsyncClient, order_ctx):
    from datetime import UTC, datetime, timedelta

    from tests.test_analytics import _insert_order

    _, kitchen_id, dish_id, _, token = order_ctx
    now = datetime.now(UTC)
    older_id = _insert_order(
        kitchen_id,
        total=199,
        status="delivered",
        created_at=now - timedelta(days=10),
        dish_id=dish_id,
    )
    newer_id = _insert_order(
        kitchen_id,
        total=199,
        status="delivered",
        created_at=now - timedelta(days=1),
        dish_id=dish_id,
    )
    headers = {"Authorization": f"Bearer {token}"}
    after = (now - timedelta(days=5)).isoformat()
    before = (now - timedelta(days=5)).isoformat()

    recent = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"created_after": after},
        headers=headers,
    )
    assert recent.status_code == 200
    recent_ids = {o["id"] for o in recent.json()["orders"]}
    assert str(newer_id) in recent_ids
    assert str(older_id) not in recent_ids

    older = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders",
        params={"created_before": before},
        headers=headers,
    )
    assert older.status_code == 200
    older_ids = {o["id"] for o in older.json()["orders"]}
    assert str(older_id) in older_ids
    assert str(newer_id) not in older_ids


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
