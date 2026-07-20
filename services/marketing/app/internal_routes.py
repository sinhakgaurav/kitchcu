"""Internal marketing APIs — service-to-service via X-Internal-Key."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Coupon
from ckac_common.auth import stream_key
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.events_context import get_event_publisher
from ckac_common.internal_auth import verify_internal_key

router = APIRouter(prefix="/internal", tags=["Internal"], dependencies=[Depends(verify_internal_key)])


class CouponRedeemRequest(BaseModel):
    kitchen_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=32)
    order_id: uuid.UUID


@router.post("/coupons/redeem", status_code=status.HTTP_204_NO_CONTENT)
async def redeem_coupon(
    body: CouponRedeemRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    code = body.code.strip().upper()
    coupon = (
        await session.execute(
            select(Coupon).where(
                Coupon.kitchen_id == body.kitchen_id,
                Coupon.code == code,
            )
        )
    ).scalar_one_or_none()
    if not coupon or not coupon.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coupon")
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon usage limit reached")
    coupon.used_count = int(coupon.used_count or 0) + 1
    await session.flush()
    publisher = get_event_publisher()
    if publisher:
        event = EventPublisher.build(
            event_type="coupon.redeemed",
            aggregate_type="coupon",
            aggregate_id=str(coupon.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(body.kitchen_id),
                "coupon_id": str(coupon.id),
                "code": coupon.code,
                "order_id": str(body.order_id),
                "used_count": coupon.used_count,
            },
        )
        await publisher.publish(stream_key("marketing", "coupon"), event, session=session)
    await session.commit()
