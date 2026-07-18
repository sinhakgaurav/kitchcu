"""Unit tests for golden-day selection gates (no DB)."""

import uuid
from datetime import date, timedelta

from app.golden_day import DishDayMetrics, select_golden_candidates


def _day(dish: uuid.UUID, name: str, offset: int, qty: int, rating: float | None, sentiment: float) -> DishDayMetrics:
    return DishDayMetrics(
        dish_id=dish,
        dish_name=name,
        day=date(2026, 7, 10) - timedelta(days=offset),
        order_qty=qty,
        order_count=max(1, qty // 2),
        avg_rating=rating,
        rating_count=2 if rating is not None else 0,
        sentiment_score=sentiment,
        sentiment_label="positive" if sentiment >= 0.62 else "neutral",
        comment_count=1,
        sample_comments=["amazing homemade taste"],
    )


def test_selects_peak_day_with_strong_rating_and_sentiment():
    dish = uuid.uuid4()
    metrics = [
        _day(dish, "Dal", 0, 10, 4.8, 0.85),  # golden
        _day(dish, "Dal", 1, 3, 4.0, 0.55),
        _day(dish, "Dal", 2, 2, 3.9, 0.50),
        _day(dish, "Dal", 3, 4, 4.1, 0.60),
    ]
    winners = select_golden_candidates(metrics)
    assert len(winners) == 1
    assert winners[0][0].order_qty == 10
    assert winners[0][0].day == date(2026, 7, 10)


def test_rejects_when_rating_too_low():
    dish = uuid.uuid4()
    metrics = [
        _day(dish, "Dal", 0, 12, 3.5, 0.9),
        _day(dish, "Dal", 1, 3, 4.0, 0.5),
        _day(dish, "Dal", 2, 2, 4.0, 0.5),
    ]
    assert select_golden_candidates(metrics) == []


def test_rejects_insufficient_history():
    dish = uuid.uuid4()
    metrics = [
        _day(dish, "Dal", 0, 10, 4.8, 0.9),
        _day(dish, "Dal", 1, 2, 4.5, 0.8),
    ]
    assert select_golden_candidates(metrics) == []
