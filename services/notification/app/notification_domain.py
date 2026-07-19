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


class DeliveryFeeDeniedNotifyRequest(BaseModel):
    """Internal request from the delivery service when a customer denies a quoted
    delivery fee at checkout (F28) — alerts the owner so they can call the customer
    and offer a waiver/pickup instead of silently losing the sale."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the denied quote was for.")
    quote_id: uuid.UUID = Field(..., description="The DeliveryQuote that was denied.")
    distance_km: float = Field(..., description="Quoted distance in km.")
    fee: float = Field(..., description="Delivery fee the customer denied, in INR.")
    subtotal: float = Field(default=0, description="Cart subtotal at the time of denial, in INR.")
    customer_phone: str | None = Field(default=None, description="Customer phone, if known, for owner callback.")


class DailyMenuBlastRequest(BaseModel):
    """Internal request from the growth service to dispatch a daily-menu WhatsApp blast (F39)."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the blast is for.")
    message: str = Field(..., description="Pre-composed blast message text.")
    recipient_count: int = Field(ge=0, description="Number of CRM-known recipients targeted (logged for audit).")


class TemplateBlastRequest(BaseModel):
    """Internal request from marketing to fan out a WhatsApp template blast per phone."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the blast is for.")
    message: str = Field(..., description="Pre-rendered message text.")
    recipient_phones: list[str] = Field(
        default_factory=list,
        max_length=200,
        description="E.164 phones to notify (capped at 200).",
    )
    template_name: str | None = Field(default=None, description="Owner template name for audit payload.")


class TemplateBlastResponse(BaseModel):
    """Result of a per-recipient marketing template blast."""

    sent: int = Field(..., description="Notification log rows created (one per phone).")
    template_id: str = Field(default="marketing_template")
    channel: str = Field(default="whatsapp")
    status: str = Field(default="sent")


class GoldenPerformanceDayNotifyRequest(BaseModel):
    """Internal request from growth when a dish has a standout order+rating+sentiment day."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen to alert.")
    dish_id: uuid.UUID = Field(..., description="Dish that had the golden day.")
    dish_name: str = Field(..., description="Dish display name.")
    performance_date: str = Field(..., description="ISO date (IST calendar day) of the standout.")
    order_qty: int = Field(..., ge=0, description="Portions sold that day.")
    avg_rating: float | None = Field(default=None, description="Average rating that day, if any.")
    sentiment_label: str = Field(default="positive", description="ML comment sentiment label.")
    suggestion_id: uuid.UUID = Field(..., description="Growth suggestion UUID for deep-link context.")


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


class OtpNotifyRequest(BaseModel):
    """Internal: identity asks notification to deliver a login OTP over WhatsApp."""

    phone: str = Field(..., min_length=8, max_length=20, description="E.164 or India mobile.")
    code: str = Field(..., min_length=4, max_length=8, description="OTP digits (never logged).")
    purpose: str = Field(
        default="login",
        description="'owner_login' | 'customer_login' | 'login'.",
    )


class OtpNotifyResponse(BaseModel):
    ok: bool
    simulated: bool = False
    channel: str = "whatsapp"


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
    status: str = "sent",
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
        status=status,
        sent_at=now if status == "sent" else None,
    )
    session.add(row)
    await session.flush()

    event = publisher.build(
        event_type="notification.sent" if status == "sent" else "notification.failed",
        aggregate_type="notification",
        aggregate_id=str(row.id),
        producer="notification-service",
        payload={
            "template_id": template_id,
            "channel": channel,
            "status": status,
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


async def _owner_phone_for_kitchen(session: AsyncSession, kitchen_id: uuid.UUID) -> str | None:
    row = (
        await session.execute(
            text(
                "SELECT o.phone FROM ckac_identity.owners o "
                "JOIN ckac_identity.kitchens k ON k.owner_id = o.id "
                "WHERE k.id = :kid LIMIT 1"
            ),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    return row


async def notify_delivery_fee_denied(
    session: AsyncSession,
    body: DeliveryFeeDeniedNotifyRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    """F28 deny path — owner gets an actionable alert, not a silent lost order."""
    owner_phone = await _owner_phone_for_kitchen(session, body.kitchen_id)
    text_body = (
        f"A customer {body.distance_km:.1f}km away denied your ₹{body.fee:.0f} delivery fee "
        f"(cart ₹{body.subtotal:.0f}). Call them to offer free delivery or pickup — "
        "or the order will be lost."
    )
    if body.customer_phone:
        text_body += f" Customer: {body.customer_phone}"

    row = await _send_notification(
        session,
        publisher,
        template_id="delivery_fee_denied",
        body=text_body,
        kitchen_id=body.kitchen_id,
        order_id=None,
        recipient_phone=owner_phone,
        payload={
            "quote_id": str(body.quote_id),
            "distance_km": body.distance_km,
            "fee": body.fee,
            "subtotal": body.subtotal,
            "customer_phone": body.customer_phone,
        },
    )
    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id="delivery_fee_denied",
        channel=row.channel,
        status=row.status,
    )


async def notify_golden_performance_day(
    session: AsyncSession,
    body: GoldenPerformanceDayNotifyRequest,
    publisher: EventPublisher,
) -> NotificationDispatchResponse:
    """Owner alert: today's dish performance was exceptional — save the recipe combo."""
    owner_phone = await _owner_phone_for_kitchen(session, body.kitchen_id)
    rating_bit = f", rating {body.avg_rating:.1f}/5" if body.avg_rating is not None else ""
    text_body = (
        f"Golden day for {body.dish_name} on {body.performance_date}: "
        f"{body.order_qty} portions{rating_bit}, comments felt {body.sentiment_label}. "
        f"Open Growth → save today's recipe & ingredients as a golden baseline."
    )
    row = await _send_notification(
        session,
        publisher,
        template_id="golden_performance_day",
        body=text_body,
        kitchen_id=body.kitchen_id,
        order_id=None,
        recipient_phone=owner_phone,
        payload={
            "dish_id": str(body.dish_id),
            "dish_name": body.dish_name,
            "performance_date": body.performance_date,
            "order_qty": body.order_qty,
            "avg_rating": body.avg_rating,
            "sentiment_label": body.sentiment_label,
            "suggestion_id": str(body.suggestion_id),
        },
    )
    return NotificationDispatchResponse(
        notification_id=row.id,
        template_id="golden_performance_day",
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


def _mask_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


async def _kitchen_whatsapp_phone_id(session: AsyncSession, kitchen_id: uuid.UUID) -> str | None:
    row = (
        await session.execute(
            text(
                "SELECT whatsapp_phone_id FROM ckac_identity.kitchens "
                "WHERE id = :kid LIMIT 1"
            ),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    return str(row).strip() if row else None


async def notify_template_blast(
    session: AsyncSession,
    body: TemplateBlastRequest,
    publisher: EventPublisher,
) -> TemplateBlastResponse:
    """Fan-out Meta WhatsApp (when configured) + one NotificationLog per phone."""
    from ckac_common.platform_config import get_platform_secret
    from app.whatsapp_send import send_text_message

    phones: list[str] = []
    seen: set[str] = set()
    for raw in body.recipient_phones:
        p = (raw or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        phones.append(p)
        if len(phones) >= 200:
            break

    phone_number_id = await _kitchen_whatsapp_phone_id(session, body.kitchen_id)
    access_token = await get_platform_secret(session, "whatsapp_access_token")
    sent = 0

    for phone in phones:
        meta = await send_text_message(
            phone_number_id=phone_number_id or "",
            to_phone=phone,
            text=body.message,
            access_token=access_token or "",
            session=session,
        )
        status = "sent" if meta.ok else "failed"
        if meta.ok:
            sent += 1
        await _send_notification(
            session,
            publisher,
            template_id="marketing_template",
            body=body.message,
            kitchen_id=body.kitchen_id,
            order_id=None,
            recipient_phone=phone,
            status=status,
            payload={
                "template_name": body.template_name,
                "recipient_phone_masked": _mask_phone(phone),
                "message_preview": body.message[:200],
                "meta_simulated": meta.simulated,
                "meta_message_id": meta.provider_message_id,
                "meta_error": meta.error,
            },
        )

    return TemplateBlastResponse(
        sent=sent,
        template_id="marketing_template",
        channel="whatsapp",
        status="sent" if sent else ("empty" if not phones else "failed"),
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


async def notify_otp(
    session: AsyncSession,
    body: OtpNotifyRequest,
) -> OtpNotifyResponse:
    """Send login OTP via platform WhatsApp number (not kitchen-scoped)."""
    from ckac_common.platform_config import get_platform_secret
    from app.whatsapp_send import send_text_message

    phone_number_id = await get_platform_secret(session, "whatsapp_otp_phone_number_id")
    access_token = await get_platform_secret(session, "whatsapp_access_token")
    purpose = (body.purpose or "login").replace("_", " ")
    # Never include code in structured logs — only in WhatsApp body.
    text = (
        f"Your kitchCU {purpose} code is {body.code}. "
        f"Valid for 10 minutes. Do not share this code."
    )
    meta = await send_text_message(
        phone_number_id=phone_number_id or "",
        to_phone=body.phone,
        text=text,
        access_token=access_token or "",
        session=session,
    )
    if not meta.ok:
        raise ValueError(meta.error or "WhatsApp OTP send failed")
    return OtpNotifyResponse(ok=True, simulated=meta.simulated, channel="whatsapp")
