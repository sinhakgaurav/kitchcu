"""Shared contact validators applied to notification intake (`ckac_common.validators`).

A support ticket or a dispatch request must not be able to introduce a phone
that owner registration would have rejected — an undeliverable number here
silently kills every WhatsApp order update that follows.
"""

import os
import subprocess
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "test-internal-key-for-pytest")
NOTIFY_ROOT = Path(__file__).resolve().parents[1]

TICKET_BODY = {
    "audience": "customer",
    "category": "order_issue",
    "subject": "Wrong items in order",
    "description": "I ordered butter chicken but received paneer instead.",
}


@pytest.fixture(scope="session", autouse=True)
def support_schema():
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd=NOTIFY_ROOT,
        check=True,
        capture_output=True,
    )


# ------------------------------------------------------------------- tickets


@pytest.mark.parametrize(
    "raw",
    ["+919876543211", "919876543211", "9876543211", "0091 9876543211", "09876543211"],
)
@pytest.mark.asyncio
async def test_ticket_phone_normalized_to_e164(client: AsyncClient, raw: str):
    r = await client.post(
        "/api/v1/support/tickets", json={**TICKET_BODY, "customer_phone": raw}
    )
    assert r.status_code == 201
    assert r.json()["customer_phone"] == "+919876543211"


@pytest.mark.parametrize(
    "raw",
    [
        "987654321011",  # 12 digits, no 91 dial code
        "98765432101",  # 11 digits
        "+14155552671",  # foreign country code
        "0123456789",  # leading 0 is not a mobile prefix
        "3876543210",  # leading 3 is not a mobile prefix
    ],
)
@pytest.mark.asyncio
async def test_ticket_rejects_undeliverable_phone(client: AsyncClient, raw: str):
    r = await client.post(
        "/api/v1/support/tickets", json={**TICKET_BODY, "customer_phone": raw}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_ticket_email_is_lowercased(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/tickets",
        json={**TICKET_BODY, "customer_email": "Priya@KitchCU.DEV"},
    )
    assert r.status_code == 201
    assert r.json()["customer_email"] == "priya@kitchcu.dev"


@pytest.mark.asyncio
async def test_ticket_name_keeps_machine_assigned_label(client: AsyncClient):
    """A signed-in reporter's name is prefilled from their profile, which is a
    `Customer 0481` label for OTP signups — display rules, not person-name rules."""
    r = await client.post(
        "/api/v1/support/tickets",
        json={**TICKET_BODY, "customer_name": "  Customer 0481  "},
    )
    assert r.status_code == 201
    assert r.json()["customer_name"] == "Customer 0481"


@pytest.mark.asyncio
async def test_ticket_rejects_overlong_name(client: AsyncClient):
    r = await client.post(
        "/api/v1/support/tickets", json={**TICKET_BODY, "customer_name": "x" * 121}
    )
    assert r.status_code == 422


# ------------------------------------------------------------------ dispatch


@pytest.mark.parametrize("raw", ["9876543210", "00919876543210", "+91-98765-43210"])
@pytest.mark.asyncio
async def test_order_placed_phone_normalized_to_e164(client: AsyncClient, raw: str):
    from tests.conftest import _seed_kitchen

    kitchen_id = _seed_kitchen()
    response = await client.post(
        "/api/v1/internal/notifications/order-placed",
        json={
            "order_id": str(uuid.uuid4()),
            "kitchen_id": str(kitchen_id),
            "order_code": "CKTEST-BILL-20260713-0009",
            "customer_phone": raw,
            "delivery_type": "pickup",
            "total": 239,
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200

    import psycopg2

    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT recipient_phone FROM ckac_notifications.notification_log "
            "WHERE id = %s::uuid",
            (response.json()["notification_id"],),
        )
        row = cur.fetchone()
    conn.close()
    assert row[0] == "+919876543210"


@pytest.mark.parametrize("raw", ["987654321011", "0123456789"])
@pytest.mark.asyncio
async def test_order_placed_rejects_undeliverable_phone(client: AsyncClient, raw: str):
    from tests.conftest import _seed_kitchen

    kitchen_id = _seed_kitchen()
    response = await client.post(
        "/api/v1/internal/notifications/order-placed",
        json={
            "order_id": str(uuid.uuid4()),
            "kitchen_id": str(kitchen_id),
            "order_code": "CKTEST-BILL-20260713-0010",
            "customer_phone": raw,
            "delivery_type": "pickup",
            "total": 239,
        },
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 422


# ----------------------------------------------------------------------- OTP


@pytest.mark.parametrize("raw", ["9876543210", "00919876543210", "09876543210"])
@pytest.mark.asyncio
async def test_otp_dispatch_accepts_every_shape(client: AsyncClient, raw: str):
    response = await client.post(
        "/api/v1/internal/notifications/otp",
        json={"phone": raw, "code": "123456", "purpose": "customer_login"},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.parametrize("raw", ["98765432101", "0123456789", "+14155552671"])
@pytest.mark.asyncio
async def test_otp_dispatch_rejects_undeliverable_phone(client: AsyncClient, raw: str):
    response = await client.post(
        "/api/v1/internal/notifications/otp",
        json={"phone": raw, "code": "123456", "purpose": "customer_login"},
        headers={"X-Internal-Key": INTERNAL_KEY},
    )
    assert response.status_code == 422
