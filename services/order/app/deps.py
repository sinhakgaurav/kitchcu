import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order
from ckac_common.auth import decode_customer_id, decode_owner_id
from ckac_common.database import get_db
from ckac_common.internal_auth import verify_internal_key

security = HTTPBearer(auto_error=False)


async def get_current_owner_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_owner_id(credentials.credentials)


async def get_current_customer_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_customer_id(credentials.credentials)


async def load_customer_profile(
    customer_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT id, name, phone, email
            FROM ckac_identity.customers
            WHERE id = :cid AND status = 'active'
            LIMIT 1
            """
        ),
        {"cid": customer_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")
    return dict(row)


async def verify_kitchen_active(kitchen_id: uuid.UUID, session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid AND status = 'active' LIMIT 1"
        ),
        {"kid": kitchen_id},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not available")


async def get_order_for_customer(
    order_id: uuid.UUID,
    customer_phone: str,
    session: AsyncSession,
) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.customer_phone != customer_phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


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


async def get_order_for_owner(
    order_id: uuid.UUID,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    await verify_kitchen_owner(order.kitchen_id, owner_id, session)
    return order
