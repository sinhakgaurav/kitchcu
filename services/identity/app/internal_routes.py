"""Internal routes — service-to-service only (X-Internal-Key)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Owner
from ckac_common.database import get_db
from ckac_common.internal_auth import verify_internal_key

router = APIRouter(prefix="/internal", dependencies=[Depends(verify_internal_key)])


class OwnerSubscriptionSyncRequest(BaseModel):
    plan_tier: Literal["starter", "growth", "pro"] = Field(..., description="Activated SaaS tier.")
    subscription_status: Literal["active"] = Field(default="active")
    subscription_expires_at: datetime = Field(..., description="Current billing period end (UTC).")


@router.patch(
    "/owners/{owner_id}/subscription",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sync owner subscription state after billing activation",
)
async def sync_owner_subscription(
    owner_id: uuid.UUID,
    body: OwnerSubscriptionSyncRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Called by billing-service when a platform subscription is activated."""
    result = await session.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    owner.subscription_tier = body.plan_tier
    owner.subscription_status = body.subscription_status
    owner.subscription_expires_at = body.subscription_expires_at
    await session.commit()
