"""Super-admin marketing — kitchen template visibility + tiffin ops."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.subscriptions import (
    CustomerSubscriptionListResponse,
    CustomerSubscriptionResponse,
    SubscriptionDecisionRequest,
    SubscriptionSummaryResponse,
    decide_subscription,
    get_subscription_for_kitchen,
    list_kitchen_subscriptions,
    subscription_summary,
    subscription_to_response,
)
from app.templates import TemplateResponse, list_templates
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_404, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin Marketing"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


class AdminContext(BaseModel):
    id: uuid.UUID
    email: str
    role: str


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


async def _assert_perm(session: AsyncSession, role: str, permission: str) -> None:
    rows = (
        await session.execute(
            text(
                "SELECT permission_code FROM ckac_identity.admin_role_permissions WHERE role = :role"
            ),
            {"role": role},
        )
    ).scalars().all()
    grants = {str(r) for r in rows}
    if "*" in grants or permission in grants:
        return
    if permission.endswith(":read") and permission[:-5] + ":write" in grants:
        return
    raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")


@router.get(
    "/kitchens/{kitchen_id}/templates",
    response_model=list[TemplateResponse],
    summary="List kitchen marketing templates (super admin)",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_templates(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    channel: Annotated[str | None, Query()] = None,
) -> list[TemplateResponse]:
    await _assert_perm(session, admin.role, "marketing:read")
    exists = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    return await list_templates(session, kitchen_id, channel=channel)


@router.get(
    "/kitchens/{kitchen_id}/tiffin-summary",
    response_model=SubscriptionSummaryResponse,
    summary="Kitchen tiffin / monthly subscription KPIs (super admin)",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_tiffin_summary(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionSummaryResponse:
    await _assert_perm(session, admin.role, "kitchens:read")
    exists = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    return await subscription_summary(session, kitchen_id)


async def _assert_kitchen(session: AsyncSession, kitchen_id: uuid.UUID) -> None:
    exists = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Kitchen not found")


@router.get(
    "/kitchens/{kitchen_id}/subscriptions",
    response_model=CustomerSubscriptionListResponse,
    summary="List kitchen tiffin subscriptions (super admin)",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_subscriptions(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> CustomerSubscriptionListResponse:
    await _assert_perm(session, admin.role, "kitchens:read")
    await _assert_kitchen(session, kitchen_id)
    rows = await list_kitchen_subscriptions(session, kitchen_id, status=status, limit=limit)
    items = [await subscription_to_response(session, s) for s in rows]
    return CustomerSubscriptionListResponse(subscriptions=items, total=len(items))


@router.post(
    "/kitchens/{kitchen_id}/subscriptions/{sub_id}/{action}",
    response_model=CustomerSubscriptionResponse,
    summary="Accept / deny / activate / deactivate a tiffin subscription (super admin)",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_decide_subscription(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    action: Literal["accept", "deny", "activate", "deactivate"],
    body: SubscriptionDecisionRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> CustomerSubscriptionResponse:
    await _assert_perm(session, admin.role, "kitchens:write")
    await _assert_kitchen(session, kitchen_id)
    try:
        sub = await get_subscription_for_kitchen(session, kitchen_id, sub_id)
        sub = await decide_subscription(
            session,
            sub,
            action=action,
            owner_id=admin.id,
            data=body,
            publisher=publisher,
        )
        await session.commit()
        await session.refresh(sub)
        return await subscription_to_response(session, sub)
    except ValueError as exc:
        await session.rollback()
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc
