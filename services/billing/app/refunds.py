"""Order refunds — gateway reverse (full) and direct UPI/bank (full or partial)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Refund
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

REFUNDABLE_PAYMENT_STATUSES = ("captured", "partially_refunded")


class RefundCreateRequest(BaseModel):
    """Owner-initiated refund for a single-kitchen order payment."""

    order_id: uuid.UUID = Field(..., description="Order to refund.")
    kind: Literal["full", "partial"] = Field(..., description="Per-order refund switch.")
    channel: Literal["gateway", "direct_transfer"] | None = Field(
        default=None,
        description="Full refunds: `gateway` (Razorpay reverse) or `direct_transfer`. Partial always uses direct transfer.",
    )
    amount: float | None = Field(
        default=None,
        gt=0,
        description="Required for partial refunds. Ignored for full (uses remaining refundable amount).",
    )
    destination_type: Literal["upi", "bank"] | None = Field(
        default=None,
        description="Direct transfer destination. Defaults from customer payout profile.",
    )
    destination_upi: str | None = Field(default=None, max_length=100)
    destination_bank_account: str | None = Field(default=None, max_length=34)
    destination_bank_ifsc: str | None = Field(default=None, max_length=11)
    destination_account_name: str | None = Field(default=None, max_length=255)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_kind_channel(self) -> RefundCreateRequest:
        if self.kind == "partial":
            if self.amount is None:
                raise ValueError("Partial refunds require amount")
            if self.channel == "gateway":
                raise ValueError("Partial refunds must use direct_transfer (UPI or bank)")
        return self


class RefundResponse(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    order_id: uuid.UUID
    kitchen_id: uuid.UUID
    kind: str
    channel: str
    amount: float
    currency: str
    status: str
    destination_type: str
    destination_upi: str | None = None
    destination_bank_account_masked: str | None = None
    destination_bank_ifsc: str | None = None
    destination_account_name: str | None = None
    transfer_remark: str
    razorpay_refund_id: str | None = None
    evidence_url: str | None = None
    reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


def _mask_account(account: str | None) -> str | None:
    if not account:
        return None
    digits = re.sub(r"\s+", "", account)
    if len(digits) <= 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def refund_to_response(refund: Refund) -> RefundResponse:
    return RefundResponse(
        id=refund.id,
        payment_id=refund.payment_id,
        order_id=refund.order_id,
        kitchen_id=refund.kitchen_id,
        kind=refund.kind,
        channel=refund.channel,
        amount=float(refund.amount),
        currency=refund.currency,
        status=refund.status,
        destination_type=refund.destination_type,
        destination_upi=refund.destination_upi,
        destination_bank_account_masked=_mask_account(refund.destination_bank_account),
        destination_bank_ifsc=refund.destination_bank_ifsc,
        destination_account_name=refund.destination_account_name,
        transfer_remark=refund.transfer_remark,
        razorpay_refund_id=refund.razorpay_refund_id,
        evidence_url=refund.evidence_url,
        reason=refund.reason,
        created_at=refund.created_at,
        completed_at=refund.completed_at,
    )


async def _load_captured_payment_for_order(
    session: AsyncSession,
    order_id: uuid.UUID,
) -> Payment:
    result = await session.execute(
        select(Payment)
        .where(
            Payment.order_id == order_id,
            Payment.status.in_(REFUNDABLE_PAYMENT_STATUSES),
        )
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise ValueError("No captured payment found for this order")
    return payment


async def _refunded_total(session: AsyncSession, payment_id: uuid.UUID) -> float:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM ckac_billing.refunds
            WHERE payment_id = :pid AND status IN ('requested', 'processing', 'completed')
            """
        ),
        {"pid": payment_id},
    )
    return float(result.scalar_one() or 0)


async def _load_customer_payout_by_phone(
    session: AsyncSession,
    phone: str | None,
) -> dict | None:
    if not phone:
        return None
    result = await session.execute(
        text(
            """
            SELECT id, upi_vpa, upi_qr_url, bank_account_number, bank_ifsc, bank_account_name
            FROM ckac_identity.customers
            WHERE phone = :phone
            LIMIT 1
            """
        ),
        {"phone": phone},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


def _resolve_direct_destination(
    body: RefundCreateRequest,
    payout: dict | None,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    dest_type = body.destination_type
    upi = (body.destination_upi or (payout or {}).get("upi_vpa") or "").strip() or None
    bank = (body.destination_bank_account or (payout or {}).get("bank_account_number") or "").strip() or None
    ifsc = (body.destination_bank_ifsc or (payout or {}).get("bank_ifsc") or "").strip() or None
    name = (body.destination_account_name or (payout or {}).get("bank_account_name") or "").strip() or None

    if dest_type is None:
        if upi:
            dest_type = "upi"
        elif bank and ifsc:
            dest_type = "bank"
        else:
            raise ValueError(
                "Customer has no UPI or bank details on file — ask them to add payout details, "
                "or pass destination_upi / bank fields"
            )

    if dest_type == "upi":
        if not upi:
            raise ValueError("UPI VPA required for direct UPI refund")
        if "@" not in upi:
            raise ValueError("Invalid UPI VPA")
        return dest_type, upi, None, None, None

    if not bank or not ifsc:
        raise ValueError("Bank account number and IFSC required for bank refund")
    return dest_type, None, bank, ifsc.upper(), name


async def _sync_payment_refund_status(
    session: AsyncSession,
    payment: Payment,
) -> None:
    total = await _refunded_total(session, payment.id)
    # Exclude in-flight for status sync of completed only when marking completed —
    # recompute completed sum:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM ckac_billing.refunds
            WHERE payment_id = :pid AND status = 'completed'
            """
        ),
        {"pid": payment.id},
    )
    completed = float(result.scalar_one() or 0)
    amount = float(payment.amount)
    if completed >= amount - 0.001:
        payment.status = "refunded"
    elif completed > 0:
        payment.status = "partially_refunded"
    payment.updated_at = datetime.now(UTC)
    await session.flush()


async def create_refund(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    order: dict,
    body: RefundCreateRequest,
    publisher: EventPublisher | None,
) -> Refund:
    payment = await _load_captured_payment_for_order(session, order["id"])

    # Concurrent double-submits (owner double-clicks "Refund") must not both read the same
    # `remaining` balance before either commits — serialize per-payment so the second request
    # sees the first request's pending/created refund row.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"refund_idempotency:{payment.id}"},
    )

    remaining = float(payment.amount) - await _refunded_total(session, payment.id)
    if remaining <= 0:
        raise ValueError("Payment is already fully refunded or refunds pending cover the amount")

    from ckac_common.platform_config import require_feature

    kind = body.kind
    if kind == "full":
        amount = remaining
        channel = body.channel or "gateway"
    else:
        amount = float(body.amount or 0)
        if amount > remaining + 0.001:
            raise ValueError(f"Partial amount exceeds refundable balance ({remaining:.2f})")
        channel = "direct_transfer"

    if channel == "gateway":
        await require_feature(session, "refunds_gateway")
        if kind != "full":
            raise ValueError("Gateway refunds are full refunds only")
        if payment.method not in ("online", "upi"):
            raise ValueError("Gateway refunds require an online/UPI payment")
        if not payment.razorpay_payment_id:
            raise ValueError("Payment has no gateway payment id — use direct_transfer")
        if amount < float(payment.amount) - 0.001:
            raise ValueError("Gateway channel only supports full remaining balance refunds")

        refund = Refund(
            payment_id=payment.id,
            order_id=order["id"],
            kitchen_id=order["kitchen_id"],
            owner_id=owner_id,
            customer_id=None,
            kind="full",
            channel="gateway",
            amount=amount,
            currency=payment.currency,
            status="requested",
            destination_type="gateway_original",
            transfer_remark=str(order["order_code"]),
            reason=body.reason,
        )
        session.add(refund)
        await session.flush()
        await _publish_refund(session, publisher, "refund.created", refund)
        return refund

    await require_feature(session, "refunds_direct")
    payout = await _load_customer_payout_by_phone(session, order.get("customer_phone"))
    dest_type, upi, bank, ifsc, acct_name = _resolve_direct_destination(body, payout)
    refund = Refund(
        payment_id=payment.id,
        order_id=order["id"],
        kitchen_id=order["kitchen_id"],
        owner_id=owner_id,
        customer_id=uuid.UUID(str(payout["id"])) if payout else None,
        kind=kind,
        channel="direct_transfer",
        amount=amount,
        currency=payment.currency,
        status="requested",
        destination_type=dest_type,
        destination_upi=upi,
        destination_bank_account=bank,
        destination_bank_ifsc=ifsc,
        destination_account_name=acct_name,
        transfer_remark=str(order["order_code"]),
        reason=body.reason,
    )
    session.add(refund)
    await session.flush()
    await _publish_refund(session, publisher, "refund.created", refund)
    return refund


async def process_gateway_refund(
    session: AsyncSession,
    refund: Refund,
    publisher: EventPublisher | None,
) -> Refund:
    if refund.channel != "gateway":
        raise ValueError("Not a gateway refund")
    if refund.status == "completed":
        return refund
    if refund.status not in ("requested", "processing", "failed"):
        raise ValueError(f"Cannot process refund in status {refund.status}")

    payment = await session.get(Payment, refund.payment_id)
    if not payment or not payment.razorpay_payment_id:
        raise ValueError("Payment missing gateway reference")

    refund.status = "processing"
    refund.updated_at = datetime.now(UTC)
    await session.flush()

    from ckac_common.platform_config import is_non_production

    if not is_non_production():
        # Live Refunds API not wired — wait for Razorpay `refund.processed` webhook.
        await _publish_refund(session, publisher, "refund.processing", refund)
        return refund

    # Dev-mocked Razorpay refund for development/test only.
    refund.razorpay_refund_id = refund.razorpay_refund_id or f"rfnd_dev_{refund.id.hex[:16]}"
    refund.status = "completed"
    refund.completed_at = datetime.now(UTC)
    refund.updated_at = datetime.now(UTC)
    await session.flush()
    await _sync_payment_refund_status(session, payment)
    await _publish_refund(session, publisher, "refund.completed", refund)
    return refund


async def attach_refund_evidence(
    session: AsyncSession,
    refund: Refund,
    evidence_url: str,
) -> Refund:
    if refund.status == "completed":
        raise ValueError("Refund already completed")
    refund.evidence_url = evidence_url
    refund.updated_at = datetime.now(UTC)
    await session.flush()
    return refund


async def complete_direct_refund(
    session: AsyncSession,
    refund: Refund,
    publisher: EventPublisher | None,
) -> Refund:
    if refund.channel != "direct_transfer":
        raise ValueError("Not a direct transfer refund — use gateway process")
    if refund.status == "completed":
        return refund
    if not refund.evidence_url:
        raise ValueError("Attach a refund screenshot before marking complete")

    payment = await session.get(Payment, refund.payment_id)
    if not payment:
        raise ValueError("Payment not found")

    refund.status = "completed"
    refund.completed_at = datetime.now(UTC)
    refund.updated_at = datetime.now(UTC)
    await session.flush()
    await _sync_payment_refund_status(session, payment)
    await _publish_refund(session, publisher, "refund.completed", refund)
    return refund


async def get_refund_for_owner(
    session: AsyncSession,
    refund_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Refund:
    refund = await session.get(Refund, refund_id)
    if not refund or refund.owner_id != owner_id:
        raise ValueError("Refund not found")
    return refund


async def list_refunds_for_owner(
    session: AsyncSession,
    owner_id: uuid.UUID,
    order_id: uuid.UUID | None = None,
) -> list[Refund]:
    stmt = select(Refund).where(Refund.owner_id == owner_id)
    if order_id:
        stmt = stmt.where(Refund.order_id == order_id)
    stmt = stmt.order_by(Refund.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def apply_gateway_refund_webhook(
    session: AsyncSession,
    razorpay_refund_id: str,
    razorpay_payment_id: str,
    publisher: EventPublisher | None,
) -> Refund | None:
    result = await session.execute(
        select(Refund).where(Refund.razorpay_refund_id == razorpay_refund_id)
    )
    refund = result.scalar_one_or_none()
    if not refund:
        pay_result = await session.execute(
            select(Payment).where(Payment.razorpay_payment_id == razorpay_payment_id)
        )
        payment = pay_result.scalar_one_or_none()
        if not payment:
            return None
        result = await session.execute(
            select(Refund)
            .where(
                Refund.payment_id == payment.id,
                Refund.channel == "gateway",
                Refund.status.in_(("requested", "processing")),
            )
            .order_by(Refund.created_at.desc())
            .limit(1)
        )
        refund = result.scalar_one_or_none()
        if not refund:
            return None
        refund.razorpay_refund_id = razorpay_refund_id

    if refund.status == "completed":
        return refund

    payment = await session.get(Payment, refund.payment_id)
    refund.status = "completed"
    refund.completed_at = datetime.now(UTC)
    refund.updated_at = datetime.now(UTC)
    await session.flush()
    if payment:
        await _sync_payment_refund_status(session, payment)
    await _publish_refund(session, publisher, "refund.completed", refund)
    return refund


async def _publish_refund(
    session: AsyncSession,
    publisher: EventPublisher | None,
    event_type: str,
    refund: Refund,
) -> None:
    if not publisher:
        return
    event = EventPublisher.build(
        event_type=event_type,
        aggregate_type="refund",
        aggregate_id=str(refund.id),
        producer="billing-service",
        payload={
            "refund_id": str(refund.id),
            "payment_id": str(refund.payment_id),
            "order_id": str(refund.order_id),
            "kitchen_id": str(refund.kitchen_id),
            "kind": refund.kind,
            "channel": refund.channel,
            "amount": float(refund.amount),
            "status": refund.status,
            "transfer_remark": refund.transfer_remark,
        },
    )
    await publisher.publish(stream_key("billing", "refund"), event, session=session)
