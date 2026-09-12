"""Live Razorpay Checkout (P42) — signature + live vs demo capture."""

from __future__ import annotations

import hashlib
import hmac

import pytest
from httpx import AsyncClient


def _sign(order_id: str, payment_id: str, secret: str) -> str:
    msg = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def test_checkout_signature_roundtrip():
    from app.razorpay_checkout import verify_checkout_signature

    secret = "test_secret"
    order_id = "order_live_abc"
    pay_id = "pay_live_xyz"
    sig = _sign(order_id, pay_id, secret)
    assert verify_checkout_signature(order_id, pay_id, sig, secret) is True
    assert verify_checkout_signature(order_id, pay_id, "deadbeef", secret) is False
    assert verify_checkout_signature(order_id, pay_id, sig, "other") is False


def test_provider_mode_from_order_id():
    from app.razorpay_checkout import checkout_provider_mode

    assert checkout_provider_mode("order_dev_abc") == "demo"
    assert checkout_provider_mode("order_RZabc123") == "live"
    assert checkout_provider_mode(None) == "demo"


@pytest.mark.asyncio
async def test_live_create_returns_key_and_live_order(client: AsyncClient, billing_ctx, monkeypatch):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    async def _creds(_session, _kitchen_id):
        return ("rzp_test_keyid", "rzp_test_secret")

    async def _create_order(**_kwargs):
        return "order_RZlive001"

    monkeypatch.setattr("app.schemas.resolve_razorpay_checkout_creds", _creds)
    monkeypatch.setattr("app.schemas.create_razorpay_order", _create_order)

    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["provider_mode"] == "live"
    assert data["razorpay_key_id"] == "rzp_test_keyid"
    assert data["razorpay_order_id"] == "order_RZlive001"


@pytest.mark.asyncio
async def test_live_capture_rejects_missing_signature(client: AsyncClient, billing_ctx, monkeypatch):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    async def _creds(_session, _kitchen_id):
        return ("rzp_test_keyid", "rzp_test_secret")

    async def _create_order(**_kwargs):
        return "order_RZlive002"

    monkeypatch.setattr("app.schemas.resolve_razorpay_checkout_creds", _creds)
    monkeypatch.setattr("app.schemas.create_razorpay_order", _create_order)

    created = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    payment_id = created.json()["id"]
    capture = await client.post(
        f"/api/v1/billing/payments/{payment_id}/capture",
        headers=headers,
    )
    assert capture.status_code == 400
    assert "signature" in capture.json()["detail"].lower()


@pytest.mark.asyncio
async def test_live_capture_accepts_valid_signature(client: AsyncClient, billing_ctx, monkeypatch):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}
    secret = "rzp_test_secret"

    async def _creds(_session, _kitchen_id):
        return ("rzp_test_keyid", secret)

    async def _create_order(**_kwargs):
        return "order_RZlive003"

    monkeypatch.setattr("app.schemas.resolve_razorpay_checkout_creds", _creds)
    monkeypatch.setattr("app.schemas.create_razorpay_order", _create_order)

    created = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    payment = created.json()
    pay_id = "pay_RZcaptured"
    sig = _sign(payment["razorpay_order_id"], pay_id, secret)
    capture = await client.post(
        f"/api/v1/billing/payments/{payment['id']}/capture",
        json={
            "razorpay_payment_id": pay_id,
            "razorpay_order_id": payment["razorpay_order_id"],
            "razorpay_signature": sig,
        },
        headers=headers,
    )
    assert capture.status_code == 200, capture.text
    body = capture.json()
    assert body["status"] == "captured"
    assert body["razorpay_payment_id"] == pay_id
    assert body["provider_mode"] == "live"


@pytest.mark.asyncio
async def test_master_kill_switch_blocks_live_razorpay(client: AsyncClient, billing_ctx, monkeypatch):
    """Kitchen keys must not reach Razorpay while third-party calls are off.

    Every other outbound integration (Meta, Porter, LiveKit, OAuth, support AI)
    already honours this switch; Checkout order creation has to as well, or a
    kitchen with keys saved makes the whole payment path fail on a stack where
    integrations are deliberately disabled.
    """
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    async def _creds_row(_session, _kitchen_id):
        return ("rzp_test_keyid", "rzp_test_secret")

    async def _must_not_call(**_kwargs):
        raise AssertionError("Razorpay must not be called while integrations are disabled")

    monkeypatch.setattr("app.razorpay_checkout._kitchen_or_platform_creds", _creds_row)
    monkeypatch.setattr("app.schemas.create_razorpay_order", _must_not_call)
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "0")

    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["provider_mode"] == "demo"
    assert data["razorpay_order_id"].startswith("order_dev_")


@pytest.mark.asyncio
async def test_live_razorpay_runs_when_switch_is_on(client: AsyncClient, billing_ctx, monkeypatch):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    async def _creds_row(_session, _kitchen_id):
        return ("rzp_test_keyid", "rzp_test_secret")

    async def _create_order(**_kwargs):
        return "order_RZswitch001"

    monkeypatch.setattr("app.razorpay_checkout._kitchen_or_platform_creds", _creds_row)
    monkeypatch.setattr("app.schemas.create_razorpay_order", _create_order)
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "1")

    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["provider_mode"] == "live"


@pytest.mark.asyncio
async def test_demo_create_still_mocks_without_keys(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/billing/payments",
        json={"order_id": str(order_id), "method": "online"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider_mode"] == "demo"
    assert data["razorpay_order_id"].startswith("order_dev_")
    assert data.get("razorpay_key_id") in (None, "")
