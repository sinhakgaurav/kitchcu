"""Shared platform-admin JWT validation (cross-schema read of platform_admins)."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.config import get_settings
from ckac_common.database import get_db

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return AdminContext(id=row["id"], email=row["email"], role=row["role"])
