"""Support ticketing tests — public create + admin management."""

import subprocess
import uuid
from pathlib import Path

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt
from datetime import UTC, datetime, timedelta

from tests.conftest import JWT_SECRET, SYNC_DB_URL, _admin_token, _seed_platform_admin

NOTIFY_ROOT = Path(__file__).resolve().parents[1]


def _ensure_support_migrated() -> None:
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=NOTIFY_ROOT,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session", autouse=True)
def support_schema():
    _ensure_support_migrated()


@pytest.fixture
def admin_headers():
    _seed_platform_admin()
    return {"Authorization": f"Bearer {_admin_token()}"}


@pytest.mark.asyncio
async def test_create_ticket_public(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/tickets",
        json={
            "audience": "customer",
            "category": "order_issue",
            "subject": "Wrong items in order",
            "description": "I ordered butter chicken but received paneer. Order CKPNQ001-BILL-20260712-0001.",
            "customer_name": "Priya Mehta",
            "customer_phone": "+919876543211",
            "order_code": "CKPNQ001-BILL-20260712-0001",
            "source": "ai_chat",
            "chat_history": [
                {"role": "user", "content": "My order was wrong"},
                {"role": "assistant", "content": "Sorry to hear that."},
            ],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ticket_number"].startswith("TKT-")
    assert data["status"] == "open"
    assert data["priority"] == "high"
    assert data["category"] == "order_issue"
    assert len(data["messages"]) >= 2


@pytest.mark.asyncio
async def test_admin_list_tickets_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/admin/tickets")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_manage_ticket(client: AsyncClient, admin_headers):
    create = await client.post(
        "/api/v1/support/tickets",
        json={
            "audience": "owner",
            "category": "billing",
            "subject": "Subscription question",
            "description": "Need to upgrade from Starter to Growth plan for analytics.",
            "customer_name": "Raj Sharma",
            "customer_email": "raj@example.com",
        },
    )
    assert create.status_code == 201
    ticket_id = create.json()["id"]

    listed = await client.get("/api/v1/admin/tickets", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = await client.get(f"/api/v1/admin/tickets/{ticket_id}", headers=admin_headers)
    assert detail.status_code == 200

    updated = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "in_progress", "priority": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    replied = await client.post(
        f"/api/v1/admin/tickets/{ticket_id}/reply",
        headers=admin_headers,
        json={"message": "We have upgraded your plan. Please refresh kitchen.kitchcu.in."},
    )
    assert replied.status_code == 200
    assert any(m["author_type"] == "admin" for m in replied.json()["messages"])

    resolved = await client.patch(
        f"/api/v1/admin/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "resolved", "resolution_note": "Plan upgraded manually."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_chat_suggests_ticket_for_complaint(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/chat",
        json={
            "audience": "customer",
            "message": "I want to raise a complaint about my wrong order",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["suggest_ticket"] is True
    assert data["suggested_category"] == "order_issue"
