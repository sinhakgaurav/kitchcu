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

SUBSCRIPTION_PLANS: dict[str, dict[str, float]] = {
    "starter": {"monthly": 499.0, "yearly": 4990.0},
    "growth": {"monthly": 999.0, "yearly": 9990.0},
    "pro": {"monthly": 1999.0, "yearly": 19990.0},
}

BILLING_CYCLE_DAYS = {"monthly": 30, "yearly": 365}


class PaymentCreateRequest(BaseModel):
    order_id: uuid.UUID
    method: Literal["online", "upi"] = "online"


class MasterPaymentCreateRequest(BaseModel):
    master_order_id: uuid.UUID
    method: Literal["online", "upi"] = "online"


class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None
    master_order_id: uuid.UUID | None = None
    kitchen_id: uuid.UUID | None
    amount: float
    currency: str
    method: str
    status: str
    razorpay_order_id: str | None
    razorpay_payment_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SettlementResponse(BaseModel):
    id: uuid.UUID
    master_order_id: uuid.UUID
    payment_id: uuid.UUID
    kitchen_id: uuid.UUID
    order_id: uuid.UUID
    gross_amount: float
    delivery_fee_amount: float
    platform_fee: float
    net_to_owner: float
    razorpay_transfer_id: str | None
    settlement_status: str
    settled_at: datetime | None

    model_config = {"from_attributes": True}


class MasterPaymentCaptureResponse(BaseModel):
    payment: PaymentResponse
    settlements: list[SettlementResponse]


class UpiIntentRequest(BaseModel):
    order_id: uuid.UUID


class UpiIntentResponse(BaseModel):
    payment_id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    currency: str
    status: str
    upi_uri: str


class SubscriptionPlanResponse(BaseModel):
    tier: str
    monthly_amount: float
    yearly_amount: float


class SubscriptionPlansResponse(BaseModel):
    plans: list[SubscriptionPlanResponse]


class SubscriptionCreateRequest(BaseModel):
    plan_tier: Literal["starter", "growth", "pro"]
    billing_cycle: Literal["monthly", "yearly"] = "monthly"


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    plan_tier: str
    billing_cycle: str
    amount: float
    status: str
    razorpay_subscription_id: str | None
    current_period_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: dict = Field(default_factory=dict)


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
    result = await session.execute(
        text(
            """
            SELECT
                COALESCE(
                    NULLIF(settings->>'razorpay_linked_account_id', ''),
                    'acc_dev_' || lower(code)
                ) AS linked_account
            FROM ckac_identity.kitchens
            WHERE id = :kid
            LIMIT 1
            """
        ),
        {"kid": kitchen_id},
    )
    linked = result.scalar_one_or_none()
    if not linked:
        raise ValueError("Kitchen not found")
    return linked


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
        settlement.razorpay_transfer_id = f"trf_dev_{settlement.id.hex[:16]}"
        settlement.settlement_status = "transferred"
        settlement.settled_at = datetime.now(UTC)
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

    payment.status = "captured"
    payment.razorpay_payment_id = payment.razorpay_payment_id or f"pay_dev_{payment.id.hex[:16]}"
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

    payment.status = "captured"
    payment.razorpay_payment_id = payment.razorpay_payment_id or f"pay_dev_{payment.id.hex[:16]}"
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

    days = BILLING_CYCLE_DAYS[sub.billing_cycle]
    sub.status = "active"
    sub.current_period_end = datetime.now(UTC) + timedelta(days=days)
    sub.updated_at = datetime.now(UTC)
    await session.flush()

    await session.execute(
        text(
            """
            UPDATE ckac_identity.owners
            SET subscription_tier = :tier,
                subscription_status = 'active',
                subscription_expires_at = :expires
            WHERE id = :owner_id
            """
        ),
        {
            "tier": sub.plan_tier,
            "expires": sub.current_period_end,
            "owner_id": sub.owner_id,
        },
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
