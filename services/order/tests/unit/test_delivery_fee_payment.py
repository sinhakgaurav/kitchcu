"""Unit tests for delivery fee collection rules."""

import pytest

from app.delivery_fee_payment import porter_requires_prepaid_capture, resolve_delivery_fee_payment


def test_shared_forces_prepaid_rejects_cod():
    assert (
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="shared",
            customer_fee=40.0,
            payment_method="upi",
            delivery_fee_payment=None,
        )
        == "prepaid"
    )
    with pytest.raises(ValueError, match="Shared delivery"):
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="shared",
            customer_fee=40.0,
            payment_method="cod",
            delivery_fee_payment="prepaid",
        )


def test_customer_must_choose_prepaid_or_pod():
    assert (
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="customer",
            customer_fee=80.0,
            payment_method="cod",
            delivery_fee_payment="pay_on_delivery",
        )
        == "pay_on_delivery"
    )
    assert (
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="customer",
            customer_fee=80.0,
            payment_method="online",
            delivery_fee_payment="prepaid",
        )
        == "prepaid"
    )
    with pytest.raises(ValueError, match="choose delivery_fee_payment"):
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="customer",
            customer_fee=80.0,
            payment_method="cod",
            delivery_fee_payment=None,
        )


def test_customer_prepaid_rejects_cod():
    with pytest.raises(ValueError, match="Pay-first"):
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="customer",
            customer_fee=50.0,
            payment_method="cod",
            delivery_fee_payment="prepaid",
        )


def test_owner_or_zero_fee_no_choice():
    assert (
        resolve_delivery_fee_payment(
            delivery_type="delivery",
            delivery_payer="owner",
            customer_fee=0.0,
            payment_method="cod",
            delivery_fee_payment=None,
        )
        is None
    )


def test_porter_gate():
    assert porter_requires_prepaid_capture(
        delivery_mode="platform",
        delivery_fee_payment="prepaid",
        delivery_payer="customer",
        customer_fee=40,
    )
    assert porter_requires_prepaid_capture(
        delivery_mode="platform",
        delivery_fee_payment=None,
        delivery_payer="shared",
        customer_fee=40,
    )
    assert not porter_requires_prepaid_capture(
        delivery_mode="platform",
        delivery_fee_payment="pay_on_delivery",
        delivery_payer="customer",
        customer_fee=40,
    )
