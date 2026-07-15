"""Refund API — full gateway + partial direct transfer with evidence."""

import io
import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


def _seed_customer_with_payout(phone: str, *, upi: str = "priya@okaxis") -> uuid.UUID:
    customer_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers
            (id, name, phone, status, upi_vpa, bank_account_number, bank_ifsc, bank_account_name)
            VALUES (%s::uuid, 'Priya', %s, 'active', %s, '123456789012', 'HDFC0001234', 'Priya Customer')
            """,
            (str(customer_id), phone, upi),
        )
    conn.close()
    return customer_id


def _set_order_phone(order_id: uuid.UUID, phone: str) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_orders.orders SET customer_phone = %s WHERE id = %s::uuid",
            (phone, str(order_id)),
        )
    conn.close()


async def _capture_payment(client: AsyncClient, order_id: uuid.UUID, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert created.status_code == 201
    payment_id = created.json()["id"]
    captured = await client.post(f"/api/v1/billing/payments/{payment_id}/capture", headers=headers)
    assert captured.status_code == 200
    return payment_id


@pytest.mark.asyncio
async def test_full_gateway_refund(client: AsyncClient, billing_ctx):
    _, _, order_id, code, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}
    await _capture_payment(client, order_id, token)

    create = await client.post(
        "/api/v1/billing/refunds",
        json={"order_id": str(order_id), "kind": "full", "channel": "gateway", "reason": "cancelled"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["kind"] == "full"
    assert body["channel"] == "gateway"
    assert body["status"] == "requested"
    assert body["transfer_remark"] == f"{code}-BILL-20260712-0001"

    process = await client.post(f"/api/v1/billing/refunds/{body['id']}/process", headers=headers)
    assert process.status_code == 200, process.text
    assert process.json()["status"] == "completed"
    assert process.json()["razorpay_refund_id"].startswith("rfnd_dev_")

    pay = await client.get(
        f"/api/v1/billing/payments/{body['payment_id']}",
        headers=headers,
    )
    assert pay.json()["status"] == "refunded"


@pytest.mark.asyncio
async def test_partial_requires_direct_and_evidence(client: AsyncClient, billing_ctx):
    _, _, order_id, code, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}
    phone = "+919123456789"
    _seed_customer_with_payout(phone)
    _set_order_phone(order_id, phone)
    await _capture_payment(client, order_id, token)

    bad = await client.post(
        "/api/v1/billing/refunds",
        json={"order_id": str(order_id), "kind": "partial", "channel": "gateway", "amount": 50},
        headers=headers,
    )
    assert bad.status_code == 422 or bad.status_code == 400

    create = await client.post(
        "/api/v1/billing/refunds",
        json={"order_id": str(order_id), "kind": "partial", "amount": 100.0, "reason": "missing item"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    refund = create.json()
    assert refund["channel"] == "direct_transfer"
    assert refund["amount"] == 100.0
    assert refund["destination_type"] == "upi"
    assert refund["destination_upi"] == "priya@okaxis"
    assert refund["transfer_remark"] == f"{code}-BILL-20260712-0001"

    complete_early = await client.post(
        f"/api/v1/billing/refunds/{refund['id']}/complete",
        headers=headers,
    )
    assert complete_early.status_code == 400
    assert "screenshot" in complete_early.json()["detail"].lower() or "evidence" in complete_early.json()[
        "detail"
    ].lower()

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
        b"\x00\x00IEND\xaeB`\x82"
    )
    evidence = await client.post(
        f"/api/v1/billing/refunds/{refund['id']}/evidence",
        headers=headers,
        files={"file": ("proof.png", io.BytesIO(png), "image/png")},
    )
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["evidence_url"]

    complete = await client.post(
        f"/api/v1/billing/refunds/{refund['id']}/complete",
        headers=headers,
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"

    pay = await client.get(
        f"/api/v1/billing/payments/{refund['payment_id']}",
        headers=headers,
    )
    assert pay.json()["status"] == "partially_refunded"


@pytest.mark.asyncio
async def test_refund_webhook_completes_gateway_refund(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}
    payment_id = await _capture_payment(client, order_id, token)
    pay = await client.get(f"/api/v1/billing/payments/{payment_id}", headers=headers)
    rz_pay = pay.json()["razorpay_payment_id"]

    created = await client.post(
        "/api/v1/billing/refunds",
        json={"order_id": str(order_id), "kind": "full", "channel": "gateway"},
        headers=headers,
    )
    assert created.status_code == 201

    hook = await client.post(
        "/api/v1/webhooks/razorpay",
        json={
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_test_webhook_1",
                        "payment_id": rz_pay,
                        "amount": 39800,
                    }
                }
            },
        },
    )
    assert hook.status_code == 200
    assert hook.json()["status"] == "ok"

    listed = await client.get(
        f"/api/v1/billing/refunds?order_id={order_id}",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "completed"
    assert listed.json()[0]["razorpay_refund_id"] == "rfnd_test_webhook_1"
