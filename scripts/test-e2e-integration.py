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

    # Probe a dish that actually carries prep steps — draft dishes are absent from the
    # public menu, so picking by name alone can land on a dish with no recipe.
    probe_name = next((n for n in DISH_PREP_STEPS if n in dish_ids), None)
    assert_ok(probe_name is not None, "No live dish has prep steps — check DISH_PREP_STEPS")
    recipe_check = request(
        "GET",
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_ids[probe_name]}/recipe",
        token=token,
    )
    assert_ok(len(recipe_check.get("prep_steps", [])) >= 1, "Recipe missing prep steps")
    assert_ok(len(recipe_check.get("lines", [])) >= 1, "Recipe missing ingredient lines")
    print(f"Recipe prep steps: {len(recipe_check['prep_steps'])} · lines: {len(recipe_check['lines'])}")

    # Order a dish whose recipe actually consumes the ingredient starved below, so
    # the shortfall warning and the deduct-on-accept assertions mean something.
    # Naming a dish outright is not safe: one without a live-capture hero stays
    # inactive and never reaches the public menu.
    order_dish_name = next(
        (
            name
            for name, lines in DISH_RECIPES.items()
            if name in dish_ids and any(line[0] == "Lal Mirch" for line in lines)
        ),
        None,
    )
    assert_ok(order_dish_name is not None, "No live dish consumes Lal Mirch — check DISH_RECIPES")

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
            "items": [{"dish_id": dish_ids[order_dish_name], "quantity": 2}],
            "delivery_type": "pickup",
            "payment_method": "cod",
            "customer_name": "E2E Tester",
        },
        token=token,
    )
    order_id = order["id"]
    assert_ok(order["status"] == "received", f"Expected received, got {order['status']}")
    print(f"Order created: {order['order_code']} ({order_dish_name} x2)")

    # Stock warnings before accept
    warnings = request("GET", f"/api/v1/orders/{order_id}/stock-warnings", token=token)
    assert_ok("warnings" in warnings, "Stock warnings response missing")
    print(f"Stock warnings: {len(warnings['warnings'])} (has_shortfall={warnings.get('has_shortfall')})")

    accepted = request(
        "PATCH",
        f"/api/v1/orders/{order_id}/status",
        {"status": "accepted"},
        token=token,
    )
    assert_ok(accepted["status"] == "accepted", "Accept failed")
    print("Order accepted")

    def lal_mirch_stock() -> float:
        row = next(
            i
            for i in request("GET", f"/api/v1/kitchens/{kitchen_id}/ingredients", token=token)["ingredients"]
            if i["id"] == lal_mirch_id
        )
        return float(row["current_stock"])

    # Stock moves on `ready`, not on `accepted` (F19/S15b) — assert both halves,
    # otherwise a deduct that silently stopped firing still looks like a pass.
    if lal_mirch_id:
        assert_ok(lal_mirch_stock() == 5.0, "Stock must not deduct before the order is ready")
        print("Stock unchanged on accept (deduct happens at ready)")

    for next_status in ("preparing", "ready"):
        moved = request(
            "PATCH",
            f"/api/v1/orders/{order_id}/status",
            {"status": next_status},
            token=token,
        )
        assert_ok(moved["status"] == next_status, f"Transition to {next_status} failed")
    print("Order marked ready — stock deduct dispatched")

    if lal_mirch_id:
        settings = request("GET", f"/api/v1/kitchens/{kitchen_id}/stock-settings", token=token)
        mode = settings.get("deduct_mode")
        after = lal_mirch_stock()
        if mode == "prep_batch_only":
            # F19b: bulk kitchens deduct when a prep batch is prepared, so an
            # order must not touch the pantry at all.
            assert_ok(after == 5.0, f"prep_batch_only kitchen must not deduct on ready (got {after}g)")
            print(f"Lal Mirch stock after ready: {after}g (prep_batch_only — no order deduct)")
        else:
            # Recipe needs 5g per plate and the order is for two, against 5g of
            # stock — the deduct clamps at zero rather than going negative.
            assert_ok(after == 0.0, f"Expected Lal Mirch to deduct to 0g on ready, got {after}g")
            print(f"Lal Mirch stock after ready: {after}g (deducted, clamped at 0)")

    # Analytics smoke
    summary = request("GET", f"/api/v1/kitchens/{kitchen_id}/analytics/summary?days=30", token=token)
    assert_ok("gross_revenue" in summary, "Analytics summary failed")
    print(f"Revenue (30d): Rs {summary['gross_revenue']}")

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
