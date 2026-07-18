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


async def notify_golden_performance_day(
    *,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    dish_name: str,
    performance_date: str,
    order_qty: int,
    avg_rating: float | None,
    sentiment_label: str,
    suggestion_id: uuid.UUID,
) -> None:
    payload = {
        "kitchen_id": str(kitchen_id),
        "dish_id": str(dish_id),
        "dish_name": dish_name,
        "performance_date": performance_date,
        "order_qty": order_qty,
        "avg_rating": avg_rating,
        "sentiment_label": sentiment_label,
        "suggestion_id": str(suggestion_id),
    }
    await _post("/api/v1/internal/notifications/golden-performance-day", payload)


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
