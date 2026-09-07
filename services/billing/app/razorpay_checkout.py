"""Live Razorpay Orders + Checkout signature (P42).

Kitchen Payment Gateway keys win; platform API Keys / env are fallback.
Never returns the secret to clients — only `key_id` for Checkout.js.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KitchenPaymentGateway
from ckac_common.platform_config import get_platform_secret, is_dev_provider_id
from ckac_common.secret_box import decrypt_secret

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"
PROVIDER = "razorpay"


def checkout_provider_mode(razorpay_order_id: str | None) -> str:
    if razorpay_order_id and not is_dev_provider_id(razorpay_order_id):
        return "live"
    return "demo"


def verify_checkout_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    signature: str,
    secret: str,
) -> bool:
    if not razorpay_order_id or not razorpay_payment_id or not signature or not secret:
        return False
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


async def resolve_razorpay_checkout_creds(
    session: AsyncSession,
    kitchen_id: uuid.UUID | None,
) -> tuple[str, str] | None:
    """Return (key_id, key_secret) or None when live Checkout cannot run."""
    if kitchen_id is not None:
        row = (
            await session.execute(
                select(KitchenPaymentGateway).where(
                    KitchenPaymentGateway.kitchen_id == kitchen_id,
                    KitchenPaymentGateway.provider == PROVIDER,
                    KitchenPaymentGateway.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row and row.key_id:
            secret = decrypt_secret(row.key_secret_enc)
            if secret:
                return row.key_id.strip(), secret
    key_id = await get_platform_secret(session, "razorpay_key_id")
    key_secret = await get_platform_secret(session, "razorpay_key_secret")
    if key_id and key_secret:
        return key_id.strip(), key_secret.strip()
    return None


async def create_razorpay_order(
    *,
    key_id: str,
    key_secret: str,
    amount: float,
    receipt: str,
    notes: dict[str, Any] | None = None,
) -> str:
    paise = int(round(float(amount) * 100))
    if paise < 100:
        raise ValueError("Razorpay order amount must be at least ₹1.00")
    payload = {
        "amount": paise,
        "currency": "INR",
        "receipt": receipt[:40],
        "notes": notes or {},
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            RAZORPAY_ORDERS_URL,
            auth=(key_id, key_secret),
            json=payload,
        )
    if response.status_code >= 400:
        detail = (response.text or "")[:240]
        raise ValueError(f"Razorpay order create failed ({response.status_code}): {detail}")
    body = response.json()
    order_id = body.get("id")
    if not isinstance(order_id, str) or not order_id:
        raise ValueError("Razorpay order create returned no id")
    return order_id
