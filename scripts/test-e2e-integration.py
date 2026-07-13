#!/usr/bin/env python3
"""End-to-end integration test: owner UI flows via gateway API (F19 + core paths).

Exercises login → ingredients CRUD → recipe → order → stock warnings → accept → deduct.

Usage:
  python scripts/test-e2e-integration.py
  CKAC_GATEWAY_URL=http://localhost:18000 python scripts/test-e2e-integration.py

Requires: docker compose up + scripts/seed-dev-data.py (or bulk seed).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import DEMO_DISHES, DEMO_OTP, DEMO_OWNER  # noqa: E402
from ingredient_demo_data import DEMO_PANTRY, DISH_RECIPES, DISH_PREP_STEPS  # noqa: E402
from seed_common import (  # noqa: E402
    ApiError,
    ensure_dish_recipes,
    ensure_ingredients,
    login_owner,
    request,
    wait_for_gateway,
)


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> None:
    print("kitchCU E2E integration test")
    print("=" * 50)
    wait_for_gateway()

    token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    assert_ok(len(kitchens) > 0, "Owner has no kitchens")
    kitchen = kitchens[0]
    kitchen_id = kitchen["id"]
    print(f"Kitchen: {kitchen.get('code')} — {kitchen.get('name')}")

    # Menu must exist
    menu = request("GET", f"/api/v1/kitchens/{kitchen_id}/menu")
    dishes = menu.get("dishes", [])
    assert_ok(len(dishes) > 0, "Menu has no dishes — run seed-dev-data.py first")
    dish_ids = {d["name"]: d["id"] for d in dishes}
    print(f"Menu dishes: {len(dishes)}")

    # F19 — ingredients + recipes with prep steps
    ingredient_ids = ensure_ingredients(token, kitchen_id, DEMO_PANTRY)
    assert_ok(len(ingredient_ids) >= len(DEMO_PANTRY), "Pantry seed incomplete")
    recipes_set = ensure_dish_recipes(
        token, kitchen_id, dish_ids, DISH_RECIPES, ingredient_ids, DISH_PREP_STEPS
    )
    assert_ok(recipes_set > 0, "No dish recipes set")
    print(f"Ingredients: {len(ingredient_ids)} · Recipes: {recipes_set}")

    paneer_tikka_id = dish_ids.get("Paneer Tikka") or dishes[0]["id"]
    recipe_check = request(
        "GET",
        f"/api/v1/kitchens/{kitchen_id}/dishes/{paneer_tikka_id}/recipe",
        token=token,
    )
    assert_ok(len(recipe_check.get("prep_steps", [])) >= 1, "Recipe missing prep steps")
    assert_ok(len(recipe_check.get("lines", [])) >= 1, "Recipe missing ingredient lines")
    print(f"Recipe prep steps: {len(recipe_check['prep_steps'])} · lines: {len(recipe_check['lines'])}")

    lal_mirch_id = ingredient_ids.get("Lal Mirch")
    if lal_mirch_id:
        before = next(
            i for i in request("GET", f"/api/v1/kitchens/{kitchen_id}/ingredients", token=token)["ingredients"]
            if i["id"] == lal_mirch_id
        )
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/ingredients/{lal_mirch_id}/adjust-stock",
            {"delta": -before["current_stock"] + 5, "reason": "E2E low-stock scenario"},
            token=token,
        )
        print("Adjusted Lal Mirch to 5g for warning test")

    # Create order (received)
    order = request(
        "POST",
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        {
            "items": [{"dish_id": paneer_tikka_id, "quantity": 2}],
            "delivery_type": "pickup",
            "payment_method": "cod",
            "customer_name": "E2E Tester",
        },
        token=token,
    )
    order_id = order["id"]
    assert_ok(order["status"] == "received", f"Expected received, got {order['status']}")
    print(f"Order created: {order['order_code']}")

    # Stock warnings before accept
    warnings = request("GET", f"/api/v1/orders/{order_id}/stock-warnings", token=token)
    assert_ok("warnings" in warnings, "Stock warnings response missing")
    print(f"Stock warnings: {len(warnings['warnings'])} (has_shortfall={warnings.get('has_shortfall')})")

    # Accept → triggers stock deduct via order → catalog internal
    accepted = request(
        "PATCH",
        f"/api/v1/orders/{order_id}/status",
        {"status": "accepted"},
        token=token,
    )
    assert_ok(accepted["status"] == "accepted", "Accept failed")
    print("Order accepted — stock deduct dispatched")

    if lal_mirch_id:
        after = next(
            i for i in request("GET", f"/api/v1/kitchens/{kitchen_id}/ingredients", token=token)["ingredients"]
            if i["id"] == lal_mirch_id
        )
        assert_ok(after["current_stock"] <= 5, "Stock should have deducted on accept")
        print(f"Lal Mirch stock after accept: {after['current_stock']}g")

    # Analytics smoke
    summary = request("GET", f"/api/v1/kitchens/{kitchen_id}/analytics/summary?days=30", token=token)
    assert_ok("total_revenue" in summary, "Analytics summary failed")
    print(f"Revenue (30d): ₹{summary['total_revenue']}")

    # Nearby public discovery
    nearby = request(
        "GET",
        "/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&limit=5",
    )
    assert_ok(nearby.get("total", 0) >= 1, "Nearby search returned no kitchens")
    print(f"Nearby kitchens: {nearby['total']}")

    print("")
    print("E2E integration test PASSED")


if __name__ == "__main__":
    try:
        run()
    except (AssertionError, ApiError) as exc:
        print(f"\nE2E FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
