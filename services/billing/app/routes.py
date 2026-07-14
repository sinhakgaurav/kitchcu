import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

router = APIRouter()

TAG_PAYMENTS = "Payments"
TAG_CUSTOMER_PAYMENTS = "Customer Payments"
TAG_SETTLEMENTS = "Settlements"
TAG_SUBSCRIPTIONS = "Subscriptions"
TAG_GST = "GST"
TAG_WEBHOOKS = "Webhooks"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


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
        master = await load_master_order_for_customer(session, body.master_order_id, phone)
        payment = await create_master_payment(session, master, body.method, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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


@router.post(
    "/webhooks/razorpay",
    tags=[TAG_WEBHOOKS],
    summary="Razorpay payment webhook",
    description=(
        "Unauthenticated Razorpay callback endpoint. Only `payment.captured` is processed — other "
        "event types are acknowledged with `{\"status\": \"ignored\"}` and no side effects. Matches "
        "the inbound payment to a `Payment` row by `razorpay_order_id` and marks it captured, "
        "publishing `payment.captured`. **Do not rely on this in place of gateway-level webhook "
        "signature verification in production.**"
    ),
    responses={400: RESP_400, 404: RESP_404},
)
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
