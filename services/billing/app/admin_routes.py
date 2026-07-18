"""Super-admin billing control — refunds, payments, settlements oversight."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_auth import AdminContext, get_current_admin
from app.models import Payment, Refund
from app.payment_gateway import (
    PaymentGatewayResponse,
    PaymentGatewayUpsertRequest,
    delete_kitchen_payment_gateway,
    get_kitchen_payment_gateway,
    upsert_kitchen_payment_gateway,
)
from app.refunds import refund_to_response, RefundResponse
from app.schemas import PaymentResponse, SettlementResponse, payment_to_response, settlement_to_response
from app.models import Settlement
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin Billing"])


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


async def _kitchen_exists(session: AsyncSession, kitchen_id: uuid.UUID) -> bool:
    row = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    return row is not None


@router.get(
    "/kitchens/{kitchen_id}/payment-gateway",
    response_model=PaymentGatewayResponse,
    summary="Get kitchen Razorpay payment gateway (super admin)",
    description=(
        "Kitchen-scoped Razorpay credentials for checkout / Route. Secrets masked. "
        "Platform SaaS Razorpay keys remain under identity `/admin/api-keys`."
    ),
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_payment_gateway_get(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentGatewayResponse:
    _ = admin
    if not await _kitchen_exists(session, kitchen_id):
        raise HTTPException(status_code=404, detail="Kitchen not found")
    return await get_kitchen_payment_gateway(session, kitchen_id)


@router.put(
    "/kitchens/{kitchen_id}/payment-gateway",
    response_model=PaymentGatewayResponse,
    summary="Upsert kitchen Razorpay payment gateway (super admin)",
    description=(
        "Onboarding / support path to set kitchen Razorpay key id, secrets, and Route "
        "linked account. Publishes `kitchen_payment_gateway.updated`."
    ),
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def admin_kitchen_payment_gateway_put(
    kitchen_id: uuid.UUID,
    body: PaymentGatewayUpsertRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentGatewayResponse:
    _ = admin
    if not await _kitchen_exists(session, kitchen_id):
        raise HTTPException(status_code=404, detail="Kitchen not found")
    result = await upsert_kitchen_payment_gateway(session, publisher, kitchen_id, body)
    await session.commit()
    return result


@router.delete(
    "/kitchens/{kitchen_id}/payment-gateway",
    response_model=PaymentGatewayResponse,
    summary="Clear kitchen Razorpay payment gateway (super admin)",
    description="Removes kitchen payment credentials. Publishes `kitchen_payment_gateway.cleared`.",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_kitchen_payment_gateway_delete(
    kitchen_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentGatewayResponse:
    _ = admin
    if not await _kitchen_exists(session, kitchen_id):
        raise HTTPException(status_code=404, detail="Kitchen not found")
    result = await delete_kitchen_payment_gateway(session, publisher, kitchen_id)
    await session.commit()
    return result


class AdminRefundPatch(BaseModel):
    status: Literal["requested", "processing", "completed", "failed"] | None = None
    admin_note: str | None = Field(default=None, max_length=1000)


class AdminMoneyStats(BaseModel):
    payments_captured: int
    payments_pending: int
    refunds_requested: int
    refunds_completed: int
    refunds_failed: int
    refunds_amount_completed: float
    settlements_transferred: int


@router.get(
    "/refunds",
    response_model=list[RefundResponse],
    summary="List all refunds (super admin)",
    responses=auth_errors(),
)
async def admin_refunds_list(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    kind: Annotated[str | None, Query()] = None,
    channel: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[RefundResponse]:
    _ = admin
    stmt = select(Refund).order_by(Refund.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Refund.status == status_filter)
    if kind:
        stmt = stmt.where(Refund.kind == kind)
    if channel:
        stmt = stmt.where(Refund.channel == channel)
    rows = list((await session.execute(stmt)).scalars().all())
    return [refund_to_response(r) for r in rows]


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    summary="Get refund detail (super admin)",
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_refund_get(
    refund_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefundResponse:
    _ = admin
    refund = await session.get(Refund, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund_to_response(refund)


@router.patch(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    summary="Update refund status / escalate (super admin)",
    description=(
        "Platform control over refund lifecycle. Completing a direct refund still expects evidence "
        "unless admin forces `failed`. Gateway completions should normally come from process/webhook."
    ),
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def admin_refund_patch(
    refund_id: uuid.UUID,
    body: AdminRefundPatch,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefundResponse:
    refund = await session.get(Refund, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    if body.status:
        if body.status == "completed" and refund.channel == "direct_transfer" and not refund.evidence_url:
            raise HTTPException(
                status_code=400,
                detail="Direct refund needs evidence before admin can mark completed",
            )
        refund.status = body.status
        if body.status == "completed":
            refund.completed_at = datetime.now(UTC)
            payment = await session.get(Payment, refund.payment_id)
            if payment:
                from app.refunds import _sync_payment_refund_status

                await _sync_payment_refund_status(session, payment)
        refund.updated_at = datetime.now(UTC)
    if body.admin_note:
        prefix = f"[admin:{admin.email}] {body.admin_note.strip()}"
        refund.reason = f"{refund.reason} | {prefix}" if refund.reason else prefix
        refund.updated_at = datetime.now(UTC)
    await session.flush()
    return refund_to_response(refund)


@router.get(
    "/payments",
    response_model=list[PaymentResponse],
    summary="List payments (super admin)",
    responses=auth_errors(),
)
async def admin_payments_list(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[PaymentResponse]:
    _ = admin
    stmt = select(Payment).order_by(Payment.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Payment.status == status_filter)
    rows = list((await session.execute(stmt)).scalars().all())
    return [payment_to_response(p) for p in rows]


@router.get(
    "/settlements",
    response_model=list[SettlementResponse],
    summary="List settlements (super admin)",
    responses=auth_errors(),
)
async def admin_settlements_list(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[SettlementResponse]:
    _ = admin
    rows = list(
        (
            await session.execute(select(Settlement).order_by(Settlement.created_at.desc()).limit(limit))
        ).scalars().all()
    )
    return [settlement_to_response(s) for s in rows]


@router.get(
    "/money-stats",
    response_model=AdminMoneyStats,
    summary="Money-movement counters (super admin)",
    responses=auth_errors(),
)
async def admin_money_stats(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminMoneyStats:
    _ = admin
    row = (
        await session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM ckac_billing.payments WHERE status = 'captured') AS payments_captured,
                  (SELECT COUNT(*) FROM ckac_billing.payments WHERE status IN ('created','pending','authorized')) AS payments_pending,
                  (SELECT COUNT(*) FROM ckac_billing.refunds WHERE status IN ('requested','processing')) AS refunds_requested,
                  (SELECT COUNT(*) FROM ckac_billing.refunds WHERE status = 'completed') AS refunds_completed,
                  (SELECT COUNT(*) FROM ckac_billing.refunds WHERE status = 'failed') AS refunds_failed,
                  (SELECT COALESCE(SUM(amount),0) FROM ckac_billing.refunds WHERE status = 'completed') AS refunds_amount_completed,
                  (SELECT COUNT(*) FROM ckac_billing.settlements WHERE settlement_status = 'transferred') AS settlements_transferred
                """
            )
        )
    ).mappings().one()
    return AdminMoneyStats(
        payments_captured=int(row["payments_captured"] or 0),
        payments_pending=int(row["payments_pending"] or 0),
        refunds_requested=int(row["refunds_requested"] or 0),
        refunds_completed=int(row["refunds_completed"] or 0),
        refunds_failed=int(row["refunds_failed"] or 0),
        refunds_amount_completed=float(row["refunds_amount_completed"] or 0),
        settlements_transferred=int(row["settlements_transferred"] or 0),
    )
