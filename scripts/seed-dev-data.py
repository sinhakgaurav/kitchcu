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
    DEMO_KITCHEN_CODE,
    DEMO_ORDERS,
    DEMO_OTP,
    DEMO_OWNER,
    DEMO_OWNERS_EXTRA,
    DEMO_ADMIN,
    DEMO_CUSTOMER_ADDRESSES,
    DEMO_CUSTOMERS,
    presence_kitchen_owner_pairs,
    pune_extra_kitchen_spec,
)
from seed_common import (  # noqa: E402
    ApiError,
    cuisine_map,
    dish_create_payload,
    ensure_customer_addresses,
    ensure_dish_recipes,
    ensure_ingredients,
    login_customer,
    login_owner,
    owner_dishes,
    request,
    run_psql,
    wait_for_gateway,
)
from ingredient_demo_data import DEMO_PANTRY, DISH_PREP_STEPS, DISH_RECIPES  # noqa: E402
from seed_platform_extras import seed_kitchen_integrations, seed_kitchen_modules  # noqa: E402


def _register_owner(owner: dict) -> None:
    try:
        request(
            "POST",
            "/api/v1/owners/register",
            {
                "phone": owner["phone"],
                "name": owner["name"],
                "email": owner.get("email"),
            },
        )
        print(f"Registered owner {owner['name']} ({owner['phone_e164']})")
    except ApiError as exc:
        if "409" in str(exc) or "already" in str(exc).lower():
            print(f"Owner already exists ({owner['phone_e164']})")
        else:
            raise


def ensure_owner() -> None:
    _register_owner(DEMO_OWNER)


def retire_orphan_kitchens() -> None:
    """Hide kitchens left on the shared DB by identity pytest (not demo owners)."""
    phones = [
        DEMO_OWNER["phone_e164"],
        *[owner["phone_e164"] for owner in DEMO_OWNERS_EXTRA],
        *[owner["phone_e164"] for owner, _ in presence_kitchen_owner_pairs()],
    ]
    listed = ", ".join("'" + phone.replace("'", "''") + "'" for phone in phones)
    sql = (
        "UPDATE ckac_identity.kitchens AS k "
        "SET status = 'suspended' "
        "FROM ckac_identity.owners AS o "
        "WHERE k.owner_id = o.id "
        f"AND o.phone NOT IN ({listed}) "
        "AND k.status = 'active';"
    )
    ok, err = run_psql(sql)
    if not ok:
        print(f"  ! orphan kitchen cleanup: {err}")
    else:
        print("Retired leftover test kitchens (not owned by demo hosts).")


def ensure_extra_owners() -> list[tuple[dict, dict]]:
    """Register secondary demo owners with one kitchen each (for multi-login UI)."""
    created: list[tuple[dict, dict]] = []
    for owner in DEMO_OWNERS_EXTRA:
        _register_owner(owner)
        token = login_owner(owner["phone_e164"], DEMO_OTP)
        kitchens = request("GET", "/api/v1/kitchens/me", token=token)
        if kitchens:
            kitchen = kitchens[0]
            print(f"  {owner['name']} kitchen: {kitchen.get('code')} - {kitchen.get('name')}")
        else:
            kitchen = request(
                "POST",
                "/api/v1/kitchens",
                pune_extra_kitchen_spec(owner),
                token=token,
            )
            print(f"  Created {kitchen['code']} - {kitchen['name']}")
        try:
            mapped = seed_kitchen_menu(token, kitchen["id"])
            seed_kitchen_modules(token, kitchen["id"], mapped)
            first_dish = next(iter(mapped.values()), None)
            seed_kitchen_integrations(
                token,
                kitchen["id"],
                kitchen.get("name") or owner.get("kitchen_label") or owner["name"],
                kitchen_code=kitchen.get("code"),
                dish_id=first_dish,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (menu/modules seed skipped: {exc})")
        created.append((owner, kitchen))
    return created


def ensure_kitchens(token: str) -> dict:
    """Primary demo owner keeps only Sharma Home Kitchen (CKPNQ001)."""
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    primary = next((k for k in kitchens if k.get("code") == DEMO_KITCHEN_CODE), None)
    if primary is None:
        primary = next((k for k in kitchens if k.get("name") == DEMO_KITCHEN["name"]), None)
    if primary is None:
        primary = request("POST", "/api/v1/kitchens", DEMO_KITCHEN, token=token)
        print(f"Created kitchen {primary['code']} - {primary['name']}")
    print(f"Primary demo kitchen: {primary['code']} - {primary['name']}")
    return primary


def _reassign_kitchen_owner(*, kitchen_name: str, owner_phone_e164: str) -> None:
    escaped_name = kitchen_name.replace("'", "''")
    escaped_phone = owner_phone_e164.replace("'", "''")
    sql = (
        "UPDATE ckac_identity.kitchens AS k "
        "SET owner_id = o.id "
        "FROM ckac_identity.owners AS o "
        f"WHERE k.name = '{escaped_name}' "
        f"AND o.phone = '{escaped_phone}' "
        "AND k.owner_id IS DISTINCT FROM o.id;"
    )
    ok, err = run_psql(sql)
    if not ok:
        print(f"  ! reassign {kitchen_name}: {err}")


def ensure_presence_kitchens() -> list[tuple[dict, dict]]:
    """City / extra Pune kitchens belong to dedicated hosts, not Raj."""
    created: list[tuple[dict, dict]] = []
    print()
    print("Presence kitchens (dedicated owners)")
    print("-" * 40)
    for owner, spec in presence_kitchen_owner_pairs():
        _register_owner(owner)
        token = login_owner(owner["phone_e164"], DEMO_OTP)
        mine = request("GET", "/api/v1/kitchens/me", token=token)
        kitchen = next((k for k in mine if k.get("name") == spec["name"]), None)
        if kitchen is None:
            _reassign_kitchen_owner(
                kitchen_name=spec["name"],
                owner_phone_e164=owner["phone_e164"],
            )
            mine = request("GET", "/api/v1/kitchens/me", token=token)
            kitchen = next((k for k in mine if k.get("name") == spec["name"]), None)
        if kitchen is None:
            kitchen = request("POST", "/api/v1/kitchens", spec, token=token)
            print(f"  Created {kitchen['code']} - {kitchen['name']} ({spec['city']})")
        else:
            print(f"  {owner['name']}: {kitchen.get('code')} - {kitchen.get('name')}")
        try:
            mapped = seed_kitchen_menu(token, kitchen["id"])
            seed_kitchen_modules(token, kitchen["id"], mapped)
            first_dish = next(iter(mapped.values()), None)
            seed_kitchen_integrations(
                token,
                kitchen["id"],
                kitchen.get("name") or spec["name"],
                kitchen_code=kitchen.get("code"),
                dish_id=first_dish,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (menu/modules seed skipped: {exc})")
        created.append((owner, kitchen))
    return created


def category_map(token: str, kitchen_id: str) -> dict[str, str]:
    categories = request("GET", f"/api/v1/kitchens/{kitchen_id}/categories", token=token)
    return {c["slug"]: c["id"] for c in categories}


def seed_kitchen_menu(token: str, kitchen_id: str) -> dict[str, str]:
    dish_ids = ensure_dishes(token, kitchen_id)
    ingredient_ids = ensure_ingredients(token, kitchen_id, DEMO_PANTRY)
    ensure_dish_recipes(token, kitchen_id, dish_ids, DISH_RECIPES, ingredient_ids, DISH_PREP_STEPS)
    return dish_ids


def ensure_dishes(token: str, kitchen_id: str) -> dict[str, str]:
    existing = {d["name"]: d["id"] for d in owner_dishes(token, kitchen_id)}
    cats = category_map(token, kitchen_id)
    cuisines = cuisine_map(token, kitchen_id)
    created = 0
    published = 0

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
        live = "live" if payload.get("media") else "draft — awaiting live capture"
        if payload.get("media"):
            published += 1
        print(f"  + dish: {dish['name']} ({live})")

    if created == 0:
        print(f"Menu already has {len(existing)} dishes - skipped dish creation.")
    else:
        print(f"Added {created} dishes: {published} live with a matching hero, {created - published} drafts.")

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
            # P34: customer-paid fee requires prepaid | pay_on_delivery
            method = (spec.get("payment_method") or "cod").lower()
            payload["delivery_fee_payment"] = (
                "pay_on_delivery" if method == "cod" else "prepaid"
            )

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
    retire_orphan_kitchens()
    ensure_owner()
    token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    print("Authenticated demo owner.")
    kitchen = ensure_kitchens(token)
    presence = ensure_presence_kitchens()
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    leftover = [k for k in kitchens if k["id"] != kitchen["id"]]
    if leftover:
        print(
            f"  ! primary owner still has {len(leftover)} extra kitchen(s); "
            "re-run seed after postgres is reachable so presence hosts can claim them."
        )
    dish_ids: dict[str, str] = {}
    for k in kitchens:
        try:
            mapped = seed_kitchen_menu(token, k["id"])
            print(f"  pantry+recipes: {k.get('code')} ({len(mapped)} dishes)")
            if k["id"] == kitchen["id"]:
                dish_ids = mapped
        except Exception as exc:  # noqa: BLE001
            print(f"  ! pantry seed skipped for {k.get('code')}: {exc}")
    if not dish_ids:
        dish_ids = seed_kitchen_menu(token, kitchen["id"])
    ensure_orders(token, kitchen["id"], dish_ids)

    print()
    print("Brand page + tiffin + integrations")
    print("-" * 40)
    seed_kitchen_modules(token, kitchen["id"], dish_ids)
    first_dish = next(iter(dish_ids.values()), None)
    seed_kitchen_integrations(
        token,
        kitchen["id"],
        kitchen.get("name") or DEMO_KITCHEN["name"],
        kitchen_code=kitchen.get("code") or DEMO_KITCHEN_CODE,
        dish_id=first_dish,
    )

    print()
    print("Extra demo owners")
    print("-" * 40)
    extra = ensure_extra_owners()

    print()
    print("Demo customer addresses")
    print("-" * 40)
    for spec in DEMO_CUSTOMER_ADDRESSES:
        try:
            diner_token = login_customer(spec["phone_e164"], DEMO_OTP)
            added = ensure_customer_addresses(diner_token, spec["addresses"])
            print(f"  {spec['phone_e164']}: +{added} address(es)")
        except ApiError as exc:
            print(f"  ! {spec['phone_e164']}: {exc}")

    print()
    print("Demo credentials")
    print("-" * 40)
    print(f"  OTP (all owners/customers, dev): {DEMO_OTP}")
    print(f"  Primary owner : {DEMO_OWNER['phone']} — {DEMO_OWNER['name']} ({kitchen.get('code', DEMO_KITCHEN_CODE)})")
    for owner, k in extra:
        print(f"  Owner         : {owner['phone']} — {owner['name']} ({k.get('code', '?')})")
    if presence:
        first_phone = presence[0][0]["phone"]
        last_phone = presence[-1][0]["phone"]
        print(f"  City hosts    : {first_phone}–{last_phone} — one kitchen each")
    print(f"  Admin         : {DEMO_ADMIN['email']} / {DEMO_ADMIN['password']}")
    for c in DEMO_CUSTOMERS:
        print(f"  Customer      : {c['phone']} — {c['name']} ({c.get('note', '')})")
    print("  Referrals     : seeded by seed-bulk-data / seed-all (P37 dual program)")
    print(f"  Customer app: {os.environ.get('VITE_CUSTOMER_APP_URL', 'http://localhost:13001')}")
    print(f"  Kitchen app:  {os.environ.get('VITE_KITCHEN_APP_URL', 'http://localhost:13002')}/login")
    print()
    print("For large dataset: python scripts/seed-bulk-data.py")
    print("Seed complete.")


if __name__ == "__main__":
    main()
