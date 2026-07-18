"""Resolve platform secrets and feature flags (DB → env fallback).

Admin-stored values live in ``ckac_identity.platform_api_keys`` /
``ckac_identity.feature_flags``. Services already use cross-schema reads for
kitchen ownership checks; these helpers follow the same pattern so toggles and
keys configured in Control take effect without redeploy.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.config import get_settings
from ckac_common.secret_box import decrypt_secret

# Admin Control key → env var / Settings attribute fallback
PLATFORM_KEY_ENV: dict[str, str] = {
    "razorpay_key_id": "RAZORPAY_KEY_ID",
    "razorpay_key_secret": "RAZORPAY_KEY_SECRET",
    "razorpay_webhook_secret": "RAZORPAY_WEBHOOK_SECRET",
    "livekit_url": "LIVEKIT_URL",
    "livekit_api_key": "LIVEKIT_API_KEY",
    "livekit_api_secret": "LIVEKIT_API_SECRET",
    "support_ai_api_key": "SUPPORT_AI_API_KEY",
    "whatsapp_verify_token": "WHATSAPP_VERIFY_TOKEN",
    "whatsapp_app_secret": "WHATSAPP_APP_SECRET",
    "whatsapp_access_token": "WHATSAPP_ACCESS_TOKEN",
    "whatsapp_otp_phone_number_id": "WHATSAPP_OTP_PHONE_NUMBER_ID",
    "google_maps_api_key": "GOOGLE_MAPS_API_KEY",
    "oauth_google_client_id": "OAUTH_GOOGLE_CLIENT_ID",
    "oauth_google_client_secret": "OAUTH_GOOGLE_CLIENT_SECRET",
    "oauth_facebook_client_id": "OAUTH_FACEBOOK_CLIENT_ID",
    "oauth_facebook_client_secret": "OAUTH_FACEBOOK_CLIENT_SECRET",
}

_SETTINGS_ATTR: dict[str, str] = {
    "razorpay_key_id": "razorpay_key_id",
    "razorpay_key_secret": "razorpay_key_secret",
    "razorpay_webhook_secret": "razorpay_webhook_secret",
    "livekit_url": "livekit_url",
    "livekit_api_key": "livekit_api_key",
    "livekit_api_secret": "livekit_api_secret",
    "support_ai_api_key": "support_ai_api_key",
    "whatsapp_verify_token": "whatsapp_verify_token",
    "whatsapp_app_secret": "whatsapp_app_secret",
    "whatsapp_access_token": "whatsapp_access_token",
    "whatsapp_otp_phone_number_id": "whatsapp_otp_phone_number_id",
    "google_maps_api_key": "google_maps_api_key",
    "oauth_google_client_id": "oauth_google_client_id",
    "oauth_google_client_secret": "oauth_google_client_secret",
    "oauth_facebook_client_id": "oauth_facebook_client_id",
    "oauth_facebook_client_secret": "oauth_facebook_client_secret",
}


def is_non_production() -> bool:
    return get_settings().app_env in ("development", "test")


def allows_fixed_dev_otp() -> bool:
    """Fixed demo OTP is only allowed in development/test."""
    return is_non_production()


def get_demo_otp() -> str:
    return (os.environ.get("DEMO_OTP") or get_settings().demo_otp or "123456").strip()


def require_dev_payment_mocks(action: str) -> None:
    """Raise when forged Razorpay ids would be used outside development/test."""
    if not is_non_production():
        raise ValueError(
            f"{action} requires live Razorpay outside development/test "
            "(dev mock payment ids are disabled)"
        )


def is_dev_provider_id(value: str | None) -> bool:
    if not value:
        return True
    return value.startswith(("order_dev_", "pay_dev_", "rfnd_dev_", "sub_dev_", "trf_dev_", "acc_dev_"))


def _env_fallback(key: str) -> str | None:
    env_name = PLATFORM_KEY_ENV.get(key)
    if env_name:
        raw = os.environ.get(env_name, "").strip()
        if raw:
            return raw
    attr = _SETTINGS_ATTR.get(key)
    if attr:
        val = getattr(get_settings(), attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


async def get_platform_secret(session: AsyncSession | None, key: str) -> str | None:
    """Return decrypted platform secret from DB, else env/Settings."""
    if session is not None:
        result = await session.execute(
            text(
                """
                SELECT value_enc
                FROM ckac_identity.platform_api_keys
                WHERE key = :key
                LIMIT 1
                """
            ),
            {"key": key},
        )
        enc = result.scalar_one_or_none()
        if enc:
            plain = decrypt_secret(enc)
            if plain:
                return plain
    return _env_fallback(key)


async def is_feature_enabled(
    session: AsyncSession,
    key: str,
    *,
    default: bool = True,
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT enabled
            FROM ckac_identity.feature_flags
            WHERE key = :key
            LIMIT 1
            """
        ),
        {"key": key},
    )
    val = result.scalar_one_or_none()
    if val is None:
        return default
    return bool(val)


async def require_feature(session: AsyncSession, key: str) -> None:
    """Raise ValueError when the named feature flag is off."""
    if not await is_feature_enabled(session, key):
        raise ValueError(f"Feature '{key}' is disabled")


def feature_http_status(exc: BaseException) -> int | None:
    """Return 403 if ``exc`` is a feature-disabled ValueError, else None."""
    detail = str(exc)
    if detail.startswith("Feature '") and detail.endswith("' is disabled"):
        return 403
    if detail.startswith("Module '") and "is disabled for this kitchen" in detail:
        return 403
    return None


async def kitchen_has_assigned_package(session: AsyncSession, kitchen_id) -> bool:
    """True when billing has an explicit kitchen_packages row (hard entitlement mode)."""
    try:
        row = (
            await session.execute(
                text(
                    """
                    SELECT 1 FROM ckac_billing.kitchen_packages
                    WHERE kitchen_id = CAST(:kid AS uuid)
                    LIMIT 1
                    """
                ),
                {"kid": str(kitchen_id)},
            )
        ).scalar_one_or_none()
        return row is not None
    except Exception:
        return False


async def is_kitchen_module_enabled(
    session: AsyncSession,
    kitchen_id,
    module_key: str,
    *,
    default: bool = True,
) -> bool:
    """Global flag + per-kitchen module flags.

    Hard entitlement: when the kitchen has an assigned package (or
    ``kitchen_module_overrides`` is on), missing flag rows default to **disabled**.
    """
    from ckac_common.risk_config import KITCHEN_MODULE_GLOBAL_FLAGS, KITCHEN_MODULE_KEYS

    if module_key not in KITCHEN_MODULE_KEYS:
        return default

    global_flag = KITCHEN_MODULE_GLOBAL_FLAGS.get(module_key)
    if global_flag and not await is_feature_enabled(session, global_flag, default=True):
        return False

    overrides_on = await is_feature_enabled(session, "kitchen_module_overrides", default=False)
    packaged = await kitchen_has_assigned_package(session, kitchen_id)
    if not overrides_on and not packaged:
        return True

    result = await session.execute(
        text(
            """
            SELECT enabled FROM ckac_identity.kitchen_module_flags
            WHERE kitchen_id = CAST(:kid AS uuid) AND module_key = :mk
            LIMIT 1
            """
        ),
        {"kid": str(kitchen_id), "mk": module_key},
    )
    row = result.scalar_one_or_none()
    if row is None:
        # Packaged kitchens: default-deny unknown modules
        return False if packaged else default
    return bool(row)


async def require_kitchen_module(session: AsyncSession, kitchen_id, module_key: str) -> None:
    if not await is_kitchen_module_enabled(session, kitchen_id, module_key):
        raise ValueError(f"Module '{module_key}' is disabled for this kitchen")


def verify_razorpay_webhook_signature(
    body: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def verify_meta_signature(
    body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """Verify Meta ``X-Hub-Signature-256: sha256=<hex>``."""
    if not app_secret or not signature_header:
        return False
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False
    expected = signature_header[len(prefix) :].strip()
    digest = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)
