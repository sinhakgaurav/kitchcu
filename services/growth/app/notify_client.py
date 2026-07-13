"""Fire-and-forget calls to notification service after growth writes."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def notify_daily_menu_blast(
    *,
    kitchen_id: uuid.UUID,
    message: str,
    recipient_count: int,
) -> None:
    payload = {
        "kitchen_id": str(kitchen_id),
        "message": message,
        "recipient_count": recipient_count,
    }
    await _post("/api/v1/internal/notifications/daily-menu-blast", payload)


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
