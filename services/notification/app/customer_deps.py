"""Customer JWT helpers for notification service."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.auth import decode_customer_id
from ckac_common.database import get_db

security = HTTPBearer(auto_error=False)


async def get_current_customer_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_customer_id(credentials.credentials)


async def load_customer_contact(
    customer_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        text(
            "SELECT name, phone, email FROM ckac_identity.customers "
            "WHERE id = :cid AND status = 'active' LIMIT 1"
        ),
        {"cid": customer_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")
    return dict(row)
