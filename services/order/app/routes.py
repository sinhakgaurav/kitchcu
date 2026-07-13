import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import analytics
from app.notify_client import dispatch_order_placed, dispatch_order_status_changed
from app.catalog_client import deduct_order_stock
from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    get_order_for_customer,
    get_order_for_owner,
    load_customer_profile,
    verify_internal_key,
    verify_kitchen_active,
    verify_kitchen_owner,
)
from app.schemas import (
    CustomerOrderCreateRequest,
    ManualOrderCreateRequest,
    MasterOrderCreateRequest,
    MasterOrderResponse,
    OrderDraftListResponse,
    OrderDraftResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderStockWarningsResponse,
    ParseMessageRequest,
    _draft_to_response,
    confirm_draft,
    create_customer_order,
    create_draft_from_message,
    create_manual_order,
    create_master_order,
    get_master_order_for_customer,
    get_order_stock_warnings,
    list_customer_orders,
    list_kitchen_drafts,
    list_kitchen_orders,
    master_order_to_response,
    order_to_response,
    repeat_customer_order,
    update_order_status,
)
from ckac_common.cache import (
    analytics_cache_key,
    get_cached_json,
    set_cached_json,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

from sqlalchemy import select

from app.models import Order, OrderItem

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


def get_redis():
    from app.main import redis_client

    return redis_client


@router.post(
    "/kitchens/{kitchen_id}/orders/manual",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def manual_order_create(
    kitchen_id: uuid.UUID,
    body: ManualOrderCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        order = await create_manual_order(session, kitchen_id, owner_id, body, publisher)
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await dispatch_order_placed(order)
    return await order_to_response(session, order)


@router.post(
    "/kitchens/{kitchen_id}/orders/customer",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_order_create(
    kitchen_id: uuid.UUID,
    body: CustomerOrderCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    await verify_kitchen_active(kitchen_id, session)
    profile = await load_customer_profile(customer_id, session)
    phone = body.customer_phone or profile.get("phone")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number required — sign in with WhatsApp OTP",
        )
    try:
        order = await create_customer_order(
            session,
            kitchen_id,
            customer_id,
            profile["name"],
            phone,
            body,
            publisher,
        )
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await dispatch_order_placed(order)
    return await order_to_response(session, order)


@router.post(
    "/customers/me/master-orders",
    response_model=MasterOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_master_order_create(
    body: MasterOrderCreateRequest,
    response: Response,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ],
) -> MasterOrderResponse:
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number required — sign in with WhatsApp OTP",
        )
    try:
        master, created = await create_master_order(
            session,
            customer_id,
            profile["name"],
            phone,
            idempotency_key,
            body,
            publisher,
        )
        await session.commit()
        await session.refresh(master)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not created:
        response.status_code = status.HTTP_200_OK
    else:
        sub_orders = (
            await session.execute(select(Order).where(Order.master_order_id == master.id))
        ).scalars().all()
        for sub_order in sub_orders:
            await dispatch_order_placed(sub_order)
    return await master_order_to_response(session, master)


@router.get(
    "/customers/me/master-orders/{master_order_id}",
    response_model=MasterOrderResponse,
)
async def customer_master_order_get(
    master_order_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MasterOrderResponse:
    master = await get_master_order_for_customer(session, master_order_id, customer_id)
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master order not found",
        )
    return await master_order_to_response(session, master)


@router.get("/customers/me/orders", response_model=OrderListResponse)
async def customer_orders_list(
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderListResponse:
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        return OrderListResponse(kitchen_id=uuid.UUID(int=0), orders=[], total=0)
    orders = await list_customer_orders(session, phone)
    enriched = [await order_to_response(session, o) for o in orders]
    kitchen_id = orders[0].kitchen_id if orders else uuid.UUID(int=0)
    return OrderListResponse(kitchen_id=kitchen_id, orders=enriched, total=len(enriched))


@router.get("/customers/me/orders/{order_id}", response_model=OrderResponse)
async def customer_order_get(
    order_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = await get_order_for_customer(order_id, phone, session)
    return await order_to_response(session, order)


@router.post(
    "/customers/me/orders/{order_id}/repeat",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def customer_order_repeat(
    order_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone required")
    order = await get_order_for_customer(order_id, phone, session)
    try:
        new_order = await repeat_customer_order(session, order, customer_id, publisher)
        await session.commit()
        await session.refresh(new_order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await dispatch_order_placed(new_order)
    return await order_to_response(session, new_order)


@router.get("/kitchens/{kitchen_id}/orders", response_model=OrderListResponse)
async def orders_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    source: Annotated[str | None, Query()] = None,
) -> OrderListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    orders = await list_kitchen_orders(session, kitchen_id, status=status_filter, source=source)
    enriched = [await order_to_response(session, o) for o in orders]
    return OrderListResponse(kitchen_id=kitchen_id, orders=enriched, total=len(enriched))


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def order_get(
    order_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    return await order_to_response(session, order)


@router.get("/orders/{order_id}/stock-warnings", response_model=OrderStockWarningsResponse)
async def order_stock_warnings(
    order_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderStockWarningsResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    return await get_order_stock_warnings(session, order)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def order_status_update(
    order_id: uuid.UUID,
    body: OrderStatusUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    previous_status = order.status
    try:
        order = await update_order_status(session, order, owner_id, body, publisher)
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await dispatch_order_status_changed(order, previous_status)
    if body.status == "accepted" and previous_status != "accepted":
        rows = (await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
        items = [{"dish_id": str(i.dish_id), "quantity": i.quantity} for i in rows]
        if items:
            try:
                await deduct_order_stock(order.kitchen_id, order.id, items)
            except Exception:
                pass
    return await order_to_response(session, order)


@router.post(
    "/kitchens/{kitchen_id}/orders/parse-message",
    response_model=OrderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def parse_message(
    kitchen_id: uuid.UUID,
    body: ParseMessageRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderDraftResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    draft = await create_draft_from_message(session, kitchen_id, body, publisher)
    await session.commit()
    await session.refresh(draft)
    return _draft_to_response(draft)


@router.get("/kitchens/{kitchen_id}/orders/drafts", response_model=OrderDraftListResponse)
async def drafts_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderDraftListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    drafts = await list_kitchen_drafts(session, kitchen_id)
    return OrderDraftListResponse(
        kitchen_id=kitchen_id,
        drafts=[_draft_to_response(d) for d in drafts],
        total=len(drafts),
    )


@router.post(
    "/kitchens/{kitchen_id}/orders/drafts/{draft_id}/confirm",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def draft_confirm(
    kitchen_id: uuid.UUID,
    draft_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        order = await confirm_draft(session, draft_id, kitchen_id, owner_id, publisher)
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await dispatch_order_placed(order)
    return await order_to_response(session, order)


@router.get(
    "/kitchens/{kitchen_id}/analytics/summary",
    response_model=analytics.RevenueSummary,
)
async def analytics_summary(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> analytics.RevenueSummary:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    redis_client = get_redis()
    key = analytics_cache_key(kitchen_id, "summary", days)
    cached = await get_cached_json(redis_client, key)
    if cached is not None:
        return analytics.RevenueSummary(**cached)
    result = await analytics.revenue_summary(session, kitchen_id, days)
    await set_cached_json(redis_client, key, result.model_dump())
    return result


@router.get(
    "/kitchens/{kitchen_id}/analytics/revenue-timeseries",
    response_model=analytics.RevenueTimeseries,
)
async def analytics_revenue_timeseries(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> analytics.RevenueTimeseries:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await analytics.revenue_timeseries(session, kitchen_id, days)


@router.get(
    "/kitchens/{kitchen_id}/analytics/top-dishes",
    response_model=analytics.TopDishes,
)
async def analytics_top_dishes(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> analytics.TopDishes:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await analytics.top_dishes(session, kitchen_id, days, limit)


@router.get(
    "/kitchens/{kitchen_id}/analytics/peak-hours",
    response_model=analytics.PeakHours,
)
async def analytics_peak_hours(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> analytics.PeakHours:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await analytics.peak_hours(session, kitchen_id, days)


@router.get(
    "/kitchens/{kitchen_id}/analytics/customers",
    response_model=analytics.CustomerSegments,
)
async def analytics_customers(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 90,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> analytics.CustomerSegments:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await analytics.customer_segments(session, kitchen_id, days, limit)


@router.post(
    "/internal/kitchens/{kitchen_id}/orders/from-whatsapp",
    response_model=OrderDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def whatsapp_intake(
    kitchen_id: uuid.UUID,
    body: ParseMessageRequest,
    _: Annotated[None, Depends(verify_internal_key)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderDraftResponse:
    body.source = "whatsapp"
    draft = await create_draft_from_message(session, kitchen_id, body, publisher)
    await session.commit()
    await session.refresh(draft)
    return _draft_to_response(draft)
