#!/usr/bin/env python3
"""Weekly QA cohort seed — a fresh, fully-exercised slice of the platform each ISO week.

Driven by a systemd timer on the GCP VM (``infra/gcp-vm/weekly-seed.sh``) so QA always has
untouched accounts *and* realistic data for the current week without wiping earlier cohorts.

Each run seeds, per week:

* 5 owners, each with a kitchen in a rotating city and a full menu
* 10 new customers
* 10 orders per kitchen, mixing this week's new diners with the previous cohort's
  returning diners, every order walked through the lifecycle to ``delivered``
* ratings on delivered orders (feeds home-taste aggregates and dish scores)
* promo rotation — last cohort's QA coupon and promotion are deactivated, this week's
  pair is created, so there is never more than one live QA offer
* a tiffin subscription plan plus one customer subscription
* CRM refresh, growth suggestions (combos/patterns mining), and a support ticket

Idempotent within a week: every identifier is derived from the ISO year + week, so a
re-run reuses the same cohort instead of creating duplicates. Orders are the one
exception — they top up to the target count rather than duplicating a fixed set.

Phone scheme — 10-digit India mobile, ``{prefix}{YY}{WW}{index:05d}``::

    owner     7 26 37 00001  ->  7263700001
    customer  8 26 37 00001  ->  8263700001

The ``7``/``8`` prefixes are reserved for seeded QA accounts and are configurable via
``CKAC_WEEKLY_OWNER_PREFIX`` / ``CKAC_WEEKLY_CUSTOMER_PREFIX`` so a deployment can move
the block if it ever collides with real traffic.

Usage::

    python scripts/weekly_test_data.py
    python scripts/weekly_test_data.py --owners 5 --customers 10 --orders-per-kitchen 10
    python scripts/weekly_test_data.py --week 2026-W40 --dry-run
    python scripts/weekly_test_data.py --manifest /var/lib/ckac/weekly-cohort.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import (  # noqa: E402
    CAPTURED_AT,
    DEMO_DISHES,
    DEMO_KITCHENS_CITIES,
    DEMO_OTP,
)
from seed_common import (  # noqa: E402
    ApiError,
    cuisine_map,
    dish_create_payload,
    log,
    login_customer,
    login_owner,
    request,
    wait_for_gateway,
)

OWNER_PREFIX = os.environ.get("CKAC_WEEKLY_OWNER_PREFIX", "7")
CUSTOMER_PREFIX = os.environ.get("CKAC_WEEKLY_CUSTOMER_PREFIX", "8")
DEFAULT_OWNERS = int(os.environ.get("CKAC_WEEKLY_OWNERS", "5"))
DEFAULT_CUSTOMERS = int(os.environ.get("CKAC_WEEKLY_CUSTOMERS", "10"))
DEFAULT_ORDERS_PER_KITCHEN = int(os.environ.get("CKAC_WEEKLY_ORDERS_PER_KITCHEN", "10"))

# Every QA marketing artefact carries this prefix so rotation can find last week's
# offers without touching coupons a real kitchen created.
QA_COUPON_PREFIX = "QA"
QA_PROMO_PREFIX = "QA cohort"

OWNER_NAMES = (
    "Anita Kulkarni",
    "Vikram Iyer",
    "Fatima Sheikh",
    "Rohit Bansal",
    "Meera Nair",
    "Sandeep Rana",
    "Lakshmi Rao",
)
CUSTOMER_NAMES = (
    "Kavya Reddy",
    "Imran Qureshi",
    "Neha Bhatt",
    "Arjun Pillai",
    "Sneha Joshi",
    "Tarun Gupta",
    "Divya Menon",
    "Karan Ahuja",
    "Ritu Chaudhary",
    "Aditya Ghosh",
    "Pooja Mehta",
)

# Spread orders across fulfilment and payment shapes so owner analytics, delivery
# quotes, and billing all get non-degenerate weekly data.
ORDER_SHAPES = (
    {"delivery_type": "pickup", "payment_method": "cod"},
    {"delivery_type": "delivery", "payment_method": "cod"},
    {"delivery_type": "pickup", "payment_method": "upi"},
    {"delivery_type": "delivery", "payment_method": "upi"},
)
# Delivery orders walk the full graph so tracking links and order-update notifications
# (F29/F45) fire; pickup goes ready -> delivered, which is the legal shortcut.
LIFECYCLE_PICKUP = ("accepted", "preparing", "ready", "delivered")
LIFECYCLE_DELIVERY = ("accepted", "preparing", "ready", "out_for_delivery", "delivered")


# --------------------------------------------------------------------------- cohort


def resolve_week(spec: str | None) -> tuple[int, int]:
    """Return ``(iso_year, iso_week)`` for ``YYYY-Www`` or today when ``spec`` is None."""
    if not spec:
        year, week, _ = dt.date.today().isocalendar()
        return year, week
    try:
        year_part, week_part = spec.upper().split("-W", 1)
        year, week = int(year_part), int(week_part)
    except ValueError as exc:
        raise SystemExit(f"--week must look like 2026-W40, got {spec!r}") from exc
    if not 1 <= week <= 53:
        raise SystemExit(f"--week week number out of range: {week}")
    return year, week


def previous_week(year: int, week: int) -> tuple[int, int] | None:
    """ISO week before ``(year, week)``, or None when the date cannot be formed.

    Week 53 does not exist in every ISO year, so a hand-passed ``--week 2026-W53``
    can fail to resolve; returning None simply means "no returning cohort".
    """
    try:
        monday = dt.date.fromisocalendar(year, week, 1)
    except ValueError:
        return None
    prev_year, prev_week, _ = (monday - dt.timedelta(days=7)).isocalendar()
    return prev_year, prev_week


def cohort_tag(year: int, week: int) -> str:
    return f"W{year % 100:02d}{week:02d}"


def _phone(prefix: str, year: int, week: int, index: int) -> str:
    """Build a 10-digit India mobile for the cohort slot."""
    phone = f"{prefix}{year % 100:02d}{week:02d}{index:05d}"
    if len(phone) != 10:
        raise SystemExit(f"Generated phone is not 10 digits: {phone}")
    return phone


def cohort_owners(year: int, week: int, count: int) -> list[dict]:
    tag = cohort_tag(year, week)
    owners = []
    for i in range(1, count + 1):
        phone = _phone(OWNER_PREFIX, year, week, i)
        name = OWNER_NAMES[(week + i) % len(OWNER_NAMES)]
        owners.append(
            {
                "phone": phone,
                "phone_e164": f"+91{phone}",
                "name": name,
                # `.test` is a reserved TLD and email-validator rejects it, so QA
                # addresses live on a subdomain of a domain we actually own.
                "email": f"qa.owner.{tag.lower()}.{i}@qa.kitchcu.in",
                "kitchen_label": f"{name.split()[0]} QA Kitchen {tag}",
                "city": DEMO_KITCHENS_CITIES[(week + i) % len(DEMO_KITCHENS_CITIES)],
            }
        )
    return owners


def cohort_customers(year: int, week: int, count: int) -> list[dict]:
    tag = cohort_tag(year, week)
    customers = []
    for i in range(1, count + 1):
        phone = _phone(CUSTOMER_PREFIX, year, week, i)
        customers.append(
            {
                "phone": phone,
                "phone_e164": f"+91{phone}",
                "name": CUSTOMER_NAMES[(week + i) % len(CUSTOMER_NAMES)],
                "note": f"QA cohort {tag} diner {i}",
                "cohort": tag,
            }
        )
    return customers


# ----------------------------------------------------------------------- owner seed


def is_conflict(exc: ApiError) -> bool:
    """True only for a genuine 409.

    ``request`` formats failures as ``METHOD /path -> CODE: detail``, so match the
    status position rather than searching the whole string — a bare ``"409" in text``
    also matches a phone number or an id that happens to contain those digits.
    """
    return "-> 409:" in str(exc)


def register_owner(owner: dict) -> bool:
    """Register the owner. Returns True when newly created, False when already present."""
    try:
        request(
            "POST",
            "/api/v1/owners/register",
            {"phone": owner["phone"], "name": owner["name"], "email": owner["email"]},
        )
        return True
    except ApiError as exc:
        if is_conflict(exc):
            return False
        raise


def kitchen_jitter(owner: dict) -> float:
    return (int(owner["phone"][-2:]) % 20) * 0.001


def ensure_kitchen(token: str, owner: dict) -> dict:
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    label = owner["kitchen_label"]
    for kitchen in kitchens:
        if kitchen["name"] == label:
            return kitchen

    city = owner["city"]
    # Nudge each cohort kitchen off the city centre so discovery returns distinct pins.
    jitter = kitchen_jitter(owner)
    return request(
        "POST",
        "/api/v1/kitchens",
        {
            "name": label,
            "description": f"Weekly QA kitchen — {city['city']}.",
            "address_line": city["address_line"],
            "city": city["city"],
            "state": city["state"],
            "pincode": city["pincode"],
            "latitude": round(city["latitude"] + jitter, 6),
            "longitude": round(city["longitude"] + jitter, 6),
        },
        token=token,
    )


def ensure_menu(token: str, kitchen_id: str) -> dict[str, str]:
    menu = request("GET", f"/api/v1/kitchens/{kitchen_id}/menu")
    dish_ids = {d["name"]: d["id"] for d in menu.get("dishes", [])}
    categories = request("GET", f"/api/v1/kitchens/{kitchen_id}/categories", token=token)
    category_ids = {c["slug"]: c["id"] for c in categories}
    cuisine_ids = cuisine_map(token, kitchen_id)

    for dish in DEMO_DISHES:
        if dish["name"] in dish_ids:
            continue
        payload = dish_create_payload(
            dish,
            category_ids=category_ids,
            cuisine_ids=cuisine_ids,
            captured_at=CAPTURED_AT,
        )
        created = request("POST", f"/api/v1/kitchens/{kitchen_id}/dishes", payload, token=token)
        dish_ids[dish["name"]] = created["id"]
    return dish_ids


def seed_owner(owner: dict) -> dict:
    created = register_owner(owner)
    token = login_owner(owner["phone_e164"], DEMO_OTP)
    kitchen = ensure_kitchen(token, owner)
    dish_ids = ensure_menu(token, kitchen["id"])
    log(
        f"  owner {owner['phone']} — {owner['name']} "
        f"({'new' if created else 'existing'}) → {kitchen.get('code')} "
        f"{kitchen['name']}, {len(dish_ids)} dishes"
    )
    return {
        "phone": owner["phone"],
        "name": owner["name"],
        "email": owner["email"],
        "token": token,
        "kitchen_code": kitchen.get("code"),
        "kitchen_id": kitchen["id"],
        "kitchen_name": kitchen["name"],
        "city": owner["city"]["city"],
        "latitude": round(owner["city"]["latitude"] + kitchen_jitter(owner), 6),
        "longitude": round(owner["city"]["longitude"] + kitchen_jitter(owner), 6),
        "dish_ids": dish_ids,
    }


# -------------------------------------------------------------------- customer seed


def seed_customer(customer: dict) -> dict:
    """Sign the diner in. Customer accounts are created on first OTP verify."""
    token = login_customer(customer["phone_e164"], DEMO_OTP)
    return {**customer, "token": token}


def returning_customers(year: int, week: int, count: int) -> list[dict]:
    """Last week's cohort, signed back in so this week's orders include repeat diners.

    If last week's timer never ran, these sign-ins create the accounts instead — which
    still leaves them genuinely "returning" by the following week.
    """
    prev = previous_week(year, week)
    if not prev:
        return []
    sessions = []
    for customer in cohort_customers(prev[0], prev[1], count):
        try:
            sessions.append(seed_customer(customer))
        except ApiError as exc:
            log(f"    (returning diner {customer['phone']} skipped: {exc})")
    return sessions


# ------------------------------------------------------------------------- ordering


def order_roster(new_diners: list[dict], repeat_diners: list[dict], offset: int) -> list[dict]:
    """Interleave new and returning diners, rotated per kitchen.

    Roughly two new diners per returning one, so CRM sees both first-time and repeat
    behaviour, and the offset stops every kitchen from serving the same faces.
    """
    roster: list[dict] = []
    n, r = len(new_diners), len(repeat_diners)
    if not n and not r:
        return roster
    for i in range(max(n, r) * 3):
        if i % 3 == 2 and r:
            roster.append(repeat_diners[(i // 3 + offset) % r])
        elif n:
            roster.append(new_diners[(i + offset) % n])
    return roster


def count_kitchen_orders(owner_token: str, kitchen_id: str) -> int:
    try:
        listed = request(
            "GET", f"/api/v1/kitchens/{kitchen_id}/orders?limit=100", token=owner_token
        )
    except ApiError:
        return 0
    if isinstance(listed, dict):
        return int(listed.get("total") or len(listed.get("orders") or []))
    return len(listed or [])


def place_order(diner: dict, kitchen: dict, shape: dict, dish_names: list[str], slot: int) -> dict:
    dish_name = dish_names[slot % len(dish_names)]
    items = [{"dish_id": kitchen["dish_ids"][dish_name], "quantity": 1 + (slot % 2)}]
    # Every third order is a two-dish basket so combo mining has something to find.
    if slot % 3 == 0 and len(dish_names) > 1:
        second = dish_names[(slot + 1) % len(dish_names)]
        items.append({"dish_id": kitchen["dish_ids"][second], "quantity": 1})
    body: dict = {"items": items, **shape}
    if shape["delivery_type"] == "delivery":
        # Drop the diner a few hundred metres from the kitchen: inside the delivery
        # radius, so self-delivery quotes a zero fee and the order needs no fee
        # acceptance, while still producing a distance and a tracking token.
        body["customer_latitude"] = round(kitchen["latitude"] + 0.004, 6)
        body["customer_longitude"] = round(kitchen["longitude"] + 0.004, 6)
    return request(
        "POST",
        f"/api/v1/kitchens/{kitchen['kitchen_id']}/orders/customer",
        body,
        token=diner["token"],
    )


def advance_to_delivered(order_id: str, owner_token: str, delivery_type: str) -> None:
    lifecycle = LIFECYCLE_DELIVERY if delivery_type == "delivery" else LIFECYCLE_PICKUP
    for status in lifecycle:
        request("PATCH", f"/api/v1/orders/{order_id}/status", {"status": status}, token=owner_token)


def rate_order(diner: dict, order: dict) -> bool:
    items = order.get("items") or []
    dish_id = items[0].get("dish_id") if items else None
    if not dish_id:
        return False
    # Vary scores so dish aggregates are not a flat 5.0 across the whole cohort.
    home_taste = 4 + (len(diner["phone"]) + len(order.get("order_code") or "")) % 2
    request(
        "POST",
        f"/api/v1/customers/me/orders/{order['id']}/ratings",
        {
            "ratings": [
                {"dish_id": dish_id, "home_taste_score": home_taste, "quality_score": 4}
            ]
        },
        token=diner["token"],
    )
    return True


def seed_kitchen_orders(
    kitchen: dict,
    new_diners: list[dict],
    repeat_diners: list[dict],
    target: int,
    offset: int,
) -> dict:
    """Top the kitchen up to ``target`` delivered orders and rate them."""
    dish_names = list(kitchen["dish_ids"].keys())[:8]
    if not dish_names:
        return {"orders": 0, "ratings": 0}

    existing = count_kitchen_orders(kitchen["token"], kitchen["kitchen_id"])
    wanted = max(0, target - existing)
    roster = order_roster(new_diners, repeat_diners, offset)
    if not roster:
        return {"orders": 0, "ratings": 0}

    placed = rated = 0
    for slot in range(wanted):
        diner = roster[slot % len(roster)]
        shape = ORDER_SHAPES[(slot + offset) % len(ORDER_SHAPES)]
        try:
            order = place_order(diner, kitchen, shape, dish_names, slot)
            advance_to_delivered(order["id"], kitchen["token"], shape["delivery_type"])
            placed += 1
        except ApiError as exc:
            log(f"    ! order for {diner['phone']}: {exc}")
            continue
        try:
            if rate_order(diner, order):
                rated += 1
        except ApiError as exc:
            log(f"    ! rating for {diner['phone']}: {exc}")
    log(
        f"    orders: {placed} new (+{existing} already present), {rated} rated"
        f" — target {target}"
    )
    return {"orders": placed, "ratings": rated}


# ------------------------------------------------------------------------ marketing


def retire_offers(kitchen_id: str, token: str) -> int:
    """Deactivate every live QA coupon and promotion on one kitchen."""
    retired = 0
    try:
        listed = request("GET", f"/api/v1/kitchens/{kitchen_id}/coupons", token=token)
        for coupon in listed.get("coupons", []):
            if str(coupon.get("code") or "").startswith(QA_COUPON_PREFIX) and coupon.get("is_active"):
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/coupons/{coupon['id']}",
                    {"is_active": False},
                    token=token,
                )
                retired += 1
        listed = request("GET", f"/api/v1/kitchens/{kitchen_id}/promotions", token=token)
        for promo in listed.get("promotions", []):
            if str(promo.get("name") or "").startswith(QA_PROMO_PREFIX) and promo.get("is_active"):
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/promotions/{promo['id']}",
                    {"is_active": False},
                    token=token,
                )
                retired += 1
    except ApiError as exc:
        log(f"  ! retiring offers on {kitchen_id[:8]}: {exc}")
    return retired


def retire_previous_cohort_offers(year: int, week: int, count: int) -> int:
    """Close last week's QA offers so only the current week's promo is ever live.

    Each cohort gets its own kitchens, so rotating within a kitchen is not enough —
    without this, every past week's coupon would stay redeemable forever and the QA
    estate would drift further from what a real kitchen looks like.
    """
    prev = previous_week(year, week)
    if not prev:
        return 0
    retired = 0
    for owner in cohort_owners(prev[0], prev[1], count):
        try:
            token = login_owner(owner["phone_e164"], DEMO_OTP)
            kitchens = request("GET", "/api/v1/kitchens/me", token=token)
        except ApiError:
            # Cohort never ran (or was reset) — nothing to retire.
            continue
        for kitchen in kitchens:
            retired += retire_offers(kitchen["id"], token)
    return retired


def rotate_coupon(kitchen: dict, tag: str) -> str | None:
    """Retire earlier QA coupons and open this week's — one live QA offer at a time."""
    code = f"{QA_COUPON_PREFIX}{tag}"
    kitchen_id, token = kitchen["kitchen_id"], kitchen["token"]
    try:
        listed = request("GET", f"/api/v1/kitchens/{kitchen_id}/coupons", token=token)
    except ApiError as exc:
        log(f"    ! coupon list: {exc}")
        return None

    present = False
    retired = 0
    for coupon in listed.get("coupons", []):
        current = str(coupon.get("code") or "")
        if current == code:
            present = True
            continue
        if current.startswith(QA_COUPON_PREFIX) and coupon.get("is_active"):
            try:
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/coupons/{coupon['id']}",
                    {"is_active": False},
                    token=token,
                )
                retired += 1
            except ApiError as exc:
                log(f"    ! retire coupon {current}: {exc}")

    if not present:
        try:
            request(
                "POST",
                f"/api/v1/kitchens/{kitchen_id}/coupons",
                {
                    "code": code,
                    "discount_type": "percent",
                    "discount_value": 15,
                    "min_order_amount": 199,
                    "max_uses": 200,
                },
                token=token,
            )
        except ApiError as exc:
            log(f"    ! create coupon {code}: {exc}")
            return None
    log(f"    coupon: {code} live" + (f", {retired} earlier QA code(s) retired" if retired else ""))
    return code


def rotate_promotion(kitchen: dict, tag: str) -> str | None:
    """Same rotation for dish promotions — last cohort's ends when this one starts."""
    name = f"{QA_PROMO_PREFIX} {tag} special"
    kitchen_id, token = kitchen["kitchen_id"], kitchen["token"]
    dish_names = list(kitchen["dish_ids"].keys())
    if not dish_names:
        return None
    try:
        listed = request("GET", f"/api/v1/kitchens/{kitchen_id}/promotions", token=token)
    except ApiError as exc:
        log(f"    ! promotion list: {exc}")
        return None

    present = False
    for promo in listed.get("promotions", []):
        current = str(promo.get("name") or "")
        if current == name:
            present = True
            continue
        if current.startswith(QA_PROMO_PREFIX) and promo.get("is_active"):
            try:
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/promotions/{promo['id']}",
                    {"is_active": False},
                    token=token,
                )
            except ApiError as exc:
                log(f"    ! retire promotion {current}: {exc}")

    if not present:
        now = dt.datetime.now(dt.timezone.utc)
        try:
            request(
                "POST",
                f"/api/v1/kitchens/{kitchen_id}/promotions",
                {
                    "name": name,
                    "dish_id": kitchen["dish_ids"][dish_names[0]],
                    "special_price": 129,
                    "segment": "all",
                    "starts_at": (now - dt.timedelta(hours=1)).isoformat(),
                    "ends_at": (now + dt.timedelta(days=7)).isoformat(),
                },
                token=token,
            )
        except ApiError as exc:
            log(f"    ! create promotion {name}: {exc}")
            return None
    log(f"    promotion: {name} live")
    return name


def ensure_subscription_plan(kitchen: dict, tag: str) -> str | None:
    """A weekly tiffin plan so subscription screens have a current offer."""
    name = f"QA Weekly Thali {tag}"
    kitchen_id, token = kitchen["kitchen_id"], kitchen["token"]
    dish_ids = list(kitchen["dish_ids"].values())
    if len(dish_ids) < 2:
        return None
    try:
        listed = request(
            "GET", f"/api/v1/kitchens/{kitchen_id}/subscription-plans", token=token
        )
        plans = listed.get("plans") if isinstance(listed, dict) else listed
        for plan in plans or []:
            if plan.get("name") == name:
                return plan["id"]
        created = request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
            {
                "name": name,
                "description": f"Weekday thali for QA cohort {tag}.",
                "plan_type": "thali",
                "price_monthly": 2299.0,
                "dishes_config": {
                    "dish_ids": dish_ids[:2],
                    "weekdays": [0, 1, 2, 3, 4],
                    "meals_per_day": 1,
                },
            },
            token=token,
        )
        return created["id"]
    except ApiError as exc:
        log(f"    ! subscription plan: {exc}")
        return None


def subscribe_customer(diner: dict, kitchen_id: str, plan_id: str) -> bool:
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan_id}/subscribe",
            {"customer_name": diner["name"], "note": diner["note"]},
            token=diner["token"],
        )
        return True
    except ApiError as exc:
        # A re-run inside the same week hits the "one open subscription per kitchen"
        # rule, which the API reports as 400 rather than 409. Already subscribed is
        # the state we wanted, so treat it as success.
        if is_conflict(exc) or "open subscription" in str(exc).lower():
            return True
        log(f"    ! subscribe {diner['phone']}: {exc}")
        return False


# -------------------------------------------------------------------------- growth


def refresh_crm(kitchen: dict) -> None:
    try:
        request(
            "GET",
            f"/api/v1/kitchens/{kitchen['kitchen_id']}/crm/customers?refresh=true",
            token=kitchen["token"],
        )
    except ApiError as exc:
        log(f"    ! CRM refresh: {exc}")


def generate_growth_suggestions(kitchen: dict) -> int:
    """Mine this week's orders into combo/pattern suggestions for the owner."""
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen['kitchen_id']}/growth/suggestions/generate",
            token=kitchen["token"],
        )
        listed = request(
            "GET",
            f"/api/v1/kitchens/{kitchen['kitchen_id']}/growth/suggestions",
            token=kitchen["token"],
        )
        rows = listed.get("suggestions") if isinstance(listed, dict) else listed
        count = len(rows or [])
        log(f"    growth suggestions: {count}")
        return count
    except ApiError as exc:
        log(f"    ! growth suggestions: {exc}")
        return 0


def open_support_ticket(diner: dict, kitchen: dict, tag: str) -> bool:
    subject = f"QA {tag} — {kitchen['kitchen_code']} order follow-up"
    try:
        listed = request("GET", "/api/v1/customers/me/tickets", token=diner["token"])
        rows = listed.get("tickets") if isinstance(listed, dict) else listed
        # Tickets have no natural key, so match on the cohort+kitchen subject to
        # keep a mid-week re-run from stacking duplicates on the triage queue.
        if any(str(t.get("subject") or "") == subject for t in rows or []):
            return True
        request(
            "POST",
            "/api/v1/customers/me/tickets",
            {
                "audience": "customer",
                "category": "quality",
                "subject": subject,
                "description": (
                    f"Seeded ticket for cohort {tag} against {kitchen['kitchen_name']} so "
                    "support triage has an open conversation to work."
                ),
                "source": "web_form",
            },
            token=diner["token"],
        )
        return True
    except ApiError as exc:
        log(f"    ! support ticket: {exc}")
        return False


# ----------------------------------------------------------------------------- main


def seed_kitchen_activity(
    kitchen: dict,
    new_diners: list[dict],
    repeat_diners: list[dict],
    tag: str,
    orders_target: int,
    offset: int,
) -> dict:
    log(f"  {kitchen['kitchen_code']} {kitchen['kitchen_name']} ({kitchen['city']})")
    totals = seed_kitchen_orders(kitchen, new_diners, repeat_diners, orders_target, offset)
    refresh_crm(kitchen)
    coupon = rotate_coupon(kitchen, tag)
    promotion = rotate_promotion(kitchen, tag)
    plan_id = ensure_subscription_plan(kitchen, tag)
    subscribed = 0
    if plan_id and new_diners:
        # One subscriber per kitchen keeps the owner's subscription inbox non-empty
        # without turning every diner into a subscriber.
        if subscribe_customer(new_diners[offset % len(new_diners)], kitchen["kitchen_id"], plan_id):
            subscribed = 1
    suggestions = generate_growth_suggestions(kitchen)
    tickets = 0
    if new_diners and open_support_ticket(new_diners[offset % len(new_diners)], kitchen, tag):
        tickets = 1
    return {
        **totals,
        "coupon": coupon,
        "promotion": promotion,
        "subscriptions": subscribed,
        "suggestions": suggestions,
        "tickets": tickets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--week", help="ISO week to seed, e.g. 2026-W40 (default: current week)")
    parser.add_argument("--owners", type=int, default=DEFAULT_OWNERS)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
    parser.add_argument(
        "--orders-per-kitchen",
        type=int,
        default=DEFAULT_ORDERS_PER_KITCHEN,
        help="Delivered orders each cohort kitchen should end the run with",
    )
    parser.add_argument("--manifest", help="Write the cohort summary to this JSON file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the cohort that would be created without calling the API",
    )
    args = parser.parse_args()

    year, week = resolve_week(args.week)
    tag = cohort_tag(year, week)
    owners = cohort_owners(year, week, args.owners)
    customers = cohort_customers(year, week, args.customers)

    log(f"kitchCU weekly QA cohort {tag} ({year}-W{week:02d})")
    log("=" * 60)

    if args.dry_run:
        for owner in owners:
            log(f"  owner    {owner['phone']} — {owner['name']} @ {owner['city']['city']}")
        for customer in customers:
            log(f"  customer {customer['phone']} — {customer['name']}")
        prev = previous_week(year, week)
        if prev:
            log(f"  returning diners from {prev[0]}-W{prev[1]:02d} (cohort {cohort_tag(*prev)})")
        log(
            f"  plan: {args.orders_per_kitchen} orders per kitchen, coupon "
            f"{QA_COUPON_PREFIX}{tag}, promotion '{QA_PROMO_PREFIX} {tag} special'"
        )
        return 0

    wait_for_gateway()

    log("")
    log("Owners + kitchens")
    kitchens: list[dict] = []
    for owner in owners:
        try:
            kitchens.append(seed_owner(owner))
        except ApiError as exc:
            log(f"  ! owner {owner['phone']} failed: {exc}")

    log("")
    log("Customers")
    new_diners: list[dict] = []
    for customer in customers:
        try:
            new_diners.append(seed_customer(customer))
            log(f"  customer {customer['phone']} — {customer['name']}")
        except ApiError as exc:
            log(f"  ! customer {customer['phone']} failed: {exc}")

    repeat_diners = returning_customers(year, week, args.customers)
    log(f"  returning diners signed in: {len(repeat_diners)}")

    retired = retire_previous_cohort_offers(year, week, args.owners)
    log(f"  previous cohort offers retired: {retired}")

    log("")
    log("Kitchen activity (orders · ratings · marketing · growth)")
    activity: list[dict] = []
    for offset, kitchen in enumerate(kitchens):
        try:
            activity.append(
                {
                    "kitchen_code": kitchen["kitchen_code"],
                    **seed_kitchen_activity(
                        kitchen, new_diners, repeat_diners, tag, args.orders_per_kitchen, offset
                    ),
                }
            )
        except ApiError as exc:
            log(f"  ! activity for {kitchen['kitchen_code']} failed: {exc}")

    totals = {
        key: sum(int(a.get(key) or 0) for a in activity)
        for key in ("orders", "ratings", "subscriptions", "suggestions", "tickets")
    }

    manifest = {
        "cohort": tag,
        "iso_year": year,
        "iso_week": week,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "otp": DEMO_OTP,
        "coupon_code": f"{QA_COUPON_PREFIX}{tag}",
        "owners": [
            {k: v for k, v in o.items() if k not in ("dish_ids", "token")} for o in kitchens
        ],
        "customers": [
            {k: v for k, v in c.items() if k != "token"} for c in new_diners
        ],
        "activity": activity,
        "totals": totals,
    }

    if args.manifest:
        path = Path(args.manifest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(f"\nManifest written to {path}")

    log("")
    log("=" * 60)
    log(
        f"Cohort {tag}: {len(kitchens)}/{len(owners)} owners, "
        f"{len(new_diners)}/{len(customers)} customers, "
        f"{totals['orders']} orders, {totals['ratings']} ratings, "
        f"{totals['suggestions']} growth suggestions, "
        f"{totals['subscriptions']} subscriptions, {totals['tickets']} tickets"
    )
    log(f"Coupon this week: {QA_COUPON_PREFIX}{tag} (earlier QA codes deactivated)")
    log(f"OTP for every seeded account: {DEMO_OTP}")

    failed = len(kitchens) != len(owners) or len(new_diners) != len(customers)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except ApiError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
