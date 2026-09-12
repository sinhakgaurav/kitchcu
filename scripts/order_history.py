"""Shape a seeded order history so six months of Reports read like real trading.

Backdating used to be a single SQL sweep: spread rows linearly across N days and
subtract ``random() * 12 hours`` from ``NOW()``. That is fine for a 30-day smoke
run and wrong for a 6-month demo, because it produces three things no kitchen
would recognise:

* a flat revenue line — no weekly rhythm, no growth
* an empty dinner service — the 12-hour window trails whenever the seeder ran,
  so a 17:00 run can only mint orders between 05:00 and 17:00
* orders from five months ago still sitting in ``preparing``

This module decides the shape in Python so it can be asserted without a
database (``scripts/tests/test_order_history.py``). The seeder creates orders
oldest-first through the normal API — status still moves through the real state
machine and still publishes events — and then stamps the planned timestamps.

All wall-clock reasoning is Asia/Kolkata, matching the analytics bucketing in
``services/order/app/analytics.py``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from string import ascii_uppercase
from zoneinfo import ZoneInfo

# Host Python on the GCP VM is 3.10 — datetime.UTC exists only in 3.11+.
UTC = timezone.utc

IST = ZoneInfo("Asia/Kolkata")

# Average Gregorian month, so "6 months" is 183 days rather than 180.
DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class ServiceWindow:
    """A stretch of the day a kitchen actually takes orders in."""

    name: str
    start_hour: int
    end_hour: int  # exclusive
    weight: int


# Weights are relative order volume, not durations. Lunch and dinner carry the
# day for tiffin and home-food kitchens; breakfast and the afternoon are thin.
# The windows are contiguous (08:00–23:00) so no hour inside trading is dead.
SERVICE_WINDOWS: tuple[ServiceWindow, ...] = (
    ServiceWindow("breakfast", 8, 11, 10),
    ServiceWindow("lunch", 11, 15, 35),
    ServiceWindow("snacks", 15, 19, 15),
    ServiceWindow("dinner", 19, 23, 40),
)

# Orders older than this must have reached a terminal state. Anything newer may
# still be in flight, which is what keeps the owner dashboard queue populated.
IN_FLIGHT_MAX_AGE_DAYS = 2

# Chain keys index STATUS_CHAINS in bulk_demo_data.
TERMINAL_CHAIN_KEYS = frozenset(
    {"delivered", "delivered_delivery", "cancelled", "cancelled_late"}
)

# How far an unfinished order plausibly got depends on its age. A rider can still
# be out overnight; a three-day-old ticket cannot still say "received".
LATE_STAGE_CHAIN_KEYS = frozenset({"ready", "out_for_delivery"})

# Settled history: almost everything was delivered; a small tail was cancelled.
HISTORIC_CHAIN_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("delivered", 62),
    ("delivered_delivery", 30),
    ("cancelled", 5),
    ("cancelled_late", 3),
)

# Today: the full live queue an owner logs in to work.
TODAY_CHAIN_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("received", 18),
    ("accepted", 14),
    ("preparing", 20),
    ("ready", 12),
    ("out_for_delivery", 10),
    ("delivered", 16),
    ("delivered_delivery", 6),
    ("cancelled", 3),
    ("cancelled_late", 1),
)

# Yesterday and the day before: mostly closed, with a few late-stage stragglers.
RECENT_CHAIN_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("delivered", 55),
    ("delivered_delivery", 28),
    ("out_for_delivery", 6),
    ("ready", 4),
    ("cancelled", 4),
    ("cancelled_late", 3),
)

# Relative volume of the oldest day against the newest, so a 6-month chart shows
# a kitchen that grew rather than one that traded flat.
GROWTH_FLOOR = 0.45

# Saturday/Sunday lift.
WEEKEND_LIFT = 1.4

# Per-day noise, so the curve is not visibly a formula.
DAY_JITTER = (0.85, 1.15)


@dataclass(frozen=True)
class OrderSlot:
    """One planned order: when it was placed (IST) and how far it got."""

    day_offset: int  # days before today; 0 = today
    hour: int  # IST
    minute: int  # IST
    chain_key: str


def _weighted_choice(rng: random.Random, weights: tuple[tuple[str, int], ...]) -> str:
    keys = [k for k, _ in weights]
    return rng.choices(keys, weights=[w for _, w in weights], k=1)[0]


def _pick_clock(rng: random.Random) -> tuple[int, int]:
    window = rng.choices(
        SERVICE_WINDOWS, weights=[w.weight for w in SERVICE_WINDOWS], k=1
    )[0]
    hour = rng.randrange(window.start_hour, window.end_hour)
    return hour, rng.randrange(0, 60)


def _day_weights(days: int, *, now: datetime, rng: random.Random) -> list[float]:
    """Relative volume per day, newest first, blending growth, weekend and noise."""
    local_now = now.astimezone(IST)
    weights: list[float] = []
    for offset in range(days):
        # 0.0 at the oldest day, 1.0 at the newest.
        progress = 1.0 - (offset / max(days - 1, 1))
        growth = GROWTH_FLOOR + (1.0 - GROWTH_FLOOR) * progress
        weekday = (local_now - timedelta(days=offset)).weekday()
        weekend = WEEKEND_LIFT if weekday >= 5 else 1.0
        weights.append(growth * weekend * rng.uniform(*DAY_JITTER))
    return weights


def order_history_plan(
    count: int,
    *,
    days: int,
    seed: int = 42,
    now: datetime | None = None,
) -> list[OrderSlot]:
    """Plan ``count`` orders across the last ``days``, oldest first.

    Oldest-first matters: the seeder creates orders in this order and the SQL
    pass matches plan slots to rows by creation sequence.
    """
    if count <= 0:
        return []
    if days <= 0:
        raise ValueError(f"days must be positive, got {days}")
    now = now or datetime.now(UTC)
    rng = random.Random(seed)

    # One order on every day first, so no day in a daily chart is empty purely
    # because the weighted draw missed it. The remainder carries the shape.
    per_day = [0] * days
    remaining = count
    if count >= days:
        per_day = [1] * days
        remaining = count - days

    if remaining:
        weights = _day_weights(days, now=now, rng=rng)
        for offset in rng.choices(range(days), weights=weights, k=remaining):
            per_day[offset] += 1

    slots: list[OrderSlot] = []
    for offset in range(days - 1, -1, -1):  # oldest first
        if offset == 0:
            table = TODAY_CHAIN_WEIGHTS
        elif offset <= IN_FLIGHT_MAX_AGE_DAYS:
            table = RECENT_CHAIN_WEIGHTS
        else:
            table = HISTORIC_CHAIN_WEIGHTS
        for _ in range(per_day[offset]):
            hour, minute = _pick_clock(rng)
            slots.append(
                OrderSlot(
                    day_offset=offset,
                    hour=hour,
                    minute=minute,
                    chain_key=_weighted_choice(rng, table),
                )
            )
    return slots


def slot_to_utc(slot: OrderSlot, *, now: datetime) -> datetime:
    """Resolve a slot to a UTC instant that has actually already happened."""
    local_now = now.astimezone(IST)
    day = (local_now - timedelta(days=slot.day_offset)).date()
    stamped = datetime.combine(day, time(slot.hour, slot.minute), tzinfo=IST).astimezone(UTC)
    if stamped <= now:
        return stamped

    # Today can hold a dinner slot while it is still lunchtime. Compress the slot
    # into the part of today that has already elapsed rather than clamping every
    # such order onto the same instant.
    open_hour = SERVICE_WINDOWS[0].start_hour
    close_hour = SERVICE_WINDOWS[-1].end_hour
    day_open = datetime.combine(day, time(open_hour, 0), tzinfo=IST).astimezone(UTC)
    if now <= day_open:
        return now
    minutes_in = (slot.hour * 60 + slot.minute) - open_hour * 60
    span_minutes = (close_hour - open_hour) * 60
    fraction = min(max(minutes_in / span_minutes, 0.0), 1.0)
    return day_open + (now - day_open) * fraction


# ── Diners ───────────────────────────────────────────────────────────────────
#
# Sharing six months of orders between the two or three registered city diners
# made every customer look like a VIP with seventy orders, which leaves CRM,
# customer segments and churn risk with nothing to say. A real kitchen has a
# small loyal core, a wider set of regulars, and a long tail of one-off diners.

# Orders per distinct diner over the window. Analytics calls >=5 orders a VIP
# and >=2 a repeat customer, so this has to land near those thresholds.
ORDERS_PER_DINER = 3.5

# (share of pool, relative order frequency)
DINER_TIERS: tuple[tuple[float, int], ...] = (
    (0.12, 6),  # loyal core — several orders a month
    (0.30, 3),  # regulars
    (0.58, 1),  # tried it once or twice
)

# 74xxxxxxxx keeps generated walk-ins clear of every seeded login: demo owners
# are 98765…, demo customers 9123…, and bulk city diners 62…. Weekly QA uses
# 7-prefixed owners, so the second digit is pinned to 4.
WALKIN_PHONE_PREFIX = "74"

# Names are combined rather than listed so a 600-order pool still gives every
# diner a distinct name — a CRM list with three different "Rahul Gupta" phone
# numbers reads as a bug, not as a demo.
WALKIN_FIRST_NAMES = (
    "Aarav", "Ishita", "Rehan", "Kavya", "Devansh", "Nandini", "Yusuf", "Tara",
    "Siddharth", "Aditi", "Zoya", "Kabir", "Meghna", "Aniket", "Shreya",
    "Harshad", "Bhavna", "Om", "Ruchi", "Tejas",
)
# Coprime with the first-name count, so stepping both lists together walks every
# pair exactly once. Equal-length or common-factor lists would hand the first
# twenty diners the same surname, and a CRM list of one family reads as a bug.
WALKIN_LAST_NAMES = (
    "Bhalerao", "Chitnis", "Gokhale", "Hegde", "Jadhav", "Kamat", "Lokhande",
    "Mhatre", "Nadkarni", "Pawar", "Ranade", "Sathe", "Thorat",
)


def _walkin_names(count: int, *, taken: set[str]) -> list[str]:
    """Distinct names, walking first names fastest so a short pool stays varied."""
    combinations = len(WALKIN_FIRST_NAMES) * len(WALKIN_LAST_NAMES)
    limit = combinations * (len(ascii_uppercase) + 1)
    names: list[str] = []
    offset = 0
    while len(names) < count:
        if offset >= limit:
            raise ValueError(f"Cannot generate {count} distinct diner names")
        pass_index, position = divmod(offset, combinations)
        offset += 1
        first = WALKIN_FIRST_NAMES[position % len(WALKIN_FIRST_NAMES)]
        last = WALKIN_LAST_NAMES[position % len(WALKIN_LAST_NAMES)]
        # Once the plain combinations are used up a middle initial keeps names
        # distinct, instead of the pool quietly shrinking to the name supply.
        name = (
            f"{first} {last}"
            if pass_index == 0
            else f"{first} {ascii_uppercase[pass_index - 1]}. {last}"
        )
        if name in taken:
            continue
        taken.add(name)
        names.append(name)
    return names


@dataclass(frozen=True)
class DinerPool:
    """Diners to draw orders from, with how often each one orders."""

    diners: tuple[tuple[str, str], ...]  # (name, E.164 phone)
    weights: tuple[int, ...]


def diner_pool(
    order_count: int,
    located: list[tuple[str, str]] | tuple[tuple[str, str], ...],
    *,
    seed: int = 42,
) -> DinerPool:
    """Build a diner pool sized to the order volume.

    Registered city diners go in first and sit in the loyal core, so their
    logins demo a full order history; the rest are generated walk-ins that give
    the long tail segmentation needs.
    """
    rng = random.Random(seed)
    located = list(located)
    target = max(len(located), round(order_count / ORDERS_PER_DINER), 1)

    diners: list[tuple[str, str]] = list(located)
    used_phones = {phone for _, phone in located}
    taken_names = {name for name, _ in located}
    names = _walkin_names(target - len(located), taken=taken_names)
    slot = 1
    while len(diners) < target and names:
        phone = f"+91{WALKIN_PHONE_PREFIX}{slot:08d}"
        slot += 1
        if phone in used_phones:
            continue
        used_phones.add(phone)
        diners.append((names.pop(0), phone))

    weights: list[int] = []
    for index in range(len(diners)):
        position = index / len(diners)
        cumulative = 0.0
        weight = DINER_TIERS[-1][1]
        for share, tier_weight in DINER_TIERS:
            cumulative += share
            if position < cumulative:
                weight = tier_weight
                break
        weights.append(weight)

    # Shuffle only the generated tail: the located diners keep the core weights.
    tail = list(zip(diners[len(located) :], weights[len(located) :]))
    rng.shuffle(tail)
    merged = list(zip(diners[: len(located)], weights[: len(located)])) + tail
    return DinerPool(
        diners=tuple(d for d, _ in merged),
        weights=tuple(w for _, w in merged),
    )


# ── Basket ───────────────────────────────────────────────────────────────────

# 1-3 dishes at quantity 1-3 averaged four units an order and pushed the demo
# average order value past Rs 1000 — double what home food and tiffin actually
# bill. Most orders are one dish for one person.
DISH_COUNT_WEIGHTS: tuple[tuple[int, int], ...] = ((1, 50), (2, 35), (3, 15))
QUANTITY_WEIGHTS: tuple[tuple[int, int], ...] = ((1, 78), (2, 18), (3, 4))


def basket_shape(rng: random.Random, *, available: int) -> tuple[int, int]:
    """(number of distinct dishes, quantity each) for one order."""
    counts = [(n, w) for n, w in DISH_COUNT_WEIGHTS if n <= available]
    if not counts:
        counts = [(max(1, min(available, 1)), 1)]
    dishes = rng.choices([n for n, _ in counts], weights=[w for _, w in counts], k=1)[0]
    quantity = rng.choices(
        [q for q, _ in QUANTITY_WEIGHTS], weights=[w for _, w in QUANTITY_WEIGHTS], k=1
    )[0]
    return dishes, quantity


def plan_summary(slots: list[OrderSlot]) -> str:
    """One-line description for seeder logs."""
    if not slots:
        return "no orders"
    oldest = max(s.day_offset for s in slots)
    live = sum(1 for s in slots if s.chain_key not in TERMINAL_CHAIN_KEYS)
    cancelled = sum(1 for s in slots if s.chain_key.startswith("cancelled"))
    days_hit = len({s.day_offset for s in slots})
    return (
        f"{len(slots)} orders over {oldest + 1}d ({days_hit} active days), "
        f"{live} in flight, {cancelled} cancelled"
    )
