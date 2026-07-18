"""Delivery fee collection rules (Porter / logistics honesty).

CEO/CPO:
  - shared (kitchen + customer both pay): customer share must be prepaid — no COD.
  - customer only: choose prepaid (pay first) or pay_on_delivery.
  - owner / ₹0 fee: no delivery-fee payment choice.
"""

from __future__ import annotations

from typing import Literal

DeliveryFeePayment = Literal["prepaid", "pay_on_delivery"]


def resolve_delivery_fee_payment(
    *,
    delivery_type: str,
    delivery_payer: str | None,
    customer_fee: float,
    payment_method: str,
    delivery_fee_payment: str | None,
) -> str | None:
    """Validate and return stored delivery_fee_payment (or None).

    Raises ValueError on illegal combinations.
    """
    if delivery_type != "delivery" or float(customer_fee) <= 0:
        return None

    payer = (delivery_payer or "customer").strip().lower()
    method = (payment_method or "cod").strip().lower()
    choice = (delivery_fee_payment or "").strip().lower() or None

    if payer == "owner":
        return None

    if payer == "shared":
        # Kitchen and customer share — collect customer share before logistics.
        if method == "cod":
            raise ValueError(
                "Shared delivery cost requires prepaid payment (UPI/online). "
                "Cash on delivery is not allowed when kitchen and customer split the fee."
            )
        if choice and choice != "prepaid":
            raise ValueError("Shared delivery cost must use delivery_fee_payment=prepaid")
        return "prepaid"

    # customer bears full logistics fee
    if choice not in ("prepaid", "pay_on_delivery"):
        raise ValueError(
            "When you pay the full delivery fee, choose delivery_fee_payment="
            "'prepaid' (pay first) or 'pay_on_delivery'"
        )
    if choice == "prepaid" and method == "cod":
        raise ValueError("Pay-first delivery fee requires UPI or online payment (not COD)")
    return choice


def porter_requires_prepaid_capture(
    *,
    delivery_mode: str | None,
    delivery_fee_payment: str | None,
    delivery_payer: str | None,
    customer_fee: float,
) -> bool:
    """True when Porter/platform book must wait for captured prepaid payment."""
    if (delivery_mode or "") != "platform":
        return False
    if float(customer_fee) <= 0:
        return False
    if (delivery_payer or "") == "shared":
        return True
    return (delivery_fee_payment or "") == "prepaid"
