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


async def get_current_customer_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_customer_id(credentials.credentials)


async def load_customer_phone(customer_id: uuid.UUID, session: AsyncSession) -> str:
    result = await session.execute(
        text(
            "SELECT phone FROM ckac_identity.customers WHERE id = :cid AND status = 'active' LIMIT 1"
        ),
        {"cid": customer_id},
    )
    phone = result.scalar_one_or_none()
    if not phone:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")
    return phone


async def load_order_for_customer(
    order_id: uuid.UUID,
    customer_phone: str,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT o.id, o.kitchen_id, o.order_code, o.total, o.payment_method, o.customer_phone
            FROM ckac_orders.orders o
            WHERE o.id = :oid
            LIMIT 1
            """
        ),
        {"oid": order_id},
    )
    row = result.mappings().one_or_none()
    if not row or row["customer_phone"] != customer_phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return dict(row)


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


async def load_order_for_owner(
    order_id: uuid.UUID,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT o.id, o.kitchen_id, o.order_code, o.total, o.payment_method, o.customer_phone
            FROM ckac_orders.orders o
            JOIN ckac_identity.kitchens k ON k.id = o.kitchen_id
            WHERE o.id = :oid AND k.owner_id = :owner_id
            LIMIT 1
            """
        ),
        {"oid": order_id, "owner_id": owner_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return dict(row)
