"""Customer profile / live-photo uploads (same MinIO backend as kitchen media)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.storage import get_media_storage

MAX_IMAGE_BYTES = 10 * 1024 * 1024
PHOTO_FEATURE = "customer_profile_photos"


def sniff_image(data: bytes) -> tuple[str, str]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 10MB")
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use JPEG, PNG, or WebP")


def upload_customer_image(*, customer_id: uuid.UUID, context: str, data: bytes) -> str:
    content_type, ext = sniff_image(data)
    return get_media_storage().upload(
        kitchen_id=f"customer-{customer_id}",
        context=context,
        data=data,
        content_type=content_type,
        extension=ext,
    )


def parse_captured_at(raw: str | None) -> datetime:
    if not raw or not str(raw).strip():
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="captured_at must be ISO-8601",
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


async def publish_customer_photo_updated(
    publisher: EventPublisher,
    session: AsyncSession,
    customer: Customer,
    *,
    photo_kind: str,
) -> None:
    event = EventPublisher.build(
        event_type="customer.updated",
        aggregate_type="customer",
        aggregate_id=str(customer.id),
        producer="identity-service",
        payload={
            "customer_id": str(customer.id),
            "photo_kind": photo_kind,
            "has_avatar": bool(customer.avatar_url),
            "has_live_photo": bool(customer.live_photo_url),
        },
    )
    await publisher.publish(stream_key("identity", "customer"), event, session=session)
