import pytest
from pydantic import ValidationError

from app.models import VALID_TRANSITIONS, can_transition
from app.schemas import OrderStatusUpdateRequest


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
