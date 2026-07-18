"""Super-admin marketing — kitchen template visibility."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.templates import TemplateResponse, list_templates
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.openapi import RESP_404, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin Marketing"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


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
