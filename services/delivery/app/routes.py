from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    DeliveryQuoteRequest,
    DeliveryQuoteResponse,
    TrackingResponse,
    quote_delivery,
    track_by_token,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_404, RESP_422

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post(
    "/delivery/quote",
    response_model=DeliveryQuoteResponse,
    tags=["Delivery"],
    summary="Quote the delivery fee for a kitchen + customer location",
    description=(
        "**Auth:** None — public endpoint, called during cart/checkout before an order is "
        "placed (and again server-side during order creation to validate the fee).\n\n"
        "**Body:** `DeliveryQuoteRequest` — `kitchen_id`, customer `latitude`/`longitude`, and "
        "the cart `subtotal` (needed to evaluate minimum-order-for-free-delivery).\n\n"
        "**Fee rules (in order):**\n"
        "1. Beyond the kitchen's `max_delivery_radius_km` -> `status=\"out_of_range\"`, fee `0` "
        "(kitchen does not deliver this far).\n"
        "2. Within `free_delivery_radius_km` -> fee `0`.\n"
        "3. Beyond the free radius -> `delivery_fee_flat_beyond + ceil(distance_km - "
        "free_delivery_radius_km) * delivery_fee_per_km`.\n"
        "4. If `subtotal >= min_order_for_free_delivery` (when configured), any fee from step 3 "
        "is waived to `0`.\n\n"
        "**Behavior:** Computes distance via PostGIS geography distance, persists the quote for "
        "audit, and emits `delivery.fee_quoted`.\n\n"
        "**Response:** `DeliveryQuoteResponse` with the fee and a `breakdown` explaining which "
        "rule applied."
    ),
    responses={404: RESP_404, 422: RESP_422},
)
async def delivery_quote(
    body: DeliveryQuoteRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DeliveryQuoteResponse:
    try:
        result = await quote_delivery(session, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return result


@router.get(
    "/delivery/track/{token}",
    response_model=TrackingResponse,
    tags=["Delivery"],
    summary="Look up live order status by public tracking token (F29)",
    description=(
        "**Auth:** None — the opaque `tracking_token` itself is the credential. No JWT/API key "
        "required, so this link can be shared with anyone following the delivery (e.g. via "
        "WhatsApp) without asking them to log in.\n\n"
        "**Behavior:** Only orders with `delivery_type=\"delivery\"` receive a tracking token "
        "(issued at order-creation time); pickup orders have none. The token is unique and "
        "reveals only the minimal fields needed to follow the delivery — never other orders or "
        "kitchen-internal data.\n\n"
        "**Response:** `TrackingResponse` — current status, ETA, distance, and delivery fee."
    ),
    responses={404: RESP_404, 422: RESP_422},
)
async def delivery_track(
    token: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrackingResponse:
    try:
        return await track_by_token(session, token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
