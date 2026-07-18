"""Read-only billing checks before Porter book (prepaid delivery fee)."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def order_has_captured_payment(session: AsyncSession, order_id: uuid.UUID) -> bool:
    """True if billing has a captured (or partially refunded) payment for this order."""
    row = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM ckac_billing.payments
                WHERE order_id = :oid
                  AND status IN ('captured', 'partially_refunded')
                LIMIT 1
                """
            ),
            {"oid": order_id},
        )
    ).scalar_one_or_none()
    if row is not None:
        return True
    # Master-order sub-orders: payment may sit on master_order_id only.
    master = (
        await session.execute(
            text(
                """
                SELECT master_order_id FROM ckac_orders.orders
                WHERE id = :oid LIMIT 1
                """
            ),
            {"oid": order_id},
        )
    ).scalar_one_or_none()
    if master is None:
        return False
    mrow = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM ckac_billing.payments
                WHERE master_order_id = :mid
                  AND status IN ('captured', 'partially_refunded')
                LIMIT 1
                """
            ),
            {"mid": master},
        )
    ).scalar_one_or_none()
    return mrow is not None
