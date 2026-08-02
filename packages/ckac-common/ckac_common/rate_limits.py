"""Gateway rate-limit defaults + Redis cache contract (admin-configurable).

Identity persists overrides in ``ckac_identity.gateway_rate_limit_settings`` and
publishes the same JSON to Redis under ``REDIS_KEY`` so the gateway (no DB) can
enforce without a sync call on every request.
"""

from __future__ import annotations

from typing import Any, TypedDict

REDIS_KEY = "ckac:gateway:rate_limits"
# Gateway in-memory refresh interval when reading Redis (seconds).
CACHE_TTL_SECONDS = 30


class RuleConfig(TypedDict):
    limit: int
    window_seconds: int


# Production-safe defaults — mirrored by gateway matchers (first match wins).
DEFAULT_RULES: dict[str, RuleConfig] = {
    "otp_request": {"limit": 5, "window_seconds": 600},
    "otp_verify": {"limit": 10, "window_seconds": 600},
    "owner_register": {"limit": 10, "window_seconds": 3600},
    "checkout": {"limit": 30, "window_seconds": 60},
    "default": {"limit": 600, "window_seconds": 60},
}

# Generous preset for QA / test-phase (Super Admin → Control → Apply test preset).
TEST_PHASE_RULES: dict[str, RuleConfig] = {
    "otp_request": {"limit": 200, "window_seconds": 600},
    "otp_verify": {"limit": 200, "window_seconds": 600},
    "owner_register": {"limit": 100, "window_seconds": 3600},
    "checkout": {"limit": 120, "window_seconds": 60},
    "default": {"limit": 3000, "window_seconds": 60},
}

RULE_LABELS: dict[str, str] = {
    "otp_request": "OTP request (owner + customer WhatsApp)",
    "otp_verify": "OTP verify (owner + customer)",
    "owner_register": "Owner registration",
    "checkout": "Customer checkout / place order",
    "default": "All other API routes",
}


def default_payload(*, enabled: bool = True) -> dict[str, Any]:
    return {"enabled": enabled, "rules": {k: dict(v) for k, v in DEFAULT_RULES.items()}}


def test_phase_payload() -> dict[str, Any]:
    return {"enabled": True, "rules": {k: dict(v) for k, v in TEST_PHASE_RULES.items()}}


def merge_rules(raw: dict[str, Any] | None) -> dict[str, RuleConfig]:
    """Merge stored rules onto defaults; ignore unknown keys / bad values."""
    out: dict[str, RuleConfig] = {k: dict(v) for k, v in DEFAULT_RULES.items()}
    if not raw:
        return out
    for name, cfg in raw.items():
        if name not in out or not isinstance(cfg, dict):
            continue
        limit = cfg.get("limit")
        window = cfg.get("window_seconds")
        if isinstance(limit, int) and 1 <= limit <= 1_000_000:
            out[name]["limit"] = limit
        if isinstance(window, int) and 1 <= window <= 86400:
            out[name]["window_seconds"] = window
    return out


def normalize_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    data = data or {}
    enabled = bool(data.get("enabled", True))
    rules = merge_rules(data.get("rules") if isinstance(data.get("rules"), dict) else None)
    return {"enabled": enabled, "rules": rules}
