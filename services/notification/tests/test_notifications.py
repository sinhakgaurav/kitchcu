"""Internal notification dispatch tests — Sprint 14 (F29/F45)."""

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, _seed_kitchen

INTERNAL_KEY = os.environ["INTERNAL_API_KEY"]


def _seed_order(
    kitchen_id: uuid.UUID,
    *,
    tracking_token: str = "track-abc123",
    delivery_type: str = "delivery",
    status: str = "received",
) -> uuid.UUID:
    order_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
            (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
             payment_method, customer_name, customer_phone, subtotal, delivery_fee, total,
             tracking_token)
            VALUES (%s::uuid, %s::uuid, 'BILL-TEST-001', %s, %s, 'manual', %s,
                    'cod', 'Test Customer', '+919876543210', 199, 40, 239, %s)
            """,
            (
                str(order_id),
                str(kitchen_id),
                f"ORD-{order_id.hex[:8].upper()}",
                status,
                delivery_type,
                tracking_token if delivery_type == "delivery" else None,
            ),
        )
    conn.close()
    return order_id


@pytest.mark.asyncio
async def test_order_placed_notification(client: AsyncClient):
    kitchen_id = _seed_kitchen()

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:notify:dispatch")

    order_id = uuid.uuid4()
    order_code = "CKTEST-BILL-20260713-0001"
    response = await client.post(
        "/api/v1/internal/notifications/order-placed",
        json={
            "order_id": str(order_id),
            "kitchen_id": str(kitchen_id),
            "order_code": order_code,
            "customer_phone": "+919876543210",
            "delivery_type": "delivery",
            "total": 239,
            "tracking_token": "tok-test-001",
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == "order_confirmed"
    assert data["channel"] == "whatsapp"
    assert data["status"] == "sent"

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT body, template_id FROM ckac_notifications.notification_log WHERE id = %s::uuid",
            (data["notification_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert "/t/tok-test-001" in row[0]
    assert row[1] == "order_confirmed"

    messages = await redis_client.xread({"ckac:notify:dispatch": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "notification.sent"


@pytest.mark.asyncio
async def test_order_placed_requires_internal_key(client: AsyncClient):
    response = await client.post(
        "/api/v1/internal/notifications/order-placed",
        json={
            "order_id": str(uuid.uuid4()),
            "kitchen_id": str(uuid.uuid4()),
            "order_code": "X",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_status_change_creates_tracking_reminder(client: AsyncClient):
    kitchen_id = _seed_kitchen()
    order_id = _seed_order(kitchen_id, tracking_token="tok-reminder", delivery_type="delivery")

    response = await client.post(
        "/api/v1/internal/notifications/order-status-changed",
        json={
            "order_id": str(order_id),
            "kitchen_id": str(kitchen_id),
            "order_code": "ORD-REMINDER",
            "customer_phone": "+919876543210",
            "from_status": "accepted",
            "to_status": "preparing",
            "tracking_token": "tok-reminder",
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    assert response.json()["template_id"] == "order_status_update"

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT is_active, order_status, tracking_token
            FROM ckac_notifications.tracking_reminders
            WHERE order_id = %s::uuid
            """,
            (str(order_id),),
        )
        row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] is True
    assert row[1] == "preparing"
    assert row[2] == "tok-reminder"


@pytest.mark.asyncio
async def test_tracking_interval_tick_sends_due_reminders(client: AsyncClient):
    kitchen_id = _seed_kitchen()
    order_id = _seed_order(kitchen_id, tracking_token="tok-tick", status="preparing")
    reminder_id = uuid.uuid4()
    past = datetime.now(UTC) - timedelta(minutes=1)

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_notifications.tracking_reminders
            (id, order_id, kitchen_id, order_code, customer_phone, tracking_token,
             order_status, interval_min, next_reminder_at, is_active)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'ORD-TICK', '+919876543210', 'tok-tick',
                    'preparing', 5, %s, true)
            """,
            (str(reminder_id), str(order_id), str(kitchen_id), past),
        )
    conn.close()

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:notify:dispatch", "ckac:notify:tracking")

    response = await client.post(
        "/api/v1/internal/notifications/tracking-interval/tick",
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    tick = response.json()
    assert tick["processed"] >= 1
    assert tick["sent"] >= 1

    messages = await redis_client.xread({"ckac:notify:tracking": "0-0"}, count=10)
    assert len(messages) >= 1
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "notification.tracking_interval"


@pytest.mark.asyncio
async def test_daily_menu_blast(client: AsyncClient):
    kitchen_id = _seed_kitchen()

    response = await client.post(
        "/api/v1/internal/notifications/daily-menu-blast",
        json={
            "kitchen_id": str(kitchen_id),
            "message": "Today's specials: Paneer Tikka. Order on kitchCU!",
            "recipient_count": 12,
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == "daily_menu_blast"
    assert data["status"] == "sent"


@pytest.mark.asyncio
async def test_trial_sample_blast(client: AsyncClient):
    kitchen_id = _seed_kitchen()
    trial_id = uuid.uuid4()

    response = await client.post(
        "/api/v1/internal/notifications/trial-sample-blast",
        json={
            "kitchen_id": str(kitchen_id),
            "trial_id": str(trial_id),
            "dish_name": "Trial Korma",
            "message": "Try our new Trial Korma — free sample for loyal customers!",
            "recipient_count": 8,
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == "trial_sample_offer"
    assert data["status"] == "sent"
