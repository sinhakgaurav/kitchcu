import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    get_optional_customer_id,
    load_customer_phone,
    load_customer_profile,
    verify_kitchen_owner,
)
from app.models import CustomerSubscription
from app.subscriptions import (
    MODULE_KEY as TIFFIN_MODULE,
    CustomerSubscriptionResponse,
    SubscribeRequest,
    SubscriptionDecisionRequest,
    SubscriptionPlanCreate,
    SubscriptionPlanListResponse,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
    SubscriptionSummaryResponse,
    CustomerSubscriptionListResponse,
    cancel_subscription,
    create_plan,
    decide_subscription,
    get_plan_for_kitchen,
    get_subscription_for_kitchen,
    list_customer_subscriptions,
    list_kitchen_subscriptions,
    list_plans,
    plan_to_response,
    request_subscribe,
    subscription_summary,
    subscription_to_response,
    update_plan,
)
from app.schemas import (
    ActivePromotionListResponse,
    CouponCreateRequest,
    CouponListResponse,
    CouponResponse,
    CouponUpdateRequest,
    CouponValidateRequest,
    CouponValidateResponse,
    KitchenCustomerListResponse,
    KitchenCustomerResponse,
    KitchenCustomerTagsUpdate,
    PromotionCreateRequest,
    PromotionListResponse,
    PromotionResponse,
    coupon_to_response,
    create_coupon,
    create_promotion,
    list_active_promotions,
    list_coupons,
    list_kitchen_customers,
    list_promotions,
    promotion_to_response,
    update_coupon,
    update_customer_tags,
    validate_coupon,
)
from app.templates import (
    TemplateCreateRequest,
    TemplateResponse,
    TemplateSendRequest,
    TemplateSendResponse,
    TemplateUpdateRequest,
    create_template,
    delete_template,
    list_templates,
    send_template,
    update_template,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors
from ckac_common.platform_config import require_kitchen_module

router = APIRouter()

TAG_CRM = "CRM"
TAG_COUPONS = "Coupons"
TAG_PROMOTIONS = "Promotions"
TAG_TEMPLATES = "Templates"
TAG_TIFFIN = "Tiffin subscriptions"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/kitchens/{kitchen_id}/crm/customers",
    response_model=KitchenCustomerListResponse,
    tags=[TAG_CRM],
    summary="List kitchen CRM customer profiles (F37)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `refresh` (default `false`) — when `true`, re-aggregates the CRM roster from "
        "`ckac_orders.orders`/`order_items` (spend, favorite dishes, peak hours) before returning, "
        "publishing `crm.synced`, and stamping `synced_at`.\n\n"
        "**Response:** `KitchenCustomerListResponse` — profiles ranked by `total_spend` descending. "
        "This CRM data belongs to the kitchen and is never shared across kitchens."
    ),
    responses=auth_errors(include_403=True),
)
async def crm_list_customers(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    refresh: bool = Query(default=False),
) -> KitchenCustomerListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_kitchen_customers(session, kitchen_id, refresh=refresh, publisher=publisher)


@router.patch(
    "/kitchens/{kitchen_id}/crm/customers/{customer_id}",
    response_model=KitchenCustomerResponse,
    tags=[TAG_CRM],
    summary="Update an owner's CRM tags for a customer",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `KitchenCustomerTagsUpdate` — full replacement of up to 20 free-form tags "
        "(e.g. `vip`, `no-onion`), normalized to lowercase.\n\n"
        "**Response:** Updated `KitchenCustomerResponse`. 404 if the profile does not exist for "
        "this kitchen."
    ),
    responses={**auth_errors(include_403=True), 404: RESP_404},
)
async def crm_update_customer_tags(
    kitchen_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: KitchenCustomerTagsUpdate,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenCustomerResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await update_customer_tags(session, kitchen_id, customer_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return row


@router.get(
    "/kitchens/{kitchen_id}/coupons",
    response_model=CouponListResponse,
    tags=[TAG_COUPONS],
    summary="List a kitchen's coupons (F36)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `CouponListResponse` — all coupons (active and inactive) ordered newest first."
    ),
    responses=auth_errors(include_403=True),
)
async def coupons_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CouponListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_coupons(session, kitchen_id)


@router.post(
    "/kitchens/{kitchen_id}/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_COUPONS],
    summary="Create a coupon",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `CouponCreateRequest` — code, discount type (`percent`/`fixed`), value, and "
        "optional min-order / max-uses / validity window. Rejects duplicate codes for the same "
        "kitchen (400).\n\n"
        "**Response:** Created `CouponResponse`. Publishes `coupon.created`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def coupons_create(
    kitchen_id: uuid.UUID,
    body: CouponCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> CouponResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        coupon = await create_coupon(session, kitchen_id, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return coupon_to_response(coupon)


@router.patch(
    "/kitchens/{kitchen_id}/coupons/{coupon_id}",
    response_model=CouponResponse,
    tags=[TAG_COUPONS],
    summary="Activate or deactivate a coupon",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `CouponUpdateRequest` — `is_active` flag. Deactivating pauses redemptions "
        "without deleting usage history.\n\n"
        "**Response:** Updated `CouponResponse`. 404 if the coupon does not exist for this kitchen."
    ),
    responses={**auth_errors(include_403=True), 404: RESP_404},
)
async def coupons_update(
    kitchen_id: uuid.UUID,
    coupon_id: uuid.UUID,
    body: CouponUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CouponResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        coupon = await update_coupon(session, kitchen_id, coupon_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return coupon_to_response(coupon)


@router.post(
    "/marketing/coupons/validate",
    response_model=CouponValidateResponse,
    tags=[TAG_COUPONS],
    summary="Validate + price a coupon for checkout",
    description=(
        "**Auth:** Customer JWT — any authenticated customer (coupon eligibility itself does not "
        "depend on the caller's identity, only on cart subtotal and coupon state).\n\n"
        "**Body:** `CouponValidateRequest` — `kitchen_id`, `code`, cart `subtotal`.\n\n"
        "**Checks (in order):** exists → active → within validity window → under `max_uses` → "
        "`subtotal` meets `min_order_amount`.\n\n"
        "**Response:** `CouponValidateResponse` with `valid` + computed `discount_amount` (INR) "
        "and a human-readable `message` explaining the result either way."
    ),
    responses=auth_errors(),
)
async def coupons_validate(
    body: CouponValidateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CouponValidateResponse:
    _ = customer_id
    return await validate_coupon(session, body)


@router.get(
    "/kitchens/{kitchen_id}/promotions",
    response_model=PromotionListResponse,
    tags=[TAG_PROMOTIONS],
    summary="List a kitchen's promotions (F38)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `PromotionListResponse` — all promotions (past, live, and future) ordered "
        "newest first."
    ),
    responses=auth_errors(include_403=True),
)
async def promotions_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PromotionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_promotions(session, kitchen_id)


@router.post(
    "/kitchens/{kitchen_id}/promotions",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_PROMOTIONS],
    summary="Create a targeted dish promotion",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `PromotionCreateRequest` — dish, special price, target `segment` "
        "(all/repeat/vip/churn_risk/top_spenders), and a start/end window. `segment_limit` is "
        "required when `segment='top_spenders'`. Rejects a dish that does not belong to the "
        "kitchen, or an invalid time window (400).\n\n"
        "**Response:** Created `PromotionResponse`. Publishes `promotion.created`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def promotions_create(
    kitchen_id: uuid.UUID,
    body: PromotionCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PromotionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        promo = await create_promotion(session, kitchen_id, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return promotion_to_response(promo)


@router.get(
    "/kitchens/{kitchen_id}/promotions/active",
    response_model=ActivePromotionListResponse,
    tags=[TAG_PROMOTIONS],
    summary="List currently-live promotions the caller is eligible for",
    description=(
        "**Auth:** None required — public endpoint for the customer-facing menu. If an optional "
        "customer Bearer token is supplied, promotions are personalized to that customer's segment "
        "(repeat/vip/churn_risk/top_spenders); without a token, only `segment='all'` promotions "
        "are returned.\n\n"
        "**Response:** `ActivePromotionListResponse` — live promotions within their start/end "
        "window and eligible for the caller's segment, with minimal customer-facing fields "
        "(no internal targeting details)."
    ),
)
async def promotions_active(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    customer_id: Annotated[uuid.UUID | None, Depends(get_optional_customer_id)],
) -> ActivePromotionListResponse:
    phone = None
    if customer_id:
        phone = await load_customer_phone(customer_id, session)
    return await list_active_promotions(session, kitchen_id, phone)


@router.get(
    "/kitchens/{kitchen_id}/templates",
    response_model=list[TemplateResponse],
    tags=[TAG_TEMPLATES],
    summary="List WhatsApp / email marketing templates",
    responses=auth_errors(include_403=True),
)
async def templates_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    channel: str | None = Query(default=None, description="Filter: whatsapp | email"),
) -> list[TemplateResponse]:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, "marketing_broadcast")
    return await list_templates(session, kitchen_id, channel=channel)


@router.post(
    "/kitchens/{kitchen_id}/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_TEMPLATES],
    summary="Create WhatsApp or email marketing template",
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def templates_create(
    kitchen_id: uuid.UUID,
    body: TemplateCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TemplateResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, "marketing_broadcast")
    result = await create_template(session, publisher, kitchen_id, body)
    await session.commit()
    return result


@router.patch(
    "/kitchens/{kitchen_id}/templates/{template_id}",
    response_model=TemplateResponse,
    tags=[TAG_TEMPLATES],
    summary="Update marketing template",
    responses={**auth_errors(include_403=True), 400: RESP_400, 404: RESP_404},
)
async def templates_update(
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TemplateResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, "marketing_broadcast")
    result = await update_template(session, publisher, kitchen_id, template_id, body)
    await session.commit()
    return result


@router.delete(
    "/kitchens/{kitchen_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[TAG_TEMPLATES],
    summary="Delete marketing template",
    responses={**auth_errors(include_403=True), 404: RESP_404},
)
async def templates_delete(
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> None:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, "marketing_broadcast")
    await delete_template(session, publisher, kitchen_id, template_id)
    await session.commit()


@router.post(
    "/kitchens/{kitchen_id}/templates/{template_id}/send",
    response_model=TemplateSendResponse,
    tags=[TAG_TEMPLATES],
    summary="Send a marketing template to a CRM audience",
    description=(
        "Resolves CRM phones by audience (all/vip/repeat/churn_risk/phones), renders variables, "
        "publishes `message_template.send_requested`, and for WhatsApp queues notify dispatch. "
        "Use dry_run=true to preview without dispatch."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400, 404: RESP_404},
)
async def templates_send(
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
    body: TemplateSendRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TemplateSendResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, "marketing_broadcast")
    result = await send_template(session, publisher, kitchen_id, template_id, body)
    await session.commit()
    return result


# --- F34 / F35 Tiffin & monthly plans ---


@router.post(
    "/kitchens/{kitchen_id}/subscription-plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_TIFFIN],
    summary="Create a monthly thali/tiffin plan (F35)",
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def owner_create_plan(
    kitchen_id: uuid.UUID,
    body: SubscriptionPlanCreate,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    try:
        plan = await create_plan(session, kitchen_id, body, publisher)
        await session.commit()
        await session.refresh(plan)
        return await plan_to_response(session, plan)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/subscription-plans",
    response_model=SubscriptionPlanListResponse,
    tags=[TAG_TIFFIN],
    summary="List kitchen subscription plans (owner)",
    responses=auth_errors(include_403=True),
)
async def owner_list_plans(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(default=False),
) -> SubscriptionPlanListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    plans = await list_plans(session, kitchen_id, active_only=active_only)
    items = [await plan_to_response(session, p) for p in plans]
    return SubscriptionPlanListResponse(plans=items, total=len(items))


@router.patch(
    "/kitchens/{kitchen_id}/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    tags=[TAG_TIFFIN],
    summary="Update / activate / deactivate a plan",
    responses={**auth_errors(include_403=True), 400: RESP_400, 404: RESP_404},
)
async def owner_update_plan(
    kitchen_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: SubscriptionPlanUpdate,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    try:
        plan = await get_plan_for_kitchen(session, kitchen_id, plan_id)
        plan = await update_plan(session, plan, body, publisher)
        await session.commit()
        await session.refresh(plan)
        return await plan_to_response(session, plan)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/subscription-plans/public",
    response_model=SubscriptionPlanListResponse,
    tags=[TAG_TIFFIN],
    summary="Public active plans for a kitchen (customer)",
)
async def public_list_plans(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionPlanListResponse:
    plans = await list_plans(session, kitchen_id, active_only=True)
    items = [await plan_to_response(session, p) for p in plans]
    return SubscriptionPlanListResponse(plans=items, total=len(items))


@router.post(
    "/kitchens/{kitchen_id}/subscription-plans/{plan_id}/subscribe",
    response_model=CustomerSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_TIFFIN],
    summary="Customer requests monthly subscription (F34)",
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def customer_subscribe(
    kitchen_id: uuid.UUID,
    plan_id: uuid.UUID,
    body: SubscribeRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    phone, name = await load_customer_profile(customer_id, session)
    if not phone:
        raise HTTPException(status_code=400, detail="Customer profile incomplete")
    try:
        sub = await request_subscribe(
            session,
            kitchen_id,
            plan_id,
            customer_id=customer_id,
            customer_phone=phone,
            customer_name=name,
            data=body,
            publisher=publisher,
        )
        await session.commit()
        await session.refresh(sub)
        return await subscription_to_response(session, sub)
    except ValueError as exc:
        await session.rollback()
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/subscriptions",
    response_model=CustomerSubscriptionListResponse,
    tags=[TAG_TIFFIN],
    summary="List enrollments for kitchen (owner)",
    responses=auth_errors(include_403=True),
)
async def owner_list_subscriptions(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
) -> CustomerSubscriptionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    rows = await list_kitchen_subscriptions(
        session, kitchen_id, status=status_filter, limit=limit
    )
    items = [await subscription_to_response(session, s) for s in rows]
    return CustomerSubscriptionListResponse(subscriptions=items, total=len(items))


@router.get(
    "/kitchens/{kitchen_id}/subscriptions/summary",
    response_model=SubscriptionSummaryResponse,
    tags=[TAG_TIFFIN],
    summary="Subscription KPIs for reports / intelligence",
    responses=auth_errors(include_403=True),
)
async def owner_subscription_summary(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionSummaryResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    return await subscription_summary(session, kitchen_id)


async def _owner_decide(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    action: str,
    body: SubscriptionDecisionRequest,
    owner_id: uuid.UUID,
    session: AsyncSession,
    publisher: EventPublisher,
):
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    await require_kitchen_module(session, kitchen_id, TIFFIN_MODULE)
    try:
        sub = await get_subscription_for_kitchen(session, kitchen_id, sub_id)
        sub = await decide_subscription(
            session, sub, action=action, owner_id=owner_id, data=body, publisher=publisher
        )
        await session.commit()
        await session.refresh(sub)
        return await subscription_to_response(session, sub)
    except ValueError as exc:
        await session.rollback()
        code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/subscriptions/{sub_id}/accept",
    response_model=CustomerSubscriptionResponse,
    tags=[TAG_TIFFIN],
    summary="Accept a pending subscription request",
)
async def owner_accept_sub(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    body: SubscriptionDecisionRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    return await _owner_decide(kitchen_id, sub_id, "accept", body, owner_id, session, publisher)


@router.post(
    "/kitchens/{kitchen_id}/subscriptions/{sub_id}/deny",
    response_model=CustomerSubscriptionResponse,
    tags=[TAG_TIFFIN],
    summary="Deny a pending subscription request",
)
async def owner_deny_sub(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    body: SubscriptionDecisionRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    return await _owner_decide(kitchen_id, sub_id, "deny", body, owner_id, session, publisher)


@router.post(
    "/kitchens/{kitchen_id}/subscriptions/{sub_id}/activate",
    response_model=CustomerSubscriptionResponse,
    tags=[TAG_TIFFIN],
    summary="Re-activate a paused subscription",
)
async def owner_activate_sub(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    body: SubscriptionDecisionRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    return await _owner_decide(kitchen_id, sub_id, "activate", body, owner_id, session, publisher)


@router.post(
    "/kitchens/{kitchen_id}/subscriptions/{sub_id}/deactivate",
    response_model=CustomerSubscriptionResponse,
    tags=[TAG_TIFFIN],
    summary="Pause an active subscription",
)
async def owner_deactivate_sub(
    kitchen_id: uuid.UUID,
    sub_id: uuid.UUID,
    body: SubscriptionDecisionRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    return await _owner_decide(kitchen_id, sub_id, "deactivate", body, owner_id, session, publisher)


@router.get(
    "/customers/me/subscriptions",
    response_model=CustomerSubscriptionListResponse,
    tags=[TAG_TIFFIN],
    summary="List my kitchen subscriptions",
    responses=auth_errors(),
)
async def customer_list_subs(
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CustomerSubscriptionListResponse:
    rows = await list_customer_subscriptions(session, customer_id)
    items = [await subscription_to_response(session, s) for s in rows]
    return CustomerSubscriptionListResponse(subscriptions=items, total=len(items))


@router.post(
    "/customers/me/subscriptions/{sub_id}/cancel",
    response_model=CustomerSubscriptionResponse,
    tags=[TAG_TIFFIN],
    summary="Customer cancels their subscription",
    responses={**auth_errors(), 400: RESP_400, 404: RESP_404},
)
async def customer_cancel_sub(
    sub_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    sub = await session.get(CustomerSubscription, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    try:
        sub = await cancel_subscription(session, sub, customer_id=customer_id, publisher=publisher)
        await session.commit()
        await session.refresh(sub)
        return await subscription_to_response(session, sub)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
