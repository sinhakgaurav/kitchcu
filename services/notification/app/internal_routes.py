from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.notification_domain import (
    DailyMenuBlastRequest,
    NotificationDispatchResponse,
    OrderPlacedNotifyRequest,
    OrderStatusChangedNotifyRequest,
    TrialSampleBlastRequest,
    TrackingTickResponse,
    notify_daily_menu_blast,
    notify_order_placed,
    notify_order_status_changed,
    notify_trial_sample_blast,
    process_tracking_interval_tick,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.internal_auth import verify_internal_key

router = APIRouter(prefix="/internal/notifications", dependencies=[Depends(verify_internal_key)])


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post("/order-placed", response_model=NotificationDispatchResponse)
async def internal_order_placed(
    body: OrderPlacedNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_order_placed(session, body, publisher)
    await session.commit()
    return result


@router.post("/order-status-changed", response_model=NotificationDispatchResponse)
async def internal_order_status_changed(
    body: OrderStatusChangedNotifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_order_status_changed(session, body, publisher)
    await session.commit()
    return result


@router.post("/daily-menu-blast", response_model=NotificationDispatchResponse)
async def internal_daily_menu_blast(
    body: DailyMenuBlastRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_daily_menu_blast(session, body, publisher)
    await session.commit()
    return result


@router.post("/trial-sample-blast", response_model=NotificationDispatchResponse)
async def internal_trial_sample_blast(
    body: TrialSampleBlastRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> NotificationDispatchResponse:
    result = await notify_trial_sample_blast(session, body, publisher)
    await session.commit()
    return result


@router.post("/tracking-interval/tick", response_model=TrackingTickResponse)
async def internal_tracking_interval_tick(
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TrackingTickResponse:
    result = await process_tracking_interval_tick(session, publisher)
    await session.commit()
    return result
