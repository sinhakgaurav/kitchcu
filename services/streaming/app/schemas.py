"""Live streaming domain — F46–F48."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.livekit_tokens import (
    build_livekit_token,
    livekit_configured,
    publisher_identity,
    viewer_identity,
)
from app.models import KitchenStreamSettings, LiveSession
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.event_bus import EventPublisher


class StreamSettingsResponse(BaseModel):
    """A kitchen's live-streaming opt-in settings and current live status (F47)."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID.")
    live_sharing_enabled: bool = Field(..., description="Owner opt-in — must be true before the kitchen can go live.")
    q_and_a_enabled: bool = Field(..., description="Whether live Q&A is enabled during streams (reserved for future use in the viewer UI).")
    is_live: bool = Field(..., description="Whether the kitchen currently has an active live session.")
    livekit_configured: bool = Field(..., description="Whether this deployment has LiveKit credentials configured. False means go-live/viewer-token calls will return sessions without usable tokens.")

    model_config = {"from_attributes": True}


class StreamSettingsUpdate(BaseModel):
    """Owner partial update to stream settings."""

    live_sharing_enabled: bool | None = Field(default=None, description="Opt in/out of live streaming entirely.")
    q_and_a_enabled: bool | None = Field(default=None, description="Enable/disable live Q&A.")


class GoLiveRequest(BaseModel):
    """Owner request to start a live publisher session."""

    title: str = Field(default="Live kitchen prep", max_length=255, description="Session title shown to viewers.")
    order_id: uuid.UUID | None = Field(default=None, description="Optionally tie this stream to a specific order (e.g. showing live prep for that customer's order).")


class LiveSessionResponse(BaseModel):
    """A live (or just-ended) streaming session."""

    id: uuid.UUID = Field(..., description="Session UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Streaming kitchen UUID.")
    title: str = Field(..., description="Session title.")
    room_name: str = Field(..., description="LiveKit room name, derived deterministically from the kitchen ID.")
    status: str = Field(..., description="'live' or 'ended'.")
    order_id: uuid.UUID | None = Field(default=None, description="Linked order, if this stream is tied to a specific order.")
    viewer_count: int = Field(..., description="Running count of viewer tokens issued for this session.")
    started_at: datetime = Field(..., description="Session start timestamp, UTC.")
    ended_at: datetime | None = Field(default=None, description="Session end timestamp, UTC, once ended.")
    livekit_url: str | None = Field(default=None, description="LiveKit server URL for the client SDK to connect to; null if LiveKit is not configured.")
    publisher_token: str | None = Field(default=None, description="Short-lived LiveKit publish token for the owner's broadcasting client; only returned to the owner (go-live/current-session calls), never to viewers.")

    model_config = {"from_attributes": True}


class ViewerTokenResponse(BaseModel):
    """A short-lived, viewer-only LiveKit token for watching a live session."""

    session_id: uuid.UUID = Field(..., description="Live session UUID this token grants access to.")
    room_name: str = Field(..., description="LiveKit room name to join.")
    livekit_url: str | None = Field(default=None, description="LiveKit server URL; null if LiveKit is not configured.")
    token: str | None = Field(default=None, description="Viewer (subscribe-only, cannot publish) LiveKit token; null if LiveKit is not configured.")
    kitchen_name: str | None = Field(default=None, description="Streaming kitchen's display name, for the viewer UI.")


class LiveKitchenSummary(BaseModel):
    """One currently-live, opted-in, active kitchen (public discovery — F48)."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID.")
    kitchen_code: str = Field(..., description="Kitchen code.")
    kitchen_name: str = Field(..., description="Kitchen display name.")
    session_id: uuid.UUID = Field(..., description="Active live session UUID.")
    title: str = Field(..., description="Current session title.")
    started_at: datetime = Field(..., description="Session start timestamp, UTC.")


class LiveKitchenListResponse(BaseModel):
    """Public directory of kitchens currently streaming."""

    kitchens: list[LiveKitchenSummary] = Field(..., description="Live kitchens, most recently started first.")
    total: int = Field(..., description="Number of live kitchens returned.")


async def _get_settings_row(session: AsyncSession, kitchen_id: uuid.UUID) -> KitchenStreamSettings:
    row = (
        await session.execute(
            select(KitchenStreamSettings).where(KitchenStreamSettings.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if not row:
        row = KitchenStreamSettings(kitchen_id=kitchen_id)
        session.add(row)
        await session.flush()
    return row


async def _active_session(session: AsyncSession, kitchen_id: uuid.UUID) -> LiveSession | None:
    return (
        await session.execute(
            select(LiveSession).where(
                LiveSession.kitchen_id == kitchen_id,
                LiveSession.status == "live",
            )
        )
    ).scalar_one_or_none()


def _session_response(session_row: LiveSession, *, publisher_token: str | None = None) -> LiveSessionResponse:
    settings = get_settings()
    return LiveSessionResponse(
        id=session_row.id,
        kitchen_id=session_row.kitchen_id,
        title=session_row.title,
        room_name=session_row.room_name,
        status=session_row.status,
        order_id=session_row.order_id,
        viewer_count=session_row.viewer_count,
        started_at=session_row.started_at,
        ended_at=session_row.ended_at,
        livekit_url=settings.livekit_url or None,
        publisher_token=publisher_token,
    )


async def get_stream_settings(session: AsyncSession, kitchen_id: uuid.UUID) -> StreamSettingsResponse:
    row = await _get_settings_row(session, kitchen_id)
    live = await _active_session(session, kitchen_id)
    return StreamSettingsResponse(
        kitchen_id=kitchen_id,
        live_sharing_enabled=row.live_sharing_enabled,
        q_and_a_enabled=row.q_and_a_enabled,
        is_live=live is not None,
        livekit_configured=livekit_configured(),
    )


async def update_stream_settings(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: StreamSettingsUpdate,
    publisher: EventPublisher,
) -> StreamSettingsResponse:
    row = await _get_settings_row(session, kitchen_id)
    if data.live_sharing_enabled is not None:
        row.live_sharing_enabled = data.live_sharing_enabled
    if data.q_and_a_enabled is not None:
        row.q_and_a_enabled = data.q_and_a_enabled
    await session.flush()

    event = EventPublisher.build(
        event_type="stream.settings_updated",
        aggregate_type="stream_settings",
        aggregate_id=str(kitchen_id),
        producer="streaming-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "live_sharing_enabled": row.live_sharing_enabled,
        },
    )
    await publisher.publish(stream_key("streaming", "session"), event, session=session)
    return await get_stream_settings(session, kitchen_id)


async def go_live(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: GoLiveRequest,
    publisher: EventPublisher,
) -> LiveSessionResponse:
    settings_row = await _get_settings_row(session, kitchen_id)
    if not settings_row.live_sharing_enabled:
        raise ValueError("Enable live sharing in settings before going live")

    existing = await _active_session(session, kitchen_id)
    if existing:
        raise ValueError("Kitchen already has an active live session")

    room_name = f"kitchcu-{kitchen_id.hex[:12]}"
    live = LiveSession(
        kitchen_id=kitchen_id,
        owner_id=owner_id,
        title=data.title.strip(),
        room_name=room_name,
        status="live",
        order_id=data.order_id,
    )
    session.add(live)
    await session.flush()

    token = build_livekit_token(
        room_name=room_name,
        identity=publisher_identity(kitchen_id),
        can_publish=True,
    )

    event = EventPublisher.build(
        event_type="stream.started",
        aggregate_type="live_session",
        aggregate_id=str(live.id),
        producer="streaming-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "session_id": str(live.id),
            "room_name": room_name,
            "title": live.title,
        },
    )
    await publisher.publish(stream_key("streaming", "session"), event, session=session)
    return _session_response(live, publisher_token=token)


async def end_live(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    publisher: EventPublisher,
) -> LiveSessionResponse:
    live = await _active_session(session, kitchen_id)
    if not live:
        raise ValueError("No active live session")

    live.status = "ended"
    live.ended_at = datetime.now(UTC)
    await session.flush()

    event = EventPublisher.build(
        event_type="stream.ended",
        aggregate_type="live_session",
        aggregate_id=str(live.id),
        producer="streaming-service",
        payload={"kitchen_id": str(kitchen_id), "session_id": str(live.id)},
    )
    await publisher.publish(stream_key("streaming", "session"), event, session=session)
    return _session_response(live)


async def get_current_session(session: AsyncSession, kitchen_id: uuid.UUID) -> LiveSessionResponse | None:
    live = await _active_session(session, kitchen_id)
    if not live:
        return None
    token = build_livekit_token(
        room_name=live.room_name,
        identity=publisher_identity(kitchen_id),
        can_publish=True,
    )
    return _session_response(live, publisher_token=token)


async def issue_viewer_token(
    session: AsyncSession,
    session_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> ViewerTokenResponse:
    live = (
        await session.execute(
            select(LiveSession).where(LiveSession.id == session_id, LiveSession.status == "live")
        )
    ).scalar_one_or_none()
    if not live:
        raise ValueError("Live session not found")

    await session.execute(
        update(LiveSession)
        .where(LiveSession.id == session_id)
        .values(viewer_count=LiveSession.viewer_count + 1)
    )
    await session.flush()

    kitchen_name = (
        await session.execute(
            text("SELECT name FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": live.kitchen_id},
        )
    ).scalar_one_or_none()

    settings = get_settings()
    token = build_livekit_token(
        room_name=live.room_name,
        identity=viewer_identity(customer_id),
        can_publish=False,
    )
    return ViewerTokenResponse(
        session_id=live.id,
        room_name=live.room_name,
        livekit_url=settings.livekit_url or None,
        token=token,
        kitchen_name=kitchen_name,
    )


async def list_live_kitchens(session: AsyncSession) -> LiveKitchenListResponse:
    rows = (
        await session.execute(
            text(
                """
                SELECT s.id, s.kitchen_id, s.title, s.started_at, k.code, k.name
                FROM ckac_streaming.live_sessions s
                JOIN ckac_identity.kitchens k ON k.id = s.kitchen_id
                JOIN ckac_streaming.kitchen_stream_settings st ON st.kitchen_id = s.kitchen_id
                WHERE s.status = 'live' AND st.live_sharing_enabled = true AND k.status = 'active'
                ORDER BY s.started_at DESC
                """
            )
        )
    ).fetchall()
    kitchens = [
        LiveKitchenSummary(
            kitchen_id=uuid.UUID(str(r[1])),
            session_id=uuid.UUID(str(r[0])),
            title=r[2],
            started_at=r[3],
            kitchen_code=r[4],
            kitchen_name=r[5],
        )
        for r in rows
    ]
    return LiveKitchenListResponse(kitchens=kitchens, total=len(kitchens))
