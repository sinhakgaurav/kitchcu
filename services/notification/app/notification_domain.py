"""Notification dispatch — order updates, tracking intervals (F29/F45)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.notification_models import TRACKING_ACTIVE_STATUSES, NotificationLog, TrackingReminder
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.event_bus import EventPublisher

settings = get_settings()

STATUS_LABELS = {
    "received": "Received",
    "accepted": "Accepted",
    "preparing": "Preparing",
    "ready": "Ready",
    "out_for_delivery": "Out for delivery",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}


class OrderPlacedNotifyRequest(BaseModel):
    """Internal request from the order service to send an order-confirmation notification (F45)."""

    order_id: uuid.UUID = Field(..., description="Order UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Fulfilling kitchen UUID.")
    order_code: str = Field(..., description="Human-facing order code.", examples=["CKPNQ001-BILL-20260712-0042"])
    customer_phone: str | None = Field(default=None, description="Customer phone (E.164) to notify; skipped if absent.")
    delivery_type: str = Field(default="pickup", description="'pickup' or 'delivery' — delivery orders with a tracking token get a tracking link + interval reminders.")
    total: float = Field(default=0, description="Order total in INR, shown in the confirmation message.")
    tracking_token: str | None = Field(default=None, description="Opaque public tracking token, if issued (delivery orders only).")


class OrderStatusChangedNotifyRequest(BaseModel):
    """Internal request from the order service on any status transition (F29/F45)."""

    order_id: uuid.UUID = Field(..., description="Order UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Fulfilling kitchen UUID.")
    order_code: str = Field(..., description="Human-facing order code.")
    customer_phone: str | None = Field(default=None, description="Customer phone to notify; skipped if absent.")
    from_status: str = Field(..., description="Previous order status.")
    to_status: str = Field(..., description="New order status.")
    tracking_token: str | None = Field(default=None, description="Public tracking token, if issued.")


class DailyMenuBlastRequest(BaseModel):
    """Internal request from the growth service to dispatch a daily-menu WhatsApp blast (F39)."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the blast is for.")
    message: str = Field(..., description="Pre-composed blast message text.")
    recipient_count: int = Field(ge=0, description="Number of CRM-known recipients targeted (logged for audit).")


class TrialSampleBlastRequest(BaseModel):
    """Internal request from the learning service to notify customers of a dish trial sample offer (S16)."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen running the trial.")
    trial_id: uuid.UUID = Field(..., description="Dish trial UUID.")
    dish_name: str = Field(..., description="Trial dish name.")
    message: str = Field(..., description="Pre-composed blast message text.")
    recipient_count: int = Field(ge=1, le=20, description="Number of recipients targeted (trial blasts are capped small).")


class NotificationDispatchResponse(BaseModel):
    """Result of dispatching a single notification."""

    notification_id: uuid.UUID = Field(..., description="Persisted notification log row UUID.")
    template_id: str = Field(..., description="Template used, e.g. 'order_confirmed', 'order_status_update', 'daily_menu_blast', 'trial_sample_offer', 'delivery_progress'.")
    channel: str = Field(..., description="Delivery channel, e.g. 'whatsapp'.")
    status: str = Field(..., description="Dispatch status, e.g. 'sent'.")


class TrackingTickResponse(BaseModel):
    """Result of one tracking-interval scheduler tick (F29) — invoked periodically by a scheduled job."""

    processed: int = Field(..., description="Reminders due for processing this tick.")
    sent: int = Field(..., description="Reminders that resulted in a notification being sent (excludes reminders auto-deactivated because the order left an active tracking status).")


def tracking_url(token: str | None) -> str | None:
    if not token:
        return None
    base = settings.customer_oauth_redirect_base.rstrip("/")
    return f"{base}/t/{token}"


async def _kitchen_interval_min(session: AsyncSession, kitchen_id: uuid.UUID) -> int:
    row = (
        await session.execute(
            text(
                "SELECT COALESCE(tracking_notify_interval_min, 5) "
                "FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"
            ),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    return int(row or 5)


async def _send_notification(
    session: AsyncSession,
    publisher: EventPublisher,
    *,
    template_id: str,
    body: str,
    kitchen_id: uuid.UUID | None,
    order_id: uuid.UUID | None,
    recipient_phone: str | None,
    payload: dict,
    channel: str = "whatsapp",
) -> NotificationLog:
    now = datetime.now(UTC)
    row = NotificationLog(
        kitchen_id=kitchen_id,
        order_id=order_id,
        recipient_phone=recipient_phone,
        channel=channel,
        template_id=template_id,
        body=body,
        payload=payload,
        status="sent",
        sent_at=now,
    )
    session.add(row)
    await session.flush()

    event = publisher.build(
        event_type="notification.sent",
        aggregate_type="notification",
        aggregate_id=str(row.id),
        producer="notification-service",
        payload={
            "template_id": template_id,
            "channel": channel,
            "order_id": str(order_id) if order_id else None,
            "kitchen_id": str(kitchen_id) if kitchen_id else None,
            "recipient_phone": recipient_phone,
        },
    )
    await publisher.publish(stream_key("notify", "dispatch"), event, session=session)
    return row


async def _upsert_tracking_reminder(
    session: AsyncSession,
    *,
    order_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    order_code: str,
    customer_phone: str | None,
    tracking_token: str | None,
    order_status: str,
    interval_min: int,
) -> None:
    active = order_status in TRACKING_ACTIVE_STATUSES and bool(tracking_token)
    existing = (
        await session.execute(
            select(TrackingReminder).where(TrackingReminder.order_id == order_id)
        )
    ).scalar_one_or_none()
    next_at = datetime.now(UTC) + timedelta(minutes=interval_min)

    if existing:
        existing.order_status = order_status
        existing.tracking_token = tracking_token
        existing.customer_phone = customer_phone
        existing.interval_min = interval_min
        existing.is_active = active
        existing.updated_at = datetime.now(UTC)
        if active:
            existing.next_reminder_at = next_at
        await session.flush()
        return

    if not active:
        return

    session.add(
        TrackingReminder(
            order_id=order_id,
            kitchen_id=kitchen_id,
            order_code=order_code,
            customer_phone=customer_phone,
            tracking_token=tracking_token,
            order_status=order_status,
            interval_min=interval_min,
            next_reminder_at=next_at,
            is_active=True,
        )
    )
    await session.flush()


async def notify_order_placed(
    session: AsyncSession,
    body: OrderPlacedNotifyRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    link = tracking_url(body.tracking_token)
    if body.delivery_type == "delivery" and link:
        text_body = (
            f"Order {body.order_code} confirmed at kitchCU — ₹{body.total:.0f}. "
            f"Track: {link}"
        )
        template = "order_confirmed"
    else:
        text_body = f"Order {body.order_code} confirmed at kitchCU — ₹{body.total:.0f}."
        template = "order_confirmed"

    row = await _send_notification(
        session,
        publisher,
        template_id=template,
        body=text_body,
        kitchen_id=body.kitchen_id,
        order_id=body.order_id,
        recipient_phone=body.customer_phone,
        payload={
            "order_code": body.order_code,
            "total": body.total,
            "tracking_link": link,
        },
    )

    if body.tracking_token and body.delivery_type == "delivery":
        interval = await _kitchen_interval_min(session, body.kitchen_id)
        await _upsert_tracking_reminder(
            session,
            order_id=body.order_id,
            kitchen_id=body.kitchen_id,
            order_code=body.order_code,
            customer_phone=body.customer_phone,
            tracking_token=body.tracking_token,
            order_status="received",
            interval_min=interval,
        )

    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id=template,
        channel=row.channel,
        status=row.status,
    )


async def notify_order_status_changed(
    session: AsyncSession,
    body: OrderStatusChangedNotifyRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    link = tracking_url(body.tracking_token)
    label = STATUS_LABELS.get(body.to_status, body.to_status)
    text_body = f"Order {body.order_code} is now {label}."
    if link:
        text_body += f" Track: {link}"

    row = await _send_notification(
        session,
        publisher,
        template_id="order_status_update",
        body=text_body,
        kitchen_id=body.kitchen_id,
        order_id=body.order_id,
        recipient_phone=body.customer_phone,
        payload={
            "from_status": body.from_status,
            "to_status": body.to_status,
            "tracking_link": link,
        },
    )

    interval = await _kitchen_interval_min(session, body.kitchen_id)
    await _upsert_tracking_reminder(
        session,
        order_id=body.order_id,
        kitchen_id=body.kitchen_id,
        order_code=body.order_code,
        customer_phone=body.customer_phone,
        tracking_token=body.tracking_token,
        order_status=body.to_status,
        interval_min=interval,
    )

    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id="order_status_update",
        channel=row.channel,
        status=row.status,
    )


async def notify_daily_menu_blast(
    session: AsyncSession,
    body: DailyMenuBlastRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    text_body = body.message
    row = await _send_notification(
        session,
        publisher,
        template_id="daily_menu_blast",
        body=text_body,
        kitchen_id=body.kitchen_id,
        order_id=None,
        recipient_phone=None,
        payload={"recipient_count": body.recipient_count, "message": body.message},
    )
    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id="daily_menu_blast",
        channel=row.channel,
        status=row.status,
    )


async def notify_trial_sample_blast(
    session: AsyncSession,
    body: TrialSampleBlastRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    row = await _send_notification(
        session,
        publisher,
        template_id="trial_sample_offer",
        body=body.message,
        kitchen_id=body.kitchen_id,
        order_id=None,
        recipient_phone=None,
        payload={
            "trial_id": str(body.trial_id),
            "dish_name": body.dish_name,
            "recipient_count": body.recipient_count,
            "message": body.message,
        },
    )
    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id="trial_sample_offer",
        channel=row.channel,
        status=row.status,
    )


async def process_tracking_interval_tick(
    session: AsyncSession,
    publisher: EventPublisher,
) -> TrackingTickResponse:
    now = datetime.now(UTC)
    due = (
        await session.execute(
            select(TrackingReminder).where(
                TrackingReminder.is_active.is_(True),
                TrackingReminder.next_reminder_at <= now,
            )
        )
    ).scalars().all()

    sent = 0
    for reminder in due:
        if reminder.order_status not in TRACKING_ACTIVE_STATUSES:
            reminder.is_active = False
            reminder.updated_at = now
            continue

        link = tracking_url(reminder.tracking_token)
        label = STATUS_LABELS.get(reminder.order_status, reminder.order_status)
        body_text = (
            f"Your order {reminder.order_code} is {label}. "
            f"We'll keep you posted — quality-first prep."
        )
        if link:
            body_text += f" Track: {link}"

        await _send_notification(
            session,
            publisher,
            template_id="delivery_progress",
            body=body_text,
            kitchen_id=reminder.kitchen_id,
            order_id=reminder.order_id,
            recipient_phone=reminder.customer_phone,
            payload={"order_code": reminder.order_code, "tracking_link": link},
        )

        interval_event = publisher.build(
            event_type="notification.tracking_interval",
            aggregate_type="tracking_reminder",
            aggregate_id=str(reminder.id),
            producer="notification-service",
            payload={"order_id": str(reminder.order_id), "order_code": reminder.order_code},
        )
        await publisher.publish(stream_key("notify", "tracking"), interval_event, session=session)

        reminder.next_reminder_at = now + timedelta(minutes=reminder.interval_min)
        reminder.updated_at = now
        sent += 1

    await session.flush()
    return TrackingTickResponse(processed=len(due), sent=sent)
