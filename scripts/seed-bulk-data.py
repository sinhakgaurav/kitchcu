#!/usr/bin/env python3
"""Seed a large demo dataset for full UI / report verification.

Creates owners, kitchens in every presence city (Pune → Kolkata), city
customers with home addresses, dishes, orders, and WhatsApp drafts.

Usage:
  python scripts/seed-bulk-data.py
  CKAC_BULK_KITCHENS=30 CKAC_BULK_CUSTOMERS_PER_CITY=3 python scripts/seed-bulk-data.py
  CKAC_BULK_ORDERS=300 python scripts/seed-bulk-data.py
  $env:CKAC_BULK_OWNERS=5; .\\scripts\\seed-bulk-data.ps1

Six months of trading history (reports, GST periods, CRM cohorts):
  $env:CKAC_BULK_MONTHS=6; python scripts/seed-bulk-data.py

  Order volume tracks the window automatically — one order per kitchen per day,
  three per day on the primary demo kitchen. Override with
  CKAC_BULK_ORDERS_PER_KITCHEN / CKAC_BULK_PRIMARY_ORDERS. Each order costs one
  POST plus up to four status PATCHes, so a 6-month × 30-kitchen run is a long
  job; drop CKAC_BULK_KITCHENS for a faster pass.

  Orders are placed in real service hours (IST breakfast/lunch/snacks/dinner)
  with weekend lift and a growth trend, and anything older than two days is
  already delivered or cancelled. Payments, refunds, settlements, GST invoices
  and ratings are shifted with their parent order.

  Diners scale with the window (roughly one per 3.5 orders, split into a loyal
  core, regulars and one-off visitors) so CRM, customer segments and churn risk
  have something to segment. CRM profiles are re-aggregated after dating, since
  `last_order_at` is what churn risk reads.

GCP (VM repo is /opt/ckac):
  sudo systemctl start kitchcu-bulk-seed.service
  sudo bash /opt/ckac/infra/gcp-vm/bulk-seed.sh

Requires: docker compose up (gateway + postgres). The primary demo owner is
created automatically, so running seed-dev-data.py first is optional.
Dishes without a live-capture hero stay inactive; orders use active dishes only.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bulk_demo_data import (  # noqa: E402
    CUSTOMER_NAMES,
    EXTRA_OWNERS,
    SEED_CITIES,
    STATUS_CHAINS,
    WHATSAPP_MESSAGES,
    captured_at,
    city_customer_specs,
    enriched_dishes,
    owner_kitchen_specs,
)
from order_history import (  # noqa: E402
    DAYS_PER_MONTH,
    OrderSlot,
    basket_shape,
    diner_pool,
    order_history_plan,
    plan_summary,
    slot_to_utc,
)
from demo_data import DEMO_CUSTOMER_ADDRESSES, DEMO_KITCHEN_CODE, DEMO_OTP, DEMO_OWNER  # noqa: E402
from seed_common import (  # noqa: E402
    ApiError,
    cuisine_map,
    dish_create_payload,
    ensure_customer_addresses,
    ensure_dish_recipes,
    ensure_ingredients,
    login_customer,
    login_owner,
    request,
    resolve_postgres_container,
    wait_for_gateway,
)
from seed_platform_extras import (  # noqa: E402
    ensure_customer_sessions,
    ensure_ratings,
    seed_kitchen_integrations,
    seed_kitchen_modules,
    seed_platform_extras,
)
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
BULK_DRAFTS_PER_KITCHEN = env_int("CKAC_BULK_DRAFTS_PER_KITCHEN", 5)
BULK_DISHES_PER_KITCHEN = env_int("CKAC_BULK_DISHES_PER_KITCHEN", 6, minimum=1)
BULK_CUSTOMERS_PER_CITY = env_int("CKAC_BULK_CUSTOMERS_PER_CITY", 3, minimum=0)
BULK_FULL = os.environ.get("CKAC_BULK_FULL", "1").strip().lower() not in ("0", "false", "no")

# History window. CKAC_BULK_MONTHS is the headline control ("6 months of data");
# CKAC_BULK_BACKDATE_DAYS still works for anyone who wants exact days.
BULK_MONTHS = env_int("CKAC_BULK_MONTHS", 0)
if BULK_MONTHS:
    BACKDATE_DAYS = round(BULK_MONTHS * DAYS_PER_MONTH)
else:
    BACKDATE_DAYS = env_int("CKAC_BULK_BACKDATE_DAYS", 30)

# Volume has to track the window or a 6-month chart is mostly gaps. One order per
# day per kitchen is the floor that keeps every daily bucket populated; the
# primary demo kitchen gets ~3/day so its Reports page has something to say.
# Every order costs one POST plus up to four status PATCHes, so these are the
# knobs to turn when a run has to finish faster.
BULK_ORDERS_PER_KITCHEN = env_int(
    "CKAC_BULK_ORDERS_PER_KITCHEN", max(40, BACKDATE_DAYS)
)
# Governs the demo kitchen in both modes. The max() keeps the 30-day default at
# CKAC_BULK_ORDERS, so only a longer window raises it.
BULK_PRIMARY_ORDERS = env_int(
    "CKAC_BULK_PRIMARY_ORDERS", max(BULK_ORDERS, BACKDATE_DAYS * 3)
)

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
        if d.get("is_active", True):
            dish_ids[d["name"]] = d["id"]

    added = 0
    target = dishes[:limit] if limit else dishes

    # Correct heroes seeded by the old keyword/round-robin mapping (e.g. Bhel Puri on a
    # grilled-meat photo). Creation is skipped for existing dishes, so without this the
    # wrong image would survive every re-seed.
    intended_media = {d["name"]: d.get("media_url") for d in target}
    resynced = 0
    retired = 0
    for d in menu.get("dishes", []):
        if d["name"] not in intended_media:
            continue
        want = intended_media[d["name"]]
        hero = next((m for m in d.get("media", []) if m.get("is_hero")), None)
        if not want:
            # The dish lost its hero because no asset honestly showed it. Pull it off
            # the public menu instead of leaving the borrowed photo in place.
            if hero:
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/dishes/{d['id']}",
                    {"is_active": False},
                    token=token,
                )
                retired += 1
            dish_ids.pop(d["name"], None)
            continue
        if hero and hero.get("url") == want:
            continue
        request(
            "PATCH",
            f"/api/v1/kitchens/{kitchen_id}/dishes/{d['id']}",
            {
                "media": {
                    "url": want,
                    "is_hero": True,
                    "is_live_capture": True,
                    "captured_at": captured_at(),
                }
            },
            token=token,
        )
        resynced += 1
    if resynced:
        log(f"  Resynced {resynced} dish heroes to the correct image.")
    if retired:
        log(f"  Unpublished {retired} dishes whose hero did not show the dish.")
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
        if payload.get("is_active", True) and payload.get("media"):
            dish_ids[dish["name"]] = resp["id"]
        existing_names.add(dish["name"])
        added += 1
        if added % 10 == 0:
            log(f"    ... {added} dishes added")
        # e2-small: give catalog breathing room between dish creates
        if added % 5 == 0:
            time.sleep(0.5)

    if added:
        log(f"  Added {added} dishes to kitchen {kitchen_id[:8]}...")
    return dish_ids


def pick_order_items(dish_ids: dict[str, str], rng: random.Random) -> list[dict]:
    names = list(dish_ids.keys())
    rng.shuffle(names)
    count, quantity = basket_shape(rng, available=len(names))
    return [{"dish_id": dish_ids[name], "quantity": quantity} for name in names[:count]]


def advance_order(token: str, order_id: str, chain_key: str) -> None:
    chain = STATUS_CHAINS.get(chain_key, [])
    for status in chain:
        body: dict = {"status": status}
        if status == "cancelled":
            body["cancel_reason"] = "Customer cancelled / item unavailable"
        request("PATCH", f"/api/v1/orders/{order_id}/status", body, token=token)


def history_plan_for(kitchen_id: str, count: int) -> list[OrderSlot]:
    """Per-kitchen order history, so no two kitchens share an identical curve."""
    seed = int(uuid.UUID(kitchen_id)) % (2**32)
    return order_history_plan(count, days=BACKDATE_DAYS, seed=seed)


# Orders are dated in one pass at the very end of the run. Dating mid-run would
# strand every payment, rating and GST invoice created afterwards at NOW(), and
# the shift is computed from the order's current timestamp so a second pass is a
# no-op rather than a correction.
PLACED_ORDERS: dict[str, list[tuple[str, OrderSlot]]] = {}
# Owner token per kitchen, so the post-dating CRM sync can reach each tenant.
KITCHEN_TOKENS: dict[str, str] = {}


def ensure_orders(
    token: str,
    kitchen_id: str,
    dish_ids: dict[str, str],
    target: int,
    *,
    city_customers: list[dict] | None = None,
) -> list[tuple[str, OrderSlot]]:
    """Create orders oldest-first; return (order_id, slot) in creation order.

    Status still moves through the real API state machine, so lifecycle events
    are published exactly as they are in production — only the timestamps are
    rewritten afterwards.
    """
    if not dish_ids:
        log("  ! No dishes — skipping orders")
        return []

    KITCHEN_TOKENS[kitchen_id] = token
    orders_resp = request("GET", f"/api/v1/kitchens/{kitchen_id}/orders", token=token)
    current = orders_resp.get("total", 0)
    if current >= target:
        log(f"  Orders already at {current} (target {target}) — skipped.")
        return []

    need = target - current
    # The plan decides both when an order was placed and how far it got: an order
    # from five months ago is delivered or cancelled, never left "preparing".
    slots = history_plan_for(kitchen_id, need)
    plan = [s.chain_key for s in slots]
    placed: list[tuple[str, OrderSlot]] = []
    rng = random.Random(42)
    created = 0

    # Registered city diners lead the pool so CRM / nearby / order history match
    # the kitchen city; the rest of the pool is the walk-in tail that customer
    # segments and churn risk need in order to mean anything.
    located = [(c["name"], c["phone_e164"]) for c in (city_customers or []) if c.get("phone_e164")]
    pool = diner_pool(need, located, seed=int(uuid.UUID(kitchen_id)) % (2**32))
    customer_pool = list(pool.diners)
    pool_weights = list(pool.weights)

    log(
        f"  Creating {need} orders (current {current}, target {target}) "
        f"across {len(customer_pool)} diners..."
    )
    for i, chain_key in enumerate(plan):
        delivery = "delivery" if chain_key in ("out_for_delivery", "delivered_delivery") or rng.random() < 0.45 else "pickup"
        payment = rng.choice(["cod", "upi", "online"])
        delivery_fee = 40.0 if delivery == "delivery" else 0.0
        # A slice of counter pickups leave no phone behind — they should stay out
        # of CRM rather than inflate a diner's history.
        if delivery == "pickup" and rng.random() < 0.08:
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
        placed.append((order["id"], slots[i]))
        PLACED_ORDERS.setdefault(kitchen_id, []).append((order["id"], slots[i]))
        created += 1
        if created % 25 == 0:
            log(f"    ... {created}/{need} orders")
        # Soft pacing so gateway default budget (600/min) is not blown on e2-small.
        if created % 10 == 0:
            time.sleep(0.35)

    log(f"  Created {created} orders — {plan_summary(slots)}.")
    return placed


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


# Every row that has to move with its parent order. Reports read these directly,
# so leaving them stamped NOW() would put six months of orders against one month
# of payments and a single month of GST invoices.
# Missing tables and columns are skipped at runtime, so a service that is not
# deployed in a given environment costs nothing here.
ORDER_LINKED_TIMESTAMPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ckac_orders.order_status_events", ("created_at",)),
    ("ckac_billing.payments", ("created_at", "updated_at")),
    ("ckac_billing.refunds", ("created_at", "updated_at", "completed_at")),
    ("ckac_billing.settlements", ("created_at", "settled_at")),
    ("ckac_billing.gst_tax_invoices", ("created_at", "invoice_date")),
    ("ckac_ratings.dish_ratings", ("created_at",)),
)


def _run_psql(sql: str, *, timeout: int = 300) -> tuple[bool, str]:
    """Pipe a script to psql inside the Postgres container.

    The encoding is pinned because Windows would otherwise send the script as
    cp1252 and Postgres rejects the result as invalid UTF-8 the moment a comment
    or message contains a dash or rupee sign.
    """
    try:
        proc = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                "-e",
                "PGCLIENTENCODING=UTF8",
                resolve_postgres_container(),
                "psql",
                "-U",
                "ckac",
                "-d",
                "ckac",
                "-v",
                "ON_ERROR_STOP=1",
                "-q",
                "-f",
                "-",
            ],
            input=sql,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())
    return True, ""


def apply_order_history(kitchen_id: str, placed: list[tuple[str, OrderSlot]]) -> None:
    """Stamp each order with its planned instant and drag dependent rows along.

    Everything related to an order shifts by the same interval, so lifecycle
    ordering, payment-after-order and rating-after-delivery all survive.
    """
    if BACKDATE_DAYS <= 0 or not placed:
        return
    now = datetime.now(UTC)
    values = ",".join(
        f"('{order_id}'::uuid,'{slot_to_utc(slot, now=now).isoformat()}'::timestamptz)"
        for order_id, slot in placed
    )
    cascade = ",".join(
        f"('{table}','{column}')"
        for table, columns in ORDER_LINKED_TIMESTAMPS
        for column in columns
    )
    sql = f"""
BEGIN;
CREATE TEMP TABLE planned (order_id uuid PRIMARY KEY, placed_at timestamptz) ON COMMIT DROP;
INSERT INTO planned VALUES {values};

-- One delta per order keeps every dependent row's relative position intact.
CREATE TEMP TABLE shifted (order_id uuid PRIMARY KEY, delta interval) ON COMMIT DROP;
INSERT INTO shifted
SELECT p.order_id, p.placed_at - o.created_at
FROM planned p
JOIN ckac_orders.orders o ON o.id = p.order_id
WHERE o.kitchen_id = '{kitchen_id}'::uuid;

-- Refuse to report success for orders we did not touch. Without this a seeder
-- pointed at the wrong Postgres container updates nothing, exits 0, and leaves
-- the reports it was meant to populate empty.
DO $$
DECLARE matched int;
BEGIN
  SELECT count(*) INTO matched FROM shifted;
  IF matched <> {len(placed)} THEN
    RAISE EXCEPTION
      'dating matched % of % orders for kitchen {kitchen_id} — wrong database?',
      matched, {len(placed)};
  END IF;
END $$;

UPDATE ckac_orders.orders o
SET created_at = o.created_at + s.delta,
    updated_at = o.updated_at + s.delta
FROM shifted s
WHERE o.id = s.order_id;

DO $$
DECLARE v_tbl text; v_col text;
BEGIN
  FOR v_tbl, v_col IN SELECT * FROM (VALUES {cascade}) AS v(tbl, col) LOOP
    IF to_regclass(v_tbl) IS NULL THEN CONTINUE; END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = split_part(v_tbl, '.', 1)
        AND c.table_name = split_part(v_tbl, '.', 2)
        AND c.column_name = v_col
    ) THEN CONTINUE; END IF;
    EXECUTE format(
      'UPDATE %s x SET %I = x.%I + s.delta FROM shifted s WHERE x.order_id = s.order_id',
      v_tbl, v_col, v_col
    );
  END LOOP;
END $$;

-- Invoice numbers are minted as CKCODE-GST-YYYYMM-SEQ at create time. After
-- dating, the YYYYMM must follow invoice_date or March filings show a
-- September series.
UPDATE ckac_billing.gst_tax_invoices g
SET invoice_number = left(g.invoice_number, 40) || '-t' || left(g.id::text, 8)
WHERE g.kitchen_id = '{kitchen_id}'::uuid
  AND EXISTS (SELECT 1 FROM shifted s WHERE s.order_id = g.order_id);

UPDATE ckac_billing.gst_tax_invoices g
SET invoice_number = n.fresh
FROM (
  SELECT
    g2.id,
    k.code || '-GST-' || to_char(g2.invoice_date AT TIME ZONE 'UTC', 'YYYYMM')
      || '-' || lpad(
        row_number() OVER (
          PARTITION BY g2.kitchen_id, to_char(g2.invoice_date AT TIME ZONE 'UTC', 'YYYYMM')
          ORDER BY g2.invoice_date, g2.id
        )::text,
        4, '0'
      ) AS fresh
  FROM ckac_billing.gst_tax_invoices g2
  JOIN ckac_identity.kitchens k ON k.id = g2.kitchen_id
  WHERE g2.kitchen_id = '{kitchen_id}'::uuid
    AND EXISTS (SELECT 1 FROM shifted s WHERE s.order_id = g2.order_id)
) n
WHERE g.id = n.id;

COMMIT;
"""
    ok, err = _run_psql(sql)
    if ok:
        log(f"  Dated {len(placed)} orders across {BACKDATE_DAYS} days (+ linked rows).")
    else:
        log(f"  ! History dating FAILED for {kitchen_id}: {err}")
        log(f"    Postgres container: {resolve_postgres_container()} (CKAC_POSTGRES_CONTAINER)")


def date_all_history() -> int:
    """Single dating pass over every order created in this run."""
    if BACKDATE_DAYS <= 0 or not PLACED_ORDERS:
        return 0
    total = sum(len(v) for v in PLACED_ORDERS.values())
    months = BACKDATE_DAYS / DAYS_PER_MONTH
    log("")
    log(
        f"Dating history: {total} orders across {len(PLACED_ORDERS)} kitchens "
        f"over {BACKDATE_DAYS} days (~{months:.1f} months)"
    )
    log("-" * 50)
    for kitchen_id, placed in PLACED_ORDERS.items():
        apply_order_history(kitchen_id, placed)
    return total


def refresh_crm_profiles() -> int:
    """Rebuild CRM profiles for every kitchen that got orders.

    CRM aggregates are built on request (`?refresh=true`), so this has to run
    after dating: `last_order_at` drives churn risk, and a profile synced before
    the dating pass would claim every diner ordered today.
    """
    synced = 0
    # Every kitchen whose orders this run touched, not only the ones it created,
    # so an idempotent re-run still leaves a populated CRM behind.
    for kitchen_id, token in KITCHEN_TOKENS.items():
        try:
            resp = request(
                "GET",
                f"/api/v1/kitchens/{kitchen_id}/crm/customers?refresh=true",
                token=token,
            )
            synced += int(resp.get("total") or 0)
        except ApiError as exc:
            # CRM is entitlement-gated (`loyalty_crm`); a kitchen without the
            # package is a correct refusal, not a seeding failure.
            if any(code in str(exc) for code in (" 402", " 403")):
                continue
            log(f"  ! CRM sync {kitchen_id[:8]}: {exc}")
    if synced:
        log(f"  CRM profiles synced: {synced}")
    return synced


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
    city_customers: list[dict] | None = None,
) -> dict[str, str]:
    """Full menu + pantry + recipes + orders + drafts + per-kitchen integrations."""
    kid = kitchen["id"]
    log(f"  [{kitchen['code']}] {kitchen['name']} ({kitchen.get('city', '')})")
    dish_ids = ensure_dishes(token, kid, dishes)
    log(f"    menu: {len(dish_ids)} dishes")
    ingredient_ids = ensure_ingredients(token, kid, DEMO_PANTRY)
    ensure_dish_recipes(token, kid, dish_ids, DISH_RECIPES, ingredient_ids, DISH_PREP_STEPS)
    log(f"    pantry: {len(ingredient_ids)} ingredients, recipes on {len(DISH_RECIPES)} dishes")
    ensure_orders(token, kid, dish_ids, orders_target, city_customers=city_customers)
    ensure_drafts(token, kid, drafts_target)
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


def _cities_for_customer_seed(kitchen_specs: list[dict]) -> list[dict]:
    """All presence cities on a full run; only kitchens in this run on smoke."""
    if BULK_FULL or BULK_KITCHENS >= len(SEED_CITIES):
        return list(SEED_CITIES)
    used = {s["city"] for s in kitchen_specs}
    return [c for c in SEED_CITIES if c["name"] in used]


def ensure_located_customers(cities: list[dict]) -> dict[str, list[dict]]:
    """WhatsApp-login diners with a home address in each city."""
    by_city: dict[str, list[dict]] = {c["name"]: [] for c in cities}
    if BULK_CUSTOMERS_PER_CITY <= 0 or not cities:
        return by_city
    specs = city_customer_specs(BULK_CUSTOMERS_PER_CITY, cities=cities)
    log(f"City customers: {len(specs)} across {len(cities)} location(s) (OTP {DEMO_OTP})")
    for spec in specs:
        try:
            token = login_customer(spec["phone_e164"], DEMO_OTP)
        except ApiError as exc:
            log(f"  ! customer {spec['phone']}: {exc}")
            continue
        try:
            request(
                "PATCH",
                "/api/v1/customers/me",
                {"name": spec["name"], "email": f"{spec['phone']}@kitchcu.dev"},
                token=token,
            )
        except ApiError as exc:
            log(f"  ! profile {spec['phone']}: {exc}")
        try:
            existing = request("GET", "/api/v1/customers/me/addresses", token=token)
            already = any(
                str(a.get("city", "")).lower() == spec["city"].lower() for a in (existing or [])
            )
            if not already:
                request(
                    "POST",
                    "/api/v1/customers/me/addresses",
                    {
                        "label": "Home",
                        "address_line": spec["address_line"],
                        "city": spec["city"],
                        "state": spec["state"],
                        "pincode": spec["pincode"],
                        "phone": spec["phone_e164"],
                        "latitude": spec["latitude"],
                        "longitude": spec["longitude"],
                        "is_default": True,
                    },
                    token=token,
                )
        except ApiError as exc:
            # Feature flag off or validation — diner still logs in for nearby.
            log(f"  ! address {spec['phone']}: {exc}")
        by_city.setdefault(spec["city"], []).append({**spec, "token": token})
    for city_name, diners in by_city.items():
        phones = ", ".join(d["phone"] for d in diners) or "(none)"
        log(f"  {city_name}: {phones}")
    return by_city


def ensure_city_customer_orders(
    customers_by_city: dict[str, list[dict]],
    kitchens: list[dict],
    dish_ids_by_kitchen: dict[str, dict[str, str]],
    owner_token: str,
) -> int:
    """One customer-PWA order per diner at a kitchen in their city."""
    kitchens_by_city: dict[str, list[dict]] = {}
    for k in kitchens:
        kitchens_by_city.setdefault(str(k.get("city") or ""), []).append(k)
    created = 0
    for city, diners in customers_by_city.items():
        city_kitchens = kitchens_by_city.get(city) or []
        if not city_kitchens or not diners:
            continue
        kitchen = city_kitchens[0]
        dish_ids = dish_ids_by_kitchen.get(kitchen["id"]) or {}
        if not dish_ids:
            continue
        names = list(dish_ids.keys())[:6]
        for idx, diner in enumerate(diners):
            token = diner.get("token")
            if not token:
                continue
            dish_name = names[idx % len(names)]
            payload = {
                "items": [{"dish_id": dish_ids[dish_name], "quantity": 1}],
                "delivery_type": "pickup",
                "payment_method": "cod",
            }
            try:
                order = request(
                    "POST",
                    f"/api/v1/kitchens/{kitchen['id']}/orders/customer",
                    payload,
                    token=token,
                )
                for status in ("accepted", "preparing", "ready", "delivered"):
                    request(
                        "PATCH",
                        f"/api/v1/orders/{order['id']}/status",
                        {"status": status},
                        token=owner_token,
                    )
                created += 1
            except ApiError as exc:
                log(f"  ! city customer order {diner['phone']}: {exc}")
    if created:
        log(f"  City-customer PWA orders: {created}")
    return created


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
        f"{BULK_KITCHENS_PER_OWNER} kitchens | {len(SEED_CITIES)} cities × "
        f"{BULK_CUSTOMERS_PER_CITY} customers"
    )
    log(
        f"History: {BACKDATE_DAYS} days (~{BACKDATE_DAYS / DAYS_PER_MONTH:.1f} months), "
        f"weekday/weekend rhythm, lunch + dinner peaks (IST), growth trend"
    )
    if BULK_FULL:
        log(
            f"Per kitchen: full menu, pantry, {BULK_ORDERS_PER_KITCHEN} orders "
            f"({BULK_PRIMARY_ORDERS} on {DEMO_KITCHEN_CODE}), "
            f"{BULK_DRAFTS_PER_KITCHEN} drafts, integrations"
        )
    else:
        log(
            f"Primary: {BULK_PRIMARY_ORDERS} orders / {BULK_DRAFTS} drafts | "
            f"Secondary: {BULK_DISHES_PER_KITCHEN} dishes"
        )
    log("")

    wait_for_gateway()

    # Demo owner — expand kitchens + full menu + orders
    ensure_owner(DEMO_OWNER["phone"], DEMO_OWNER["name"], DEMO_OWNER["email"])
    demo_token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    log(f"Logged in as {DEMO_OWNER['name']}")

    demo_specs = owner_kitchen_specs(0, BULK_KITCHENS)
    extra_specs: list[dict] = []
    for idx, owner in enumerate(EXTRA_OWNERS[:owner_count]):
        extra_specs.extend(owner_kitchen_specs(idx + 1, BULK_KITCHENS_PER_OWNER, owner["name"]))
    demo_kitchens = ensure_kitchens_for_owner(demo_token, demo_specs)
    log(f"Demo owner has {len(demo_kitchens)} kitchen(s)")
    city_counts: dict[str, int] = {}
    for k in demo_kitchens:
        city_counts[str(k.get("city") or "?")] = city_counts.get(str(k.get("city") or "?"), 0) + 1
    log("  By city: " + ", ".join(f"{name}={n}" for name, n in sorted(city_counts.items())))

    customer_cities = _cities_for_customer_seed(demo_specs + extra_specs)
    customers_by_city = ensure_located_customers(customer_cities)
    for spec in DEMO_CUSTOMER_ADDRESSES:
        try:
            token = login_customer(spec["phone_e164"], DEMO_OTP)
            added = ensure_customer_addresses(token, spec["addresses"])
            log(f"Demo diner {spec['phone_e164']}: +{added} saved address(es)")
        except ApiError as exc:
            log(f"  ! demo diner addresses {spec['phone_e164']}: {exc}")

    primary = primary_kitchen(demo_kitchens)
    all_dishes = enriched_dishes()
    primary_dish_ids: dict[str, str] = {}
    dish_ids_by_kitchen: dict[str, dict[str, str]] = {}

    if BULK_FULL:
        log("")
        log(f"Full seed for {len(demo_kitchens)} kitchens (demo owner)")
        log("-" * 50)
        for k in demo_kitchens:
            dish_ids = ensure_kitchen_complete(
                demo_token,
                k,
                all_dishes,
                # The demo kitchen is the one every walkthrough opens, so it
                # carries the densest history.
                orders_target=(
                    BULK_PRIMARY_ORDERS
                    if k["id"] == primary["id"]
                    else BULK_ORDERS_PER_KITCHEN
                ),
                drafts_target=BULK_DRAFTS_PER_KITCHEN,
                city_customers=customers_by_city.get(str(k.get("city") or ""), []),
            )
            dish_ids_by_kitchen[k["id"]] = dish_ids
            if k["id"] == primary["id"]:
                primary_dish_ids = dish_ids
        if not primary_dish_ids:
            primary_dish_ids = ensure_dishes(demo_token, primary["id"], all_dishes)
            dish_ids_by_kitchen[primary["id"]] = primary_dish_ids
    else:
        log(f"Primary kitchen: {primary['code']} — {primary['name']}")
        primary_dish_ids = ensure_dishes(demo_token, primary["id"], all_dishes)
        dish_ids_by_kitchen[primary["id"]] = primary_dish_ids
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
            dish_ids_by_kitchen[k["id"]] = ensure_dishes(
                demo_token, k["id"], rotated, limit=BULK_DISHES_PER_KITCHEN
            )
            secondary += 1
        log(f"Seeded mini menus on {secondary} secondary kitchens")

        ensure_orders(
            demo_token,
            primary["id"],
            primary_dish_ids,
            BULK_PRIMARY_ORDERS,
            city_customers=customers_by_city.get(str(primary.get("city") or ""), []),
        )
        ensure_drafts(demo_token, primary["id"], BULK_DRAFTS)

    seed_platform_extras(
        owner_token=demo_token,
        kitchen_id=primary["id"],
        dish_ids=primary_dish_ids,
        kitchen_name=primary["name"],
        kitchen_code=primary.get("code"),
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
                    city_customers=customers_by_city.get(str(k.get("city") or ""), []),
                )
                dish_ids_by_kitchen[k["id"]] = dish_ids
                if j == 0:
                    owner_primary_dishes = dish_ids
        else:
            subset = all_dishes[: max(BULK_DISHES_PER_KITCHEN, 6)]
            for j, k in enumerate(kitchens):
                chunk = all_dishes[(idx * 5 + j * 3) : (idx * 5 + j * 3) + BULK_DISHES_PER_KITCHEN]
                if not chunk:
                    chunk = subset
                dish_ids = ensure_dishes(token, k["id"], chunk, limit=BULK_DISHES_PER_KITCHEN)
                dish_ids_by_kitchen[k["id"]] = dish_ids
                if j == 0:
                    owner_primary_dishes = dish_ids

            owner_primary = kitchens[0]
            created_orders = ensure_orders(
                token,
                owner_primary["id"],
                owner_primary_dishes,
                BULK_ORDERS_PER_OWNER,
                city_customers=customers_by_city.get(str(owner_primary.get("city") or ""), []),
            )
            created_drafts = ensure_drafts(
                token,
                owner_primary["id"],
                BULK_DRAFTS_PER_OWNER,
            )
            log(
                f"  {owner['name']}: {len(kitchens)} kitchen(s), "
                f"{len(created_orders)} new orders, {created_drafts} new drafts"
            )
        seeded_owners.append((owner, kitchens))
        if BULK_FULL:
            log(f"  {owner['name']}: {len(kitchens)} kitchen(s) fully seeded")

    all_kitchens = list(demo_kitchens) + [k for _, ks in seeded_owners for k in ks]
    ensure_city_customer_orders(
        customers_by_city,
        all_kitchens,
        dish_ids_by_kitchen,
        demo_token,
    )

    dated = date_all_history()
    refresh_crm_profiles()
    # Ratings can only be posted by a signed-in customer on their own delivered
    # orders. Do this after dating so home-taste aggregates sit on the historic
    # window, not on the handful of extra PWA orders created today.
    located_sessions = [
        diner
        for diners in customers_by_city.values()
        for diner in diners
        if diner.get("token")
    ]
    try:
        ensure_ratings(ensure_customer_sessions() + located_sessions, primary["id"])
    except Exception as exc:  # noqa: BLE001 — extras already log per-customer failures
        log(f"  ! historic ratings: {exc}")

    # Summary
    nearby = request(
        "GET",
        "/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&limit=30&max_km=50&sort=asc",
    )
    orders_final = request("GET", f"/api/v1/kitchens/{primary['id']}/orders", token=demo_token)
    drafts_final = request("GET", f"/api/v1/kitchens/{primary['id']}/orders/drafts", token=demo_token)
    menu_final = request("GET", f"/api/v1/kitchens/{primary['id']}/menu")

    log("")
    log("Bulk seed complete")
    log("-" * 50)
    total_kitchens = len(all_kitchens)
    log(f"  Kitchens seeded (total): {total_kitchens}")
    log(
        f"  History window:          {BACKDATE_DAYS} days "
        f"(~{BACKDATE_DAYS / DAYS_PER_MONTH:.1f} months), {dated} orders dated"
    )
    log(f"  Nearby Pune (50km):      {nearby.get('total', 0)}")
    for city in SEED_CITIES[1:6]:
        try:
            n = request(
                "GET",
                "/api/v1/kitchens/public/nearby"
                f"?latitude={city['latitude']}&longitude={city['longitude']}&limit=20&max_km=50&sort=asc",
            )
            log(f"  Nearby {city['name']} (50km): {n.get('total', 0)}")
        except ApiError as exc:
            log(f"  ! Nearby {city['name']}: {exc}")
    diner_total = sum(len(v) for v in customers_by_city.values())
    log(f"  City customers:         {diner_total} across {len(customers_by_city)} cities")
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
    log(f"Customer app: http://localhost:13001  (OTP {DEMO_OTP})")
    for city_name, diners in customers_by_city.items():
        if not diners:
            continue
        sample = diners[0]
        log(f"  {city_name}: {sample['phone']} ({sample['name']})" + (
            f" +{len(diners) - 1} more" if len(diners) > 1 else ""
        ))


if __name__ == "__main__":
    main()
