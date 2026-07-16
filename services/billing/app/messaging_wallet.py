"""Enterprise subscription bifurcation — platform revenue vs messaging wallet."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KitchenMessagingWallet, OwnerSubscription, SubscriptionLedgerEntry
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

ENTERPRISE_MONTHLY_INR = 1799.0
ENTERPRISE_YEARLY_INR = 17990.0
ENTERPRISE_PLATFORM_MONTHLY_INR = 1299.0
ENTERPRISE_WALLET_MONTHLY_INR = 500.0
ENTERPRISE_PLATFORM_YEARLY_INR = 12990.0
ENTERPRISE_WALLET_YEARLY_INR = 5000.0
MESSAGING_WALLET_LOW_BALANCE_INR = 50.0


class MessagingWalletResponse(BaseModel):
    """Owner-facing messaging wallet balance (Enterprise ₹500 monthly credit)."""

    kitchen_id: uuid.UUID
    balance_inr: float = Field(..., description="Current wallet balance in INR.")
    low_balance: bool = Field(..., description="True when balance is below the alert threshold.")
    low_balance_threshold_inr: float = Field(..., description="Alert threshold in INR.")
    updated_at: datetime | None = None


def enterprise_split(amount: float, billing_cycle: str) -> tuple[float, float]:
    """Return (platform_revenue, wallet_credit) for enterprise tier charges."""
    if billing_cycle == "yearly":
        return ENTERPRISE_PLATFORM_YEARLY_INR, ENTERPRISE_WALLET_YEARLY_INR
    return ENTERPRISE_PLATFORM_MONTHLY_INR, ENTERPRISE_WALLET_MONTHLY_INR


async def _primary_kitchen_id(session: AsyncSession, owner_id: uuid.UUID) -> uuid.UUID | None:
    result = await session.execute(
        text(
            """
            SELECT id FROM ckac_identity.kitchens
            WHERE owner_id = :oid AND status = 'active'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        {"oid": owner_id},
    )
    row = result.scalar_one_or_none()
    return row if row is None else uuid.UUID(str(row))


async def apply_enterprise_subscription_bifurcation(
    session: AsyncSession,
    sub: OwnerSubscription,
    publisher: EventPublisher | None,
) -> SubscriptionLedgerEntry | None:
    """Split enterprise subscription payment into platform revenue + messaging wallet credit."""
    if sub.plan_tier != "enterprise":
        return None

    platform_amount, wallet_amount = enterprise_split(float(sub.amount), sub.billing_cycle)
    if float(sub.amount) != platform_amount + wallet_amount:
        raise ValueError("Enterprise subscription amount does not match bifurcation totals")

    kitchen_id = await _primary_kitchen_id(session, sub.owner_id)
    ledger = SubscriptionLedgerEntry(
        subscription_id=sub.id,
        owner_id=sub.owner_id,
        kitchen_id=kitchen_id,
        total_amount=float(sub.amount),
        platform_revenue_amount=platform_amount,
        wallet_credit_amount=wallet_amount,
        currency="INR",
    )
    session.add(ledger)
    await session.flush()

    if kitchen_id is None:
        return ledger

    result = await session.execute(
        select(KitchenMessagingWallet).where(KitchenMessagingWallet.kitchen_id == kitchen_id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = KitchenMessagingWallet(kitchen_id=kitchen_id, balance_inr=0)
        session.add(wallet)
        await session.flush()

    wallet.balance_inr = float(wallet.balance_inr) + wallet_amount
    wallet.updated_at = datetime.now(UTC)
    if float(wallet.balance_inr) >= MESSAGING_WALLET_LOW_BALANCE_INR:
        wallet.low_balance_alerted_at = None
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="wallet.credits.added",
            aggregate_type="messaging_wallet",
            aggregate_id=str(kitchen_id),
            producer="billing-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "owner_id": str(sub.owner_id),
                "subscription_id": str(sub.id),
                "ledger_entry_id": str(ledger.id),
                "amount_inr": wallet_amount,
                "balance_inr": float(wallet.balance_inr),
                "platform_revenue_inr": platform_amount,
            },
        )
        await publisher.publish(stream_key("billing", "wallet"), event, session=session)

    return ledger


async def get_messaging_wallet(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> KitchenMessagingWallet:
    """Return kitchen messaging wallet, creating a zero-balance row if missing."""
    result = await session.execute(
        select(KitchenMessagingWallet).where(KitchenMessagingWallet.kitchen_id == kitchen_id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = KitchenMessagingWallet(kitchen_id=kitchen_id, balance_inr=0)
        session.add(wallet)
        await session.flush()
    return wallet


def messaging_wallet_to_response(wallet: KitchenMessagingWallet) -> MessagingWalletResponse:
    from ckac_common.risk_config import messaging_wallet_low_balance_inr

    balance = float(wallet.balance_inr)
    threshold = messaging_wallet_low_balance_inr()
    return MessagingWalletResponse(
        kitchen_id=wallet.kitchen_id,
        balance_inr=balance,
        low_balance=balance < threshold,
        low_balance_threshold_inr=threshold,
        updated_at=wallet.updated_at,
    )


async def deduct_messaging_wallet(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    amount_inr: float,
    *,
    reason: str,
    recipient_count: int = 1,
    publisher: EventPublisher | None,
) -> KitchenMessagingWallet:
    """Debit kitchen messaging wallet for Meta/Twilio broadcast fees."""
    from ckac_common.risk_config import messaging_wallet_low_balance_inr

    if amount_inr <= 0:
        raise ValueError("Deduction amount must be positive")

    result = await session.execute(
        select(KitchenMessagingWallet).where(KitchenMessagingWallet.kitchen_id == kitchen_id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None or float(wallet.balance_inr) < amount_inr:
        raise ValueError("Insufficient messaging wallet balance")

    threshold = messaging_wallet_low_balance_inr()
    wallet.balance_inr = float(wallet.balance_inr) - amount_inr
    wallet.updated_at = datetime.now(UTC)
    await session.flush()

    low_balance = float(wallet.balance_inr) < threshold
    emit_low_balance = low_balance and wallet.low_balance_alerted_at is None
    if emit_low_balance:
        wallet.low_balance_alerted_at = datetime.now(UTC)
        await session.flush()

    if publisher:
        debit_event = EventPublisher.build(
            event_type="wallet.debited",
            aggregate_type="messaging_wallet",
            aggregate_id=str(kitchen_id),
            producer="billing-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "amount_inr": amount_inr,
                "balance_inr": float(wallet.balance_inr),
                "reason": reason,
                "recipient_count": recipient_count,
            },
        )
        await publisher.publish(stream_key("billing", "wallet"), debit_event, session=session)
        if emit_low_balance:
            alert_event = EventPublisher.build(
                event_type="wallet.low_balance",
                aggregate_type="messaging_wallet",
                aggregate_id=str(kitchen_id),
                producer="billing-service",
                payload={
                    "kitchen_id": str(kitchen_id),
                    "balance_inr": float(wallet.balance_inr),
                    "threshold_inr": threshold,
                },
            )
            await publisher.publish(stream_key("billing", "wallet"), alert_event, session=session)

    return wallet
