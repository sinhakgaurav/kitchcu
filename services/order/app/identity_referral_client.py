"""Notify identity when a customer places an order (kitchen→customer referral trigger)."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def notify_customer_first_order(
    *,
    customer_id: uuid.UUID,
    customer_phone: str | None,
) -> None:
    url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/internal/referrals/customer-first-order"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json={
                    "customer_id": str(customer_id),
                    "customer_phone": customer_phone,
                },
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            if response.status_code >= 400:
                logger.warning(
                    "referral first-order notify failed status=%s", response.status_code
                )
    except Exception as exc:
        logger.warning("order→identity referral notify failed: %s", exc)
