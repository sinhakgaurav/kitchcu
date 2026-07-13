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

router = APIRouter(
    prefix="/internal/kitchens/{kitchen_id}/stock",
    dependencies=[Depends(verify_internal_key)],
)


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post("/low-stock-check", response_model=LowStockCheckResponse)
async def internal_low_stock_check(
    kitchen_id: uuid.UUID,
    body: LowStockCheckRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LowStockCheckResponse:
    return await check_low_stock_for_order(session, kitchen_id, body)


@router.post("/deduct-order", response_model=StockDeductResponse)
async def internal_deduct_order_stock(
    kitchen_id: uuid.UUID,
    body: StockDeductRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> StockDeductResponse:
    result = await deduct_stock_for_order(session, kitchen_id, body, publisher)
    return result
