import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_customer_id, get_current_owner_id, verify_kitchen_owner
from app.schemas import (
    GoLiveRequest,
    LiveKitchenListResponse,
    LiveSessionResponse,
    StreamSettingsResponse,
    StreamSettingsUpdate,
    ViewerTokenResponse,
    end_live,
    get_current_session,
    get_stream_settings,
    go_live,
    issue_viewer_token,
    list_live_kitchens,
    update_stream_settings,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get("/stream/live-kitchens", response_model=LiveKitchenListResponse)
async def stream_live_kitchens_public(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LiveKitchenListResponse:
    return await list_live_kitchens(session)


@router.get("/kitchens/{kitchen_id}/stream/settings", response_model=StreamSettingsResponse)
async def stream_settings_get(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamSettingsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_stream_settings(session, kitchen_id)


@router.patch("/kitchens/{kitchen_id}/stream/settings", response_model=StreamSettingsResponse)
async def stream_settings_update(
    kitchen_id: uuid.UUID,
    body: StreamSettingsUpdate,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> StreamSettingsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    result = await update_stream_settings(session, kitchen_id, body, publisher)
    await session.commit()
    return result


@router.post("/kitchens/{kitchen_id}/stream/go-live", response_model=LiveSessionResponse)
async def stream_go_live(
    kitchen_id: uuid.UUID,
    body: GoLiveRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> LiveSessionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await go_live(session, kitchen_id, owner_id, body, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/kitchens/{kitchen_id}/stream/end", response_model=LiveSessionResponse)
async def stream_end_live(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> LiveSessionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await end_live(session, kitchen_id, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/kitchens/{kitchen_id}/stream/session", response_model=LiveSessionResponse | None)
async def stream_current_session(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LiveSessionResponse | None:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_current_session(session, kitchen_id)


@router.post("/stream/sessions/{session_id}/viewer-token", response_model=ViewerTokenResponse)
async def stream_viewer_token(
    session_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ViewerTokenResponse:
    try:
        result = await issue_viewer_token(session, session_id, customer_id)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
