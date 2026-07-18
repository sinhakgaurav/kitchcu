"""Delayed Porter auto-booking after order accept (P35)."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.platform_config import is_kitchen_module_enabled

logger = logging.getLogger("order.porter_auto_book")

MODULE_KEY = "courier_porter_auto_book"
ACTIVE_STATUSES = frozenset({"accepted", "preparing", "ready"})
DEFAULT_DELAY_MIN = 15
DEFAULT_RETRY_MIN = 2
DEFAULT_MAX_ATTEMPTS = 30


def retry_interval_min() -> int:
    raw = os.getenv("PORTER_AUTO_BOOK_RETRY_MIN", str(DEFAULT_RETRY_MIN))
    try:
        return max(1, min(30, int(raw)))
    except ValueError:
        return DEFAULT_RETRY_MIN


def max_attempts() -> int:
    raw = os.getenv("PORTER_AUTO_BOOK_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS))
    try:
        return max(1, min(100, int(raw)))
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS


def compute_order_eta(
    *,
    from_time: datetime,
    prep_min: int,
    delivery_min: int,
    delivery_type: str,
) -> tuple[datetime, datetime | None, int]:
    """Return (ready_at, delivery_at, delivery_min_stored)."""
    prep = max(0, int(prep_min or 0))
    delivery = max(0, int(delivery_min or 0)) if delivery_type == "delivery" else 0
    ready_at = from_time + timedelta(minutes=prep)
    delivery_at = ready_at + timedelta(minutes=delivery) if delivery_type == "delivery" else None
    return ready_at, delivery_at, delivery


async def load_kitchen_porter_settings(
    session: AsyncSession, kitchen_id
) -> dict[str, Any]:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COALESCE(porter_auto_book_enabled, true) AS porter_auto_book_enabled,
                    COALESCE(porter_auto_book_delay_min, 15) AS porter_auto_book_delay_min
                FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1
                """
            ),
            {"kid": kitchen_id},
        )
    ).mappings().one_or_none()
    if not row:
        return {"enabled": True, "delay_min": DEFAULT_DELAY_MIN}
    delay = int(row["porter_auto_book_delay_min"] or DEFAULT_DELAY_MIN)
    delay = max(1, min(120, delay))
    return {"enabled": bool(row["porter_auto_book_enabled"]), "delay_min": delay}


async def kitchen_auto_book_entitled(session: AsyncSession, kitchen_id) -> bool:
    try:
        return await is_kitchen_module_enabled(
            session, kitchen_id, MODULE_KEY, default=True
        )
    except Exception:
        return True


async def should_schedule_auto_book(session: AsyncSession, order: Order) -> bool:
    if order.delivery_type != "delivery":
        return False
    if getattr(order, "delivery_mode", None) != "platform":
        return False
    if getattr(order, "courier_job_id", None):
        return False
    settings = await load_kitchen_porter_settings(session, order.kitchen_id)
    if not settings["enabled"]:
        return False
    return await kitchen_auto_book_entitled(session, order.kitchen_id)


async def schedule_porter_auto_book(
    session: AsyncSession,
    order: Order,
    publisher: EventPublisher | None,
    *,
    accepted_at: datetime | None = None,
) -> bool:
    """Mark order for delayed Porter book. Returns True if scheduled."""
    if not await should_schedule_auto_book(session, order):
        return False

    settings = await load_kitchen_porter_settings(session, order.kitchen_id)
    now = accepted_at or datetime.now(UTC)
    prep = int(order.estimated_prep_min or 0)
    delivery = int(getattr(order, "estimated_delivery_min", None) or 0)
    ready_at, delivery_at, delivery_stored = compute_order_eta(
        from_time=now,
        prep_min=prep,
        delivery_min=delivery,
        delivery_type=order.delivery_type,
    )
    order.estimated_ready_at = ready_at
    order.estimated_delivery_at = delivery_at
    order.estimated_delivery_min = delivery_stored
    order.porter_auto_book_at = now + timedelta(minutes=settings["delay_min"])
    order.porter_auto_book_attempts = 0
    order.porter_auto_book_last_attempt_at = None
    order.updated_at = now
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.porter_auto_book.scheduled",
            aggregate_type="order",
            aggregate_id=str(order.id),
            producer="order-service",
            payload={
                "kitchen_id": str(order.kitchen_id),
                "order_id": str(order.id),
                "order_code": order.order_code,
                "porter_auto_book_at": order.porter_auto_book_at.isoformat(),
                "estimated_ready_at": ready_at.isoformat(),
                "delay_min": settings["delay_min"],
            },
        )
        await publisher.publish(stream_key("orders", "order"), event, session=session)
    return True


async def apply_porter_booking_result(
    session: AsyncSession,
    order: Order,
    booked: dict,
) -> None:
    """Persist Porter job + adjust owner logistics cost if fare differs."""
    from app.cost_share import split_delivery_cost

    order.courier_partner = "porter"
    order.courier_job_id = booked.get("job_id")
    order.porter_auto_book_at = None
    if booked.get("fee") is None or order.distance_km is None:
        return

    kitchen_row = (
        await session.execute(
            text(
                """
                SELECT
                    max_delivery_radius_km,
                    min_order_for_free_delivery,
                    COALESCE(delivery_subsidy_percent, 50) AS delivery_subsidy_percent
                FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1
                """
            ),
            {"kid": order.kitchen_id},
        )
    ).mappings().one_or_none()
    if not kitchen_row:
        return
    in_range = float(order.distance_km) <= float(kitchen_row["max_delivery_radius_km"])
    min_order = (
        float(kitchen_row["min_order_for_free_delivery"])
        if kitchen_row["min_order_for_free_delivery"] is not None
        else None
    )
    share = split_delivery_cost(
        gross_fee=float(booked["fee"]),
        in_range=in_range,
        subtotal=float(order.subtotal or 0),
        min_order_for_subsidy=min_order,
        subsidy_percent=float(kitchen_row["delivery_subsidy_percent"] or 50),
    )
    order.owner_delivery_cost = max(
        float(share["owner_fee"]),
        float(booked["fee"]) - float(order.delivery_fee or 0),
    )
    order.delivery_payer = share["payer"]


async def attempt_porter_book(
    session: AsyncSession,
    order: Order,
    publisher: EventPublisher | None,
    *,
    reason: str,
) -> bool:
    """Try booking Porter once. Returns True if booked."""
    from app.delivery_fee_payment import porter_requires_prepaid_capture
    from app.payment_gate import order_has_captured_payment
    from app.porter_client import quote_and_book_porter

    if order.courier_job_id:
        order.porter_auto_book_at = None
        return True

    if porter_requires_prepaid_capture(
        delivery_mode=order.delivery_mode,
        delivery_fee_payment=getattr(order, "delivery_fee_payment", None),
        delivery_payer=getattr(order, "delivery_payer", None),
        customer_fee=float(order.delivery_fee or 0),
    ):
        if not await order_has_captured_payment(session, order.id):
            logger.warning(
                "Porter book deferred — prepaid fee not captured order_id=%s reason=%s",
                order.id,
                reason,
            )
            return False

    pickup_at = order.estimated_ready_at
    booked = await quote_and_book_porter(session, order, pickup_time=pickup_at)
    now = datetime.now(UTC)
    order.porter_auto_book_attempts = int(order.porter_auto_book_attempts or 0) + 1
    order.porter_auto_book_last_attempt_at = now
    order.updated_at = now

    if booked and booked.get("job_id"):
        await apply_porter_booking_result(session, order, booked)
        if publisher:
            event = EventPublisher.build(
                event_type="order.porter_auto_book.succeeded",
                aggregate_type="order",
                aggregate_id=str(order.id),
                producer="order-service",
                payload={
                    "kitchen_id": str(order.kitchen_id),
                    "order_id": str(order.id),
                    "order_code": order.order_code,
                    "courier_job_id": order.courier_job_id,
                    "reason": reason,
                    "attempts": order.porter_auto_book_attempts,
                },
            )
            await publisher.publish(stream_key("orders", "order"), event, session=session)
        await session.flush()
        return True

    if order.porter_auto_book_attempts >= max_attempts():
        order.porter_auto_book_at = None
        if publisher:
            event = EventPublisher.build(
                event_type="order.porter_auto_book.failed",
                aggregate_type="order",
                aggregate_id=str(order.id),
                producer="order-service",
                payload={
                    "kitchen_id": str(order.kitchen_id),
                    "order_id": str(order.id),
                    "order_code": order.order_code,
                    "attempts": order.porter_auto_book_attempts,
                    "reason": reason,
                },
            )
            await publisher.publish(stream_key("orders", "order"), event, session=session)
    else:
        order.porter_auto_book_at = now + timedelta(minutes=retry_interval_min())
        if publisher:
            event = EventPublisher.build(
                event_type="order.porter_auto_book.retry",
                aggregate_type="order",
                aggregate_id=str(order.id),
                producer="order-service",
                payload={
                    "kitchen_id": str(order.kitchen_id),
                    "order_id": str(order.id),
                    "order_code": order.order_code,
                    "next_at": order.porter_auto_book_at.isoformat(),
                    "attempts": order.porter_auto_book_attempts,
                    "reason": reason,
                },
            )
            await publisher.publish(stream_key("orders", "order"), event, session=session)
    await session.flush()
    return False


async def process_porter_auto_book_tick(
    session: AsyncSession,
    publisher: EventPublisher,
    *,
    limit: int = 50,
) -> dict[str, int]:
    """Process due auto-book rows. Bound for 100k-scale ticks."""
    now = datetime.now(UTC)
    limit = max(1, min(200, limit))
    due = (
        await session.execute(
            select(Order)
            .where(
                Order.porter_auto_book_at.is_not(None),
                Order.porter_auto_book_at <= now,
                Order.delivery_mode == "platform",
                Order.delivery_type == "delivery",
                Order.courier_job_id.is_(None),
                Order.status.in_(tuple(ACTIVE_STATUSES)),
            )
            .order_by(Order.porter_auto_book_at)
            .limit(limit)
        )
    ).scalars().all()

    processed = 0
    booked = 0
    retried = 0
    skipped = 0
    for order in due:
        processed += 1
        if not await should_schedule_auto_book(session, order):
            # Toggle/module turned off mid-flight — clear schedule; do not force book.
            order.porter_auto_book_at = None
            skipped += 1
            continue
        ok = await attempt_porter_book(session, order, publisher, reason="tick")
        if ok:
            booked += 1
        else:
            retried += 1

    await session.flush()
    return {
        "processed": processed,
        "booked": booked,
        "retried": retried,
        "skipped": skipped,
    }
