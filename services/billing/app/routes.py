import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    load_customer_phone,
    load_order_for_customer,
    load_order_for_owner,
    verify_kitchen_owner,
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
from app.gst import (
    GstAuditResponse,
    GstBalanceSheetResponse,
    GstMonthlyReportResponse,
    GstProfileResponse,
    GstProfileUpsertRequest,
    GstSyncResponse,
    close_monthly_audit,
    get_gst_profile,
    get_monthly_audit,
    get_monthly_gst_report,
    profile_to_response,
    invoice_to_response,
    sync_gst_invoices,
    upsert_gst_profile,
    build_balance_sheet,
)
from app.refunds import (
    RefundCreateRequest,
    RefundResponse,
    apply_gateway_refund_webhook,
    attach_refund_evidence,
    complete_direct_refund,
    create_refund,
    get_refund_for_owner,
    list_refunds_for_owner,
    process_gateway_refund,
    refund_to_response,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors
from ckac_common.platform_config import (
    get_platform_secret,
    is_non_production,
    require_feature,
    verify_razorpay_webhook_signature,
)
from ckac_common.storage import get_media_storage

router = APIRouter()


def _http_from_domain(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail.startswith("Feature '") and detail.endswith("' is disabled"):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

from app.payment_gateway import (
    PaymentGatewayResponse,
    PaymentGatewayUpsertRequest,
    get_kitchen_payment_gateway,
    upsert_kitchen_payment_gateway,
)

TAG_PAYMENTS = "Payments"
TAG_CUSTOMER_PAYMENTS = "Customer Payments"
TAG_SETTLEMENTS = "Settlements"
TAG_SUBSCRIPTIONS = "Subscriptions"
TAG_PAYMENT_GATEWAY = "Payment Gateway"
TAG_GST = "GST"
TAG_REFUNDS = "Refunds"
TAG_WEBHOOKS = "Webhooks"

_REFUND_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/billing/kitchens/{kitchen_id}/payment-gateway",
    response_model=PaymentGatewayResponse,
    tags=[TAG_PAYMENT_GATEWAY],
    summary="Get kitchen payment gateway config",
    description=(
        "Owner-only — Razorpay key id / secret / webhook / Route linked account for this kitchen. "
        "Secrets are never returned in full (masked + configured flags only)."
    ),
    responses=auth_errors(),
)
async def payment_gateway_get(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentGatewayResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_kitchen_payment_gateway(session, kitchen_id)


@router.put(
    "/billing/kitchens/{kitchen_id}/payment-gateway",
    response_model=PaymentGatewayResponse,
    tags=[TAG_PAYMENT_GATEWAY],
    summary="Upsert kitchen payment gateway config",
    description=(
        "Owner-only — save Razorpay credentials for kitchen checkout / Route splits. "
        "Omit key_secret / webhook_secret to keep existing secrets. Publishes "
        "`kitchen_payment_gateway.updated`."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
async def payment_gateway_upsert(
    kitchen_id: uuid.UUID,
    body: PaymentGatewayUpsertRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentGatewayResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await upsert_kitchen_payment_gateway(session, publisher, kitchen_id, body)


@router.get(
    "/billing/subscriptions/plans",
    response_model=SubscriptionPlansResponse,
    tags=[TAG_SUBSCRIPTIONS],
    summary="List subscription plans",
    description=(
        "Public — the platform's subscription tiers (starter/growth/pro). kitchCU is an owner "
        "**subscription SaaS**: this is the platform's only revenue source — there is **zero "
        "per-order food commission**."
    ),
)
async def subscription_plans() -> SubscriptionPlansResponse:
    return list_subscription_plans()


@router.get(
    "/billing/subscriptions/me",
    response_model=SubscriptionResponse,
    tags=[TAG_SUBSCRIPTIONS],
    summary="Get my subscription",
    description="Owner-only — the caller's current (most recent) platform subscription.",
    responses={**auth_errors(), 404: RESP_404},
)
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
    tags=[TAG_SUBSCRIPTIONS],
    summary="Start a subscription",
    description=(
        "Owner-only — start a platform SaaS subscription (starter/growth/pro, monthly or yearly). "
        "Created in `trial` status; call the activate endpoint (or await the Razorpay subscription "
        "webhook in production) to move to `active`. Publishes `subscription.created`."
    ),
    responses=auth_errors(),
)
async def subscription_create(
    body: SubscriptionCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> SubscriptionResponse:
    sub = await create_owner_subscription(session, owner_id, body, publisher)
    return subscription_to_response(sub)


@router.post(
    "/billing/subscriptions/{subscription_id}/activate",
    response_model=SubscriptionResponse,
    tags=[TAG_SUBSCRIPTIONS],
    summary="Activate a subscription",
    description=(
        "Owner-only — activate the caller's own trial/past-due subscription, extending "
        "`current_period_end` by the plan's billing cycle and syncing the owner's tier. "
        "Publishes `subscription.activated`."
    ),
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
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
    tags=[TAG_PAYMENTS],
    summary="Create a payment (owner)",
    description=(
        "Owner-only — create a payment for an order the caller owns. COD orders are rejected (400); "
        "idempotent per order+method (returns the existing in-flight payment if one exists). "
        "Publishes `payment.created`. This is a pass-through charge to the kitchen — kitchCU takes "
        "**zero per-order food commission**."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
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
    tags=[TAG_PAYMENTS],
    summary="Create a UPI intent (owner)",
    description=(
        "Owner-only — create a payment in `pending` status and return a `upi://pay` deep link/QR "
        "payload for the customer to complete via their UPI app."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
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


@router.get(
    "/billing/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=[TAG_PAYMENTS],
    summary="Get a payment (owner)",
    description="Owner-only — fetch a payment the caller owns.",
    responses={**auth_errors(), 404: RESP_404},
)
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


@router.post(
    "/billing/payments/{payment_id}/capture",
    response_model=PaymentResponse,
    tags=[TAG_PAYMENTS],
    summary="Capture a payment (owner)",
    description=(
        "Owner-only — mark a payment as `captured` (dev-mocked Razorpay capture; in production this "
        "is normally driven by the Razorpay webhook instead). Idempotent — returns the payment "
        "unchanged if already captured. Publishes `payment.captured`."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
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
    tags=[TAG_CUSTOMER_PAYMENTS],
    summary="Create a payment (customer)",
    description=(
        "Customer-only (JWT `type: customer`) — create a payment for the caller's own single-kitchen "
        "order. COD orders are rejected (400); idempotent per order+method."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
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
    tags=[TAG_CUSTOMER_PAYMENTS],
    summary="Create a UPI intent (customer)",
    description="Customer-only — create a payment and return a `upi://pay` deep link for the caller's own order.",
    responses={**auth_errors(include_404=True), 400: RESP_400},
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


@router.post(
    "/billing/payments/customer/{payment_id}/capture",
    response_model=PaymentResponse,
    tags=[TAG_CUSTOMER_PAYMENTS],
    summary="Capture a payment (customer)",
    description=(
        "Customer-only — mark the caller's own single-order payment as `captured` (dev-mocked). "
        "Publishes `payment.captured`."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
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
    tags=[TAG_CUSTOMER_PAYMENTS, TAG_SETTLEMENTS],
    summary="Create an aggregated payment for a multi-kitchen cart",
    description=(
        "Customer-only — create a single aggregated payment for a multi-kitchen master order (F44 "
        "split payment). Requires at least two sub-orders; COD master orders are rejected (400). "
        "Capture this payment to trigger the per-kitchen Razorpay Route split (see settlements below)."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
async def customer_master_payment_create(
    body: MasterPaymentCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PaymentResponse:
    phone = await load_customer_phone(customer_id, session)
    try:
        await require_feature(session, "multi_kitchen_checkout")
        master = await load_master_order_for_customer(session, body.master_order_id, phone)
        payment = await create_master_payment(session, master, body.method, publisher)
    except ValueError as exc:
        raise _http_from_domain(exc) from exc
    return payment_to_response(payment)


@router.post(
    "/billing/payments/customer/master/{payment_id}/capture",
    response_model=MasterPaymentCaptureResponse,
    tags=[TAG_CUSTOMER_PAYMENTS, TAG_SETTLEMENTS],
    summary="Capture an aggregated payment and split settlements",
    description=(
        "Customer-only — capture the aggregated master payment, splitting the charge into one "
        "settlement per kitchen via Razorpay Route (`net_to_owner` per sub-order, `platform_fee` "
        "always 0 — zero per-order food commission). Publishes `payment.captured` and "
        "`payment.split.completed`."
    ),
    responses={**auth_errors(), 400: RESP_400},
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


@router.get(
    "/billing/refunds/customer/me",
    response_model=list[RefundResponse],
    tags=[TAG_REFUNDS],
    summary="List my refunds (customer)",
    description="Customer-only — refunds tied to the caller's phone or customer_id.",
    responses=auth_errors(),
)
async def customer_refunds_list(
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RefundResponse]:
    from sqlalchemy import select, text

    from app.models import Refund

    try:
        phone = await load_customer_phone(customer_id, session)
    except HTTPException:
        phone = None

    result = await session.execute(
        text(
            """
            SELECT r.id
            FROM ckac_billing.refunds r
            LEFT JOIN ckac_orders.orders o ON o.id = r.order_id
            WHERE r.customer_id = :cid
               OR (:phone IS NOT NULL AND o.customer_phone = :phone)
            ORDER BY r.created_at DESC
            LIMIT 100
            """
        ),
        {"cid": customer_id, "phone": phone},
    )
    ids = [row[0] for row in result.all()]
    if not ids:
        return []
    refunds = await session.execute(
        select(Refund).where(Refund.id.in_(ids)).order_by(Refund.created_at.desc())
    )
    return [refund_to_response(r) for r in refunds.scalars().all()]


@router.post(
    "/billing/refunds",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_REFUNDS],
    summary="Create a refund (owner)",
    description=(
        "Owner-only — create a per-order refund. `kind=full|partial` is the refund switch. "
        "Full refunds may use `channel=gateway` (Razorpay reverse) or `direct_transfer` (UPI/bank). "
        "Partial refunds always use direct transfer with `transfer_remark` = order code. "
        "Publishes `refund.created`."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
)
async def refund_create(
    body: RefundCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> RefundResponse:
    order = await load_order_for_owner(body.order_id, owner_id, session)
    try:
        refund = await create_refund(
            session, owner_id=owner_id, order=order, body=body, publisher=publisher
        )
    except ValueError as exc:
        raise _http_from_domain(exc) from exc
    return refund_to_response(refund)


@router.get(
    "/billing/refunds",
    response_model=list[RefundResponse],
    tags=[TAG_REFUNDS],
    summary="List refunds (owner)",
    description="Owner-only — list refunds, optionally filtered by order_id.",
    responses=auth_errors(),
)
async def refund_list(
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    order_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[RefundResponse]:
    refunds = await list_refunds_for_owner(session, owner_id, order_id)
    return [refund_to_response(r) for r in refunds]


@router.get(
    "/billing/refunds/{refund_id}",
    response_model=RefundResponse,
    tags=[TAG_REFUNDS],
    summary="Get a refund (owner)",
    responses={**auth_errors(), 404: RESP_404},
)
async def refund_get(
    refund_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefundResponse:
    try:
        refund = await get_refund_for_owner(session, refund_id, owner_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return refund_to_response(refund)


@router.post(
    "/billing/refunds/{refund_id}/process",
    response_model=RefundResponse,
    tags=[TAG_REFUNDS],
    summary="Process gateway refund (owner)",
    description=(
        "Owner-only — execute a full gateway refund (dev-mocked Razorpay Refunds API). "
        "Marks payment `refunded` and publishes `refund.completed`."
    ),
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def refund_process_gateway(
    refund_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> RefundResponse:
    try:
        refund = await get_refund_for_owner(session, refund_id, owner_id)
        refund = await process_gateway_refund(session, refund, publisher)
    except ValueError as exc:
        detail = str(exc)
        code = status.HTTP_404_NOT_FOUND if detail == "Refund not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail) from exc
    return refund_to_response(refund)


@router.post(
    "/billing/refunds/{refund_id}/evidence",
    response_model=RefundResponse,
    tags=[TAG_REFUNDS],
    summary="Attach refund screenshot (owner)",
    description="Owner-only — upload proof of a direct UPI/bank refund (required before complete).",
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def refund_attach_evidence(
    refund_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> RefundResponse:
    try:
        refund = await get_refund_for_owner(session, refund_id, owner_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 10MB")

    content_type = file.content_type or ""
    if data.startswith(b"\xff\xd8\xff"):
        content_type, ext = "image/jpeg", "jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type, ext = "image/png", "png"
    elif len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        content_type, ext = "image/webp", "webp"
    elif content_type in _REFUND_IMAGE_TYPES:
        ext = _REFUND_IMAGE_TYPES[content_type]
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use JPEG, PNG, or WebP")

    url = get_media_storage().upload(
        kitchen_id=str(refund.kitchen_id),
        context="refund_evidence",
        data=data,
        content_type=content_type,
        extension=ext,
    )
    try:
        refund = await attach_refund_evidence(session, refund, url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return refund_to_response(refund)


@router.post(
    "/billing/refunds/{refund_id}/complete",
    response_model=RefundResponse,
    tags=[TAG_REFUNDS],
    summary="Complete direct refund (owner)",
    description=(
        "Owner-only — mark a direct UPI/bank refund complete after transferring funds "
        "(remark already set to order id). Requires uploaded evidence screenshot."
    ),
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def refund_complete_direct(
    refund_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> RefundResponse:
    try:
        refund = await get_refund_for_owner(session, refund_id, owner_id)
        refund = await complete_direct_refund(session, refund, publisher)
    except ValueError as exc:
        detail = str(exc)
        code = status.HTTP_404_NOT_FOUND if detail == "Refund not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail) from exc
    return refund_to_response(refund)


@router.post(
    "/webhooks/razorpay",
    tags=[TAG_WEBHOOKS],
    summary="Razorpay payment webhook",
    description=(
        "Razorpay callback. Verifies `X-Razorpay-Signature` when a webhook secret is configured "
        "(platform Control key or `RAZORPAY_WEBHOOK_SECRET`). Handles `payment.captured` "
        "(single + master split), `refund.processed`, and `payment.refunded`."
    ),
    responses={400: RESP_400, 401: {"description": "Invalid signature"}, 404: RESP_404},
)
async def razorpay_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> dict[str, str]:
    raw = await request.body()
    secret = await get_platform_secret(session, "razorpay_webhook_secret")
    if secret:
        signature = request.headers.get("X-Razorpay-Signature")
        if not verify_razorpay_webhook_signature(raw, signature, secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Razorpay webhook signature",
            )
    elif not is_non_production():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay webhook secret not configured",
        )

    try:
        body = RazorpayWebhookPayload.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload"
        ) from exc

    if body.event in ("refund.processed", "payment.refunded"):
        entity = body.payload.get("refund", {}).get("entity") or body.payload.get("payment", {}).get(
            "entity", {}
        )
        refund_id = entity.get("id") if body.event == "refund.processed" else entity.get("refund_id")
        payment_id = entity.get("payment_id")
        if body.event == "payment.refunded":
            payment_id = entity.get("id")
            refund_id = entity.get("refund_id") or refund_id
        if not payment_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payment_id")
        refund = await apply_gateway_refund_webhook(
            session,
            razorpay_refund_id=refund_id or f"rfnd_wh_{payment_id[-16:]}",
            razorpay_payment_id=payment_id,
            publisher=publisher,
        )
        if not refund:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
        return {"status": "ok"}

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
    if payment.master_order_id:
        await capture_master_payment(session, payment, publisher)
    else:
        await capture_payment(session, payment, publisher)
    return {"status": "ok"}


@router.get(
    "/kitchens/{kitchen_id}/gst/profile",
    response_model=GstProfileResponse,
    tags=[TAG_GST],
    summary="Get GST profile",
    description="Owner-only — the kitchen's GST registration profile, if one has been set up.",
    responses={**auth_errors(include_403=True), 404: RESP_404},
)
async def gst_profile_get(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GstProfileResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    profile = await get_gst_profile(session, kitchen_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GST profile not found")
    return profile_to_response(profile)


@router.put(
    "/kitchens/{kitchen_id}/gst/profile",
    response_model=GstProfileResponse,
    tags=[TAG_GST],
    summary="Create or update GST profile",
    description=(
        "Owner-only — register or update the kitchen's GST profile (GSTIN, legal name, address, tax "
        "rate). Required before invoice sync or reports; publishes `gst.profile.created`/`gst.profile.updated`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_profile_upsert(
    kitchen_id: uuid.UUID,
    body: GstProfileUpsertRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> GstProfileResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        profile = await upsert_gst_profile(session, kitchen_id, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return profile_to_response(profile)


@router.post(
    "/kitchens/{kitchen_id}/gst/sync",
    response_model=GstSyncResponse,
    tags=[TAG_GST],
    summary="Sync delivered orders into GST invoices",
    description=(
        "Owner-only — generate tax invoices for delivered orders that don't yet have one. Part of the "
        "**GST monthly close flow**: sync → review the monthly report → close the audit. Optionally "
        "scope to a single year/month; omit both to sync all outstanding delivered orders. Requires an "
        "active GST profile (400 otherwise). Publishes `gst.invoice.created` per invoice."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_sync_invoices(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    year: Annotated[int | None, Query(description="Restrict sync to this year (requires month).")] = None,
    month: Annotated[int | None, Query(description="Restrict sync to this month, 1-12 (requires year).")] = None,
) -> GstSyncResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        invoices = await sync_gst_invoices(
            session,
            kitchen_id,
            publisher,
            year=year,
            month=month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return GstSyncResponse(
        synced_count=len(invoices),
        invoices=[invoice_to_response(i) for i in invoices],
    )


@router.get(
    "/kitchens/{kitchen_id}/gst/reports/monthly",
    response_model=GstMonthlyReportResponse,
    tags=[TAG_GST],
    summary="Get the monthly GST report",
    description=(
        "Owner-only — invoice totals for a filing period (step 2 of the **GST monthly close flow**: "
        "sync → review this report → close the audit). Refreshes running totals if the audit is still open."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_monthly_report(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    year: Annotated[int, Query(description="Report year.", examples=[2026])],
    month: Annotated[int, Query(description="Report month, 1-12.", examples=[7])],
) -> GstMonthlyReportResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
    try:
        report = await get_monthly_gst_report(session, kitchen_id, year, month)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return report


@router.get(
    "/kitchens/{kitchen_id}/gst/reports/balance-sheet",
    response_model=GstBalanceSheetResponse,
    tags=[TAG_GST],
    summary="Get the monthly balance sheet",
    description=(
        "Owner-only — simplified balance sheet for a period (cash/settlements as assets, GST payable "
        "as liability, retained earnings as equity). Returns the frozen snapshot if the audit for that "
        "period is already closed, otherwise a live-computed sheet."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_balance_sheet(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    year: Annotated[int, Query(description="Period year.")],
    month: Annotated[int, Query(description="Period month, 1-12.")],
) -> GstBalanceSheetResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
    profile = await get_gst_profile(session, kitchen_id)
    if not profile or not profile.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GST profile not active")
    audit = await get_monthly_audit(session, kitchen_id, year, month)
    if audit.balance_sheet:
        return audit.balance_sheet
    sheet = await build_balance_sheet(
        session,
        kitchen_id,
        year,
        month,
        gst_payable=audit.total_tax,
        gross_sales=audit.total_gross_sales,
    )
    return sheet


@router.get(
    "/kitchens/{kitchen_id}/gst/audit",
    response_model=GstAuditResponse,
    tags=[TAG_GST],
    summary="Get the monthly audit",
    description=(
        "Owner-only — the monthly GST audit record (running totals + balance sheet) for a period. "
        "Open audits refresh their totals on read; closed audits are immutable."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_audit_get(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    year: Annotated[int, Query(description="Period year.")],
    month: Annotated[int, Query(description="Period month, 1-12.")],
) -> GstAuditResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
    try:
        audit = await get_monthly_audit(session, kitchen_id, year, month)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return audit


@router.post(
    "/kitchens/{kitchen_id}/gst/audit/close",
    response_model=GstAuditResponse,
    tags=[TAG_GST],
    summary="Close the monthly audit",
    description=(
        "Owner-only — final step of the **GST monthly close flow**: freezes the period's totals and "
        "balance sheet snapshot, marking the audit `closed` (immutable thereafter). Rejects if already "
        "closed (400). Publishes `gst.audit.closed`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def gst_audit_close(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    year: Annotated[int, Query(description="Period year to close.")],
    month: Annotated[int, Query(description="Period month to close, 1-12.")],
) -> GstAuditResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    if month < 1 or month > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
    try:
        audit = await close_monthly_audit(session, kitchen_id, owner_id, year, month, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return audit
