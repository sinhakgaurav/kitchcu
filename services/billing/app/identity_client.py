"""Identity service client — owner profile sync (no cross-schema writes)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def sync_owner_subscription(
    owner_id: uuid.UUID,
    *,
    plan_tier: str,
    subscription_expires_at: datetime,
) -> None:
    """Notify identity to update owner subscription fields after billing activation."""
    url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/internal/owners/{owner_id}/subscription"
    )
    payload = {
        "plan_tier": plan_tier,
        "subscription_status": "active",
        "subscription_expires_at": subscription_expires_at.isoformat(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.patch(
            url,
            json=payload,
            headers={"X-Internal-Key": resolve_internal_api_key()},
        )
        response.raise_for_status()
