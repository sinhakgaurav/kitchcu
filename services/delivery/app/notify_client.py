"""Fire-and-forget calls to notification service after delivery writes (F28)."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def notify_delivery_fee_denied(
    *,
    kitchen_id: uuid.UUID,
    quote_id: uuid.UUID,
    distance_km: float,
    fee: float,
    subtotal: float,
    customer_phone: str | None,
) -> None:
    payload = {
        "kitchen_id": str(kitchen_id),
        "quote_id": str(quote_id),
        "distance_km": distance_km,
        "fee": fee,
        "subtotal": subtotal,
        "customer_phone": customer_phone,
    }
    await _post("/api/v1/internal/notifications/delivery-fee-denied", payload)


async def _post(path: str, payload: dict) -> None:
    url = f"{settings.notification_service_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("notification dispatch failed: %s", exc)
