"""Super-admin streaming — kitchen live-session summary (no publisher tokens)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    LiveSessionResponse,
    StreamSettingsResponse,
    get_current_session,
    get_stream_settings,
)
from ckac_common.admin_rbac import assert_admin_permission
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.openapi import RESP_404, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin Streaming"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


class AdminContext(BaseModel):
    id: uuid.UUID
    email: str
    role: str


class AdminLiveSessionView(BaseModel):
    """Live session fields visible to platform admin — never includes publisher_token."""

    id: uuid.UUID
    kitchen_id: uuid.UUID
    title: str
    room_name: str
    status: str
    order_id: uuid.UUID | None = None
    dish_id: uuid.UUID | None = None
    dish_name: str | None = None
    showcase_phase: str = "idle"
    active_prep_step_order: int | None = None
    prepared_at: datetime | None = None
    viewer_count: int
    started_at: datetime
    ended_at: datetime | None = None
    livekit_url: str | None = None


class AdminStreamSummaryResponse(BaseModel):
    settings: StreamSettingsResponse
    current_session: AdminLiveSessionView | None = None


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminContext:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token type")
        admin_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    row = (
        await session.execute(
            text(
                "SELECT id, email, role FROM ckac_identity.platform_admins "
                "WHERE id = :id AND is_active = true LIMIT 1"
            ),
            {"id": admin_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="Admin not found")
    return AdminContext(id=row["id"], email=row["email"], role=row["role"])


def _session_without_token(session_row: LiveSessionResponse) -> AdminLiveSessionView:
    return AdminLiveSessionView.model_validate(session_row.model_dump(exclude={"publisher_token"}))


@router.get(
    "/kitchens/{kitchen_id}/stream/summary",
    response_model=AdminStreamSummaryResponse,
    summary="Kitchen live-stream summary (super admin)",
    description=(
        "Admin-only kitchen workspace Streaming tab. Returns opt-in settings plus the "
        "current session if live. Never includes a LiveKit publisher_token."
    ),
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_stream_summary(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminStreamSummaryResponse:
    await assert_admin_permission(session, role=admin.role, permission="streaming:read")
    exists = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    settings_row = await get_stream_settings(session, kitchen_id)
    current = await get_current_session(session, kitchen_id, include_publisher_token=False)
    return AdminStreamSummaryResponse(
        settings=settings_row,
        current_session=_session_without_token(current) if current else None,
    )
