"""Porter courier webhook → order.courier_status sync (does not auto-drive food SM)."""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

logger = logging.getLogger(__name__)

# Porter / partner status → normalized courier_status stored on the order.
_STATUS_MAP = {
    "order_accepted": "accepted",
    "accepted": "accepted",
    "assigned": "assigned",
    "rider_assigned": "assigned",
    "pickup_started": "pickup",
    "reached_pickup": "pickup",
    "picked_up": "picked_up",
    "order_picked_up": "picked_up",
    "in_transit": "in_transit",
    "out_for_delivery": "in_transit",
    "reached_drop": "nearby",
    "delivered": "delivered",
    "order_delivered": "delivered",
    "cancelled": "cancelled",
    "order_cancelled": "cancelled",
    "failed": "failed",
}


def normalize_porter_status(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    return _STATUS_MAP.get(key, key[:64])


def extract_porter_job_and_status(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Best-effort parse of Porter partner webhook bodies."""
    job_id = (
        payload.get("order_id")
        or payload.get("crn")
        or payload.get("job_id")
        or payload.get("id")
    )
    status = payload.get("status") or payload.get("order_status") or payload.get("event")
    data = payload.get("data")
    if isinstance(data, dict):
        job_id = job_id or data.get("order_id") or data.get("crn") or data.get("id")
        status = status or data.get("status") or data.get("order_status")
    return (str(job_id) if job_id else None, normalize_porter_status(status if isinstance(status, str) else None))


def verify_porter_webhook_secret(header_secret: str | None) -> bool:
    """Optional shared secret via PORTER_WEBHOOK_SECRET (header X-Porter-Secret or X-Webhook-Secret)."""
    expected = (os.getenv("PORTER_WEBHOOK_SECRET") or "").strip()
    if not expected:
        # Dev/mock: allow when secret unset (same posture as early WA verify).
        return True
    if not header_secret:
        return False
    return hmac.compare_digest(header_secret.strip(), expected)


async def apply_porter_webhook(
    session: AsyncSession,
    payload: dict[str, Any],
    publisher: EventPublisher | None,
) -> dict[str, Any]:
    job_id, courier_status = extract_porter_job_and_status(payload)
    if not job_id:
        raise ValueError("Porter webhook missing order/job id")
    if not courier_status:
        raise ValueError("Porter webhook missing status")

    result = await session.execute(
        select(Order).where(Order.courier_job_id == job_id).limit(1)
    )
    order = result.scalar_one_or_none()
    if order is None:
        # Idempotent unknown job — acknowledge without leaking existence details in prod logs.
        logger.info("Porter webhook for unknown job_id (ignored)")
        return {"acknowledged": True, "matched": False}

    order.courier_status = courier_status
    order.courier_partner = order.courier_partner or "porter"
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.courier_status.updated",
            aggregate_type="order",
            aggregate_id=str(order.id),
            producer="order-service",
            payload={
                "order_id": str(order.id),
                "kitchen_id": str(order.kitchen_id),
                "courier_job_id": job_id,
                "courier_status": courier_status,
                # Food lifecycle stays owner-driven — courier_status is logistics only.
                "order_status": order.status,
            },
        )
        await publisher.publish(stream_key("orders", "order"), event, session=session)

    return {
        "acknowledged": True,
        "matched": True,
        "order_id": str(order.id),
        "courier_status": courier_status,
    }
