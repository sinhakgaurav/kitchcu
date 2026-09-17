"""Super-admin dish calories / Healthy Control settings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeatureFlag, HealthyFoodSettings
from ckac_common.platform_config import (
    DISH_CALORIES_FLAG,
    DISH_HEALTHY_TAG_FLAG,
    HEALTHY_MAX_KCAL_DEFAULT,
    HEALTHY_MAX_KCAL_MAX,
    HEALTHY_MAX_KCAL_MIN,
    HEALTHY_MIN_SCORE_DEFAULT,
)

_FLAG_META = {
    DISH_CALORIES_FLAG: (
        "kitchen",
        "Public dish calorie totals from pantry × recipe (kitchen estimate, not a lab label)",
    ),
    DISH_HEALTHY_TAG_FLAG: (
        "kitchen",
        "Automatic Healthy badge when the plate meets the Control kcal cap and health-score floor",
    ),
}


class HealthyFoodSettingsResponse(BaseModel):
    healthy_max_kcal: int
    healthy_min_score: int
    dish_calories_enabled: bool
    dish_healthy_tag_enabled: bool
    updated_at: datetime | None = None


class HealthyFoodSettingsUpdate(BaseModel):
    healthy_max_kcal: int | None = Field(
        default=None,
        ge=HEALTHY_MAX_KCAL_MIN,
        le=HEALTHY_MAX_KCAL_MAX,
        description="Maximum plate kcal to earn the automatic Healthy tag.",
    )
    healthy_min_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Minimum P50 health score to earn Healthy (with the kcal cap).",
    )
    dish_calories_enabled: bool | None = None
    dish_healthy_tag_enabled: bool | None = None


async def ensure_settings(session: AsyncSession) -> HealthyFoodSettings:
    row = await session.get(HealthyFoodSettings, 1)
    if row is None:
        row = HealthyFoodSettings(
            id=1,
            healthy_max_kcal=HEALTHY_MAX_KCAL_DEFAULT,
            healthy_min_score=HEALTHY_MIN_SCORE_DEFAULT,
        )
        session.add(row)
        await session.flush()
    return row


async def _flag_enabled(session: AsyncSession, key: str, *, default: bool = True) -> bool:
    row = await session.get(FeatureFlag, key)
    if row is None:
        return default
    return bool(row.enabled)


async def _set_flag(session: AsyncSession, key: str, enabled: bool) -> None:
    scope, description = _FLAG_META[key]
    row = await session.get(FeatureFlag, key)
    if row is None:
        session.add(
            FeatureFlag(
                key=key,
                enabled=enabled,
                scope=scope,
                description=description,
                updated_at=datetime.now(UTC),
            )
        )
        return
    row.enabled = enabled
    row.updated_at = datetime.now(UTC)


async def get_settings_response(session: AsyncSession) -> HealthyFoodSettingsResponse:
    row = await ensure_settings(session)
    return HealthyFoodSettingsResponse(
        healthy_max_kcal=int(row.healthy_max_kcal),
        healthy_min_score=int(row.healthy_min_score),
        dish_calories_enabled=await _flag_enabled(session, DISH_CALORIES_FLAG),
        dish_healthy_tag_enabled=await _flag_enabled(session, DISH_HEALTHY_TAG_FLAG),
        updated_at=row.updated_at,
    )


async def update_settings(
    session: AsyncSession,
    data: HealthyFoodSettingsUpdate,
    *,
    admin_id: uuid.UUID,
) -> HealthyFoodSettingsResponse:
    row = await ensure_settings(session)
    if data.healthy_max_kcal is not None:
        row.healthy_max_kcal = data.healthy_max_kcal
    if data.healthy_min_score is not None:
        row.healthy_min_score = data.healthy_min_score
    if data.dish_calories_enabled is not None:
        await _set_flag(session, DISH_CALORIES_FLAG, data.dish_calories_enabled)
    if data.dish_healthy_tag_enabled is not None:
        await _set_flag(session, DISH_HEALTHY_TAG_FLAG, data.dish_healthy_tag_enabled)
    row.updated_at = datetime.now(UTC)
    row.updated_by = admin_id
    await session.flush()
    return await get_settings_response(session)
