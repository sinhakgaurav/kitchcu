#!/usr/bin/env python3
"""Seed a large demo dataset for full UI / report verification.

Creates many kitchens (nearby search), dishes (all categories), orders (all
statuses), and WhatsApp drafts. Idempotent — skips existing kitchens/dishes by
name; adds orders until target count is reached.

Usage:
  python scripts/seed-bulk-data.py
  CKAC_BULK_ORDERS=300 python scripts/seed-bulk-data.py

Requires: docker compose up (gateway + postgres) and scripts/seed-dev-data.py run once.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bulk_demo_data import (  # noqa: E402
    CUSTOMER_NAMES,
    EXTRA_OWNERS,
    STATUS_CHAINS,
    WHATSAPP_MESSAGES,
    captured_at,
    enriched_dishes,
    order_status_plan,
    owner_kitchen_specs,
)
from demo_data import DEMO_KITCHEN_CODE, DEMO_OTP, DEMO_OWNER  # noqa: E402
from seed_common import ApiError, cuisine_map, dish_create_payload, ensure_dish_recipes, ensure_ingredients, login_owner, request, wait_for_gateway  # noqa: E402
from ingredient_demo_data import DEMO_PANTRY, DISH_PREP_STEPS, DISH_RECIPES  # noqa: E402

BULK_KITCHENS = int(os.environ.get("CKAC_BULK_KITCHENS", "22"))
BULK_OWNERS = int(os.environ.get("CKAC_BULK_OWNERS", "5"))
BULK_KITCHENS_PER_OWNER = int(os.environ.get("CKAC_BULK_KITCHENS_PER_OWNER", "3"))
BULK_ORDERS = int(os.environ.get("CKAC_BULK_ORDERS", "250"))
BULK_DRAFTS = int(os.environ.get("CKAC_BULK_DRAFTS", "25"))
BULK_DISHES_PER_KITCHEN = int(os.environ.get("CKAC_BULK_DISHES_PER_KITCHEN", "6"))
BACKDATE_DAYS = int(os.environ.get("CKAC_BULK_BACKDATE_DAYS", "30"))
POSTGRES_CONTAINER = os.environ.get("CKAC_POSTGRES_CONTAINER", "ckac-postgres-1")

random.seed(42)


def log(msg: str) -> None:
    print(msg, flush=True)


def ensure_owner(phone: str, name: str, email: str) -> None:
    try:
        request(
            "POST",
            "/api/v1/owners/register",
            {"phone": phone, "name": name, "email": email},
        )
        log(f"  Registered owner {name} ({phone})")
    except ApiError as exc:
        if "409" in str(exc) or "already" in str(exc).lower():
            pass
        else:
            raise


def list_kitchens(token: str) -> list[dict]:
    return request("GET", "/api/v1/kitchens/me", token=token)


def ensure_kitchens_for_owner(token: str, specs: list[dict]) -> list[dict]:
    kitchens = list_kitchens(token)
    existing = {k["name"] for k in kitchens}
    for spec in specs:
        if spec["name"] in existing:
            continue
        k = request("POST", "/api/v1/kitchens", spec, token=token)
        kitchens.append(k)
        existing.add(k["name"])
        log(f"  + kitchen {k['code']} - {k['name']}")
    return kitchens


def category_map(token: str, kitchen_id: str) -> dict[str, str]:
    categories = request("GET", f"/api/v1/kitchens/{kitchen_id}/categories", token=token)
    return {c["slug"]: c["id"] for c in categories}


def menu_dish_names(kitchen_id: str) -> set[str]:
    menu = request("GET", f"/api/v1/kitchens/{kitchen_id}/menu")
    return {d["name"] for d in menu.get("dishes", [])}


def ensure_dishes(
    token: str,
    kitchen_id: str,
    dishes: list[dict],
    *,
    limit: int | None = None,
) -> dict[str, str]:
    existing_names = menu_dish_names(kitchen_id)
    cats = category_map(token, kitchen_id)
    cuisines = cuisine_map(token, kitchen_id)
    dish_ids: dict[str, str] = {}
    menu = request("GET", f"/api/v1/kitchens/{kitchen_id}/menu")
    for d in menu.get("dishes", []):
        dish_ids[d["name"]] = d["id"]

    added = 0
    target = dishes[:limit] if limit else dishes
    for i, dish in enumerate(target):
        if dish["name"] in existing_names:
            continue
        payload = dish_create_payload(
            dish,
            category_ids=cats,
            cuisine_ids=cuisines,
            captured_at=captured_at(),
        )
        resp = request("POST", f"/api/v1/kitchens/{kitchen_id}/dishes", payload, token=token)
        dish_ids[dish["name"]] = resp["id"]
        existing_names.add(dish["name"])
        added += 1
        if added % 10 == 0:
            log(f"    ... {added} dishes added")

    if added:
        log(f"  Added {added} dishes to kitchen {kitchen_id[:8]}...")
    return dish_ids


def pick_order_items(dish_ids: dict[str, str], rng: random.Random) -> list[dict]:
    names = list(dish_ids.keys())
    rng.shuffle(names)
    count = rng.randint(1, min(3, len(names)))
    items = []
    for name in names[:count]:
        items.append({"dish_id": dish_ids[name], "quantity": rng.randint(1, 3)})
    return items


def advance_order(token: str, order_id: str, chain_key: str) -> None:
    chain = STATUS_CHAINS.get(chain_key, [])
    for status in chain:
        body: dict = {"status": status}
        if status == "cancelled":
            body["cancel_reason"] = "Customer cancelled / item unavailable"
        request("PATCH", f"/api/v1/orders/{order_id}/status", body, token=token)


def ensure_orders(token: str, kitchen_id: str, dish_ids: dict[str, str], target: int) -> int:
    if not dish_ids:
        log("  ! No dishes — skipping orders")
        return 0

    orders_resp = request("GET", f"/api/v1/kitchens/{kitchen_id}/orders", token=token)
    current = orders_resp.get("total", 0)
    if current >= target:
        log(f"  Orders already at {current} (target {target}) — skipped.")
        return 0

    need = target - current
    plan = order_status_plan(need)
    rng = random.Random(42)
    created = 0

    # Build a repeat-customer pool so retention analytics (repeat rate, VIPs,
    # churn/win-back) reflect real cloud-kitchen behaviour instead of every
    # order being an anonymous one-off. A few customers order frequently
    # (Pareto), most order a handful of times, ~15% stay anonymous.
    pool_size = max(8, need // 6)
    customer_pool = [
        (rng.choice(CUSTOMER_NAMES), f"+9198{rng.randint(10000000, 99999999)}")
        for _ in range(pool_size)
    ]
    pool_weights = [pool_size - idx for idx in range(pool_size)]

    log(f"  Creating {need} orders (current {current}, target {target})...")
    for i, chain_key in enumerate(plan):
        delivery = "delivery" if chain_key in ("out_for_delivery", "delivered_delivery") or rng.random() < 0.45 else "pickup"
        payment = rng.choice(["cod", "upi", "online"])
        delivery_fee = 40.0 if delivery == "delivery" else 0.0
        if rng.random() < 0.15:
            cust_name, cust_phone = rng.choice(CUSTOMER_NAMES), None
        else:
            cust_name, cust_phone = rng.choices(customer_pool, weights=pool_weights, k=1)[0]
        payload = {
            "items": pick_order_items(dish_ids, rng),
            "delivery_type": delivery,
            "payment_method": payment,
            "delivery_fee": delivery_fee,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
        }
        if delivery == "delivery" and delivery_fee > 0:
            payload["delivery_fee_accepted"] = True
        order = request("POST", f"/api/v1/kitchens/{kitchen_id}/orders/manual", payload, token=token)
        advance_order(token, order["id"], chain_key)
        created += 1
        if created % 25 == 0:
            log(f"    ... {created}/{need} orders")

    log(f"  Created {created} orders.")
    return created


def ensure_drafts(token: str, kitchen_id: str, target: int) -> int:
    drafts_resp = request("GET", f"/api/v1/kitchens/{kitchen_id}/orders/drafts", token=token)
    current = drafts_resp.get("total", 0)
    if current >= target:
        log(f"  Drafts already at {current} (target {target}) — skipped.")
        return 0

    need = min(target - current, len(WHATSAPP_MESSAGES))
    created = 0
    for msg in WHATSAPP_MESSAGES[:need]:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
            {"message_text": msg, "source": "whatsapp"},
            token=token,
        )
        created += 1
    log(f"  Created {created} WhatsApp drafts.")
    return created


def backdate_orders(kitchen_id: str) -> None:
    """Spread order created_at over the last N days for report-style charts."""
    if BACKDATE_DAYS <= 0:
        return
    sql = f"""
    WITH ranked AS (
      SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn,
             COUNT(*) OVER () AS total
      FROM ckac_orders.orders
      WHERE kitchen_id = '{kitchen_id}'::uuid
    )
    UPDATE ckac_orders.orders o
    SET created_at = NOW() - ((r.total - r.rn) * {BACKDATE_DAYS} / GREATEST(r.total, 1)) * INTERVAL '1 day'
                        - (random() * INTERVAL '12 hours'),
        updated_at = NOW() - ((r.total - r.rn) * {BACKDATE_DAYS} / GREATEST(r.total, 1)) * INTERVAL '1 day'
    FROM ranked r
    WHERE o.id = r.id;
    """
    try:
        proc = subprocess.run(
            [
                "docker",
                "exec",
                POSTGRES_CONTAINER,
                "psql",
                "-U",
                "ckac",
                "-d",
                "ckac",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            log(f"  Backdated orders over {BACKDATE_DAYS} days for reporting.")
        else:
            log(f"  ! Backdate skipped: {proc.stderr.strip() or proc.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log(f"  ! Backdate skipped ({exc})")


def primary_kitchen(kitchens: list[dict]) -> dict:
    return next((k for k in kitchens if k.get("code") == DEMO_KITCHEN_CODE), kitchens[0])


def main() -> None:
    log("CKAC bulk seed")
    log("=" * 50)
    log(
        f"Targets: {BULK_KITCHENS} demo kitchens, {BULK_OWNERS} extra owners x "
        f"{BULK_KITCHENS_PER_OWNER} kitchens, {BULK_ORDERS} orders, {BULK_DRAFTS} drafts"
    )
    log("")

    wait_for_gateway()

    # Demo owner — expand kitchens + full menu + orders
    ensure_owner(DEMO_OWNER["phone"], DEMO_OWNER["name"], DEMO_OWNER["email"])
    demo_token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    log(f"Logged in as {DEMO_OWNER['name']}")

    demo_specs = owner_kitchen_specs(0, BULK_KITCHENS)
    demo_kitchens = ensure_kitchens_for_owner(demo_token, demo_specs)
    log(f"Demo owner has {len(demo_kitchens)} kitchen(s)")

    primary = primary_kitchen(demo_kitchens)
    log(f"Primary kitchen: {primary['code']} — {primary['name']}")

    all_dishes = enriched_dishes()
    primary_dish_ids = ensure_dishes(demo_token, primary["id"], all_dishes)
    log(f"Primary menu: {len(primary_dish_ids)} dishes")

    primary_ingredient_ids = ensure_ingredients(demo_token, primary["id"], DEMO_PANTRY)
    ensure_dish_recipes(demo_token, primary["id"], primary_dish_ids, DISH_RECIPES, primary_ingredient_ids, DISH_PREP_STEPS)
    log(f"Primary pantry: {len(primary_ingredient_ids)} ingredients")

    # Mini menus on other demo kitchens (customer browse + nearby cards)
    subset = all_dishes[: max(BULK_DISHES_PER_KITCHEN, 6)]
    secondary = 0
    for k in demo_kitchens:
        if k["id"] == primary["id"]:
            continue
        offset = secondary * 3
        rotated = all_dishes[offset : offset + BULK_DISHES_PER_KITCHEN]
        if len(rotated) < BULK_DISHES_PER_KITCHEN:
            rotated = (rotated + all_dishes)[:BULK_DISHES_PER_KITCHEN]
        ensure_dishes(demo_token, k["id"], rotated, limit=BULK_DISHES_PER_KITCHEN)
        secondary += 1
    log(f"Seeded mini menus on {secondary} secondary kitchens")

    ensure_orders(demo_token, primary["id"], primary_dish_ids, BULK_ORDERS)
    ensure_drafts(demo_token, primary["id"], BULK_DRAFTS)
    backdate_orders(primary["id"])

    # Additional owners — more kitchens for nearby density
    log("")
    log("Extra owners for nearby search diversity:")
    for idx, owner in enumerate(EXTRA_OWNERS[:BULK_OWNERS]):
        ensure_owner(owner["phone"], owner["name"], owner["email"])
        token = login_owner(owner["phone_e164"], DEMO_OTP)
        specs = owner_kitchen_specs(idx + 1, BULK_KITCHENS_PER_OWNER, owner["name"])
        kitchens = ensure_kitchens_for_owner(token, specs)
        for j, k in enumerate(kitchens):
            chunk = all_dishes[(idx * 5 + j * 3) : (idx * 5 + j * 3) + BULK_DISHES_PER_KITCHEN]
            if not chunk:
                chunk = subset
            ensure_dishes(token, k["id"], chunk, limit=BULK_DISHES_PER_KITCHEN)
        log(f"  {owner['name']}: {len(kitchens)} kitchen(s)")

    # Summary
    nearby = request(
        "GET",
        f"/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&limit=30&max_km=50&sort=asc",
    )
    orders_final = request("GET", f"/api/v1/kitchens/{primary['id']}/orders", token=demo_token)
    drafts_final = request("GET", f"/api/v1/kitchens/{primary['id']}/orders/drafts", token=demo_token)
    menu_final = request("GET", f"/api/v1/kitchens/{primary['id']}/menu")

    log("")
    log("Bulk seed complete")
    log("-" * 50)
    log(f"  Nearby kitchens (50km): {nearby.get('total', 0)}")
    log(f"  Primary menu dishes:    {len(menu_final.get('dishes', []))}")
    log(f"  Primary orders:         {orders_final.get('total', 0)}")
    log(f"  Primary drafts:         {drafts_final.get('total', 0)}")
    log("")
    log("Demo login (kitchen app http://localhost:13002)")
    log(f"  Phone: {DEMO_OWNER['phone']}  OTP: {DEMO_OTP}")
    log(f"  Kitchen: {primary['code']} — {primary['name']}")
    log("")
    log("Customer app: http://localhost:13001  (#nearby for kitchen list)")


if __name__ == "__main__":
    main()
