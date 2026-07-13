"""LiveKit access token helper (F46)."""

from __future__ import annotations

import time
import uuid

from jose import jwt

from ckac_common.config import get_settings


def livekit_configured() -> bool:
    s = get_settings()
    return bool(s.livekit_url and s.livekit_api_key and s.livekit_api_secret)


def build_livekit_token(
    *,
    room_name: str,
    identity: str,
    can_publish: bool,
    ttl_seconds: int = 3600,
) -> str | None:
    settings = get_settings()
    if not livekit_configured():
        return None
    now = int(time.time())
    grants = {
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": True,
        }
    }
    payload = {
        "iss": settings.livekit_api_key,
        "sub": identity,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
        **grants,
    }
    return jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")


def viewer_identity(customer_id: uuid.UUID) -> str:
    return f"viewer-{customer_id}"


def publisher_identity(kitchen_id: uuid.UUID) -> str:
    return f"kitchen-{kitchen_id}"
