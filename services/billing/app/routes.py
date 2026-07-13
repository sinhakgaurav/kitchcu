import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    load_customer_phone,
    load_order_for_customer,
    load_order_for_owner,
)
from app.schemas import (
    MasterPaymentCaptureResponse,
    MasterPaymentCreateRequest,
    PaymentCreateRequest,
    PaymentResponse,
    RazorpayWebhookPayload,
    SubscriptionCreateRequest,
    SubscriptionPlansResponse,
    SubscriptionResponse,
    UpiIntentRequest,
    UpiIntentResponse,
    activate_subscription,
    capture_master_payment,
    capture_payment,
    create_master_payment,
    create_owner_subscription,
    create_payment,
    create_upi_intent,
    get_current_subscription,
    get_payment_for_customer,
    get_payment_for_customer_master,
    get_payment_for_owner,
    list_subscription_plans,
    load_master_order_for_customer,
    payment_to_response,
    settlement_to_response,
    subscription_to_response,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get("/billing/subscriptions/plans", response_model=SubscriptionPlansResponse)
async def subscription_plans() -> SubscriptionPlansResponse:
    return list_subscription_plans()


@router.get("/billing/subscriptions/me", response_model=SubscriptionResponse)
async def subscription_me(
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionResponse:
    sub = await get_current_subscription(session, owner_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")
    return subscription_to_response(sub)


@router.post(
    "/billing/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscription_create(
    body: SubscriptionCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> SubscriptionResponse:
    sub = await create_owner_subscription(session, owner_id, body, publisher)
    return subscription_to_response(sub)


@router.post("/billing/subscriptions/{subscription_id}/activate", response_model=SubscriptionResponse)
async def subscription_activate(
    subscription_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> SubscriptionResponse:
    sub = await get_current_subscription(session, owner_id)
    if not sub or sub.id != subscription_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    try:
        sub = await activate_subscription(session, sub, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return subscription_to_response(sub)


@router.post(
    "/billing/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def payment_create(
    body: PaymentCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    order = await load_order_for_owner(body.order_id, owner_id, session)
    try:
        payment = await create_payment(session, owner_id, order, body.method, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/upi-intent",
    response_model=UpiIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def payment_upi_intent(
    body: UpiIntentRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> UpiIntentResponse:
    order = await load_order_for_owner(body.order_id, owner_id, session)
    try:
        payment, upi_uri = await create_upi_intent(session, owner_id, order, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UpiIntentResponse(
        payment_id=payment.id,
        order_id=order["id"],
        amount=float(payment.amount),
        currency=payment.currency,
        status=payment.status,
        upi_uri=upi_uri,
    )


@router.get("/billing/payments/{payment_id}", response_model=PaymentResponse)
async def payment_get(
    payment_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentResponse:
    try:
        payment = await get_payment_for_owner(session, payment_id, owner_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post("/billing/payments/{payment_id}/capture", response_model=PaymentResponse)
async def payment_capture(
    payment_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    try:
        payment = await get_payment_for_owner(session, payment_id, owner_id)
        payment = await capture_payment(session, payment, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/customer",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_payment_create(
    body: PaymentCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    phone = await load_customer_phone(customer_id, session)
    order = await load_order_for_customer(body.order_id, phone, session)
    try:
        payment = await create_payment(session, None, order, body.method, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/customer/upi-intent",
    response_model=UpiIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_payment_upi_intent(
    body: UpiIntentRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> UpiIntentResponse:
    phone = await load_customer_phone(customer_id, session)
    order = await load_order_for_customer(body.order_id, phone, session)
    try:
        payment, upi_uri = await create_upi_intent(session, None, order, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UpiIntentResponse(
        payment_id=payment.id,
        order_id=order["id"],
        amount=float(payment.amount),
        currency=payment.currency,
        status=payment.status,
        upi_uri=upi_uri,
    )


@router.post("/billing/payments/customer/{payment_id}/capture", response_model=PaymentResponse)
async def customer_payment_capture(
    payment_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    phone = await load_customer_phone(customer_id, session)
    try:
        payment = await get_payment_for_customer(session, payment_id, phone)
        payment = await capture_payment(session, payment, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/customer/master",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_master_payment_create(
    body: MasterPaymentCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    phone = await load_customer_phone(customer_id, session)
    try:
        master = await load_master_order_for_customer(session, body.master_order_id, phone)
        payment = await create_master_payment(session, master, body.method, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/customer/master/{payment_id}/capture",
    response_model=MasterPaymentCaptureResponse,
)
async def customer_master_payment_capture(
    payment_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> MasterPaymentCaptureResponse:
    phone = await load_customer_phone(customer_id, session)
    try:
        payment = await get_payment_for_customer_master(session, payment_id, phone)
        payment, settlements = await capture_master_payment(session, payment, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MasterPaymentCaptureResponse(
        payment=payment_to_response(payment),
        settlements=[settlement_to_response(s) for s in settlements],
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    body: RazorpayWebhookPayload,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> dict[str, str]:
    if body.event != "payment.captured":
        return {"status": "ignored"}

    payment_entity = body.payload.get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    if not razorpay_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing order_id")

    from sqlalchemy import select

    from app.models import Payment

    result = await session.execute(
        select(Payment).where(Payment.razorpay_order_id == razorpay_order_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    payment.razorpay_payment_id = razorpay_payment_id
    await capture_payment(session, payment, publisher)
    return {"status": "ok"}
