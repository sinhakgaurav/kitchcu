"""EDD — support ticket writes must publish Redis Stream + transactional outbox."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, _admin_token, _seed_platform_admin

NOTIFY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def support_schema():
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=NOTIFY_ROOT,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def admin_headers():
    _seed_platform_admin()
    return {"Authorization": f"Bearer {_admin_token()}"}


def _latest_outbox(event_type: str) -> tuple[str, bool] | None:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_type, published FROM ckac_events.outbox "
            "WHERE event_type = %s ORDER BY created_at DESC LIMIT 1",
            (event_type,),
        )
        row = cur.fetchone()
    conn.close()
    return (row[0], row[1]) if row else None


@pytest.mark.asyncio
async def test_ticket_created_publishes_stream_and_outbox(client: AsyncClient):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:notify:support")

    r = await client.post(
        "/api/v1/support/tickets",
        json={
            "audience": "customer",
            "category": "order_issue",
            "subject": "EDD ticket create",
            "description": "Wrong items — event assert path for support.ticket.created.",
            "customer_name": "Priya Mehta",
            "customer_phone": "+919876543299",
            "source": "ai_chat",
        },
    )
    assert r.status_code == 201, r.text
    ticket_id = r.json()["id"]
    ticket_number = r.json()["ticket_number"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:notify:support": "0-0"}, count=20)
    assert len(messages) >= 1
    _, entries = messages[0]
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "support.ticket.created"
    assert event_data["aggregate_type"] == "support_ticket"
    assert event_data["aggregate_id"] == ticket_id
    assert event_data["producer"] == "notification-service"
    assert event_data["payload"]["ticket_number"] == ticket_number

    outbox = _latest_outbox("support.ticket.created")
    assert outbox is not None
    assert outbox[1] is True


@pytest.mark.asyncio
async def test_ticket_updated_and_replied_publish_events(
    client: AsyncClient, admin_headers: dict
):
    from app.main import redis_client

    create = await client.post(
        "/api/v1/support/tickets",
        json={
            "audience": "owner",
            "category": "billing",
            "subject": "EDD ticket update",
            "description": "Need plan upgrade — event assert for updated/replied.",
            "customer_name": "Raj Sharma",
            "customer_email": "raj-edd@example.com",
        },
    )
    assert create.status_code == 201, create.text
    ticket_id = create.json()["id"]

    if redis_client:
        await redis_client.delete("ckac:notify:support")

    updated = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "in_progress", "priority": "high"},
    )
    assert updated.status_code == 200, updated.text

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:notify:support": "0-0"}, count=20)
    assert len(messages) >= 1
    _, entries = messages[0]
    types = [json.loads(e[1]["data"])["event_type"] for e in entries]
    assert "support.ticket.updated" in types

    outbox_u = _latest_outbox("support.ticket.updated")
    assert outbox_u is not None
    assert outbox_u[1] is True

    if redis_client:
        await redis_client.delete("ckac:notify:support")

    replied = await client.post(
        f"/api/v1/admin/tickets/{ticket_id}/reply",
        headers=admin_headers,
        json={"message": "Plan upgraded — EDD reply event."},
    )
    assert replied.status_code == 200, replied.text

    messages = await redis_client.xread({"ckac:notify:support": "0-0"}, count=20)
    assert len(messages) >= 1
    _, entries = messages[0]
    types = [json.loads(e[1]["data"])["event_type"] for e in entries]
    assert "support.ticket.replied" in types

    outbox_r = _latest_outbox("support.ticket.replied")
    assert outbox_r is not None
    assert outbox_r[1] is True
