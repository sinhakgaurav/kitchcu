"""Public customer discovery feed — geo-scoped order pathways (not marketing)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DiscoveryKitchenCard(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    city: str | None = None
    distance_km: float
    latitude: float
    longitude: float
    has_veg: bool = False
    has_non_veg: bool = False
    has_live_capture: bool = False
    is_live_now: bool = False
    is_featured: bool = False
    avg_rating: float | None = None
    rating_count: int = 0
    min_dish_price: float | None = None
    tagline: str | None = None
    logo_url: str | None = None


class DiscoveryDishCard(BaseModel):
    dish_id: uuid.UUID
    kitchen_id: uuid.UUID
    kitchen_code: str
    kitchen_name: str
    dish_name: str
    price: float
    distance_km: float
    is_live_capture_hero: bool = False
    image_url: str | None = None


class DiscoveryHomeResponse(BaseModel):
    customer_latitude: float
    customer_longitude: float
    max_km: float
    total_kitchens: int = Field(..., description="Active kitchens in radius before section slicing.")
    near_you: list[DiscoveryKitchenCard]
    featured: list[DiscoveryKitchenCard]
    most_liked: list[DiscoveryKitchenCard]
    live_now: list[DiscoveryKitchenCard]
    cheapest_dishes: list[DiscoveryDishCard]


def _card_from_row(row) -> DiscoveryKitchenCard:
    avg = float(row.avg_rating) if row.avg_rating is not None else None
    min_price = float(row.min_dish_price) if row.min_dish_price is not None else None
    return DiscoveryKitchenCard(
        id=row.id,
        code=row.code,
        name=row.name,
        city=row.city,
        distance_km=round(float(row.distance_km), 2),
        latitude=float(row.lat),
        longitude=float(row.lng),
        has_veg=bool(row.has_veg),
        has_non_veg=bool(row.has_non_veg),
        has_live_capture=bool(row.has_live_capture),
        is_live_now=bool(row.is_live_now),
        is_featured=bool(row.is_featured),
        avg_rating=round(avg, 2) if avg is not None else None,
        rating_count=int(row.rating_count or 0),
        min_dish_price=round(min_price, 2) if min_price is not None else None,
        tagline=row.tagline,
        logo_url=row.logo_url,
    )


async def build_discovery_home(
    session: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    max_km: float = 25.0,
    section_limit: int = 12,
) -> DiscoveryHomeResponse:
    max_m = max_km * 1000.0
    section_limit = min(max(section_limit, 1), 30)
    params = {"lat": latitude, "lng": longitude, "max_m": max_m, "lim": section_limit}

    kitchen_sql = """
        WITH nearby AS (
            SELECT
                k.id,
                k.code,
                k.name,
                k.city,
                ST_Y(k.location::geometry) AS lat,
                ST_X(k.location::geometry) AS lng,
                ST_Distance(
                    k.location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                ) / 1000.0 AS distance_km,
                COALESCE((k.settings->'branded_page'->>'enabled')::boolean, false) AS branded_enabled,
                NULLIF(TRIM(k.settings->'branded_page'->>'tagline'), '') AS tagline,
                NULLIF(TRIM(k.settings->'branded_page'->>'logo_url'), '') AS logo_url,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.categories c ON c.id = d.category_id
                    WHERE d.kitchen_id = k.id AND d.is_active = true AND c.slug = 'veg'
                ) AS has_veg,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.categories c ON c.id = d.category_id
                    WHERE d.kitchen_id = k.id AND d.is_active = true AND c.slug = 'non_veg'
                ) AS has_non_veg,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.dish_media m ON m.dish_id = d.id
                    WHERE d.kitchen_id = k.id AND d.is_active = true
                      AND m.is_hero = true AND m.is_live_capture = true
                ) AS has_live_capture,
                EXISTS (
                    SELECT 1 FROM ckac_streaming.live_sessions s
                    INNER JOIN ckac_streaming.kitchen_stream_settings st ON st.kitchen_id = s.kitchen_id
                    WHERE s.kitchen_id = k.id AND s.status = 'live' AND st.live_sharing_enabled = true
                ) AS is_live_now,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    WHERE d.kitchen_id = k.id AND d.is_active = true AND d.is_featured = true
                ) AS has_featured_dish,
                (
                    SELECT AVG(a.overall_rating)::float
                    FROM ckac_ratings.dish_rating_aggregates a
                    WHERE a.kitchen_id = k.id AND a.rating_count > 0
                ) AS avg_rating,
                (
                    SELECT COALESCE(SUM(a.rating_count), 0)::int
                    FROM ckac_ratings.dish_rating_aggregates a
                    WHERE a.kitchen_id = k.id
                ) AS rating_count,
                (
                    SELECT MIN(d.price)::float
                    FROM ckac_catalog.dishes d
                    WHERE d.kitchen_id = k.id AND d.is_active = true
                ) AS min_dish_price
            FROM ckac_identity.kitchens k
            WHERE k.status = 'active'
              AND ST_DWithin(
                    k.location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :max_m
                  )
        )
        SELECT
            *,
            (branded_enabled OR has_featured_dish) AS is_featured
        FROM nearby
        ORDER BY distance_km ASC
    """

    kitchen_rows = (await session.execute(text(kitchen_sql), params)).all()
    cards = [_card_from_row(r) for r in kitchen_rows]

    near_you = cards[:section_limit]
    featured = [c for c in cards if c.is_featured][:section_limit]
    # If nothing flagged featured, surface branded/home kitchens nearest as "Featured picks"
    if not featured:
        featured = near_you[: min(6, section_limit)]

    most_liked = sorted(
        [c for c in cards if c.rating_count > 0],
        key=lambda c: (-(c.avg_rating or 0), -c.rating_count, c.distance_km),
    )[:section_limit]
    if not most_liked:
        # Soft fallback: kitchens with live-capture (trust signal) then nearest
        most_liked = sorted(
            cards,
            key=lambda c: (0 if c.has_live_capture else 1, c.distance_km),
        )[:section_limit]

    live_now = [c for c in cards if c.is_live_now][:section_limit]

    dish_sql = """
        SELECT
            d.id AS dish_id,
            d.kitchen_id,
            k.code AS kitchen_code,
            k.name AS kitchen_name,
            d.name AS dish_name,
            d.price::float AS price,
            ST_Distance(
                k.location,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            ) / 1000.0 AS distance_km,
            EXISTS (
                SELECT 1 FROM ckac_catalog.dish_media m
                WHERE m.dish_id = d.id AND m.is_hero = true AND m.is_live_capture = true
            ) AS is_live_capture_hero,
            (
                SELECT m.url FROM ckac_catalog.dish_media m
                WHERE m.dish_id = d.id AND m.is_hero = true
                LIMIT 1
            ) AS image_url
        FROM ckac_catalog.dishes d
        INNER JOIN ckac_identity.kitchens k ON k.id = d.kitchen_id
        WHERE k.status = 'active'
          AND d.is_active = true
          AND ST_DWithin(
                k.location,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :max_m
              )
        ORDER BY d.price ASC, distance_km ASC
        LIMIT :lim
    """
    dish_rows = (await session.execute(text(dish_sql), params)).all()
    cheapest = [
        DiscoveryDishCard(
            dish_id=r.dish_id,
            kitchen_id=r.kitchen_id,
            kitchen_code=r.kitchen_code,
            kitchen_name=r.kitchen_name,
            dish_name=r.dish_name,
            price=round(float(r.price), 2),
            distance_km=round(float(r.distance_km), 2),
            is_live_capture_hero=bool(r.is_live_capture_hero),
            image_url=r.image_url,
        )
        for r in dish_rows
    ]

    return DiscoveryHomeResponse(
        customer_latitude=latitude,
        customer_longitude=longitude,
        max_km=max_km,
        total_kitchens=len(cards),
        near_you=near_you,
        featured=featured,
        most_liked=most_liked,
        live_now=live_now,
        cheapest_dishes=cheapest,
    )
