"""Kitchen media upload — live-capture photos for dishes, ingredients, prep steps."""

from __future__ import annotations

import uuid

from fastapi import UploadFile
from pydantic import BaseModel

from ckac_common.storage import get_media_storage

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_CONTEXTS = frozenset({"dish", "ingredient", "prep_step", "general"})

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
WEBP_MAGIC = b"RIFF"


class MediaUploadResponse(BaseModel):
    url: str
    object_key: str
    content_type: str
    is_live_capture: bool
    captured_at: str | None = None


def _detect_image(data: bytes, declared: str | None) -> tuple[str, str]:
    if data.startswith(JPEG_MAGIC):
        return "image/jpeg", "jpg"
    if data.startswith(PNG_MAGIC):
        return "image/png", "png"
    if len(data) >= 12 and data[:4] == WEBP_MAGIC and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    if declared and declared in ALLOWED_CONTENT_TYPES:
        return declared, ALLOWED_CONTENT_TYPES[declared]
    raise ValueError("Unsupported image format — use JPEG, PNG, or WebP")


async def upload_kitchen_media(
    *,
    kitchen_id: uuid.UUID,
    file: UploadFile,
    is_live_capture: bool,
    context: str,
    captured_at: str | None = None,
) -> MediaUploadResponse:
    if context not in ALLOWED_CONTEXTS:
        raise ValueError(f"context must be one of: {', '.join(sorted(ALLOWED_CONTEXTS))}")

    data = await file.read()
    if not data:
        raise ValueError("Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds 10MB limit")

    content_type, extension = _detect_image(data, file.content_type)
    storage = get_media_storage()
    url = storage.upload(
        kitchen_id=str(kitchen_id),
        context=context,
        data=data,
        content_type=content_type,
        extension=extension,
    )
    object_key = url.rsplit("/", 1)[-1] if "/" in url else url
    return MediaUploadResponse(
        url=url,
        object_key=object_key,
        content_type=content_type,
        is_live_capture=is_live_capture,
        captured_at=captured_at if is_live_capture else None,
    )
