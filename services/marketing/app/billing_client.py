"""Billing service client — messaging wallet deduct."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def deduct_messaging_wallet(
    kitchen_id: uuid.UUID,
    *,
    amount_inr: float,
    reason: str,
    recipient_count: int,
) -> bool:
    """Return True when deduct succeeded, False when billing unreachable or insufficient."""
    url = (
        f"{settings.billing_service_url.rstrip('/')}"
        f"/api/v1/internal/wallets/{kitchen_id}/deduct"
    )
    payload = {
        "amount_inr": amount_inr,
        "reason": reason,
        "recipient_count": recipient_count,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            response.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("messaging wallet deduct failed for %s: %s", kitchen_id, exc)
        return False
