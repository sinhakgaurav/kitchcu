"""Notification client — trial sample WhatsApp blast."""

from __future__ import annotations

import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key


async def notify_trial_sample_blast(
    *,
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    dish_name: str,
    message: str,
    recipient_count: int,
) -> None:
    settings = get_settings()
    url = f"{settings.notification_service_url.rstrip('/')}/api/v1/internal/notifications/trial-sample-blast"
    payload = {
        "kitchen_id": str(kitchen_id),
        "trial_id": str(trial_id),
        "dish_name": dish_name,
        "message": message,
        "recipient_count": recipient_count,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"X-Internal-Key": resolve_internal_api_key()},
        )
    if response.status_code >= 400:
        detail = response.json().get("detail", "Notification request failed")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
