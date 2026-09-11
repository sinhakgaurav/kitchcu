"""A seeded hero photo is a promise about what arrives in the bag.

QA ID-16 found the demo menu breaking that promise three ways: one salad-bowl photo
stood in for thirteen different curries, a veg thali wore a plate of chicken fried
rice, and two dishes wore photos of the dining room. These tests pin the rules that
prevent a re-seed from reintroducing any of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from bulk_demo_data import BULK_DISHES, enriched_dishes  # noqa: E402
from demo_data import (  # noqa: E402
    DEMO_DISHES,
    DISH_MEDIA_BY_NAME,
    FOOD_ASSET_SUBJECTS,
    NON_VEG_ASSETS,
    UNUSABLE_DISH_ASSETS,
    normalize_category_slug,
)
from seed_common import dish_create_payload  # noqa: E402

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "apps" / "website" / "public" / "media" / "food"
VEG_SLUGS = {"veg", "vegan"}
DIET_SLUGS = ("veg", "non_veg", "vegan", "eggetarian")


def _mapped_assets() -> dict[str, str]:
    return {name: asset for name, asset in DISH_MEDIA_BY_NAME.items() if asset}


def test_every_described_asset_exists_on_disk() -> None:
    for asset in FOOD_ASSET_SUBJECTS:
        assert (MEDIA_ROOT / asset).is_file(), f"{asset} is described but missing from {MEDIA_ROOT}"


def test_every_mapped_asset_is_described() -> None:
    """An undescribed asset is an unreviewed claim about a dish."""
    for name, asset in _mapped_assets().items():
        assert asset in FOOD_ASSET_SUBJECTS, f"{name} uses {asset}, which has no subject description"


def test_no_asset_is_reused_across_dishes() -> None:
    """One photo, one dish. Reuse is how Aloo Gobi ended up wearing a salad bowl."""
    owners: dict[str, list[str]] = {}
    for name, asset in _mapped_assets().items():
        owners.setdefault(asset, []).append(name)
    shared = {asset: names for asset, names in owners.items() if len(names) > 1}
    assert not shared, f"assets reused across dishes: {shared}"


def test_venue_and_branded_photos_are_never_dish_heroes() -> None:
    for name, asset in _mapped_assets().items():
        assert asset not in UNUSABLE_DISH_ASSETS, f"{name} must not use {asset}"


def test_veg_dishes_never_show_meat_or_egg() -> None:
    """Diet is the one claim a diner cannot verify before the food arrives."""
    by_name = {d["name"]: d for d in BULK_DISHES + DEMO_DISHES}
    for name, asset in _mapped_assets().items():
        dish = by_name.get(name)
        if dish is None:
            continue
        if normalize_category_slug(dish) in VEG_SLUGS:
            assert asset not in NON_VEG_ASSETS, f"{name} is vegetarian but shows {asset}"


def test_dishes_without_an_honest_photo_seed_as_drafts() -> None:
    """No hero means no active dish, so a diner never sees a dish with a borrowed photo."""
    for dish in enriched_dishes():
        if dish.get("media_url"):
            continue
        payload = dish_create_payload(
            dish,
            category_ids={slug: f"cat-{slug}" for slug in DIET_SLUGS},
            cuisine_ids={"home_style": "cui-home"},
            captured_at="2026-09-11T00:00:00Z",
        )
        assert payload["is_active"] is False, f"{dish['name']} has no hero but would go live"
        assert "media" not in payload


def test_demo_and_bulk_menus_agree_on_every_hero() -> None:
    """Two seeders, one truth table — otherwise the primary kitchen drifts."""
    for dish in DEMO_DISHES:
        expected = DISH_MEDIA_BY_NAME.get(dish["name"])
        actual = dish.get("media_url")
        if expected:
            assert actual and actual.endswith(expected), f"{dish['name']} hero should be {expected}"
        else:
            assert not actual, f"{dish['name']} has no honest asset but carries {actual}"


def test_active_demo_menu_is_large_enough_to_demo() -> None:
    """Truthful but empty is also a failure — the demo needs a menu worth browsing."""
    active = [d for d in DEMO_DISHES if d.get("media_url")]
    assert len(active) >= 10, f"only {len(active)} demo dishes have an honest hero"
