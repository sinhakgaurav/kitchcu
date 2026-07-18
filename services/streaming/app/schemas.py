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
    resolve_livekit_creds,
    viewer_identity,
)
from app.models import SHOWCASE_PHASES, KitchenStreamSettings, LiveSession
from app.showcase import SHOWCASE_PHASE_SET, load_dish_showcase_snapshot
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.platform_config import require_feature


class ShowcaseIngredient(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    photo_url: str | None = None
    sort_order: int = 0


class ShowcasePrepStep(BaseModel):
    step_order: int
    title: str | None = None
    body_html: str | None = None
    photo_url: str | None = None
    duration_min: int | None = None


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
    order_id: uuid.UUID | None = Field(
        default=None,
        description="Optionally tie this stream to a specific order (e.g. showing live prep for that customer's order).",
    )
    dish_id: uuid.UUID | None = Field(
        default=None,
        description="Feature this dish on go-live — loads ingredients + prep steps for the showcase.",
    )
    showcase_phase: str | None = Field(
        default=None,
        description="Initial phase when dish_id is set: 'ingredients', 'prep', or 'prepared'. Default 'ingredients'.",
    )


class ShowcaseUpdateRequest(BaseModel):
    """Owner updates the per-dish showcase while live (feature dish / change phase / advance prep)."""

    dish_id: uuid.UUID | None = Field(
        default=None,
        description="Switch featured dish (reloads recipe snapshot). Omit to keep current dish.",
    )
    showcase_phase: str | None = Field(
        default=None,
        description=f"One of {list(SHOWCASE_PHASES)}.",
    )
    active_prep_step_order: int | None = Field(
        default=None,
        ge=1,
        description="Highlight this prep step order while phase is 'prep'.",
    )
    clear_dish: bool = Field(
        default=False,
        description="When true, clears dish showcase back to idle.",
    )


class LiveSessionResponse(BaseModel):
    """A live (or just-ended) streaming session."""

    id: uuid.UUID = Field(..., description="Session UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Streaming kitchen UUID.")
    title: str = Field(..., description="Session title.")
    room_name: str = Field(..., description="LiveKit room name, derived deterministically from the kitchen ID.")
    status: str = Field(..., description="'live' or 'ended'.")
    order_id: uuid.UUID | None = Field(default=None, description="Linked order, if this stream is tied to a specific order.")
    dish_id: uuid.UUID | None = Field(default=None, description="Featured dish for this live session, if any.")
    dish_name: str | None = Field(default=None, description="Featured dish name.")
    showcase_phase: str = Field(
        default="idle",
        description="Per-dish stage: idle | ingredients | prep | prepared.",
    )
    active_prep_step_order: int | None = Field(
        default=None,
        description="Active prep step order while showcasing prep.",
    )
    prepared_at: datetime | None = Field(default=None, description="When the dish was marked prepared, UTC.")
    viewer_count: int = Field(..., description="Running count of viewer tokens issued for this session.")
    started_at: datetime = Field(..., description="Session start timestamp, UTC.")
    ended_at: datetime | None = Field(default=None, description="Session end timestamp, UTC, once ended.")
    livekit_url: str | None = Field(default=None, description="LiveKit server URL for the client SDK to connect to; null if LiveKit is not configured.")
    publisher_token: str | None = Field(default=None, description="Short-lived LiveKit publish token for the owner's broadcasting client; only returned to the owner (go-live/current-session calls), never to viewers.")

    model_config = {"from_attributes": True}


class LiveShowcaseResponse(BaseModel):
    """Public/customer view of the dish showcase for a live session."""

    session_id: uuid.UUID
    kitchen_id: uuid.UUID
    title: str
    status: str
    dish_id: uuid.UUID | None = None
    dish_name: str | None = None
    showcase_phase: str = "idle"
    active_prep_step_order: int | None = None
    prepared_at: datetime | None = None
    ingredients: list[ShowcaseIngredient] = Field(default_factory=list)
    prep_steps: list[ShowcasePrepStep] = Field(default_factory=list)


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
    dish_id: uuid.UUID | None = Field(default=None, description="Featured dish, if any.")
    dish_name: str | None = Field(default=None, description="Featured dish name.")
    showcase_phase: str = Field(default="idle", description="Current showcase phase.")


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


async def _session_response(
    session: AsyncSession,
    session_row: LiveSession,
    *,
    publisher_token: str | None = None,
) -> LiveSessionResponse:
    url, _, _ = await resolve_livekit_creds(session)
    return LiveSessionResponse(
        id=session_row.id,
        kitchen_id=session_row.kitchen_id,
        title=session_row.title,
        room_name=session_row.room_name,
        status=session_row.status,
        order_id=session_row.order_id,
        dish_id=session_row.dish_id,
        dish_name=session_row.dish_name,
        showcase_phase=session_row.showcase_phase or "idle",
        active_prep_step_order=session_row.active_prep_step_order,
        prepared_at=session_row.prepared_at,
        viewer_count=session_row.viewer_count,
        started_at=session_row.started_at,
        ended_at=session_row.ended_at,
        livekit_url=url or None,
        publisher_token=publisher_token,
    )


def _showcase_from_session(live: LiveSession) -> LiveShowcaseResponse:
    snap = live.showcase_snapshot if isinstance(live.showcase_snapshot, dict) else {}
    ingredients = [ShowcaseIngredient.model_validate(i) for i in (snap.get("ingredients") or [])]
    prep_steps = [ShowcasePrepStep.model_validate(s) for s in (snap.get("prep_steps") or [])]
    return LiveShowcaseResponse(
        session_id=live.id,
        kitchen_id=live.kitchen_id,
        title=live.title,
        status=live.status,
        dish_id=live.dish_id,
        dish_name=live.dish_name,
        showcase_phase=live.showcase_phase or "idle",
        active_prep_step_order=live.active_prep_step_order,
        prepared_at=live.prepared_at,
        ingredients=ingredients,
        prep_steps=prep_steps,
    )


async def _apply_dish_to_session(
    session: AsyncSession,
    live: LiveSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    *,
    phase: str | None = None,
) -> None:
    snapshot = await load_dish_showcase_snapshot(session, kitchen_id, dish_id)
    live.dish_id = dish_id
    live.dish_name = snapshot["dish_name"]
    live.showcase_snapshot = snapshot
    next_phase = (phase or "ingredients").strip().lower()
    if next_phase not in SHOWCASE_PHASE_SET or next_phase == "idle":
        next_phase = "ingredients"
    live.showcase_phase = next_phase
    steps = snapshot.get("prep_steps") or []
    if next_phase == "prep" and steps:
        live.active_prep_step_order = int(steps[0]["step_order"])
    elif next_phase != "prep":
        live.active_prep_step_order = None
    if next_phase == "prepared":
        live.prepared_at = datetime.now(UTC)
    else:
        live.prepared_at = None


async def get_stream_settings(session: AsyncSession, kitchen_id: uuid.UUID) -> StreamSettingsResponse:
    row = await _get_settings_row(session, kitchen_id)
    live = await _active_session(session, kitchen_id)
    return StreamSettingsResponse(
        kitchen_id=kitchen_id,
        live_sharing_enabled=row.live_sharing_enabled,
        q_and_a_enabled=row.q_and_a_enabled,
        is_live=live is not None,
        livekit_configured=await livekit_configured(session),
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
    await require_feature(session, "live_streaming")
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
        showcase_phase="idle",
        showcase_snapshot={},
    )
    session.add(live)
    await session.flush()

    if data.dish_id is not None:
        await _apply_dish_to_session(
            session,
            live,
            kitchen_id,
            data.dish_id,
            phase=data.showcase_phase,
        )
        await session.flush()

    token = await build_livekit_token(
        room_name=room_name,
        identity=publisher_identity(kitchen_id),
        can_publish=True,
        session=session,
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
            "dish_id": str(live.dish_id) if live.dish_id else None,
            "showcase_phase": live.showcase_phase,
        },
    )
    await publisher.publish(stream_key("streaming", "session"), event, session=session)
    return await _session_response(session, live, publisher_token=token)


async def update_live_showcase(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: ShowcaseUpdateRequest,
    publisher: EventPublisher,
) -> LiveSessionResponse:
    live = await _active_session(session, kitchen_id)
    if not live:
        raise ValueError("No active live session")

    if data.clear_dish:
        live.dish_id = None
        live.dish_name = None
        live.showcase_phase = "idle"
        live.active_prep_step_order = None
        live.prepared_at = None
        live.showcase_snapshot = {}
    else:
        if data.dish_id is not None:
            await _apply_dish_to_session(
                session,
                live,
                kitchen_id,
                data.dish_id,
                phase=data.showcase_phase or live.showcase_phase or "ingredients",
            )
        elif data.showcase_phase is not None:
            phase = data.showcase_phase.strip().lower()
            if phase not in SHOWCASE_PHASE_SET:
                raise ValueError(f"Invalid showcase_phase — use one of {list(SHOWCASE_PHASES)}")
            if phase != "idle" and not live.dish_id:
                raise ValueError("Feature a dish before setting showcase phase")
            live.showcase_phase = phase
            if phase == "prepared":
                live.prepared_at = datetime.now(UTC)
                live.active_prep_step_order = None
            elif phase == "prep":
                live.prepared_at = None
                snap = live.showcase_snapshot if isinstance(live.showcase_snapshot, dict) else {}
                steps = snap.get("prep_steps") or []
                if data.active_prep_step_order is not None:
                    live.active_prep_step_order = data.active_prep_step_order
                elif steps and live.active_prep_step_order is None:
                    live.active_prep_step_order = int(steps[0]["step_order"])
            else:
                live.prepared_at = None
                if phase != "prep":
                    live.active_prep_step_order = None

        if data.active_prep_step_order is not None and not data.clear_dish:
            if live.showcase_phase != "prep":
                live.showcase_phase = "prep"
                live.prepared_at = None
            live.active_prep_step_order = data.active_prep_step_order

    await session.flush()

    event = EventPublisher.build(
        event_type="stream.showcase_updated",
        aggregate_type="live_session",
        aggregate_id=str(live.id),
        producer="streaming-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "session_id": str(live.id),
            "dish_id": str(live.dish_id) if live.dish_id else None,
            "dish_name": live.dish_name,
            "showcase_phase": live.showcase_phase,
            "active_prep_step_order": live.active_prep_step_order,
        },
    )
    await publisher.publish(stream_key("streaming", "session"), event, session=session)
    return await _session_response(session, live)


async def get_live_showcase(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> LiveShowcaseResponse:
    live = (
        await session.execute(select(LiveSession).where(LiveSession.id == session_id))
    ).scalar_one_or_none()
    if not live:
        raise ValueError("Live session not found")
    if live.status != "live":
        raise ValueError("Live session is not active")
    return _showcase_from_session(live)


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
    return await _session_response(session, live)


async def get_current_session(session: AsyncSession, kitchen_id: uuid.UUID) -> LiveSessionResponse | None:
    live = await _active_session(session, kitchen_id)
    if not live:
        return None
    token = await build_livekit_token(
        room_name=live.room_name,
        identity=publisher_identity(kitchen_id),
        can_publish=True,
        session=session,
    )
    return await _session_response(session, live, publisher_token=token)


async def issue_viewer_token(
    session: AsyncSession,
    session_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> ViewerTokenResponse:
    await require_feature(session, "live_streaming")
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

    url, _, _ = await resolve_livekit_creds(session)
    token = await build_livekit_token(
        room_name=live.room_name,
        identity=viewer_identity(customer_id),
        can_publish=False,
        session=session,
    )
    return ViewerTokenResponse(
        session_id=live.id,
        room_name=live.room_name,
        livekit_url=url or None,
        token=token,
        kitchen_name=kitchen_name,
    )


async def list_live_kitchens(session: AsyncSession) -> LiveKitchenListResponse:
    rows = (
        await session.execute(
            text(
                """
                SELECT s.id, s.kitchen_id, s.title, s.started_at, k.code, k.name,
                       s.dish_id, s.dish_name, s.showcase_phase
                FROM ckac_streaming.live_sessions s
                JOIN ckac_identity.kitchens k ON k.id = s.kitchen_id
                JOIN ckac_streaming.kitchen_stream_settings st ON st.kitchen_id = s.kitchen_id
                WHERE s.status = 'live' AND st.live_sharing_enabled = true AND k.status = 'active'
                ORDER BY s.started_at DESC
                """
            )
        )
    ).mappings().all()
    kitchens = [
        LiveKitchenSummary(
            kitchen_id=uuid.UUID(str(r["kitchen_id"])),
            session_id=uuid.UUID(str(r["id"])),
            title=r["title"],
            started_at=r["started_at"],
            kitchen_code=r["code"],
            kitchen_name=r["name"],
            dish_id=uuid.UUID(str(r["dish_id"])) if r["dish_id"] else None,
            dish_name=r["dish_name"],
            showcase_phase=r["showcase_phase"] or "idle",
        )
        for r in rows
    ]
    return LiveKitchenListResponse(kitchens=kitchens, total=len(kitchens))
