"""Internal routes — service-to-service only (X-Internal-Key)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Owner
from ckac_common.database import get_db
from ckac_common.internal_auth import verify_internal_key

router = APIRouter(prefix="/internal", dependencies=[Depends(verify_internal_key)])


class OwnerSubscriptionSyncRequest(BaseModel):
    plan_tier: Literal["starter", "growth", "pro", "enterprise"] = Field(
        ..., description="Activated SaaS tier."
    )
    subscription_status: Literal["active"] = Field(default="active")
    subscription_expires_at: datetime = Field(..., description="Current billing period end (UTC).")


class InternalAdminAuditRequest(BaseModel):
    """Cross-service admin audit write (billing → identity)."""

    actor_admin_id: uuid.UUID | None = None
    actor_email: str = Field(..., min_length=3, max_length=255)
    actor_role: str = Field(..., min_length=2, max_length=32)
    action: str = Field(..., min_length=3, max_length=64)
    resource_type: str = Field(..., min_length=2, max_length=64)
    resource_id: str = Field(..., min_length=1, max_length=64)
    kitchen_id: uuid.UUID | None = None
    summary: str = Field(default="", max_length=500)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


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


@router.post(
    "/admin-audit",
    status_code=status.HTTP_201_CREATED,
    summary="Record a platform admin audit event from another service",
)
async def internal_admin_audit(
    body: InternalAdminAuditRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    from app.admin_audit import record_admin_audit

    row = await record_admin_audit(
        session,
        action=body.action,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        kitchen_id=body.kitchen_id,
        summary=body.summary,
        before=body.before,
        after=body.after,
        actor_admin_id=body.actor_admin_id,
        actor_email=body.actor_email,
        actor_role=body.actor_role,
    )
    await session.commit()
    return {"id": str(row.id)}


class ReferralFirstOrderRequest(BaseModel):
    customer_id: uuid.UUID
    customer_phone: str | None = None


class ReferralApplyCreditRequest(BaseModel):
    owner_id: uuid.UUID
    charge_amount_inr: float = Field(..., ge=0)


@router.post(
    "/referrals/customer-first-order",
    summary="Reward kitchen referrer when a referred customer places first order",
)
async def internal_referral_first_order(
    body: ReferralFirstOrderRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.main import event_publisher
    from app.referral import try_reward_customer_first_order

    lead = await try_reward_customer_first_order(
        session,
        customer_id=body.customer_id,
        phone=body.customer_phone,
        publisher=event_publisher,
    )
    await session.commit()
    return {"rewarded": lead is not None, "lead_id": str(lead.id) if lead else None}


@router.post(
    "/referrals/apply-owner-credit",
    summary="Apply owner referral credit against a SaaS charge",
)
async def internal_apply_owner_credit(
    body: ReferralApplyCreditRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    from app.main import event_publisher
    from app.referral import apply_owner_credit

    result = await apply_owner_credit(
        session,
        owner_id=body.owner_id,
        charge_amount_inr=body.charge_amount_inr,
        publisher=event_publisher,
    )
    await session.commit()
    return result.model_dump()
