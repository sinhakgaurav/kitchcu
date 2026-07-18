import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.auth import decode_customer_id, decode_owner_id

security = HTTPBearer(auto_error=False)


async def get_current_owner_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_owner_id(credentials.credentials)


async def get_optional_customer_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID | None:
    if not credentials:
        return None
    try:
        return decode_customer_id(credentials.credentials)
    except HTTPException:
        return None


async def get_current_customer_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_customer_id(credentials.credentials)


async def verify_kitchen_owner(
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM ckac_identity.kitchens "
            "WHERE id = :kid AND owner_id = :oid LIMIT 1"
        ),
        {"kid": kitchen_id, "oid": owner_id},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kitchen access denied")


async def load_customer_phone(customer_id: uuid.UUID, session: AsyncSession) -> str | None:
    result = await session.execute(
        text(
            "SELECT phone FROM ckac_identity.customers WHERE id = :cid AND status = 'active' LIMIT 1"
        ),
        {"cid": customer_id},
    )
    return result.scalar_one_or_none()


async def load_customer_profile(
    customer_id: uuid.UUID, session: AsyncSession
) -> tuple[str | None, str | None]:
    """Return (phone, name) for an active customer."""
    result = await session.execute(
        text(
            "SELECT phone, name FROM ckac_identity.customers "
            "WHERE id = :cid AND status = 'active' LIMIT 1"
        ),
        {"cid": customer_id},
    )
    row = result.one_or_none()
    if not row:
        return None, None
    return row[0], row[1]
