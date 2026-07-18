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
from app.receipts import (
    bill_pdf_filename,
    build_master_receipt,
    build_order_receipt,
    render_master_bill_pdf,
    render_order_bill_pdf,
)
from app.schemas import (
    CustomerOrderCreateRequest,
    DeliveryFulfillmentRequest,
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
    list_kitchen_drafts,
    list_kitchen_orders,
    list_customer_orders,
    master_order_to_response,
    order_to_response,
    repeat_customer_order,
    set_delivery_fulfillment,
    update_order_status,
)
from app.customer_dashboard import CustomerDashboardResponse, build_customer_dashboard
from ckac_common.cache import (
    analytics_cache_key,
    get_cached_json,
    set_cached_json,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import (
    RESP_400,
    RESP_403,
    RESP_422,
    auth_errors,
)

from sqlalchemy import select, text

from app.models import Order, OrderItem

router = APIRouter()

TAG_OWNER_ORDERS = "Owner Orders"
TAG_CUSTOMER_CHECKOUT = "Customer Checkout"
TAG_MASTER_ORDERS = "Master Orders"
TAG_ANALYTICS = "Analytics"
TAG_BILLS = "Bills"


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
    tags=[TAG_OWNER_ORDERS],
    summary="Create a manual order (owner-entered walk-in/phone order)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Body:** `ManualOrderCreateRequest` — dish line items, delivery type, payment method, "
        "and optional customer contact/location.\n\n"
        "**Behavior:** Resolves each dish against the live catalog (rejecting inactive/unknown "
        "dishes), computes `subtotal` from current prices, and — for delivery orders with "
        "customer coordinates — recomputes and validates the delivery fee against the kitchen's "
        "radius rules. Creates the order in `received` status, emits `order.placed`, and (for "
        "delivery orders) issues a public tracking token via `delivery.tracking_created`.\n\n"
        "**Response:** `201` with the created `OrderResponse` (`total = subtotal + delivery_fee`)."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
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
        order, created = await create_manual_order(session, kitchen_id, owner_id, body, publisher)
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if created:
        await dispatch_order_placed(order)
    return await order_to_response(session, order)


@router.post(
    "/kitchens/{kitchen_id}/orders/customer",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_CUSTOMER_CHECKOUT],
    summary="Place a single-kitchen checkout order",
    description=(
        "**Auth:** Customer JWT (Bearer, `type: customer`).\n\n"
        "**Headers:** `Idempotency-Key` (optional, 8-128 chars) — replaying the same key for the "
        "same kitchen returns the previously created order with `200 OK` instead of creating a "
        "duplicate; a new (or omitted) key creates a fresh order with `201 Created`.\n\n"
        "**Body:** `CustomerOrderCreateRequest` — cart line items, delivery type, payment "
        "method, and optional delivery location/fee acknowledgement.\n\n"
        "**Behavior:** Verifies the kitchen is active, resolves the customer's phone from their "
        "profile (or the request), then creates the order exactly like a manual order but tagged "
        "`source=\"customer_pwa\"`. Emits `order.placed` and, for delivery, `delivery.tracking_created`.\n\n"
        "**Response:** `201` with the created `OrderResponse` (or `200` on idempotent replay)."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
)
async def customer_order_create(
    kitchen_id: uuid.UUID,
    body: CustomerOrderCreateRequest,
    response: Response,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
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
        order, created = await create_customer_order(
            session,
            kitchen_id,
            customer_id,
            profile["name"],
            phone,
            body,
            publisher,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if created:
        await dispatch_order_placed(order)
    else:
        response.status_code = status.HTTP_200_OK
    return await order_to_response(session, order)


@router.post(
    "/customers/me/master-orders",
    response_model=MasterOrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_MASTER_ORDERS],
    summary="Place a multi-kitchen checkout (grouped sub-orders, single payment)",
    description=(
        "**Auth:** Customer JWT (Bearer).\n\n"
        "**Headers:** `Idempotency-Key` (required, 8-128 chars) — replaying the same key for "
        "the same customer returns the previously created master order with `200 OK` instead of "
        "creating a duplicate; a new key creates a fresh master order with `201 Created`.\n\n"
        "**Body:** `MasterOrderCreateRequest` — 2-10 distinct-kitchen groups, one payment method "
        "for the whole checkout.\n\n"
        "**Behavior:** Validates every kitchen is active, creates one sub-`Order` per group "
        "(each independently trackable through the order status machine), links them via "
        "`master_order_id`, and sums subtotal/delivery_fee/total across all sub-orders. Emits "
        "`master_order.created` plus `order.placed` per sub-order.\n\n"
        "**Response:** `MasterOrderResponse` with all sub-orders nested under `orders`."
    ),
    responses={**auth_errors(), 400: RESP_400},
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
    from ckac_common.platform_config import require_feature

    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number required — sign in with WhatsApp OTP",
        )
    try:
        await require_feature(session, "multi_kitchen_checkout")
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
        detail = str(exc)
        code = (
            status.HTTP_403_FORBIDDEN
            if detail.startswith("Feature '") and detail.endswith("' is disabled")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=detail) from exc
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
    tags=[TAG_MASTER_ORDERS],
    summary="Get a multi-kitchen master order (with all sub-orders)",
    description=(
        "**Auth:** Customer JWT (Bearer) — only the customer who placed the master order can "
        "read it.\n\n"
        "**Response:** `MasterOrderResponse` with each sub-order's live status, items, and "
        "status history nested under `orders`."
    ),
    responses={**auth_errors(include_404=True)},
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


@router.get(
    "/customers/me/master-orders/{master_order_id}/bill.pdf",
    tags=[TAG_BILLS],
    summary="Download the consolidated PDF receipt for a master order",
    description=(
        "**Auth:** Customer JWT (Bearer) — only the owning customer can download the receipt.\n\n"
        "**Response:** `200` with `application/pdf` body (`Content-Disposition: attachment`), "
        "a single master receipt covering every kitchen's sub-order and the aggregated total."
    ),
    responses={**auth_errors(include_404=True)},
)
async def customer_master_order_bill_pdf(
    master_order_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    master = await get_master_order_for_customer(session, master_order_id, customer_id)
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master order not found",
        )
    receipt = await build_master_receipt(session, master)
    pdf_bytes = render_master_bill_pdf(receipt)
    filename = bill_pdf_filename(receipt.master_order_code)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/customers/me/dashboard",
    response_model=CustomerDashboardResponse,
    tags=[TAG_CUSTOMER_CHECKOUT],
    summary="Customer dashboard aggregate",
    description=(
        "Orders enriched with cuisine/diet/live media, savings vs restaurant benchmarks, "
        "health comparison scores, and wellness tips. Supports filters: diet, cuisine, live_media_only."
    ),
    responses=auth_errors(),
)
async def customer_dashboard(
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    diet: Annotated[str | None, Query()] = None,
    cuisine: Annotated[str | None, Query()] = None,
    live_media_only: Annotated[bool, Query()] = False,
) -> CustomerDashboardResponse:
    from ckac_common.platform_config import (
        feature_http_status,
        is_feature_enabled,
        require_feature,
    )

    try:
        await require_feature(session, "customer_dashboard")
    except ValueError as exc:
        code = feature_http_status(exc) or status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    include_savings_health = await is_feature_enabled(session, "customer_savings_health")
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        dash = await build_customer_dashboard(session, "")
    else:
        dash = await build_customer_dashboard(
            session,
            phone,
            diet=diet,
            cuisine=cuisine,
            live_media_only=live_media_only,
        )
    if not include_savings_health:
        from app.customer_dashboard import HealthSummary, SavingsSummary

        dash = dash.model_copy(
            update={
                "savings": SavingsSummary(
                    total_saved=0,
                    restaurant_equivalent_spend=0,
                    kitchcu_spend=0,
                    by_dish=[],
                ),
                "health": HealthSummary(
                    veg_share_pct=0,
                    non_veg_share_pct=0,
                    vegan_share_pct=0,
                    home_freshness_score=0,
                    restaurant_processed_score=0,
                    note="Savings and health insights are currently unavailable.",
                ),
                "tips": [],
            }
        )
    return dash


@router.get(
    "/customers/me/orders",
    response_model=OrderListResponse,
    tags=[TAG_CUSTOMER_CHECKOUT],
    summary="List the signed-in customer's order history",
    description=(
        "**Auth:** Customer JWT (Bearer).\n\n"
        "**Behavior:** Looks up orders by the customer's registered phone number across all "
        "kitchens (F33 order history), newest first. Returns an empty list (not an error) if the "
        "profile has no phone on file.\n\n"
        "**Response:** `OrderListResponse`."
    ),
    responses=auth_errors(),
)
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


@router.get(
    "/customers/me/orders/{order_id}",
    response_model=OrderResponse,
    tags=[TAG_CUSTOMER_CHECKOUT],
    summary="Get one of the signed-in customer's own orders",
    description=(
        "**Auth:** Customer JWT (Bearer) — the order must belong to the same phone number as "
        "the caller's profile, else `404` (never reveals another customer's order).\n\n"
        "**Response:** `OrderResponse` with items and status history."
    ),
    responses={**auth_errors(include_404=True)},
)
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


@router.get(
    "/customers/me/orders/{order_id}/bill.pdf",
    tags=[TAG_BILLS],
    summary="Download the PDF receipt for one of the customer's own orders",
    description=(
        "**Auth:** Customer JWT (Bearer) — order must belong to the caller's phone number.\n\n"
        "**Response:** `200` with `application/pdf` body (`Content-Disposition: attachment`)."
    ),
    responses={**auth_errors(include_404=True)},
)
async def customer_order_bill_pdf(
    order_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    profile = await load_customer_profile(customer_id, session)
    phone = profile.get("phone")
    if not phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = await get_order_for_customer(order_id, phone, session)
    receipt = await build_order_receipt(session, order)
    pdf_bytes = render_order_bill_pdf(receipt)
    filename = bill_pdf_filename(receipt.order_code)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/customers/me/orders/{order_id}/repeat",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_CUSTOMER_CHECKOUT],
    summary="Repeat a past order (F33) as a new checkout",
    description=(
        "**Auth:** Customer JWT (Bearer) — source order must belong to the caller's phone "
        "number.\n\n"
        "**Behavior:** Copies the source order's line items, delivery type, and payment method "
        "into a brand-new order against the same kitchen (current prices and delivery-fee rules "
        "apply — this is not a price-locked replay). Emits `order.placed`.\n\n"
        "**Response:** `201` with the newly created `OrderResponse`."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
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


@router.get(
    "/kitchens/{kitchen_id}/orders",
    response_model=OrderListResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="List a kitchen's orders (owner dashboard)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** optional `status` (any status in the order lifecycle) and `source` "
        "(`manual`, `customer_pwa`, `customer_pwa_multi`, `whatsapp`, `manual_message`) filters.\n\n"
        "**Response:** `OrderListResponse`, newest first."
    ),
    responses=auth_errors(include_403=True),
)
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


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="Get a single order (owner view)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own the order's kitchen.\n\n"
        "**Response:** `OrderResponse` with items and full status-change history."
    ),
    responses=auth_errors(include_403=True, include_404=True),
)
async def order_get(
    order_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    return await order_to_response(session, order)


@router.get(
    "/orders/{order_id}/bill.pdf",
    tags=[TAG_BILLS],
    summary="Download the PDF receipt for an order (owner view)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own the order's kitchen.\n\n"
        "**Response:** `200` with `application/pdf` body (`Content-Disposition: attachment`)."
    ),
    responses=auth_errors(include_403=True, include_404=True),
)
async def order_bill_pdf(
    order_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    order = await get_order_for_owner(order_id, owner_id, session)
    receipt = await build_order_receipt(session, order)
    pdf_bytes = render_order_bill_pdf(receipt)
    filename = bill_pdf_filename(receipt.order_code)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/orders/{order_id}/stock-warnings",
    response_model=OrderStockWarningsResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="Check ingredient stock shortfall for an order (F19)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own the order's kitchen.\n\n"
        "**Behavior:** Projects this order's dishes against the ingredient balance mapper "
        "(catalog service). Best-effort — returns an empty, non-shortfall result rather than "
        "erroring if the catalog service is unreachable.\n\n"
        "**Response:** `OrderStockWarningsResponse`."
    ),
    responses=auth_errors(include_403=True, include_404=True),
)
async def order_stock_warnings(
    order_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrderStockWarningsResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    return await get_order_stock_warnings(session, order)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="Advance or cancel an order's status",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own the order's kitchen.\n\n"
        "**Body:** `OrderStatusUpdateRequest` — target `status` (must be a valid forward "
        "transition per the status machine, or `cancelled` from any non-terminal state) plus an "
        "optional `note` and a `cancel_reason` required when cancelling.\n\n"
        "**Behavior:** Rejects invalid transitions (`400`). Records the transition in the "
        "status-event audit trail, emits `order.status.changed`, dispatches a WhatsApp "
        "notification, and — on first transition into `accepted` — best-effort deducts recipe "
        "ingredients from stock (never blocks the status change if that call fails).\n\n"
        "**Response:** Updated `OrderResponse`."
    ),
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
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
        import logging

        rows = (await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
        items = [{"dish_id": str(i.dish_id), "quantity": i.quantity} for i in rows]
        if items:
            try:
                await deduct_order_stock(order.kitchen_id, order.id, items)
            except Exception:
                logging.getLogger("order.stock").exception(
                    "Stock deduct failed after accept order_id=%s kitchen_id=%s",
                    order.id,
                    order.kitchen_id,
                )
        # Book Porter only after kitchen accepts (avoid paying for cancelled carts).
        if (
            order.delivery_type == "delivery"
            and getattr(order, "delivery_mode", None) == "platform"
            and not getattr(order, "courier_job_id", None)
        ):
            try:
                from app.porter_client import quote_and_book_porter

                booked = await quote_and_book_porter(session, order)
                if booked:
                    order.courier_partner = "porter"
                    order.courier_job_id = booked.get("job_id")
                    if booked.get("fee") is not None:
                        # Keep customer fee locked at checkout; refresh owner logistics cost if Porter differs.
                        from app.cost_share import split_delivery_cost

                        kitchen_row = (
                            await session.execute(
                                text(
                                    """
                                    SELECT
                                        max_delivery_radius_km,
                                        min_order_for_free_delivery,
                                        COALESCE(delivery_subsidy_percent, 50) AS delivery_subsidy_percent
                                    FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1
                                    """
                                ),
                                {"kid": order.kitchen_id},
                            )
                        ).mappings().one_or_none()
                        if kitchen_row and order.distance_km is not None:
                            in_range = float(order.distance_km) <= float(
                                kitchen_row["max_delivery_radius_km"]
                            )
                            min_order = (
                                float(kitchen_row["min_order_for_free_delivery"])
                                if kitchen_row["min_order_for_free_delivery"] is not None
                                else None
                            )
                            share = split_delivery_cost(
                                gross_fee=float(booked["fee"]),
                                in_range=in_range,
                                subtotal=float(order.subtotal or 0),
                                min_order_for_subsidy=min_order,
                                subsidy_percent=float(kitchen_row["delivery_subsidy_percent"] or 50),
                            )
                            # Never raise customer fee after accept; absorb delta on kitchen.
                            order.owner_delivery_cost = max(
                                float(share["owner_fee"]),
                                float(booked["fee"]) - float(order.delivery_fee or 0),
                            )
                            order.delivery_payer = share["payer"]
                    await session.commit()
                    await session.refresh(order)
            except Exception:
                logging.getLogger("order.porter").exception(
                    "Porter book failed after accept order_id=%s",
                    order.id,
                )
    return await order_to_response(session, order)


@router.patch(
    "/orders/{order_id}/delivery-fulfillment",
    response_model=OrderResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="Choose self delivery or platform courier",
    description=(
        "In range: owner pays platform logistics (customer fee 0). "
        "Out of range: customer pays (self fee or platform quote)."
    ),
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
async def order_delivery_fulfillment(
    order_id: uuid.UUID,
    body: DeliveryFulfillmentRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderResponse:
    order = await get_order_for_owner(order_id, owner_id, session)
    try:
        order = await set_delivery_fulfillment(session, order, body, publisher)
        await session.commit()
        await session.refresh(order)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await order_to_response(session, order)


@router.post(
    "/kitchens/{kitchen_id}/orders/parse-message",
    response_model=OrderDraftResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_OWNER_ORDERS],
    summary="Parse a free-text message into a draft order for owner review",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Body:** `ParseMessageRequest` — raw message text (e.g. a manually pasted WhatsApp "
        "order), `source`, and optional customer phone.\n\n"
        "**Behavior:** Matches each line against the kitchen's active menu; unmatched lines and "
        "free-text notes are kept separately for the owner to resolve. Creates an "
        "`OrderDraft` (`status=\"draft\"`) and emits `order.draft.created` — no `Order` row is "
        "created until the owner confirms via the confirm endpoint.\n\n"
        "**Response:** `201` with the `OrderDraftResponse`."
    ),
    responses=auth_errors(include_403=True),
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


@router.get(
    "/kitchens/{kitchen_id}/orders/drafts",
    response_model=OrderDraftListResponse,
    tags=[TAG_OWNER_ORDERS],
    summary="List pending (unconfirmed) order drafts for a kitchen",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Response:** `OrderDraftListResponse` — drafts with `status=\"draft\"` only, newest first."
    ),
    responses=auth_errors(include_403=True),
)
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
    tags=[TAG_OWNER_ORDERS],
    summary="Confirm a draft — convert matched items into a real order",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Behavior:** Requires the draft to exist, belong to this kitchen, still be in "
        "`status=\"draft\"`, and have at least one matched item (`400` otherwise). Creates a "
        "manual order (`source` inherited from the draft) from the matched items, marks the "
        "draft `confirmed`, and links it to the new order. Emits `order.placed`.\n\n"
        "**Response:** `201` with the created `OrderResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
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
    tags=[TAG_ANALYTICS],
    summary="Revenue and order summary (F07)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` — trailing window in days (1-365, default 30).\n\n"
        "**Behavior:** Gross revenue, average order value, cancellation rate, and repeat-customer "
        "rate over the window. Cached in Redis for 1-6h per `kitchen_id` + window (tenant-scoped "
        "key), invalidated on order events.\n\n"
        "**Response:** `RevenueSummary`."
    ),
    responses=auth_errors(include_403=True),
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
    tags=[TAG_ANALYTICS],
    summary="Daily revenue timeseries (F07)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` — trailing window in days (1-365, default 30).\n\n"
        "**Response:** `RevenueTimeseries` — one revenue/order-count point per day, in the "
        "kitchen's local (Asia/Kolkata) day boundaries."
    ),
    responses=auth_errors(include_403=True),
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
    tags=[TAG_ANALYTICS],
    summary="Best-selling dishes by quantity/revenue (F08)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` (1-365, default 30), `limit` (1-50, default 10).\n\n"
        "**Response:** `TopDishes` — dishes ranked by quantity sold within the window."
    ),
    responses=auth_errors(include_403=True),
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
    tags=[TAG_ANALYTICS],
    summary="Busiest hours of day by order volume (F08)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` — trailing window in days (1-365, default 30).\n\n"
        "**Response:** `PeakHours` — order counts bucketed by local (Asia/Kolkata) hour of day."
    ),
    responses=auth_errors(include_403=True),
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
    tags=[TAG_ANALYTICS],
    summary="Customer segments — repeat rate and churn risk (F07)",
    description=(
        "**Auth:** Owner JWT (Bearer) — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` — trailing window in days (1-365, default 90); `limit` — max "
        "customers listed per segment (1-50, default 10).\n\n"
        "**Response:** `CustomerSegments` — repeat customers and churn-risk customers (2+ "
        "lifetime orders, inactive 21+ days) for owner-driven CRM outreach."
    ),
    responses=auth_errors(include_403=True),
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
    tags=[TAG_OWNER_ORDERS],
    summary="[Internal] Create an order draft from an inbound WhatsApp message",
    description=(
        "**Auth:** `X-Internal-Key` header (service-to-service only — called by the "
        "notification service's WhatsApp webhook handler; never exposed to public clients "
        "through the gateway).\n\n"
        "**Body:** `ParseMessageRequest` — `source` is forced to `\"whatsapp\"` regardless of "
        "the request body.\n\n"
        "**Behavior:** Same parsing/matching as the manual parse-message endpoint, producing an "
        "`OrderDraft` for the owner to review and confirm. Emits `order.draft.created`.\n\n"
        "**Response:** `201` with the `OrderDraftResponse`."
    ),
    responses={403: RESP_403, 422: RESP_422},
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
