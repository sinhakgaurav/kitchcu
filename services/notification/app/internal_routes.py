from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.notification_domain import (
    DailyMenuBlastRequest,
    DeliveryFeeDeniedNotifyRequest,
    GoldenPerformanceDayNotifyRequest,
    NotificationDispatchResponse,
    OrderPlacedNotifyRequest,
    OrderStatusChangedNotifyRequest,
    OtpNotifyRequest,
    OtpNotifyResponse,
    TemplateBlastRequest,
    TemplateBlastResponse,
    TrialSampleBlastRequest,
    TrackingTickResponse,
    notify_daily_menu_blast,
    notify_delivery_fee_denied,
    notify_golden_performance_day,
    notify_order_placed,
    notify_order_status_changed,
    notify_otp,
    notify_template_blast,
    notify_trial_sample_blast,
    process_tracking_interval_tick,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.internal_auth import verify_internal_key
from ckac_common.openapi import RESP_401

router = APIRouter(prefix="/internal/notifications", dependencies=[Depends(verify_internal_key)])

TAG_INTERNAL = "Internal Dispatch"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post(
    "/order-placed",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Notify customer of order confirmation",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the order service right "
        "after an order is created. Sends a WhatsApp confirmation (with tracking link for "
        "delivery orders) and, for delivery orders with a tracking token, seeds the F29 tracking "
        "interval reminder. Publishes `notification.sent`."
    ),
    responses={401: RESP_401},
)
async def internal_order_placed(
    body: OrderPlacedNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_order_placed(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/order-status-changed",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Notify customer of an order status change",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the order service on every "
        "status transition. Sends a WhatsApp status update (with tracking link if available) and "
        "refreshes the F29 tracking reminder's status/interval. Publishes `notification.sent`."
    ),
    responses={401: RESP_401},
)
async def internal_order_status_changed(
    body: OrderStatusChangedNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_order_status_changed(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/delivery-fee-denied",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Alert the owner that a customer denied the quoted delivery fee (F28)",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the delivery service when "
        "a customer denies a quoted delivery fee at checkout instead of accepting or switching "
        "to pickup. Sends a WhatsApp alert to the **owner** (resolved from `kitchen_id`) with "
        "the distance/fee/subtotal and customer phone (if known) so the owner can call and "
        "offer a waiver or pickup before the sale is lost. Publishes `notification.sent`."
    ),
    responses={401: RESP_401},
)
async def internal_delivery_fee_denied(
    body: DeliveryFeeDeniedNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_delivery_fee_denied(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/daily-menu-blast",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Dispatch a daily-menu WhatsApp blast",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the growth service "
        "(F39 `POST /kitchens/{kitchen_id}/growth/daily-menu/push`) to actually send the "
        "pre-composed blast message. Publishes `notification.sent`."
    ),
    responses={401: RESP_401},
)
async def internal_daily_menu_blast(
    body: DailyMenuBlastRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_daily_menu_blast(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/template-blast",
    response_model=TemplateBlastResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Fan-out a marketing WhatsApp template blast",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by marketing "
        "`POST .../templates/{id}/send`. Creates one notification log + `notification.sent` "
        "per recipient phone (max 200)."
    ),
    responses={401: RESP_401},
)
async def internal_template_blast(
    body: TemplateBlastRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TemplateBlastResponse:
    result = await notify_template_blast(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/golden-performance-day",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Alert owner about a golden performance day for a dish",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the growth service when "
        "order volume, ratings, and ML comment sentiment show a standout day for a dish. "
        "Sends a WhatsApp alert to the owner to save that day's recipe/ingredient combo."
    ),
    responses={401: RESP_401},
)
async def internal_golden_performance_day(
    body: GoldenPerformanceDayNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_golden_performance_day(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/trial-sample-blast",
    response_model=NotificationDispatchResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Dispatch a dish-trial sample offer blast",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — called by the learning service "
        "(S16 dish trials) to notify a small, capped set of customers about a trial sample "
        "offer. Publishes `notification.sent`."
    ),
    responses={401: RESP_401},
)
async def internal_trial_sample_blast(
    body: TrialSampleBlastRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_trial_sample_blast(session, body, publisher)
    await session.commit()
    return result


@router.post(
    "/tracking-interval/tick",
    response_model=TrackingTickResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Process due tracking-interval reminders",
    description=(
        "Internal service-to-service (`X-Internal-Key`) — invoked periodically by a scheduled "
        "job (not a public/customer-facing route) to send F29 delivery-progress WhatsApp "
        "reminders for every order whose `next_reminder_at` is due, then reschedules each per "
        "its kitchen-configured interval. Auto-deactivates reminders for orders no longer in an "
        "active tracking status. Publishes `notification.tracking_interval` per reminder sent."
    ),
    responses={401: RESP_401},
)
async def internal_tracking_interval_tick(
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TrackingTickResponse:
    result = await process_tracking_interval_tick(session, publisher)
    await session.commit()
    return result


@router.post(
    "/otp",
    response_model=OtpNotifyResponse,
    tags=[TAG_INTERNAL],
    summary="[Internal] Deliver login OTP via WhatsApp",
    description=(
        "Internal (`X-Internal-Key`) — called by identity for owner/customer OTP login. "
        "Uses platform `whatsapp_access_token` + `whatsapp_otp_phone_number_id` (env or API Keys)."
    ),
    responses={401: RESP_401},
)
async def internal_otp(
    body: OtpNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OtpNotifyResponse:
    try:
        return await notify_otp(session, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
