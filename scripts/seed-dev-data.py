#!/usr/bin/env python3
"""Seed demo owner, kitchen, menu dishes (with images), and sample orders.

Idempotent — safe to run multiple times after `docker compose up`.

Usage:
  python scripts/seed-dev-data.py
  CKAC_GATEWAY_URL=http://localhost:18000 python scripts/seed-dev-data.py

For a large dataset (orders, drafts, many kitchens):
  python scripts/seed-bulk-data.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import (  # noqa: E402
    CAPTURED_AT,
    DEMO_DISHES,
    DEMO_KITCHEN,
    DEMO_KITCHENS_EXTRA,
    DEMO_KITCHEN_CODE,
    DEMO_ORDERS,
    DEMO_OTP,
    DEMO_OWNER,
)
from seed_common import ApiError, cuisine_map, dish_create_payload, ensure_dish_recipes, ensure_ingredients, login_owner, request, wait_for_gateway  # noqa: E402
from ingredient_demo_data import DEMO_PANTRY, DISH_PREP_STEPS, DISH_RECIPES  # noqa: E402


def ensure_owner() -> None:
    try:
        request(
            "POST",
            "/api/v1/owners/register",
            {
                "phone": DEMO_OWNER["phone"],
                "name": DEMO_OWNER["name"],
                "email": DEMO_OWNER["email"],
            },
        )
        print(f"Registered demo owner {DEMO_OWNER['name']} ({DEMO_OWNER['phone_e164']})")
    except ApiError as exc:
        if "409" in str(exc) or "already" in str(exc).lower():
            print(f"Demo owner already exists ({DEMO_OWNER['phone_e164']})")
        else:
            raise


def ensure_kitchens(token: str) -> dict:
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    existing_names = {k["name"] for k in kitchens}

    if not kitchens:
        kitchen = request("POST", "/api/v1/kitchens", DEMO_KITCHEN, token=token)
        print(f"Created kitchen {kitchen['code']} - {kitchen['name']}")
        kitchens = [kitchen]

    for extra in DEMO_KITCHENS_EXTRA:
        if extra["name"] not in existing_names:
            k = request("POST", "/api/v1/kitchens", extra, token=token)
            print(f"Created kitchen {k['code']} - {k['name']}")
            kitchens.append(k)

    primary = next((k for k in kitchens if k.get("code") == DEMO_KITCHEN_CODE), kitchens[0])
    print(f"Primary demo kitchen: {primary['code']} - {primary['name']} ({len(kitchens)} total)")
    return primary


def category_map(token: str, kitchen_id: str) -> dict[str, str]:
    categories = request("GET", f"/api/v1/kitchens/{kitchen_id}/categories", token=token)
    return {c["slug"]: c["id"] for c in categories}


def ensure_dishes(token: str, kitchen_id: str) -> dict[str, str]:
    menu = request("GET", f"/api/v1/kitchens/{kitchen_id}/menu")
    existing = {d["name"]: d["id"] for d in menu.get("dishes", [])}
    cats = category_map(token, kitchen_id)
    cuisines = cuisine_map(token, kitchen_id)
    created = 0

    for dish in DEMO_DISHES:
        if dish["name"] in existing:
            continue
        payload = dish_create_payload(
            dish,
            category_ids=cats,
            cuisine_ids=cuisines,
            captured_at=CAPTURED_AT,
        )
        resp = request("POST", f"/api/v1/kitchens/{kitchen_id}/dishes", payload, token=token)
        existing[dish["name"]] = resp["id"]
        created += 1
        print(f"  + dish: {dish['name']}")

    if created == 0:
        print(f"Menu already has {len(existing)} dishes - skipped dish creation.")
    else:
        print(f"Added {created} dishes with live-capture images.")

    return existing


def ensure_orders(token: str, kitchen_id: str, dish_ids: dict[str, str]) -> None:
    orders_resp = request("GET", f"/api/v1/kitchens/{kitchen_id}/orders", token=token)
    if orders_resp.get("total", 0) >= len(DEMO_ORDERS):
        print(f"Sample orders already exist ({orders_resp['total']}) - skipped.")
        return

    status_chain: dict[str, list[str]] = {
        "received": [],
        "preparing": ["accepted", "preparing"],
        "delivered": ["accepted", "preparing", "ready", "delivered"],
    }

    for spec in DEMO_ORDERS:
        items = []
        for item in spec["items"]:
            dish_id = dish_ids.get(item["dish_name"])
            if not dish_id:
                print(f"  ! skip order item - dish not found: {item['dish_name']}")
                continue
            items.append({"dish_id": dish_id, "quantity": item["quantity"]})
        if not items:
            continue

        payload = {
            "items": items,
            "delivery_type": spec["delivery_type"],
            "payment_method": spec["payment_method"],
            "delivery_fee": spec["delivery_fee"],
            "customer_name": spec["customer_name"],
        }
        if spec.get("customer_phone"):
            payload["customer_phone"] = spec["customer_phone"]
        if spec["delivery_type"] == "delivery" and spec.get("delivery_fee", 0) > 0:
            payload["delivery_fee_accepted"] = True

        order = request("POST", f"/api/v1/kitchens/{kitchen_id}/orders/manual", payload, token=token)
        target = spec["target_status"]
        for status in status_chain.get(target, []):
            order = request(
                "PATCH",
                f"/api/v1/orders/{order['id']}/status",
                {"status": status},
                token=token,
            )
        print(f"  + order {order['order_code']} -> {target} ({spec['customer_name']})")


def main() -> None:
    print("CKAC dev seed")
    print("=" * 40)
    wait_for_gateway()
    ensure_owner()
    token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    print("Authenticated demo owner.")
    kitchen = ensure_kitchens(token)
    dish_ids = ensure_dishes(token, kitchen["id"])
    ingredient_ids = ensure_ingredients(token, kitchen["id"], DEMO_PANTRY)
    ensure_dish_recipes(token, kitchen["id"], dish_ids, DISH_RECIPES, ingredient_ids, DISH_PREP_STEPS)
    ensure_orders(token, kitchen["id"], dish_ids)

    print()
    print("Demo credentials")
    print("-" * 40)
    print(f"  Owner phone : {DEMO_OWNER['phone']}  (E.164: {DEMO_OWNER['phone_e164']})")
    print(f"  OTP (dev)   : {DEMO_OTP}")
    print(f"  Kitchen code: {kitchen.get('code', DEMO_KITCHEN_CODE)}")
    print(f"  Customer app: {os.environ.get('VITE_CUSTOMER_APP_URL', 'http://localhost:13001')}")
    print(f"  Kitchen app:  {os.environ.get('VITE_KITCHEN_APP_URL', 'http://localhost:13002')}/login")
    print()
    print("For large dataset: python scripts/seed-bulk-data.py")
    print("Seed complete.")


if __name__ == "__main__":
    main()
