"""Platform risk / Phase-2 capability toggles — env overrides + feature flags."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.platform_config import is_feature_enabled

# Global feature-flag keys for optional / Phase-2 capabilities (OFF = safe default in prod).
RISK_FEATURE_FLAGS: dict[str, str] = {
    "order_parser_llm": "order_parser_llm",
    "courier_porter_dunzo": "courier_porter_dunzo",
    "courier_porter_auto_book": "courier_porter_auto_book",
    "tiffin_plans": "tiffin_plans",
    "payments_stripe_multi_region": "payments_stripe_multi_region",
    "messaging_wallet_deduct": "messaging_wallet_deduct",
    "kitchen_module_overrides": "kitchen_module_overrides",
    "third_party_integrations": "third_party_integrations",
}

# Per-kitchen module keys → optional global gate (None = kitchen override only).
KITCHEN_MODULE_GLOBAL_FLAGS: dict[str, str | None] = {
    "whatsapp": None,
    "livekit": "live_streaming",
    "razorpay": None,
    "refunds": "refunds_gateway",
    "marketing_broadcast": "messaging_wallet_deduct",
    "customer_checkout": "multi_kitchen_checkout",
    "streaming": "live_streaming",
    "courier_porter_auto_book": "courier_porter_auto_book",
    "tiffin_plans": "tiffin_plans",
}

KITCHEN_MODULE_KEYS: tuple[str, ...] = tuple(KITCHEN_MODULE_GLOBAL_FLAGS.keys())


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def messaging_fee_per_recipient_inr() -> float:
    return env_float("MESSAGING_FEE_PER_RECIPIENT_INR", 1.0)


def messaging_wallet_low_balance_inr() -> float:
    return env_float("MESSAGING_WALLET_LOW_BALANCE_INR", 50.0)


def webhook_stress_burst_size() -> int:
    return env_int("WEBHOOK_STRESS_BURST_SIZE", 500)


def webhook_stress_max_concurrency() -> int:
    return env_int("WEBHOOK_STRESS_MAX_CONCURRENCY", 40)


async def is_risk_capability_enabled(
    session: AsyncSession,
    capability: str,
    *,
    default: bool = False,
) -> bool:
    """Check DB feature flag for a named risk/Phase-2 capability."""
    flag_key = RISK_FEATURE_FLAGS.get(capability, capability)
    return await is_feature_enabled(session, flag_key, default=default)
