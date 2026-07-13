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

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/kitchens/{kitchen_id}/crm/customers",
    response_model=KitchenCustomerListResponse,
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


@router.get("/kitchens/{kitchen_id}/coupons", response_model=CouponListResponse)
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


@router.patch("/kitchens/{kitchen_id}/coupons/{coupon_id}", response_model=CouponResponse)
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


@router.post("/marketing/coupons/validate", response_model=CouponValidateResponse)
async def coupons_validate(
    body: CouponValidateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CouponValidateResponse:
    _ = customer_id
    return await validate_coupon(session, body)


@router.get("/kitchens/{kitchen_id}/promotions", response_model=PromotionListResponse)
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
