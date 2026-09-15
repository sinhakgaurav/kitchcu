"""Owner identity — photos + masked Aadhaar/PAN."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_media import parse_captured_at, sniff_image
from app.models import Owner
from app.schemas import OwnerResponse
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.storage import get_media_storage

KYC_FEATURE = "owner_kyc"

_AADHAAR_RE = re.compile(r"^[2-9][0-9]{11}$")
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


class OwnerKycUpdateRequest(BaseModel):
    aadhaar_number: str | None = Field(
        default=None,
        max_length=20,
        description="12-digit Aadhaar. Stored; only a masked value is returned.",
    )
    pan_number: str | None = Field(
        default=None,
        max_length=16,
        description="PAN in ABCDE1234F form. Stored; only a masked value is returned.",
    )


def normalize_aadhaar(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not _AADHAAR_RE.fullmatch(digits) or len(set(digits)) == 1:
        raise ValueError("Aadhaar must be 12 digits and cannot start with 0 or 1")
    return digits


def normalize_pan(raw: str) -> str:
    value = re.sub(r"\s+", "", (raw or "")).upper()
    if not _PAN_RE.fullmatch(value):
        raise ValueError("PAN must look like ABCDE1234F")
    return value


def mask_aadhaar(number: str | None) -> str | None:
    if not number:
        return None
    return f"XXXX-XXXX-{number[-4:]}"


def mask_pan(number: str | None) -> str | None:
    if not number:
        return None
    return f"XXXXX{number[-5:]}"


def owner_kyc_complete(owner: Owner) -> bool:
    return bool(
        owner.avatar_url
        and owner.live_photo_url
        and owner.aadhaar_number
        and owner.pan_number
    )


def owner_to_response(owner: Owner) -> OwnerResponse:
    return OwnerResponse(
        id=owner.id,
        phone=owner.phone,
        name=owner.name,
        email=owner.email,
        subscription_tier=owner.subscription_tier,
        subscription_status=owner.subscription_status,
        avatar_url=owner.avatar_url,
        live_photo_url=owner.live_photo_url,
        live_photo_captured_at=owner.live_photo_captured_at,
        has_live_photo=bool(owner.live_photo_url),
        aadhaar_masked=mask_aadhaar(owner.aadhaar_number),
        pan_masked=mask_pan(owner.pan_number),
        kyc_complete=owner_kyc_complete(owner),
    )


def apply_owner_kyc(owner: Owner, body: OwnerKycUpdateRequest) -> Owner:
    if body.aadhaar_number is not None and body.aadhaar_number.strip():
        owner.aadhaar_number = normalize_aadhaar(body.aadhaar_number)
    if body.pan_number is not None and body.pan_number.strip():
        owner.pan_number = normalize_pan(body.pan_number)
    return owner


def upload_owner_image(*, owner_id: uuid.UUID, context: str, data: bytes) -> str:
    content_type, ext = sniff_image(data)
    return get_media_storage().upload(
        kitchen_id=f"owner-{owner_id}",
        context=context,
        data=data,
        content_type=content_type,
        extension=ext,
    )


async def publish_owner_updated(
    publisher: EventPublisher,
    session: AsyncSession,
    owner: Owner,
    *,
    kind: str,
) -> None:
    event = EventPublisher.build(
        event_type="owner.updated",
        aggregate_type="owner",
        aggregate_id=str(owner.id),
        producer="identity-service",
        payload={
            "owner_id": str(owner.id),
            "kind": kind,
            "has_avatar": bool(owner.avatar_url),
            "has_live_photo": bool(owner.live_photo_url),
            "has_aadhaar": bool(owner.aadhaar_number),
            "has_pan": bool(owner.pan_number),
            "kyc_complete": owner_kyc_complete(owner),
        },
    )
    await publisher.publish(stream_key("identity", "owner"), event, session=session)


def parse_live_captured_at(raw: str | None) -> datetime:
    return parse_captured_at(raw)
