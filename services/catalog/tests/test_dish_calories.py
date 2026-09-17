"""P53 — pantry kcal × recipe quantity → dish calories + automatic Healthy tag."""

from __future__ import annotations

from app.dish_calories import (
    HEALTHY_MAX_KCAL,
    apply_public_calorie_flags,
    is_healthy_tag,
    line_kcal,
    sum_recipe_kcal,
)
from app.ingredient_health import score_ingredient_lines


def test_grams_line_uses_kcal_per_100():
    # 150 g spinach at 23 kcal / 100 g → 34.5 → 34 or 35 rounded at dish level
    assert line_kcal(kcal_per_100=23, quantity=150, recipe_unit="g", ingredient_unit="g") == 34.5


def test_ml_line_same_as_grams():
    assert line_kcal(kcal_per_100=40, quantity=50, recipe_unit="ml", ingredient_unit="ml") == 20.0


def test_piece_uses_per_piece_not_per_100g():
    assert line_kcal(kcal_per_100=90, quantity=2, recipe_unit="pcs", ingredient_unit="pcs") == 180.0


def test_missing_pantry_kcal_is_none():
    assert line_kcal(kcal_per_100=None, quantity=100, recipe_unit="g", ingredient_unit="g") is None


def test_sum_skips_unmapped_and_flags_incomplete():
    total, mapped, n, complete = sum_recipe_kcal(
        [
            (340.0, 80, "g", "g"),  # dal 272
            (None, 10, "g", "g"),
        ]
    )
    assert total == 272
    assert mapped == 1
    assert n == 2
    assert complete is False


def test_complete_sum_rounds_to_int():
    total, mapped, n, complete = sum_recipe_kcal(
        [
            (23.0, 150, "g", "g"),
            (40.0, 50, "g", "g"),
        ]
    )
    assert complete is True
    assert mapped == n == 2
    assert total == 55  # 34.5 + 20


def test_healthy_requires_complete_map_score_and_kcal_cap():
    assert (
        is_healthy_tag(calories_kcal=400, complete=True, health_score=80, recipe_lines=2) is True
    )
    assert (
        is_healthy_tag(calories_kcal=400, complete=False, health_score=80, recipe_lines=2) is False
    )
    assert (
        is_healthy_tag(
            calories_kcal=HEALTHY_MAX_KCAL + 1, complete=True, health_score=80, recipe_lines=2
        )
        is False
    )
    assert (
        is_healthy_tag(calories_kcal=400, complete=True, health_score=64, recipe_lines=2) is False
    )


def test_healthy_uses_admin_kcal_cap():
    assert (
        is_healthy_tag(
            calories_kcal=400,
            complete=True,
            health_score=80,
            recipe_lines=2,
            max_kcal=350,
        )
        is False
    )
    assert (
        is_healthy_tag(
            calories_kcal=400,
            complete=True,
            health_score=80,
            recipe_lines=2,
            max_kcal=400,
        )
        is True
    )


def test_public_flags_hide_kcal_and_healthy():
    kcal, note, incomplete, tag = apply_public_calorie_flags(
        calories_kcal=127,
        calories_description="Light bowl",
        calories_incomplete=False,
        healthy_tag=True,
        calories_enabled=False,
        healthy_tag_enabled=True,
    )
    assert kcal is None
    assert note is None
    assert incomplete is False
    assert tag is False

    kcal, note, incomplete, tag = apply_public_calorie_flags(
        calories_kcal=127,
        calories_description="Light bowl",
        calories_incomplete=False,
        healthy_tag=True,
        calories_enabled=True,
        healthy_tag_enabled=False,
    )
    assert kcal == 127
    assert note == "Light bowl"
    assert tag is False


def test_light_mapped_recipe_can_earn_healthy_tag():
    lines = [("Spinach", 150, "g"), ("Lentils", 80, "g")]
    snap = score_ingredient_lines(lines)
    total, _, n, complete = sum_recipe_kcal(
        [(23.0, 150, "g", "g"), (116.0, 80, "g", "g")]
    )
    assert snap.score is not None and snap.score >= 65
    assert is_healthy_tag(
        calories_kcal=total, complete=complete, health_score=snap.score, recipe_lines=n
    )
