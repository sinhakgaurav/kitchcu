import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    get_optional_customer_id,
    load_customer_phone,
    verify_kitchen_owner,
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
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

router = APIRouter()

TAG_CRM = "CRM"
TAG_COUPONS = "Coupons"
TAG_PROMOTIONS = "Promotions"


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
