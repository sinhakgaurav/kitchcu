#!/usr/bin/env python3
"""Seed a large demo dataset for full UI / report verification.

Creates multiple owners, many kitchens (nearby search), dishes (all categories),
orders (all statuses), and WhatsApp drafts. Idempotent — skips existing
kitchens/dishes by name and adds orders/drafts until each target is reached.

Usage:
  python scripts/seed-bulk-data.py
  CKAC_BULK_KITCHENS=30 CKAC_BULK_FULL=1 python scripts/seed-bulk-data.py
  CKAC_BULK_ORDERS=300 python scripts/seed-bulk-data.py
  $env:CKAC_BULK_OWNERS=5; .\\scripts\\seed-bulk-data.ps1

Requires: docker compose up (gateway + postgres). The primary demo owner is
created automatically, so running seed-dev-data.py first is optional.
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
from seed_common import (  # noqa: E402
    ApiError,
    cuisine_map,
    dish_create_payload,
    ensure_dish_recipes,
    ensure_ingredients,
    login_owner,
    log,
    request,
    resolve_postgres_container,
    wait_for_gateway,
)
from seed_platform_extras import seed_kitchen_integrations, seed_kitchen_modules, seed_platform_extras  # noqa: E402
from ingredient_demo_data import DEMO_PANTRY, DISH_PREP_STEPS, DISH_RECIPES  # noqa: E402

def env_int(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise SystemExit(f"{name} must be at least {minimum}, got {value}")
    return value


BULK_KITCHENS = env_int("CKAC_BULK_KITCHENS", 30, minimum=1)
BULK_OWNERS = env_int("CKAC_BULK_OWNERS", 0)
BULK_KITCHENS_PER_OWNER = env_int("CKAC_BULK_KITCHENS_PER_OWNER", 3, minimum=1)
BULK_ORDERS = env_int("CKAC_BULK_ORDERS", 250)
BULK_DRAFTS = env_int("CKAC_BULK_DRAFTS", 25)
BULK_ORDERS_PER_OWNER = env_int("CKAC_BULK_ORDERS_PER_OWNER", 40)
BULK_DRAFTS_PER_OWNER = env_int("CKAC_BULK_DRAFTS_PER_OWNER", 5)
BULK_ORDERS_PER_KITCHEN = env_int("CKAC_BULK_ORDERS_PER_KITCHEN", 40)
BULK_DRAFTS_PER_KITCHEN = env_int("CKAC_BULK_DRAFTS_PER_KITCHEN", 5)
BULK_DISHES_PER_KITCHEN = env_int("CKAC_BULK_DISHES_PER_KITCHEN", 6, minimum=1)
BACKDATE_DAYS = env_int("CKAC_BULK_BACKDATE_DAYS", 30)
BULK_FULL = os.environ.get("CKAC_BULK_FULL", "1").strip().lower() not in ("0", "false", "no")

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
            # Customer pays full logistics fee — choice required (P34).
            # COD cannot be prepaid; UPI/online can be either.
            if payment == "cod":
                payload["delivery_fee_payment"] = "pay_on_delivery"
            else:
                payload["delivery_fee_payment"] = rng.choice(["prepaid", "pay_on_delivery"])
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
                resolve_postgres_container(),
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
            timeout=180,
        )
        if proc.returncode == 0:
            log(f"  Backdated orders over {BACKDATE_DAYS} days for reporting.")
        else:
            log(f"  ! Backdate skipped: {proc.stderr.strip() or proc.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log(f"  ! Backdate skipped ({exc})")


def primary_kitchen(kitchens: list[dict]) -> dict:
    return next((k for k in kitchens if k.get("code") == DEMO_KITCHEN_CODE), kitchens[0])


def ensure_kitchen_complete(
    token: str,
    kitchen: dict,
    dishes: list[dict],
    *,
    orders_target: int,
    drafts_target: int,
    with_modules: bool = True,
) -> dict[str, str]:
    """Full menu + pantry + recipes + orders + drafts + per-kitchen integrations."""
    kid = kitchen["id"]
    log(f"  [{kitchen['code']}] {kitchen['name']}")
    dish_ids = ensure_dishes(token, kid, dishes)
    log(f"    menu: {len(dish_ids)} dishes")
    ingredient_ids = ensure_ingredients(token, kid, DEMO_PANTRY)
    ensure_dish_recipes(token, kid, dish_ids, DISH_RECIPES, ingredient_ids, DISH_PREP_STEPS)
    log(f"    pantry: {len(ingredient_ids)} ingredients, recipes on {len(DISH_RECIPES)} dishes")
    ensure_orders(token, kid, dish_ids, orders_target)
    ensure_drafts(token, kid, drafts_target)
    backdate_orders(kid)
    if with_modules:
        seed_kitchen_modules(token, kid, dish_ids)
        first_dish = next(iter(dish_ids.values()), None)
        seed_kitchen_integrations(
            token,
            kid,
            kitchen["name"],
            kitchen_code=kitchen.get("code"),
            dish_id=first_dish,
        )
    return dish_ids


def main() -> None:
    owner_count = min(BULK_OWNERS, len(EXTRA_OWNERS))
    if BULK_OWNERS > len(EXTRA_OWNERS):
        log(
            f"Requested {BULK_OWNERS} extra owners, but only {len(EXTRA_OWNERS)} "
            "deterministic owner profiles are available; using all available profiles."
        )

    log("CKAC bulk seed")
    log("=" * 50)
    mode = "full data per kitchen" if BULK_FULL else "primary full + mini secondary menus"
    log(
        f"Mode: {mode} | {BULK_KITCHENS} demo-owner kitchens, {owner_count} extra owners x "
        f"{BULK_KITCHENS_PER_OWNER} kitchens"
    )
    if BULK_FULL:
        log(
            f"Per kitchen: full menu, pantry, {BULK_ORDERS_PER_KITCHEN} orders, "
            f"{BULK_DRAFTS_PER_KITCHEN} drafts, integrations"
        )
    else:
        log(
            f"Primary: {BULK_ORDERS} orders / {BULK_DRAFTS} drafts | "
            f"Secondary: {BULK_DISHES_PER_KITCHEN} dishes"
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
    all_dishes = enriched_dishes()
    primary_dish_ids: dict[str, str] = {}

    if BULK_FULL:
        log("")
        log(f"Full seed for {len(demo_kitchens)} kitchens (demo owner)")
        log("-" * 50)
        for k in demo_kitchens:
            dish_ids = ensure_kitchen_complete(
                demo_token,
                k,
                all_dishes,
                orders_target=BULK_ORDERS_PER_KITCHEN,
                drafts_target=BULK_DRAFTS_PER_KITCHEN,
            )
            if k["id"] == primary["id"]:
                primary_dish_ids = dish_ids
        if not primary_dish_ids:
            primary_dish_ids = ensure_dishes(demo_token, primary["id"], all_dishes)
    else:
        log(f"Primary kitchen: {primary['code']} — {primary['name']}")
        primary_dish_ids = ensure_dishes(demo_token, primary["id"], all_dishes)
        log(f"Primary menu: {len(primary_dish_ids)} dishes")

        primary_ingredient_ids = ensure_ingredients(demo_token, primary["id"], DEMO_PANTRY)
        ensure_dish_recipes(
            demo_token, primary["id"], primary_dish_ids, DISH_RECIPES, primary_ingredient_ids, DISH_PREP_STEPS
        )
        log(f"Primary pantry: {len(primary_ingredient_ids)} ingredients")

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

    seed_platform_extras(
        owner_token=demo_token,
        kitchen_id=primary["id"],
        dish_ids=primary_dish_ids,
        kitchen_name=primary["name"],
    )

    # Additional owners — more kitchens for nearby density
    log("")
    log("Extra owners for nearby search diversity:")
    seeded_owners: list[tuple[dict, list[dict]]] = []
    for idx, owner in enumerate(EXTRA_OWNERS[:owner_count]):
        ensure_owner(owner["phone"], owner["name"], owner["email"])
        token = login_owner(owner["phone_e164"], DEMO_OTP)
        specs = owner_kitchen_specs(idx + 1, BULK_KITCHENS_PER_OWNER, owner["name"])
        kitchens = ensure_kitchens_for_owner(token, specs)
        owner_primary_dishes: dict[str, str] = {}
        if BULK_FULL:
            for j, k in enumerate(kitchens):
                dish_ids = ensure_kitchen_complete(
                    token,
                    k,
                    all_dishes,
                    orders_target=BULK_ORDERS_PER_OWNER,
                    drafts_target=BULK_DRAFTS_PER_OWNER,
                )
                if j == 0:
                    owner_primary_dishes = dish_ids
        else:
            subset = all_dishes[: max(BULK_DISHES_PER_KITCHEN, 6)]
            for j, k in enumerate(kitchens):
                chunk = all_dishes[(idx * 5 + j * 3) : (idx * 5 + j * 3) + BULK_DISHES_PER_KITCHEN]
                if not chunk:
                    chunk = subset
                dish_ids = ensure_dishes(token, k["id"], chunk, limit=BULK_DISHES_PER_KITCHEN)
                if j == 0:
                    owner_primary_dishes = dish_ids

            owner_primary = kitchens[0]
            created_orders = ensure_orders(
                token,
                owner_primary["id"],
                owner_primary_dishes,
                BULK_ORDERS_PER_OWNER,
            )
            created_drafts = ensure_drafts(
                token,
                owner_primary["id"],
                BULK_DRAFTS_PER_OWNER,
            )
            backdate_orders(owner_primary["id"])
            log(
                f"  {owner['name']}: {len(kitchens)} kitchen(s), "
                f"{created_orders} new orders, {created_drafts} new drafts"
            )
        seeded_owners.append((owner, kitchens))
        if BULK_FULL:
            log(f"  {owner['name']}: {len(kitchens)} kitchen(s) fully seeded")

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
    total_kitchens = len(demo_kitchens) + sum(len(k) for _, k in seeded_owners)
    log(f"  Kitchens seeded (total): {total_kitchens}")
    log(f"  Nearby kitchens (50km):  {nearby.get('total', 0)}")
    log(f"  Primary menu dishes:    {len(menu_final.get('dishes', []))}")
    log(f"  Primary orders:         {orders_final.get('total', 0)}")
    log(f"  Primary drafts:         {drafts_final.get('total', 0)}")
    log("")
    log("Owner logins (kitchen app http://localhost:13002)")
    log(f"  {DEMO_OWNER['phone']} / {DEMO_OTP} — {DEMO_OWNER['name']} ({primary['code']})")
    for owner, kitchens in seeded_owners:
        kitchen = kitchens[0]
        log(f"  {owner['phone']} / {DEMO_OTP} — {owner['name']} ({kitchen['code']})")
    log("")
    log("Customer app: http://localhost:13001  (#nearby for kitchen list)")


if __name__ == "__main__":
    main()
