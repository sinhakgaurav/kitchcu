"""Unit tests for tiffin plan config validators."""

import uuid

import pytest
from pydantic import ValidationError

from app.subscriptions import (
    DishesConfig,
    SubscriptionPlanCreate,
    _config_dict,
    validate_plan_dish_selection,
)


def test_dishes_config_requires_weekday():
    with pytest.raises(ValidationError):
        DishesConfig(weekdays=[])


def test_dishes_config_normalizes_weekdays():
    cfg = DishesConfig(weekdays=[3, 1, 1, 5])
    assert cfg.weekdays == [1, 3, 5]


def test_dishes_config_accepts_dish_ids_and_image_url():
    dish_a = uuid.uuid4()
    dish_b = uuid.uuid4()
    cfg = DishesConfig(
        dish_ids=[dish_a, dish_b],
        image_url="https://cdn.example/plans/thali.jpg",
        meals_per_day=2,
    )
    dumped = _config_dict(cfg)
    assert dumped["dish_ids"] == [str(dish_a), str(dish_b)]
    assert dumped["image_url"] == "https://cdn.example/plans/thali.jpg"
    assert dumped["meals_per_day"] == 2


def test_plan_create_allows_rich_description_and_linked_dishes():
    dish_id = uuid.uuid4()
    plan = SubscriptionPlanCreate(
        name="Veg Thali Monthly",
        description="<p>Homestyle thali with <strong>dal + roti</strong></p>",
        plan_type="thali",
        price_monthly=2499,
        dishes_config=DishesConfig(
            dish_ids=[dish_id],
            image_url="https://cdn.example/cover.webp",
        ),
    )
    assert "<strong>" in (plan.description or "")
    assert plan.dishes_config.dish_ids == [dish_id]


def test_plan_create_price_positive():
    with pytest.raises(ValidationError):
        SubscriptionPlanCreate(name="X", price_monthly=0)


def test_single_dish_requires_exactly_one():
    with pytest.raises(ValueError, match="at least one"):
        validate_plan_dish_selection("single_dish", DishesConfig(dish_ids=[]))
    with pytest.raises(ValueError, match="exactly one"):
        validate_plan_dish_selection(
            "single_dish",
            DishesConfig(dish_ids=[uuid.uuid4(), uuid.uuid4()]),
        )
    validate_plan_dish_selection("single_dish", DishesConfig(dish_ids=[uuid.uuid4()]))


def test_combo_requires_at_least_two():
    with pytest.raises(ValueError, match="at least two"):
        validate_plan_dish_selection("combo", DishesConfig(dish_ids=[uuid.uuid4()]))
    validate_plan_dish_selection(
        "combo",
        DishesConfig(dish_ids=[uuid.uuid4(), uuid.uuid4()]),
    )


def test_thali_allows_one_or_more():
    validate_plan_dish_selection("thali", DishesConfig(dish_ids=[uuid.uuid4()]))
    validate_plan_dish_selection(
        "tiffin",
        DishesConfig(dish_ids=[uuid.uuid4(), uuid.uuid4()]),
    )
