"""Kitchen vs customer delivery cost share (CEO/CPO product rules).

In range (distance ≤ max_delivery_radius_km):
  Kitchen bears 100% — customer fee is always 0.

Out of range:
  If cart meets min_order_for_free_delivery, kitchen bears
  ``delivery_subsidy_percent`` of the logistics cost; customer pays the rest.
  Otherwise customer bears 100%.
"""

from __future__ import annotations

from typing import Any


def split_delivery_cost(
    *,
    gross_fee: float,
    in_range: bool,
    subtotal: float,
    min_order_for_subsidy: float | None,
    subsidy_percent: float,
) -> dict[str, Any]:
    """Return customer_fee, owner_fee, payer (owner|customer|shared), and breakdown."""
    gross = round(max(0.0, float(gross_fee)), 2)
    pct = max(0.0, min(100.0, float(subsidy_percent)))

    if in_range:
        return {
            "customer_fee": 0.0,
            "owner_fee": gross,
            "payer": "owner",
            "gross_fee": gross,
            "subsidy_percent_applied": 100.0,
            "rule": "in_range_kitchen_bears_full",
        }

    qualifies = (
        min_order_for_subsidy is not None
        and float(subtotal) >= float(min_order_for_subsidy)
        and pct > 0
        and gross > 0
    )
    if not qualifies:
        return {
            "customer_fee": gross,
            "owner_fee": 0.0,
            "payer": "customer",
            "gross_fee": gross,
            "subsidy_percent_applied": 0.0,
            "rule": "extended_customer_bears_full",
            "min_order_for_subsidy": min_order_for_subsidy,
            "subtotal": float(subtotal),
        }

    owner_fee = round(gross * pct / 100.0, 2)
    customer_fee = round(gross - owner_fee, 2)
    if customer_fee <= 0:
        payer = "owner"
        customer_fee = 0.0
        owner_fee = gross
    elif owner_fee <= 0:
        payer = "customer"
        owner_fee = 0.0
        customer_fee = gross
    else:
        payer = "shared"

    return {
        "customer_fee": customer_fee,
        "owner_fee": owner_fee,
        "payer": payer,
        "gross_fee": gross,
        "subsidy_percent_applied": pct,
        "rule": "extended_min_order_kitchen_subsidy",
        "min_order_for_subsidy": float(min_order_for_subsidy) if min_order_for_subsidy is not None else None,
        "subtotal": float(subtotal),
    }
