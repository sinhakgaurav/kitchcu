"""Redis cache helpers — per AGENTS.md caching rules."""

import json
from uuid import UUID

MENU_CACHE_TTL_SECONDS = 300


def menu_cache_key(kitchen_id: UUID | str) -> str:
    return f"menu:{kitchen_id}"


async def get_cached_menu(redis_client, kitchen_id: UUID | str) -> dict | None:
    if not redis_client:
        return None
    raw = await redis_client.get(menu_cache_key(kitchen_id))
    if not raw:
        return None
    return json.loads(raw)


async def set_cached_menu(redis_client, kitchen_id: UUID | str, menu: dict) -> None:
    if not redis_client:
        return
    await redis_client.setex(
        menu_cache_key(kitchen_id),
        MENU_CACHE_TTL_SECONDS,
        json.dumps(menu, default=str),
    )


async def invalidate_menu_cache(redis_client, kitchen_id: UUID | str) -> None:
    if not redis_client:
        return
    await redis_client.delete(menu_cache_key(kitchen_id))


# Analytics aggregates change slowly relative to how often a dashboard is
# refreshed; a short TTL keeps the owner dashboard snappy while bounding
# staleness. Per AGENTS.md, analytics may be cached (aggregates, not payments).
ANALYTICS_CACHE_TTL_SECONDS = 120


def analytics_cache_key(kitchen_id: UUID | str, report: str, days: int) -> str:
    return f"analytics:{kitchen_id}:{report}:{days}"


async def get_cached_json(redis_client, key: str) -> dict | None:
    if not redis_client:
        return None
    raw = await redis_client.get(key)
    if not raw:
        return None
    return json.loads(raw)


async def set_cached_json(
    redis_client, key: str, value: dict, ttl: int = ANALYTICS_CACHE_TTL_SECONDS
) -> None:
    if not redis_client:
        return
    await redis_client.setex(key, ttl, json.dumps(value, default=str))
