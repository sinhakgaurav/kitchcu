"""Owner-configurable per-kitchen payment gateway credentials."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KitchenPaymentGateway
from ckac_common.event_bus import EventPublisher
from ckac_common.secret_box import decrypt_secret, encrypt_secret, mask_secret

PROVIDER = "razorpay"


class PaymentGatewayResponse(BaseModel):
    kitchen_id: uuid.UUID
    provider: str
    key_id: str | None
    key_secret_configured: bool
    key_secret_masked: str | None
    webhook_secret_configured: bool
    webhook_secret_masked: str | None
    linked_account_id: str | None
    is_active: bool
    updated_at: datetime | None


class PaymentGatewayUpsertRequest(BaseModel):
    key_id: str | None = Field(default=None, max_length=128)
    key_secret: str | None = Field(default=None, max_length=4000)
    webhook_secret: str | None = Field(default=None, max_length=4000)
    linked_account_id: str | None = Field(default=None, max_length=128)
    is_active: bool = True
    clear_key_secret: bool = False
    clear_webhook_secret: bool = False


def _to_response(row: KitchenPaymentGateway) -> PaymentGatewayResponse:
    secret = decrypt_secret(row.key_secret_enc)
    webhook = decrypt_secret(row.webhook_secret_enc)
    return PaymentGatewayResponse(
        kitchen_id=row.kitchen_id,
        provider=row.provider,
        key_id=row.key_id,
        key_secret_configured=bool(secret),
        key_secret_masked=mask_secret(secret),
        webhook_secret_configured=bool(webhook),
        webhook_secret_masked=mask_secret(webhook),
        linked_account_id=row.linked_account_id,
        is_active=row.is_active,
        updated_at=row.updated_at,
    )


async def get_kitchen_payment_gateway(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> PaymentGatewayResponse:
    row = (
        await session.execute(
            select(KitchenPaymentGateway).where(
                KitchenPaymentGateway.kitchen_id == kitchen_id,
                KitchenPaymentGateway.provider == PROVIDER,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return PaymentGatewayResponse(
            kitchen_id=kitchen_id,
            provider=PROVIDER,
            key_id=None,
            key_secret_configured=False,
            key_secret_masked=None,
            webhook_secret_configured=False,
            webhook_secret_masked=None,
            linked_account_id=None,
            is_active=True,
            updated_at=None,
        )
    return _to_response(row)


async def upsert_kitchen_payment_gateway(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    body: PaymentGatewayUpsertRequest,
) -> PaymentGatewayResponse:
    row = (
        await session.execute(
            select(KitchenPaymentGateway).where(
                KitchenPaymentGateway.kitchen_id == kitchen_id,
                KitchenPaymentGateway.provider == PROVIDER,
            )
        )
    ).scalar_one_or_none()
    if not row:
        row = KitchenPaymentGateway(kitchen_id=kitchen_id, provider=PROVIDER)
        session.add(row)

    if body.key_id is not None:
        row.key_id = body.key_id.strip() or None
    if body.linked_account_id is not None:
        row.linked_account_id = body.linked_account_id.strip() or None
    row.is_active = body.is_active

    if body.clear_key_secret:
        row.key_secret_enc = None
    elif body.key_secret is not None and body.key_secret.strip():
        row.key_secret_enc = encrypt_secret(body.key_secret.strip())

    if body.clear_webhook_secret:
        row.webhook_secret_enc = None
    elif body.webhook_secret is not None and body.webhook_secret.strip():
        row.webhook_secret_enc = encrypt_secret(body.webhook_secret.strip())

    if not row.key_id and not row.key_secret_enc and not row.linked_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least a Razorpay key id, secret, or linked account id",
        )

    row.updated_at = datetime.now(UTC)
    await session.flush()

    event = EventPublisher.build(
        event_type="kitchen_payment_gateway.updated",
        aggregate_type="kitchen_payment_gateway",
        aggregate_id=str(kitchen_id),
        producer="billing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "provider": PROVIDER,
            "key_id_set": bool(row.key_id),
            "secret_set": bool(row.key_secret_enc),
            "is_active": row.is_active,
        },
    )
    await publisher.publish("ckac:billing:payment", event, session=session)
    return _to_response(row)


async def delete_kitchen_payment_gateway(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
) -> PaymentGatewayResponse:
    """Remove kitchen Razorpay credentials (owner disconnect / admin clear)."""
    row = (
        await session.execute(
            select(KitchenPaymentGateway).where(
                KitchenPaymentGateway.kitchen_id == kitchen_id,
                KitchenPaymentGateway.provider == PROVIDER,
            )
        )
    ).scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.flush()
        event = EventPublisher.build(
            event_type="kitchen_payment_gateway.cleared",
            aggregate_type="kitchen_payment_gateway",
            aggregate_id=str(kitchen_id),
            producer="billing-service",
            payload={"kitchen_id": str(kitchen_id), "provider": PROVIDER},
        )
        await publisher.publish("ckac:billing:payment", event, session=session)
    return await get_kitchen_payment_gateway(session, kitchen_id)
