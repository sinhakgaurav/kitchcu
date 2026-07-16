"""Gap wiring — kitchen linked accounts, webhook signature, feature flags (TDD)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from ckac_common.platform_config import verify_razorpay_webhook_signature
from ckac_common.secret_box import encrypt_secret
from tests.conftest import SYNC_DB_URL
from tests.test_master_payments import _seed_master_order_context


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_razorpay_webhook_signature_roundtrip():
    secret = "whsec_test_abc"
    body = b'{"event":"payment.captured"}'
    sig = _sign(body, secret)
    assert verify_razorpay_webhook_signature(body, sig, secret) is True
    assert verify_razorpay_webhook_signature(body, "bad", secret) is False


@pytest.mark.asyncio
async def test_linked_account_prefers_kitchen_payment_gateway():
    from app.schemas import _get_kitchen_linked_account
    from ckac_common.database import SessionLocal

    master_id, _, _headers = _seed_master_order_context()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT kitchen_id FROM ckac_orders.orders WHERE master_order_id = %s::uuid LIMIT 1",
            (str(master_id),),
        )
        kitchen_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO ckac_billing.kitchen_payment_gateways
                (id, kitchen_id, provider, key_id, linked_account_id, is_active)
            VALUES (%s::uuid, %s::uuid, 'razorpay', 'rzp_test', 'acc_from_gateway_table', true)
            ON CONFLICT (kitchen_id, provider) DO UPDATE
            SET linked_account_id = EXCLUDED.linked_account_id, is_active = true
            """,
            (str(uuid.uuid4()), str(kitchen_id)),
        )
    conn.close()

    async with SessionLocal() as session:
        linked = await _get_kitchen_linked_account(session, uuid.UUID(str(kitchen_id)))
    assert linked == "acc_from_gateway_table"


@pytest.mark.asyncio
async def test_refund_blocked_when_gateway_flag_disabled(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    pay = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert pay.status_code == 201, pay.text
    pid = pay.json()["id"]
    cap = await client.post(f"/api/v1/billing/payments/{pid}/capture", headers=headers)
    assert cap.status_code == 200, cap.text

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'refunds_gateway'"
        )
    conn.close()

    try:
        created = await client.post(
            "/api/v1/billing/refunds",
            json={"order_id": str(order_id), "kind": "full", "channel": "gateway"},
            headers=headers,
        )
        assert created.status_code == 403, created.text
        assert "refunds_gateway" in created.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'refunds_gateway'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature_when_secret_configured(client: AsyncClient):
    enc = encrypt_secret("whsec_billing_test")
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_api_keys (key, category, is_secret, value_enc, updated_at)
            VALUES ('razorpay_webhook_secret', 'payments', true, %s, now())
            ON CONFLICT (key) DO UPDATE SET value_enc = EXCLUDED.value_enc
            """,
            (enc,),
        )
    conn.close()

    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {}}}}
    raw = json.dumps(payload).encode()
    try:
        bad = await client.post(
            "/api/v1/webhooks/razorpay",
            content=raw,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": "deadbeef"},
        )
        assert bad.status_code == 401

        good_sig = _sign(raw, "whsec_billing_test")
        ok_sig = await client.post(
            "/api/v1/webhooks/razorpay",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": good_sig,
            },
        )
        assert ok_sig.status_code == 400
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.platform_api_keys SET value_enc = NULL "
                "WHERE key = 'razorpay_webhook_secret'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_multi_kitchen_payment_blocked_when_flag_disabled(client: AsyncClient):
    master_id, _, headers = _seed_master_order_context()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false WHERE key = 'multi_kitchen_checkout'"
        )
    conn.close()
    try:
        response = await client.post(
            "/api/v1/billing/payments/customer/master",
            json={"master_order_id": str(master_id), "method": "online"},
            headers=headers,
        )
        assert response.status_code == 403, response.text
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true WHERE key = 'multi_kitchen_checkout'"
            )
        conn.close()
