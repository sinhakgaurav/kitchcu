"""Unit tests for tiffin plan config validators."""

import pytest
from pydantic import ValidationError

from app.subscriptions import DishesConfig, SubscriptionPlanCreate


def test_dishes_config_requires_weekday():
    with pytest.raises(ValidationError):
        DishesConfig(weekdays=[])


def test_dishes_config_normalizes_weekdays():
    cfg = DishesConfig(weekdays=[3, 1, 1, 5])
    assert cfg.weekdays == [1, 3, 5]


def test_plan_create_price_positive():
    with pytest.raises(ValidationError):
        SubscriptionPlanCreate(name="X", price_monthly=0)
