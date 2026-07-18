import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_customer_id, get_current_owner_id, verify_kitchen_owner
from app.schemas import (
    GoLiveRequest,
    LiveKitchenListResponse,
    LiveSessionResponse,
    LiveShowcaseResponse,
    ShowcaseUpdateRequest,
    StreamSettingsResponse,
    StreamSettingsUpdate,
    ViewerTokenResponse,
    end_live,
    get_current_session,
    get_live_showcase,
    get_stream_settings,
    go_live,
    issue_viewer_token,
    list_live_kitchens,
    update_live_showcase,
    update_stream_settings,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

router = APIRouter()

TAG_STREAMING = "Live Streaming"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/stream/live-kitchens",
    response_model=LiveKitchenListResponse,
    tags=[TAG_STREAMING],
    summary="Discover currently-live kitchens (F48)",
    description=(
        "**Auth:** None — public discovery feed.\n\n"
        "**Response:** `LiveKitchenListResponse` — active kitchens with `live_sharing_enabled=true` "
        "and an in-progress session, most recently started first. Use "
        "`POST /stream/sessions/{session_id}/viewer-token` to get a watch token for one."
    ),
)
async def stream_live_kitchens_public(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LiveKitchenListResponse:
    return await list_live_kitchens(session)


@router.get(
    "/kitchens/{kitchen_id}/stream/settings",
    response_model=StreamSettingsResponse,
    tags=[TAG_STREAMING],
    summary="Get a kitchen's streaming settings",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `StreamSettingsResponse` — opt-in flags, current live status, and whether "
        "LiveKit is configured on this deployment."
    ),
    responses=auth_errors(include_403=True),
)
async def stream_settings_get(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> StreamSettingsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_stream_settings(session, kitchen_id)


@router.patch(
    "/kitchens/{kitchen_id}/stream/settings",
    response_model=StreamSettingsResponse,
    tags=[TAG_STREAMING],
    summary="Update a kitchen's streaming opt-in settings (F47)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `StreamSettingsUpdate` — toggle `live_sharing_enabled` and/or "
        "`q_and_a_enabled`.\n\n"
        "**Behavior:** Publishes `stream.settings_updated`.\n\n"
        "**Response:** Updated `StreamSettingsResponse`."
    ),
    responses=auth_errors(include_403=True),
)
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


@router.post(
    "/kitchens/{kitchen_id}/stream/go-live",
    response_model=LiveSessionResponse,
    tags=[TAG_STREAMING],
    summary="Start a live publisher session",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `GoLiveRequest` — title, optional linked `order_id`, optional `dish_id` to "
        "feature ingredients/prep/prepared showcase. Rejects if `live_sharing_enabled` is false "
        "or the kitchen already has an active session (400).\n\n"
        "**Behavior:** Creates a `LiveSession` in a deterministic LiveKit room and issues the "
        "owner's publish-capable token. Publishes `stream.started`.\n\n"
        "**Response:** `LiveSessionResponse` including `publisher_token` (owner-only — never "
        "share with viewers)."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
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
        from ckac_common.platform_config import feature_http_status

        code = feature_http_status(exc) or status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/stream/end",
    response_model=LiveSessionResponse,
    tags=[TAG_STREAMING],
    summary="End the active live session",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Behavior:** Rejects if there is no active session (400). Marks the session `ended`, "
        "stamps `ended_at`, and publishes `stream.ended`.\n\n"
        "**Response:** Updated `LiveSessionResponse` (no `publisher_token` on the ended response)."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
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


@router.get(
    "/kitchens/{kitchen_id}/stream/session",
    response_model=LiveSessionResponse | None,
    tags=[TAG_STREAMING],
    summary="Get the kitchen's current active session, if any",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `LiveSessionResponse` (with a fresh `publisher_token` for the owner to "
        "reconnect) if a session is active, otherwise `null`."
    ),
    responses=auth_errors(include_403=True),
)
async def stream_current_session(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LiveSessionResponse | None:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_current_session(session, kitchen_id)


@router.patch(
    "/kitchens/{kitchen_id}/stream/showcase",
    response_model=LiveSessionResponse,
    tags=[TAG_STREAMING],
    summary="Update per-dish live showcase (prep / ingredients / prepared)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `ShowcaseUpdateRequest` — feature a dish, set phase "
        "(`ingredients` | `prep` | `prepared`), advance prep step, or clear.\n\n"
        "**Behavior:** Reloads recipe snapshot from catalog when dish changes. Publishes "
        "`stream.showcase_updated`.\n\n"
        "**Response:** Updated `LiveSessionResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def stream_showcase_update(
    kitchen_id: uuid.UUID,
    body: ShowcaseUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> LiveSessionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await update_live_showcase(session, kitchen_id, body, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/stream/sessions/{session_id}/showcase",
    response_model=LiveShowcaseResponse,
    tags=[TAG_STREAMING],
    summary="Get live dish showcase (ingredients, prep steps, prepared state)",
    description=(
        "**Auth:** None — public while the session is live (customers watching prep).\n\n"
        "**Response:** `LiveShowcaseResponse` with phase + ingredient/prep snapshot.\n\n"
        "**404:** session missing or not live."
    ),
    responses={404: RESP_404},
)
async def stream_showcase_public(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LiveShowcaseResponse:
    try:
        return await get_live_showcase(session, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/stream/sessions/{session_id}/viewer-token",
    response_model=ViewerTokenResponse,
    tags=[TAG_STREAMING],
    summary="Get a viewer-only token to watch a live session",
    description=(
        "**Auth:** Customer JWT.\n\n"
        "**Behavior:** 404 if the session does not exist or is not currently live. Increments "
        "the session's `viewer_count` and issues a subscribe-only (cannot publish) LiveKit "
        "token.\n\n"
        "**Response:** `ViewerTokenResponse`."
    ),
    responses={**auth_errors(), 404: RESP_404},
)
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
        from ckac_common.platform_config import feature_http_status

        code = feature_http_status(exc) or status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(exc)) from exc
