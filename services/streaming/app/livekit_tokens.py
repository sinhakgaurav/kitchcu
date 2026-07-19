"""LiveKit access token helper (F46) — credentials from platform keys or env."""

from __future__ import annotations

import time
import uuid

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.config import get_settings
from ckac_common.platform_config import get_platform_secret


async def resolve_livekit_creds(
    session: AsyncSession | None = None,
) -> tuple[str, str, str]:
    """Return (url, api_key, api_secret) preferring Control-stored platform keys."""
    settings = get_settings()
    url = (await get_platform_secret(session, "livekit_url")) or settings.livekit_url
    key = (await get_platform_secret(session, "livekit_api_key")) or settings.livekit_api_key
    secret = (await get_platform_secret(session, "livekit_api_secret")) or settings.livekit_api_secret
    return (url or "").strip(), (key or "").strip(), (secret or "").strip()


async def livekit_configured(session: AsyncSession | None = None) -> bool:
    from ckac_common.platform_config import third_party_integrations_enabled

    if not await third_party_integrations_enabled(session, default=False):
        return False
    url, key, secret = await resolve_livekit_creds(session)
    return bool(url and key and secret)


def livekit_configured_sync() -> bool:
    """Env-only check (no DB) — used when a session is unavailable."""
    s = get_settings()
    return bool(s.livekit_url and s.livekit_api_key and s.livekit_api_secret)


async def build_livekit_token(
    *,
    room_name: str,
    identity: str,
    can_publish: bool,
    ttl_seconds: int = 3600,
    session: AsyncSession | None = None,
) -> str | None:
    from ckac_common.platform_config import third_party_integrations_enabled

    if not await third_party_integrations_enabled(session, default=False):
        return None
    url, api_key, api_secret = await resolve_livekit_creds(session)
    if not (url and api_key and api_secret):
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
        "iss": api_key,
        "sub": identity,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
        **grants,
    }
    return jwt.encode(payload, api_secret, algorithm="HS256")


def viewer_identity(customer_id: uuid.UUID) -> str:
    return f"viewer-{customer_id}"


def publisher_identity(kitchen_id: uuid.UUID) -> str:
    return f"kitchen-{kitchen_id}"
