"""Seed payloads must not activate a dish that has no live-capture hero."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from seed_common import dish_create_payload  # noqa: E402


def test_drink_without_media_stays_inactive() -> None:
    payload = dish_create_payload(
        {
            "name": "Mango Lassi",
            "price": 80,
            "prep_time_min": 5,
            "category_slug": "veg",
            "cuisine_slug": "home_style",
            "media_url": None,
        },
        category_ids={"veg": "cat-veg"},
        cuisine_ids={"home_style": "cui-home"},
        captured_at="2026-09-07T00:00:00Z",
    )
    assert payload["is_active"] is False
    assert "media" not in payload


def test_dish_with_hero_omits_inactive_flag() -> None:
    payload = dish_create_payload(
        {
            "name": "Paneer Tikka",
            "price": 199,
            "prep_time_min": 25,
            "category_slug": "veg",
            "cuisine_slug": "north_indian",
            "media_url": "https://media.example/paneer.jpg",
        },
        category_ids={"veg": "cat-veg"},
        cuisine_ids={"north_indian": "cui-north", "home_style": "cui-home"},
        captured_at="2026-09-07T00:00:00Z",
    )
    assert "is_active" not in payload
    assert payload["media"]["is_live_capture"] is True
    assert payload["media"]["is_hero"] is True
