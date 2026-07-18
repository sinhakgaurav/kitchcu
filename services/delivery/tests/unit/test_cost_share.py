"""Delivery cost-share rules — unit (no DB)."""

from app.cost_share import split_delivery_cost


def test_in_range_kitchen_bears_full():
    r = split_delivery_cost(
        gross_fee=80,
        in_range=True,
        subtotal=100,
        min_order_for_subsidy=200,
        subsidy_percent=50,
    )
    assert r["customer_fee"] == 0.0
    assert r["owner_fee"] == 80.0
    assert r["payer"] == "owner"
    assert r["rule"] == "in_range_kitchen_bears_full"


def test_extended_below_min_order_customer_full():
    r = split_delivery_cost(
        gross_fee=80,
        in_range=False,
        subtotal=150,
        min_order_for_subsidy=200,
        subsidy_percent=50,
    )
    assert r["customer_fee"] == 80.0
    assert r["owner_fee"] == 0.0
    assert r["payer"] == "customer"
    assert r["rule"] == "extended_customer_bears_full"


def test_extended_min_order_met_kitchen_subsidy_percent():
    r = split_delivery_cost(
        gross_fee=80,
        in_range=False,
        subtotal=250,
        min_order_for_subsidy=200,
        subsidy_percent=50,
    )
    assert r["customer_fee"] == 40.0
    assert r["owner_fee"] == 40.0
    assert r["payer"] == "shared"
    assert r["subsidy_percent_applied"] == 50.0


def test_extended_100_percent_subsidy_owner_pays():
    r = split_delivery_cost(
        gross_fee=60,
        in_range=False,
        subtotal=500,
        min_order_for_subsidy=200,
        subsidy_percent=100,
    )
    assert r["customer_fee"] == 0.0
    assert r["owner_fee"] == 60.0
    assert r["payer"] == "owner"
