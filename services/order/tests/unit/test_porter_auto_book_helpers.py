"""Unit tests — Porter auto-book ETA helpers (P35)."""

from datetime import UTC, datetime, timedelta

from app.porter_auto_book import compute_order_eta, max_attempts, retry_interval_min


def test_compute_order_eta_delivery_is_prep_plus_delivery():
    start = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)
    ready, delivery_at, delivery_min = compute_order_eta(
        from_time=start,
        prep_min=25,
        delivery_min=20,
        delivery_type="delivery",
    )
    assert ready == start + timedelta(minutes=25)
    assert delivery_at == start + timedelta(minutes=45)
    assert delivery_min == 20


def test_compute_order_eta_pickup_has_no_delivery_at():
    start = datetime(2026, 7, 19, 10, 0, tzinfo=UTC)
    ready, delivery_at, delivery_min = compute_order_eta(
        from_time=start,
        prep_min=30,
        delivery_min=20,
        delivery_type="pickup",
    )
    assert ready == start + timedelta(minutes=30)
    assert delivery_at is None
    assert delivery_min == 0


def test_retry_defaults_bounded():
    assert 1 <= retry_interval_min() <= 30
    assert 1 <= max_attempts() <= 100
