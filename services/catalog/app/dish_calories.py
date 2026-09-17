"""P53 — recipe calorie sum from pantry kcal × quantity (kitchen estimate, not a lab label)."""

from __future__ import annotations

from app.ingredient_health import _line_weight
from ckac_common.platform_config import (
    HEALTHY_MAX_KCAL_DEFAULT as HEALTHY_MAX_KCAL,
    HEALTHY_MIN_SCORE_DEFAULT as HEALTHY_MIN_SCORE,
)

KCAL_PER_100_MAX = 2000.0

_PCS = frozenset({"pcs", "pc", "piece", "pieces"})


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def line_kcal(
    *,
    kcal_per_100: float | None,
    quantity: float,
    recipe_unit: str,
    ingredient_unit: str,
) -> float | None:
    """Calories for one recipe line.

    ``kcal_per_100`` is kcal per 100 g/ml when the pantry unit is g or ml,
    and kcal **per piece** when the pantry unit is pcs.
    """
    if kcal_per_100 is None:
        return None
    kcal = float(kcal_per_100)
    if kcal < 0:
        return None
    qty = max(float(quantity or 0), 0.0)
    recipe = (recipe_unit or ingredient_unit or "g").strip().lower()
    pantry = (ingredient_unit or "g").strip().lower()
    if pantry in _PCS:
        if recipe in _PCS:
            return round(kcal * qty, 1)
        grams = _line_weight(qty, recipe)
        return round(kcal * (grams / 50.0), 1)
    grams = _line_weight(qty, recipe)
    return round(kcal * (grams / 100.0), 1)


def sum_recipe_kcal(
    lines: list[tuple[float | None, float, str, str]],
) -> tuple[int | None, int, int, bool]:
    """Return (rounded total, mapped lines, total lines, complete).

    Each line is ``(kcal_per_100, quantity, recipe_unit, ingredient_unit)``.
    """
    mapped = 0
    total = 0
    acc = 0.0
    for kcal_per_100, qty, recipe_unit, ingredient_unit in lines:
        total += 1
        kcal = line_kcal(
            kcal_per_100=kcal_per_100,
            quantity=qty,
            recipe_unit=recipe_unit,
            ingredient_unit=ingredient_unit,
        )
        if kcal is None:
            continue
        mapped += 1
        acc += kcal
    if mapped == 0:
        return None, 0, total, total == 0
    complete = mapped == total and total > 0
    return int(acc + 0.5), mapped, total, complete


def is_healthy_tag(
    *,
    calories_kcal: int | None,
    complete: bool,
    health_score: int | None,
    recipe_lines: int,
    max_kcal: int = HEALTHY_MAX_KCAL,
    min_score: int = HEALTHY_MIN_SCORE,
) -> bool:
    """Automatic Healthy mark — owners cannot set this flag."""
    if recipe_lines <= 0 or not complete or calories_kcal is None or health_score is None:
        return False
    return calories_kcal <= max_kcal and health_score >= min_score


def apply_public_calorie_flags(
    *,
    calories_kcal: int | None,
    calories_description: str | None,
    calories_incomplete: bool,
    healthy_tag: bool,
    calories_enabled: bool,
    healthy_tag_enabled: bool,
) -> tuple[int | None, str | None, bool, bool]:
    """Strip public kcal / Healthy when Control kill-switches are off."""
    if not calories_enabled:
        return None, None, False, False
    if not healthy_tag_enabled:
        return calories_kcal, calories_description, calories_incomplete, False
    return calories_kcal, calories_description, calories_incomplete, healthy_tag
