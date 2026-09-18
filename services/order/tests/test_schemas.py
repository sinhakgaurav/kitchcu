import uuid

import pytest
from pydantic import ValidationError

from app.models import VALID_TRANSITIONS, can_transition
from app.schemas import OrderItemResponse, OrderStatusUpdateRequest, apply_item_ratings


def test_can_transition_received_to_accepted():
    assert can_transition("received", "accepted") is True


def test_can_transition_received_to_delivered_invalid():
    assert can_transition("received", "delivered") is False


def test_terminal_states_have_no_transitions():
    assert VALID_TRANSITIONS["delivered"] == frozenset()
    assert VALID_TRANSITIONS["cancelled"] == frozenset()


def test_cancel_requires_reason():
    with pytest.raises(ValidationError):
        OrderStatusUpdateRequest(status="cancelled")


def test_cancel_with_reason_valid():
    req = OrderStatusUpdateRequest(status="cancelled", cancel_reason="Customer no-show")
    assert req.cancel_reason == "Customer no-show"


def test_apply_item_ratings_maps_per_dish_and_leaves_unrated_null():
    rated_dish = uuid.uuid4()
    pending_dish = uuid.uuid4()
    items = [
        OrderItemResponse(
            id=uuid.uuid4(),
            dish_id=rated_dish,
            dish_name="Dal",
            quantity=1,
            unit_price=80,
            special_instructions=None,
            prep_time_min=15,
        ),
        OrderItemResponse(
            id=uuid.uuid4(),
            dish_id=pending_dish,
            dish_name="Rice",
            quantity=2,
            unit_price=40,
            special_instructions=None,
            prep_time_min=10,
        ),
    ]
    out = apply_item_ratings(items, {rated_dish: (5, 4)})
    assert out[0].rating_home_taste == 5
    assert out[0].rating_quality == 4
    assert out[1].rating_home_taste is None
    assert out[1].rating_quality is None
