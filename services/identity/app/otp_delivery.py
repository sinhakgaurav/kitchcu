"""Production OTP: random code → Redis → WhatsApp via notification service."""

from __future__ import annotations

import logging
import secrets

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)

OWNER_OTP_PREFIX = "otp:owner:"
CUSTOMER_OTP_PREFIX = "otp:customer:"
OTP_TTL_SEC = 600


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def store_otp_redis(redis_client, *, prefix: str, phone: str, code: str) -> None:
    if redis_client is None:
        raise RuntimeError("Redis unavailable for OTP storage")
    await redis_client.setex(f"{prefix}{phone.strip()}", OTP_TTL_SEC, code)


async def send_otp_whatsapp(*, phone: str, code: str, purpose: str) -> None:
    """Ask notification service to deliver OTP over Meta WhatsApp Cloud API."""
    settings = get_settings()
    url = f"{settings.notification_service_url.rstrip('/')}/api/v1/internal/notifications/otp"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"phone": phone, "code": code, "purpose": purpose},
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            if response.status_code >= 400:
                detail = response.text[:200]
                logger.warning("OTP WhatsApp dispatch failed %s: %s", response.status_code, detail)
                raise RuntimeError(f"OTP delivery failed ({response.status_code})")
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("OTP WhatsApp dispatch error: %s", exc)
        raise RuntimeError("OTP delivery unavailable") from exc
