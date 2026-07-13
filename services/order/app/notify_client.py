"""Fire-and-forget calls to notification service after order writes."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def notify_order_placed(
    *,
    order_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    order_code: str,
    customer_phone: str | None,
    delivery_type: str,
    total: float,
    tracking_token: str | None,
) -> None:
    payload = {
        "order_id": str(order_id),
        "kitchen_id": str(kitchen_id),
        "order_code": order_code,
        "customer_phone": customer_phone,
        "delivery_type": delivery_type,
        "total": total,
        "tracking_token": tracking_token,
    }
    await _post("/api/v1/internal/notifications/order-placed", payload)


async def notify_order_status_changed(
    *,
    order_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    order_code: str,
    customer_phone: str | None,
    from_status: str,
    to_status: str,
    tracking_token: str | None,
) -> None:
    payload = {
        "order_id": str(order_id),
        "kitchen_id": str(kitchen_id),
        "order_code": order_code,
        "customer_phone": customer_phone,
        "from_status": from_status,
        "to_status": to_status,
        "tracking_token": tracking_token,
    }
    await _post("/api/v1/internal/notifications/order-status-changed", payload)


async def dispatch_order_placed(order) -> None:
    await notify_order_placed(
        order_id=order.id,
        kitchen_id=order.kitchen_id,
        order_code=order.order_code,
        customer_phone=order.customer_phone,
        delivery_type=order.delivery_type,
        total=float(order.total),
        tracking_token=order.tracking_token,
    )


async def dispatch_order_status_changed(order, from_status: str) -> None:
    await notify_order_status_changed(
        order_id=order.id,
        kitchen_id=order.kitchen_id,
        order_code=order.order_code,
        customer_phone=order.customer_phone,
        from_status=from_status,
        to_status=order.status,
        tracking_token=order.tracking_token,
    )


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
