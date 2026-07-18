"""Unit tests for order-side delivery cost share (no DB)."""

from app.cost_share import split_delivery_cost


def test_in_range_kitchen_bears_full():
    r = split_delivery_cost(
        gross_fee=80.0,
        in_range=True,
        subtotal=100.0,
        min_order_for_subsidy=300.0,
        subsidy_percent=50.0,
    )
    assert r["customer_fee"] == 0.0
    assert r["owner_fee"] == 80.0
    assert r["payer"] == "owner"


def test_out_of_range_no_min_order_customer_full():
    r = split_delivery_cost(
        gross_fee=80.0,
        in_range=False,
        subtotal=200.0,
        min_order_for_subsidy=None,
        subsidy_percent=50.0,
    )
    assert r["customer_fee"] == 80.0
    assert r["owner_fee"] == 0.0
    assert r["payer"] == "customer"


def test_out_of_range_min_met_shared_subsidy():
    r = split_delivery_cost(
        gross_fee=100.0,
        in_range=False,
        subtotal=400.0,
        min_order_for_subsidy=349.0,
        subsidy_percent=50.0,
    )
    assert r["customer_fee"] == 50.0
    assert r["owner_fee"] == 50.0
    assert r["payer"] == "shared"


def test_out_of_range_min_not_met_customer_full():
    r = split_delivery_cost(
        gross_fee=100.0,
        in_range=False,
        subtotal=200.0,
        min_order_for_subsidy=349.0,
        subsidy_percent=50.0,
    )
    assert r["customer_fee"] == 100.0
    assert r["owner_fee"] == 0.0
    assert r["payer"] == "customer"
