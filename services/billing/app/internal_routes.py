"""Billing internal routes — wallet deduct (service-to-service)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging_wallet import deduct_messaging_wallet
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.internal_auth import verify_internal_key
from ckac_common.openapi import RESP_401

router = APIRouter(prefix="/internal", dependencies=[Depends(verify_internal_key)])


class WalletDeductRequest(BaseModel):
    amount_inr: float = Field(gt=0, description="Total INR to debit from the kitchen messaging wallet.")
    reason: str = Field(min_length=3, max_length=200, description="Audit reason, e.g. daily_menu_blast.")
    recipient_count: int = Field(default=1, ge=1, le=100_000)


class WalletDeductResponse(BaseModel):
    kitchen_id: uuid.UUID
    balance_inr: float
    deducted_inr: float


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post(
    "/wallets/{kitchen_id}/deduct",
    response_model=WalletDeductResponse,
    summary="[Internal] Deduct messaging wallet for broadcast fees",
    responses={401: RESP_401, 400: {"description": "Insufficient balance"}},
)
async def internal_wallet_deduct(
    kitchen_id: uuid.UUID,
    body: WalletDeductRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> WalletDeductResponse:
    try:
        wallet = await deduct_messaging_wallet(
            session,
            kitchen_id,
            body.amount_inr,
            reason=body.reason,
            recipient_count=body.recipient_count,
            publisher=publisher,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WalletDeductResponse(
        kitchen_id=kitchen_id,
        balance_inr=float(wallet.balance_inr),
        deducted_inr=body.amount_inr,
    )
