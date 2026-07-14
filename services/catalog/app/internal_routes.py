from typing import Annotated
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients import (
    LowStockCheckRequest,
    LowStockCheckResponse,
    StockDeductRequest,
    StockDeductResponse,
    check_low_stock_for_order,
    deduct_stock_for_order,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.internal_auth import verify_internal_key
from ckac_common.openapi import RESP_401

router = APIRouter(
    prefix="/internal/kitchens/{kitchen_id}/stock",
    dependencies=[Depends(verify_internal_key)],
)

TAG_INGREDIENTS = "Ingredients"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post(
    "/low-stock-check",
    response_model=LowStockCheckResponse,
    tags=[TAG_INGREDIENTS],
    summary="[Internal] Check ingredient availability",
    description=(
        "Internal service-to-service (X-Internal-Key) — called by the order service to project ingredient "
        "shortfalls for a set of order line items, without deducting stock."
    ),
    responses={401: RESP_401},
)
async def internal_low_stock_check(
    kitchen_id: uuid.UUID,
    body: LowStockCheckRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LowStockCheckResponse:
    return await check_low_stock_for_order(session, kitchen_id, body)


@router.post(
    "/deduct-order",
    response_model=StockDeductResponse,
    tags=[TAG_INGREDIENTS],
    summary="[Internal] Deduct stock for an order",
    description=(
        "Internal service-to-service (X-Internal-Key) — called by the order service on order acceptance "
        "to deduct ingredient stock per dish recipe, publishing `ingredient.stock.deducted` and "
        "`ingredient.low_stock` events as thresholds are crossed."
    ),
    responses={401: RESP_401},
)
async def internal_deduct_order_stock(
    kitchen_id: uuid.UUID,
    body: StockDeductRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> StockDeductResponse:
    result = await deduct_stock_for_order(session, kitchen_id, body, publisher)
    return result
