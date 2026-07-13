from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    DeliveryQuoteRequest,
    DeliveryQuoteResponse,
    TrackingResponse,
    quote_delivery,
    track_by_token,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post("/delivery/quote", response_model=DeliveryQuoteResponse)
async def delivery_quote(
    body: DeliveryQuoteRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DeliveryQuoteResponse:
    try:
        result = await quote_delivery(session, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return result


@router.get("/delivery/track/{token}", response_model=TrackingResponse)
async def delivery_track(
    token: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrackingResponse:
    try:
        return await track_by_token(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
