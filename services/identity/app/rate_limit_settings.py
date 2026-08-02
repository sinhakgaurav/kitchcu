"""Super-admin gateway rate-limit configuration (DB + Redis publish)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GatewayRateLimitSettings
from ckac_common.rate_limits import (
    DEFAULT_RULES,
    REDIS_KEY,
    RULE_LABELS,
    TEST_PHASE_RULES,
    default_payload,
    merge_rules,
    normalize_payload,
    test_phase_payload,
)


class RateLimitRuleBody(BaseModel):
    limit: int = Field(..., ge=1, le=1_000_000, description="Max requests per window")
    window_seconds: int = Field(..., ge=1, le=86400, description="Fixed window length in seconds")


class RateLimitSettingsUpdate(BaseModel):
    enabled: bool | None = Field(
        default=None,
        description="When false, gateway skips all rate limiting (test phase).",
    )
    rules: dict[str, RateLimitRuleBody] | None = Field(
        default=None,
        description="Partial or full rule map keyed by rule name.",
    )
    preset: Literal["defaults", "test_phase"] | None = Field(
        default=None,
        description="Apply a named preset (overrides rules/enabled for that preset).",
    )

    @field_validator("rules")
    @classmethod
    def known_rules_only(cls, v: dict[str, RateLimitRuleBody] | None):
        if v is None:
            return v
        unknown = set(v) - set(DEFAULT_RULES)
        if unknown:
            raise ValueError(f"Unknown rate-limit rules: {sorted(unknown)}")
        return v


class RateLimitRuleResponse(BaseModel):
    name: str
    label: str
    limit: int
    window_seconds: int


class RateLimitSettingsResponse(BaseModel):
    enabled: bool
    rules: list[RateLimitRuleResponse]
    updated_at: datetime | None = None
    presets: dict[str, str] = Field(
        default_factory=lambda: {
            "defaults": "Production-safe thresholds",
            "test_phase": "High limits for QA / test phase",
        }
    )


async def ensure_settings(session: AsyncSession) -> GatewayRateLimitSettings:
    row = await session.get(GatewayRateLimitSettings, 1)
    if row is None:
        payload = default_payload()
        row = GatewayRateLimitSettings(
            id=1,
            enabled=payload["enabled"],
            rules=payload["rules"],
        )
        session.add(row)
        await session.flush()
    return row


def _to_response(row: GatewayRateLimitSettings) -> RateLimitSettingsResponse:
    rules = merge_rules(row.rules if isinstance(row.rules, dict) else None)
    return RateLimitSettingsResponse(
        enabled=bool(row.enabled),
        rules=[
            RateLimitRuleResponse(
                name=name,
                label=RULE_LABELS.get(name, name),
                limit=cfg["limit"],
                window_seconds=cfg["window_seconds"],
            )
            for name, cfg in rules.items()
        ],
        updated_at=row.updated_at,
    )


async def get_settings_response(session: AsyncSession) -> RateLimitSettingsResponse:
    row = await ensure_settings(session)
    return _to_response(row)


def payload_for_redis(row: GatewayRateLimitSettings) -> dict[str, Any]:
    return normalize_payload({"enabled": row.enabled, "rules": row.rules})


async def publish_to_redis(redis_client, row: GatewayRateLimitSettings) -> None:
    if redis_client is None:
        return
    payload = payload_for_redis(row)
    await redis_client.set(REDIS_KEY, json.dumps(payload))


async def update_settings(
    session: AsyncSession,
    data: RateLimitSettingsUpdate,
    *,
    admin_id: uuid.UUID | None,
    redis_client=None,
) -> GatewayRateLimitSettings:
    row = await ensure_settings(session)

    if data.preset == "defaults":
        payload = default_payload(enabled=True)
        row.enabled = payload["enabled"]
        row.rules = payload["rules"]
    elif data.preset == "test_phase":
        payload = test_phase_payload()
        row.enabled = payload["enabled"]
        row.rules = payload["rules"]
    else:
        if data.enabled is not None:
            row.enabled = data.enabled
        if data.rules is not None:
            current = merge_rules(row.rules if isinstance(row.rules, dict) else None)
            for name, cfg in data.rules.items():
                current[name] = {"limit": cfg.limit, "window_seconds": cfg.window_seconds}
            row.rules = current

    row.updated_at = datetime.now(UTC)
    row.updated_by = admin_id
    await session.flush()
    await publish_to_redis(redis_client, row)
    return row


# Re-export for tests / docs
__all__ = [
    "DEFAULT_RULES",
    "TEST_PHASE_RULES",
    "RateLimitSettingsUpdate",
    "RateLimitSettingsResponse",
    "ensure_settings",
    "get_settings_response",
    "update_settings",
    "publish_to_redis",
]
