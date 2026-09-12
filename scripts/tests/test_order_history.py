"""Six months of seeded orders has to read like six months a kitchen actually worked.

The previous backdating spread orders linearly and drew the clock as
``NOW() - random() * 12 hours``, which produced three lies an owner would spot
immediately in Reports: a dead-flat revenue line, no dinner service at all (the
12-hour window trails the moment the seeder ran), and orders from five months ago
still sitting in ``preparing``.

These tests pin the distribution instead of the SQL, so the shape is verifiable
without a database.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from bulk_demo_data import STATUS_CHAINS  # noqa: E402
from order_history import (  # noqa: E402
    IN_FLIGHT_MAX_AGE_DAYS,
    LATE_STAGE_CHAIN_KEYS,
    SERVICE_WINDOWS,
    TERMINAL_CHAIN_KEYS,
    WALKIN_FIRST_NAMES,
    WALKIN_LAST_NAMES,
    _walkin_names,
    basket_shape,
    diner_pool,
    order_history_plan,
    slot_to_utc,
)

IST = ZoneInfo("Asia/Kolkata")
SIX_MONTHS = 183


def plan(count: int = 900, days: int = SIX_MONTHS, seed: int = 42):
    return order_history_plan(count, days=days, seed=seed)


# ── Window coverage ──────────────────────────────────────────────────────────


def test_plan_returns_exactly_the_requested_count() -> None:
    assert len(plan(count=250)) == 250
    assert len(plan(count=1)) == 1
    assert plan(count=0) == []


def test_plan_stays_inside_the_requested_window() -> None:
    for slot in plan():
        assert 0 <= slot.day_offset < SIX_MONTHS


def test_plan_spans_the_whole_six_months() -> None:
    """A 6-month report is useless if every order landed in the last fortnight."""
    offsets = [s.day_offset for s in plan()]
    assert max(offsets) >= SIX_MONTHS - 7
    assert min(offsets) <= 1


def test_plan_covers_most_days_in_the_window() -> None:
    """Daily revenue charts need most buckets populated, not a handful of spikes."""
    days_hit = {s.day_offset for s in plan(count=900)}
    assert len(days_hit) >= int(SIX_MONTHS * 0.9)


def test_plan_is_sorted_oldest_first() -> None:
    """The SQL pass matches plan slots to rows by creation order, so order matters."""
    offsets = [s.day_offset for s in plan()]
    assert offsets == sorted(offsets, reverse=True)


# ── Clock realism ────────────────────────────────────────────────────────────


def test_orders_land_only_in_real_service_hours() -> None:
    """No kitchen takes orders at 04:00. The old 12-hour random window did."""
    allowed = {h for window in SERVICE_WINDOWS for h in range(window.start_hour, window.end_hour)}
    for slot in plan():
        assert slot.hour in allowed, f"hour {slot.hour} outside service windows"
        assert 0 <= slot.minute < 60


def test_both_lunch_and_dinner_service_appear() -> None:
    """The peak-hours report was flat because the old window never reached dinner."""
    hours = Counter(s.hour for s in plan())
    lunch = sum(n for h, n in hours.items() if 12 <= h <= 14)
    dinner = sum(n for h, n in hours.items() if 19 <= h <= 22)
    assert lunch > 0 and dinner > 0
    # Neither service may collapse to a rounding error against the other.
    assert min(lunch, dinner) > max(lunch, dinner) * 0.25


def test_lunch_and_dinner_outrank_the_quiet_hours() -> None:
    hours = Counter(s.hour for s in plan())
    peak = sum(n for h, n in hours.items() if h in (13, 20))
    quiet = sum(n for h, n in hours.items() if h in (10, 16))
    assert peak > quiet


# ── Status realism ───────────────────────────────────────────────────────────


def test_every_chain_key_is_a_real_status_chain() -> None:
    for slot in plan():
        assert slot.chain_key in STATUS_CHAINS


def test_old_orders_are_always_finished() -> None:
    """An order from five months ago cannot still be 'preparing'."""
    for slot in plan():
        if slot.day_offset > IN_FLIGHT_MAX_AGE_DAYS:
            assert slot.chain_key in TERMINAL_CHAIN_KEYS, (
                f"day -{slot.day_offset} left in {slot.chain_key}"
            )


def test_recent_orders_still_have_live_work() -> None:
    """The owner dashboard needs a live queue, so today's orders stay in flight."""
    recent = [s for s in plan() if s.day_offset <= IN_FLIGHT_MAX_AGE_DAYS]
    assert recent, "no recent orders at all"
    assert any(s.chain_key not in TERMINAL_CHAIN_KEYS for s in recent)


def test_yesterdays_unfinished_orders_are_nearly_done() -> None:
    """An order can still be out for delivery overnight; it cannot still be 'received'."""
    for slot in plan():
        if slot.day_offset != 1 or slot.chain_key in TERMINAL_CHAIN_KEYS:
            continue
        assert slot.chain_key in LATE_STAGE_CHAIN_KEYS, (
            f"yesterday's order sitting in {slot.chain_key}"
        )


def test_only_today_holds_early_stage_orders() -> None:
    early = {
        s.day_offset
        for s in plan()
        if s.chain_key not in TERMINAL_CHAIN_KEYS
        and s.chain_key not in LATE_STAGE_CHAIN_KEYS
    }
    assert early <= {0}, f"early-stage orders dated {sorted(early)} days back"


def test_cancellations_stay_a_minority() -> None:
    keys = Counter(s.chain_key for s in plan())
    cancelled = keys["cancelled"] + keys["cancelled_late"]
    assert 0 < cancelled < len(plan()) * 0.15


# ── Business shape ───────────────────────────────────────────────────────────


def test_volume_grows_over_the_six_months() -> None:
    """A kitchen on a growth OS should be visibly growing, not flat."""
    slots = plan(count=900)
    first_month = sum(1 for s in slots if s.day_offset >= SIX_MONTHS - 30)
    last_month = sum(1 for s in slots if s.day_offset < 30)
    assert last_month > first_month * 1.2


def test_weekends_are_busier_than_weekdays() -> None:
    now = datetime.now(UTC)
    per_day: Counter[int] = Counter()
    for slot in plan(count=900):
        day = (now - timedelta(days=slot.day_offset)).astimezone(IST)
        per_day[day.weekday()] += 1
    weekend = (per_day[5] + per_day[6]) / 2
    weekday = sum(per_day[d] for d in range(5)) / 5
    assert weekend > weekday


# ── Determinism ──────────────────────────────────────────────────────────────


def test_plan_is_deterministic_for_a_seed() -> None:
    assert plan(seed=7) == plan(seed=7)


def test_different_seeds_give_different_kitchens_different_days() -> None:
    """Every kitchen sharing one curve would make the platform look synthetic."""
    a = [s.day_offset for s in plan(count=200, seed=1)]
    b = [s.day_offset for s in plan(count=200, seed=2)]
    assert a != b


# ── UTC conversion ───────────────────────────────────────────────────────────


def test_utc_alias_works_on_python_310() -> None:
    """GCP host python3 is 3.10; datetime.UTC is 3.11+ only."""
    import order_history

    assert order_history.UTC is timezone.utc


def test_slot_converts_ist_wall_clock_to_utc() -> None:
    now = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
    slot = next(s for s in plan() if s.day_offset == 30)
    stamped = slot_to_utc(slot, now=now)
    local = stamped.astimezone(IST)
    assert local.hour == slot.hour
    assert local.minute == slot.minute
    assert stamped.tzinfo is not None


def test_no_slot_is_dated_in_the_future() -> None:
    """Dinner slots on 'today' must not be stamped before dinner has happened."""
    now = datetime.now(UTC)
    for slot in plan():
        assert slot_to_utc(slot, now=now) <= now


def test_today_slots_are_clamped_but_stay_today() -> None:
    now = datetime(2026, 9, 11, 6, 0, tzinfo=UTC)  # 11:30 IST — before dinner
    for slot in plan():
        if slot.day_offset != 0:
            continue
        stamped = slot_to_utc(slot, now=now)
        assert stamped <= now
        assert stamped.astimezone(IST).date() == now.astimezone(IST).date()


# ── Diner pool ───────────────────────────────────────────────────────────────
#
# Six months of orders shared between three phone numbers makes CRM, customer
# segments and churn risk meaningless: every diner looks like a VIP with 70
# orders. The pool has to grow with the order count and keep a repeat core.

LOCATED = [("Sneha Kulkarni", "+916201000001"), ("Amit Desai", "+916201000002")]


def test_distinct_diners_scale_with_order_volume() -> None:
    small = diner_pool(60, LOCATED, seed=1)
    large = diner_pool(600, LOCATED, seed=1)
    assert len(large.diners) > len(small.diners) * 5


def test_pool_is_large_enough_for_meaningful_segments() -> None:
    """Analytics splits at >=5 (vip) and >=2 (repeat) orders in the window."""
    pool = diner_pool(200, LOCATED, seed=1)
    assert 30 <= len(pool.diners) <= 90, len(pool.diners)


def test_located_diners_are_the_repeat_core() -> None:
    """Registered city diners must have rich history; their logins demo order history."""
    pool = diner_pool(200, LOCATED, seed=1)
    phones = [phone for _, phone in pool.diners]
    for _, phone in LOCATED:
        assert phone in phones
    weight_by_phone = dict(zip(phones, pool.weights))
    median = sorted(pool.weights)[len(pool.weights) // 2]
    for _, phone in LOCATED:
        assert weight_by_phone[phone] > median


def test_pool_mixes_heavy_and_one_off_diners() -> None:
    pool = diner_pool(300, LOCATED, seed=1)
    assert max(pool.weights) >= 3 * min(pool.weights)


def test_pool_phones_are_unique_and_indian_mobiles() -> None:
    pool = diner_pool(300, LOCATED, seed=1)
    phones = [p for _, p in pool.diners if p]
    assert len(phones) == len(set(phones))
    for phone in phones:
        assert phone.startswith("+91") and len(phone) == 13, phone


def test_pool_does_not_collide_with_seeded_login_numbers() -> None:
    """Generated walk-ins must not shadow a demo account's order history."""
    pool = diner_pool(400, LOCATED, seed=1)
    generated = {p for _, p in pool.diners} - {p for _, p in LOCATED}
    for phone in generated:
        assert not phone.startswith("+9198765")  # demo owners
        assert not phone.startswith("+919123")  # demo customers
        assert not phone.startswith("+9162")  # bulk city diners


def test_every_diner_has_a_distinct_name() -> None:
    """Three phones sharing one name makes the CRM list look like a bug."""
    pool = diner_pool(600, LOCATED, seed=1)
    names = [name for name, _ in pool.diners]
    assert len(names) == len(set(names))


def test_surnames_vary_from_the_first_few_diners() -> None:
    """Top-of-CRM diners sharing one surname reads as a bug, not a customer base."""
    pool = diner_pool(60, [], seed=1)
    surnames = {name.split()[-1] for name, _ in pool.diners[:10]}
    assert len(surnames) >= 5, surnames


def test_plain_name_combinations_are_used_before_initials() -> None:
    count = len(WALKIN_FIRST_NAMES) * len(WALKIN_LAST_NAMES)
    names = _walkin_names(count, taken=set())
    assert len(set(names)) == count
    assert not any("." in name for name in names)


def test_a_years_worth_of_diners_still_all_get_names() -> None:
    """A 12-month window asks for more diners than there are name combinations."""
    pool = diner_pool(2000, LOCATED, seed=1)
    assert len(pool.diners) == pytest.approx(2000 / 3.5, abs=1)
    assert len({name for name, _ in pool.diners}) == len(pool.diners)


def test_generated_names_never_shadow_a_located_diner() -> None:
    pool = diner_pool(400, LOCATED, seed=1)
    generated = [name for name, phone in pool.diners if phone not in {p for _, p in LOCATED}]
    for name, _ in LOCATED:
        assert name not in generated


def test_pool_is_deterministic_for_a_seed() -> None:
    assert diner_pool(200, LOCATED, seed=5) == diner_pool(200, LOCATED, seed=5)


def test_pool_works_with_no_located_diners() -> None:
    pool = diner_pool(120, [], seed=1)
    assert len(pool.diners) >= 20
    assert len(pool.weights) == len(pool.diners)


# ── Basket ───────────────────────────────────────────────────────────────────


def test_basket_stays_a_plausible_home_food_order() -> None:
    """1-3 dishes at quantity 1-3 averaged a 4-item basket and a Rs 1000+ AOV."""
    import random as _random

    rng = _random.Random(3)
    baskets = [basket_shape(rng, available=11) for _ in range(4000)]
    avg_units = sum(dishes * qty for dishes, qty in baskets) / len(baskets)
    assert 1.5 < avg_units < 3.0, avg_units


def test_basket_never_exceeds_the_menu() -> None:
    import random as _random

    rng = _random.Random(3)
    for available in (1, 2, 3, 11):
        for _ in range(200):
            dishes, qty = basket_shape(rng, available=available)
            assert 1 <= dishes <= available
            assert 1 <= qty <= 3


def test_single_dish_orders_are_the_most_common() -> None:
    import random as _random

    rng = _random.Random(3)
    counts = Counter(basket_shape(rng, available=11)[0] for _ in range(4000))
    assert counts[1] > counts[3]
