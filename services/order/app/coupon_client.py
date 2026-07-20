"""Apply / redeem marketing coupons from order-service (read + internal redeem)."""

from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def resolve_coupon_discount(
    session: AsyncSession,
    *,
    kitchen_id: uuid.UUID,
    code: str,
    subtotal: float,
) -> tuple[str, float]:
    """Validate coupon via marketing schema (read-only) and return (code, discount)."""
    normalized = code.strip().upper()
    if not normalized:
        raise ValueError("Coupon code required")
    row = (
        await session.execute(
            text(
                """
                SELECT code, discount_type, discount_value, is_active,
                       valid_from, valid_until, max_uses, used_count, min_order_amount
                FROM ckac_marketing.coupons
                WHERE kitchen_id = :kid AND code = :code
                LIMIT 1
                """
            ),
            {"kid": kitchen_id, "code": normalized},
        )
    ).mappings().first()
    if not row:
        raise ValueError("Invalid coupon code")
    if not row["is_active"]:
        raise ValueError("Coupon is inactive")
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    if row["valid_from"] and now < row["valid_from"]:
        raise ValueError("Coupon not yet valid")
    if row["valid_until"] and now > row["valid_until"]:
        raise ValueError("Coupon expired")
    if row["max_uses"] is not None and int(row["used_count"] or 0) >= int(row["max_uses"]):
        raise ValueError("Coupon usage limit reached")
    if row["min_order_amount"] is not None and subtotal < float(row["min_order_amount"]):
        raise ValueError(f"Minimum order ₹{float(row['min_order_amount']):.0f} required")

    if row["discount_type"] == "percent":
        discount = round(subtotal * float(row["discount_value"]) / 100, 2)
    else:
        discount = round(min(float(row["discount_value"]), subtotal), 2)
    return str(row["code"]), discount


async def redeem_coupon_internal(
    *,
    kitchen_id: uuid.UUID,
    code: str,
    order_id: uuid.UUID,
) -> None:
    """Increment used_count in marketing-service (cross-service write via internal API)."""
    # Prefer env-configured URL; host-mapped default is :18006 (compose publishes marketing there).
    base = getattr(settings, "marketing_service_url", None) or "http://localhost:18006"
    if base.rstrip("/").endswith(":8006") and "localhost" in base:
        base = "http://localhost:18006"
    url = f"{base.rstrip('/')}/api/v1/internal/coupons/redeem"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json={
                    "kitchen_id": str(kitchen_id),
                    "code": code,
                    "order_id": str(order_id),
                },
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            if response.status_code >= 400:
                logger.warning(
                    "coupon redeem failed status=%s detail=%s",
                    response.status_code,
                    response.text[:200],
                )
    except Exception as exc:
        logger.warning("order→marketing coupon redeem failed: %s", exc)
