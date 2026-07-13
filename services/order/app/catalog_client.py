"""Catalog service client — ingredient stock (F19)."""

from __future__ import annotations

import logging
import uuid

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def check_low_stock(
    kitchen_id: uuid.UUID,
    order_id: uuid.UUID,
    items: list[dict],
) -> dict:
    payload = {
        "order_id": str(order_id),
        "items": items,
    }
    return await _post(
        f"/api/v1/internal/kitchens/{kitchen_id}/stock/low-stock-check",
        payload,
    )


async def deduct_order_stock(
    kitchen_id: uuid.UUID,
    order_id: uuid.UUID,
    items: list[dict],
) -> None:
    payload = {
        "order_id": str(order_id),
        "items": items,
    }
    await _post(
        f"/api/v1/internal/kitchens/{kitchen_id}/stock/deduct-order",
        payload,
    )


async def _post(path: str, payload: dict) -> dict:
    url = f"{settings.catalog_service_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"X-Internal-Key": resolve_internal_api_key()},
        )
        response.raise_for_status()
        return response.json()
