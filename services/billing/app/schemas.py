import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OwnerSubscription, Payment, Settlement
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.platform_config import (
    is_dev_provider_id,
    is_non_production,
    require_dev_payment_mocks,
)

SUBSCRIPTION_PLANS: dict[str, dict[str, float]] = {
    "starter": {"monthly": 499.0, "yearly": 4990.0},
    "growth": {"monthly": 999.0, "yearly": 9990.0},
    "pro": {"monthly": 1999.0, "yearly": 19990.0},
}

BILLING_CYCLE_DAYS = {"monthly": 30, "yearly": 365}


class PaymentCreateRequest(BaseModel):
    """Create a payment for a single-kitchen order (owner-initiated or customer self-checkout).

    Only applies to online/UPI orders — COD orders never create a payment. kitchCU charges
    **zero per-order food commission**; this is a pass-through payment to the kitchen, not
    a platform revenue event (platform revenue comes from owner subscriptions, see
    `SubscriptionCreateRequest`).
    """

    order_id: uuid.UUID = Field(..., description="Order to pay for (must belong to the caller).")
    method: Literal["online", "upi"] = Field(
        default="online", description="Payment rail — card/netbanking (`online`) or UPI intent (`upi`)."
    )


class MasterPaymentCreateRequest(BaseModel):
    """Create a single aggregated payment for a multi-kitchen cart (F44 split payment).

    The customer pays once; on capture, funds are split per sub-order via Razorpay Route
    into each kitchen's linked account (see `MasterPaymentCaptureResponse`).
    """

    master_order_id: uuid.UUID = Field(..., description="Master order grouping the multi-kitchen sub-orders.")
    method: Literal["online", "upi"] = Field(default="online", description="Payment rail for the aggregated charge.")


class PaymentResponse(BaseModel):
    """A payment record — for a single order or, if `master_order_id` is set, an aggregated multi-kitchen charge."""

    id: uuid.UUID = Field(..., description="Payment ID.")
    order_id: uuid.UUID | None = Field(default=None, description="Single order this payment is for (mutually exclusive with master_order_id).")
    master_order_id: uuid.UUID | None = Field(
        default=None, description="Master order this aggregated payment is for (multi-kitchen checkout)."
    )
    kitchen_id: uuid.UUID | None = Field(
        default=None, description="Owning kitchen for single-order payments; null for master/aggregated payments."
    )
    amount: float = Field(..., description="Charge amount in `currency`.", examples=[499.0])
    currency: str = Field(..., description="ISO 4217 currency code.", examples=["INR"])
    method: str = Field(..., description="Payment rail used.", examples=["online", "upi"])
    status: str = Field(
        ...,
        description="Lifecycle status.",
        examples=["created", "pending", "authorized", "captured", "partially_refunded", "failed", "refunded"],
    )
    razorpay_order_id: str | None = Field(default=None, description="Razorpay order reference (dev-mocked).")
    razorpay_payment_id: str | None = Field(
        default=None, description="Razorpay payment reference, set once captured (dev-mocked)."
    )
    created_at: datetime = Field(..., description="Payment creation timestamp.")

    model_config = {"from_attributes": True}


class SettlementResponse(BaseModel):
    """Per-kitchen settlement produced when a multi-kitchen master payment is captured (Razorpay Route split)."""

    id: uuid.UUID = Field(..., description="Settlement ID.")
    master_order_id: uuid.UUID = Field(..., description="Master order this settlement belongs to.")
    payment_id: uuid.UUID = Field(..., description="Aggregated payment that funded this settlement.")
    kitchen_id: uuid.UUID = Field(..., description="Kitchen receiving this settlement.")
    order_id: uuid.UUID = Field(..., description="Sub-order this settlement pays out.")
    gross_amount: float = Field(..., description="Sub-order total before deductions.")
    delivery_fee_amount: float = Field(..., description="Delivery fee portion of the sub-order (owner-set, not commission).")
    platform_fee: float = Field(..., description="kitchCU platform fee — always 0; zero per-order food commission.")
    net_to_owner: float = Field(..., description="Amount transferred to the kitchen's linked account.")
    razorpay_transfer_id: str | None = Field(default=None, description="Razorpay Route transfer reference (dev-mocked).")
    settlement_status: str = Field(..., description="Settlement lifecycle status.", examples=["pending", "transferred"])
    settled_at: datetime | None = Field(default=None, description="Timestamp the transfer was completed.")

    model_config = {"from_attributes": True}


class MasterPaymentCaptureResponse(BaseModel):
    """Result of capturing a multi-kitchen master payment — the charge plus one settlement per kitchen."""

    payment: PaymentResponse = Field(..., description="The captured aggregated payment.")
    settlements: list[SettlementResponse] = Field(..., description="One settlement per sub-order/kitchen (Route split).")


class UpiIntentRequest(BaseModel):
    """Request a UPI deep-link intent for an order (customer scans/taps to pay in their UPI app)."""

    order_id: uuid.UUID = Field(..., description="Order to generate a UPI payment intent for.")


class UpiIntentResponse(BaseModel):
    payment_id: uuid.UUID = Field(..., description="Payment created in `pending` status for this intent.")
    order_id: uuid.UUID = Field(..., description="Order being paid.")
    amount: float = Field(..., description="Charge amount.")
    currency: str = Field(..., description="ISO 4217 currency code.")
    status: str = Field(..., description="Payment status — `pending` until the UPI app confirms.")
    upi_uri: str = Field(
        ...,
        description="`upi://pay?...` deep link — open in a UPI app or render as a QR code.",
        examples=["upi://pay?pa=ckpnq001%40kitchCU&pn=kitchCU+Kitchen&am=499.00&cu=INR&tn=Order+CKPNQ001-BILL-20260712-0042"],
    )


class SubscriptionPlanResponse(BaseModel):
    """A platform subscription tier — kitchCU's only source of platform revenue (no food commission)."""

    tier: str = Field(..., description="Plan tier identifier.", examples=["starter", "growth", "pro"])
    monthly_amount: float = Field(..., description="Monthly price in INR.")
    yearly_amount: float = Field(..., description="Yearly price in INR (discounted vs. 12x monthly).")


class SubscriptionPlansResponse(BaseModel):
    plans: list[SubscriptionPlanResponse] = Field(..., description="All available subscription tiers.")


class SubscriptionCreateRequest(BaseModel):
    """Start an owner's platform subscription — kitchCU's SaaS revenue model (zero per-order food commission)."""

    plan_tier: Literal["starter", "growth", "pro"] = Field(..., description="Subscription tier to start.")
    billing_cycle: Literal["monthly", "yearly"] = Field(default="monthly", description="Billing cadence.")


class SubscriptionResponse(BaseModel):
    """An owner's platform subscription — starts in `trial` status until activated."""

    id: uuid.UUID = Field(..., description="Subscription ID.")
    owner_id: uuid.UUID = Field(..., description="Owner this subscription belongs to.")
    plan_tier: str = Field(..., description="Subscription tier.", examples=["starter", "growth", "pro"])
    billing_cycle: str = Field(..., description="Billing cadence.", examples=["monthly", "yearly"])
    amount: float = Field(..., description="Charge amount for the current billing cycle, in INR.")
    status: str = Field(..., description="Lifecycle status.", examples=["trial", "active", "past_due", "cancelled"])
    razorpay_subscription_id: str | None = Field(default=None, description="Razorpay subscription reference (dev-mocked).")
    current_period_end: datetime | None = Field(default=None, description="End of the current active billing period.")
    created_at: datetime = Field(..., description="Subscription creation timestamp.")

    model_config = {"from_attributes": True}


class RazorpayWebhookPayload(BaseModel):
    """Inbound Razorpay webhook envelope. Only `payment.captured` is currently handled; others are acknowledged and ignored."""

    event: str = Field(..., description="Razorpay event type.", examples=["payment.captured"])
    payload: dict = Field(default_factory=dict, description="Razorpay event payload (entity data).")


def _mock_razorpay_order_id(payment_id: uuid.UUID) -> str:
    return f"order_dev_{payment_id.hex[:16]}"


def _build_upi_uri(kitchen_code: str, amount: float, order_code: str) -> str:
    vpa = f"{kitchen_code.lower()}@kitchCU"
    params = (
        f"pa={quote(vpa)}"
        f"&pn={quote('kitchCU Kitchen')}"
        f"&am={amount:.2f}"
        f"&cu=INR"
        f"&tn={quote(f'Order {order_code}')}"
    )
    return f"upi://pay?{params}"


async def _get_kitchen_code(session: AsyncSession, kitchen_id: uuid.UUID) -> str:
    result = await session.execute(
        text("SELECT code FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
        {"kid": kitchen_id},
    )
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("Kitchen not found")
    return code


def payment_to_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        master_order_id=payment.master_order_id,
        kitchen_id=payment.kitchen_id,
        amount=float(payment.amount),
        currency=payment.currency,
        method=payment.method,
        status=payment.status,
        razorpay_order_id=payment.razorpay_order_id,
        razorpay_payment_id=payment.razorpay_payment_id,
        created_at=payment.created_at,
    )


def subscription_to_response(sub: OwnerSubscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        owner_id=sub.owner_id,
        plan_tier=sub.plan_tier,
        billing_cycle=sub.billing_cycle,
        amount=float(sub.amount),
        status=sub.status,
        razorpay_subscription_id=sub.razorpay_subscription_id,
        current_period_end=sub.current_period_end,
        created_at=sub.created_at,
    )


def settlement_to_response(settlement: Settlement) -> SettlementResponse:
    return SettlementResponse(
        id=settlement.id,
        master_order_id=settlement.master_order_id,
        payment_id=settlement.payment_id,
        kitchen_id=settlement.kitchen_id,
        order_id=settlement.order_id,
        gross_amount=float(settlement.gross_amount),
        delivery_fee_amount=float(settlement.delivery_fee_amount),
        platform_fee=float(settlement.platform_fee),
        net_to_owner=float(settlement.net_to_owner),
        razorpay_transfer_id=settlement.razorpay_transfer_id,
        settlement_status=settlement.settlement_status,
        settled_at=settlement.settled_at,
    )


async def _get_kitchen_linked_account(session: AsyncSession, kitchen_id: uuid.UUID) -> str:
    """Prefer kitchen_payment_gateways, then kitchens.settings; `acc_dev_*` only in non-prod."""
    result = await session.execute(
        text(
            """
            SELECT
                (
                    SELECT NULLIF(g.linked_account_id, '')
                    FROM ckac_billing.kitchen_payment_gateways g
                    WHERE g.kitchen_id = k.id
                      AND g.provider = 'razorpay'
                      AND g.is_active = true
                    LIMIT 1
                ) AS gateway_linked,
                NULLIF(k.settings->>'razorpay_linked_account_id', '') AS settings_linked,
                k.code AS code
            FROM ckac_identity.kitchens k
            WHERE k.id = :kid
            LIMIT 1
            """
        ),
        {"kid": kitchen_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise ValueError("Kitchen not found")
    linked = row["gateway_linked"] or row["settings_linked"]
    if linked:
        return linked
    if is_non_production():
        return f"acc_dev_{str(row['code']).lower()}"
    raise ValueError(
        "Kitchen has no Razorpay linked account — configure Payment Gateway before split settlement"
    )


async def load_master_order_for_customer(
    session: AsyncSession,
    master_order_id: uuid.UUID,
    customer_phone: str,
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT id, master_order_code, payment_method, total, customer_phone
            FROM ckac_orders.master_orders
            WHERE id = :mid
            LIMIT 1
            """
        ),
        {"mid": master_order_id},
    )
    row = result.mappings().one_or_none()
    if not row or row["customer_phone"] != customer_phone:
        raise ValueError("Master order not found")
    return dict(row)


async def _load_master_sub_orders(
    session: AsyncSession,
    master_order_id: uuid.UUID,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, kitchen_id, order_code, subtotal, delivery_fee, total
            FROM ckac_orders.orders
            WHERE master_order_id = :mid
            ORDER BY created_at, id
            """
        ),
        {"mid": master_order_id},
    )
    rows = result.mappings().all()
    if len(rows) < 2:
        raise ValueError("Master order must have at least two sub-orders")
    return [dict(row) for row in rows]


async def create_master_payment(
    session: AsyncSession,
    master_order: dict,
    method: str,
    publisher: EventPublisher | None,
) -> Payment:
    if master_order["payment_method"] == "cod":
        raise ValueError("COD master orders do not require online payment")
    if master_order["payment_method"] not in ("online", "upi"):
        raise ValueError("Unsupported master order payment method")

    existing = await session.execute(
        select(Payment).where(
            Payment.master_order_id == master_order["id"],
            Payment.method == method,
            Payment.status.in_(("created", "pending", "authorized", "captured")),
        )
    )
    found = existing.scalar_one_or_none()
    if found:
        return found

    payment = Payment(
        master_order_id=master_order["id"],
        order_id=None,
        kitchen_id=None,
        owner_id=None,
        amount=float(master_order["total"]),
        method=method,
        status="created",
    )
    session.add(payment)
    await session.flush()
    require_dev_payment_mocks("Master payment create")
    payment.razorpay_order_id = _mock_razorpay_order_id(payment.id)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="payment.created",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            producer="billing-service",
            payload={
                "payment_id": str(payment.id),
                "master_order_id": str(master_order["id"]),
                "amount": float(payment.amount),
                "method": method,
                "provider_mode": "dev_mock",
            },
        )
        await publisher.publish(stream_key("billing", "payment"), event, session=session)

    return payment


async def capture_master_payment(
    session: AsyncSession,
    payment: Payment,
    publisher: EventPublisher | None,
) -> tuple[Payment, list[Settlement]]:
    if not payment.master_order_id:
        raise ValueError("Not a master order payment")
    if payment.status == "captured":
        existing = await session.execute(
            select(Settlement).where(Settlement.payment_id == payment.id)
        )
        return payment, list(existing.scalars().all())
    if payment.status not in ("created", "pending", "authorized"):
        raise ValueError(f"Cannot capture payment in status {payment.status}")

    sub_orders = await _load_master_sub_orders(session, payment.master_order_id)
    settlements: list[Settlement] = []
    transfer_payloads: list[dict] = []

    for order in sub_orders:
        linked_account = await _get_kitchen_linked_account(session, order["kitchen_id"])
        platform_fee = 0.0
        gross = float(order["total"])
        net = gross - platform_fee
        settlement = Settlement(
            master_order_id=payment.master_order_id,
            payment_id=payment.id,
            kitchen_id=order["kitchen_id"],
            order_id=order["id"],
            gross_amount=gross,
            delivery_fee_amount=float(order["delivery_fee"]),
            platform_fee=platform_fee,
            net_to_owner=net,
            settlement_status="pending",
        )
        session.add(settlement)
        await session.flush()
        if is_non_production():
            settlement.razorpay_transfer_id = f"trf_dev_{settlement.id.hex[:16]}"
            settlement.settlement_status = "transferred"
            settlement.settled_at = datetime.now(UTC)
        else:
            # Live Route transfers require a provider integration — keep pending.
            settlement.settlement_status = "pending"
        settlements.append(settlement)
        transfer_payloads.append(
            {
                "settlement_id": str(settlement.id),
                "kitchen_id": str(order["kitchen_id"]),
                "order_id": str(order["id"]),
                "linked_account": linked_account,
                "amount": net,
                "transfer_id": settlement.razorpay_transfer_id,
            }
        )

    if is_dev_provider_id(payment.razorpay_payment_id):
        require_dev_payment_mocks("Master payment capture")
        payment.razorpay_payment_id = payment.razorpay_payment_id or f"pay_dev_{payment.id.hex[:16]}"
    payment.status = "captured"
    payment.updated_at = datetime.now(UTC)
    await session.flush()

    if publisher:
        captured = EventPublisher.build(
            event_type="payment.captured",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            producer="billing-service",
            payload={
                "payment_id": str(payment.id),
                "master_order_id": str(payment.master_order_id),
                "amount": float(payment.amount),
                "method": payment.method,
            },
        )
        await publisher.publish(stream_key("billing", "payment"), captured, session=session)

        split_event = EventPublisher.build(
            event_type="payment.split.completed",
            aggregate_type="settlement",
            aggregate_id=str(payment.master_order_id),
            producer="billing-service",
            payload={
                "payment_id": str(payment.id),
                "master_order_id": str(payment.master_order_id),
                "transfers": transfer_payloads,
            },
        )
        await publisher.publish(stream_key("billing", "settlement"), split_event, session=session)

    return payment, settlements


async def get_payment_for_customer_master(
    session: AsyncSession,
    payment_id: uuid.UUID,
    customer_phone: str,
) -> Payment:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment or not payment.master_order_id:
        raise ValueError("Payment not found")
    await load_master_order_for_customer(session, payment.master_order_id, customer_phone)
    return payment


async def create_payment(
    session: AsyncSession,
    owner_id: uuid.UUID | None,
    order: dict,
    method: str,
    publisher: EventPublisher | None,
) -> Payment:
    if order["payment_method"] == "cod":
        raise ValueError("COD orders do not require online payment")

    existing = await session.execute(
        select(Payment).where(
            Payment.order_id == order["id"],
            Payment.method == method,
            Payment.status.in_(("created", "pending", "authorized", "captured")),
        )
    )
    found = existing.scalar_one_or_none()
    if found:
        return found

    payment = Payment(
        order_id=order["id"],
        kitchen_id=order["kitchen_id"],
        owner_id=owner_id,
        amount=float(order["total"]),
        method=method,
        status="created",
    )
    session.add(payment)
    await session.flush()
    require_dev_payment_mocks("Payment create")
    payment.razorpay_order_id = _mock_razorpay_order_id(payment.id)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="payment.created",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            producer="billing-service",
            payload={
                "payment_id": str(payment.id),
                "order_id": str(order["id"]),
                "kitchen_id": str(order["kitchen_id"]),
                "amount": float(payment.amount),
                "method": method,
                "provider_mode": "dev_mock",
            },
        )
        await publisher.publish(stream_key("billing", "payment"), event, session=session)

    return payment


async def create_upi_intent(
    session: AsyncSession,
    owner_id: uuid.UUID | None,
    order: dict,
    publisher: EventPublisher | None,
) -> tuple[Payment, str]:
    payment = await create_payment(session, owner_id, order, "upi", publisher)
    payment.status = "pending"
    payment.updated_at = datetime.now(UTC)
    await session.flush()
    kitchen_code = await _get_kitchen_code(session, order["kitchen_id"])
    upi_uri = _build_upi_uri(kitchen_code, float(payment.amount), order["order_code"])
    return payment, upi_uri


async def capture_payment(
    session: AsyncSession,
    payment: Payment,
    publisher: EventPublisher | None,
) -> Payment:
    if payment.status == "captured":
        return payment
    if payment.status not in ("created", "pending", "authorized"):
        raise ValueError(f"Cannot capture payment in status {payment.status}")

    if is_dev_provider_id(payment.razorpay_payment_id):
        require_dev_payment_mocks("Payment capture")
        payment.razorpay_payment_id = payment.razorpay_payment_id or f"pay_dev_{payment.id.hex[:16]}"
    payment.status = "captured"
    payment.updated_at = datetime.now(UTC)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="payment.captured",
            aggregate_type="payment",
            aggregate_id=str(payment.id),
            producer="billing-service",
            payload={
                "payment_id": str(payment.id),
                "order_id": str(payment.order_id) if payment.order_id else None,
                "kitchen_id": str(payment.kitchen_id) if payment.kitchen_id else None,
                "amount": float(payment.amount),
                "method": payment.method,
            },
        )
        await publisher.publish(stream_key("billing", "payment"), event, session=session)

    return payment


async def get_payment_for_owner(
    session: AsyncSession,
    payment_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Payment:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment or payment.owner_id != owner_id:
        raise ValueError("Payment not found")
    return payment


async def get_payment_for_customer(
    session: AsyncSession,
    payment_id: uuid.UUID,
    customer_phone: str,
) -> Payment:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment or not payment.order_id:
        raise ValueError("Payment not found")
    order_check = await session.execute(
        text(
            "SELECT 1 FROM ckac_orders.orders WHERE id = :oid AND customer_phone = :phone LIMIT 1"
        ),
        {"oid": payment.order_id, "phone": customer_phone},
    )
    if order_check.scalar_one_or_none() is None:
        raise ValueError("Payment not found")
    return payment


def list_subscription_plans() -> SubscriptionPlansResponse:
    return SubscriptionPlansResponse(
        plans=[
            SubscriptionPlanResponse(
                tier=tier,
                monthly_amount=amounts["monthly"],
                yearly_amount=amounts["yearly"],
            )
            for tier, amounts in SUBSCRIPTION_PLANS.items()
        ]
    )


async def create_owner_subscription(
    session: AsyncSession,
    owner_id: uuid.UUID,
    data: SubscriptionCreateRequest,
    publisher: EventPublisher | None,
) -> OwnerSubscription:
    require_dev_payment_mocks("Subscription create")
    amount = SUBSCRIPTION_PLANS[data.plan_tier][data.billing_cycle]
    sub = OwnerSubscription(
        owner_id=owner_id,
        plan_tier=data.plan_tier,
        billing_cycle=data.billing_cycle,
        amount=amount,
        status="trial",
        razorpay_subscription_id=f"sub_dev_{uuid.uuid4().hex[:16]}",
    )
    session.add(sub)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="subscription.created",
            aggregate_type="subscription",
            aggregate_id=str(sub.id),
            producer="billing-service",
            payload={
                "subscription_id": str(sub.id),
                "owner_id": str(owner_id),
                "plan_tier": data.plan_tier,
                "billing_cycle": data.billing_cycle,
                "amount": amount,
            },
        )
        await publisher.publish(stream_key("billing", "subscription"), event, session=session)

    return sub


async def activate_subscription(
    session: AsyncSession,
    sub: OwnerSubscription,
    publisher: EventPublisher | None,
) -> OwnerSubscription:
    if sub.status == "active":
        return sub

    if is_dev_provider_id(sub.razorpay_subscription_id):
        require_dev_payment_mocks("Subscription activate")

    days = BILLING_CYCLE_DAYS[sub.billing_cycle]
    sub.status = "active"
    sub.current_period_end = datetime.now(UTC) + timedelta(days=days)
    sub.updated_at = datetime.now(UTC)
    await session.flush()

    from app.identity_client import sync_owner_subscription

    await sync_owner_subscription(
        sub.owner_id,
        plan_tier=sub.plan_tier,
        subscription_expires_at=sub.current_period_end,
    )

    if publisher:
        event = EventPublisher.build(
            event_type="subscription.activated",
            aggregate_type="subscription",
            aggregate_id=str(sub.id),
            producer="billing-service",
            payload={
                "subscription_id": str(sub.id),
                "owner_id": str(sub.owner_id),
                "plan_tier": sub.plan_tier,
                "current_period_end": sub.current_period_end.isoformat(),
            },
        )
        await publisher.publish(stream_key("billing", "subscription"), event, session=session)

    return sub


async def get_current_subscription(
    session: AsyncSession,
    owner_id: uuid.UUID,
) -> OwnerSubscription | None:
    result = await session.execute(
        select(OwnerSubscription)
        .where(OwnerSubscription.owner_id == owner_id)
        .order_by(OwnerSubscription.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
