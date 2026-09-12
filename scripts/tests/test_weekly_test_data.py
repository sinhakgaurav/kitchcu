"""Weekly QA cohort generator — the pure logic behind the seeding cron.

The cron runs unattended on the VM, so a bad cohort would silently mint accounts the
API rejects, or reuse identifiers across weeks and corrupt earlier cohorts. These tests
cover the identifier scheme, week arithmetic, and diner mix without touching the API.

Every generated phone is checked against the real production validator
(`ckac_common.validators.normalize_india_phone`) rather than a local copy of the rules.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

from ckac_common.validators import normalize_india_phone

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_module():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "weekly_test_data", SCRIPTS_DIR / "weekly_test_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


wtd = _load_module()


# ------------------------------------------------------------------- identifiers


@pytest.mark.parametrize("week", [1, 9, 26, 52, 53])
@pytest.mark.parametrize("count", [5, 10])
def test_every_cohort_phone_is_accepted_by_the_api_validator(week: int, count: int) -> None:
    """A phone the cron mints must be one owner/customer registration will accept."""
    people = wtd.cohort_owners(2026, week, count) + wtd.cohort_customers(2026, week, count)
    assert len(people) == count * 2
    for person in people:
        assert len(person["phone"]) == 10, person
        # Raises ValueError if the platform would reject it.
        assert normalize_india_phone(person["phone"]) == person["phone_e164"]


def test_owner_and_customer_number_spaces_never_collide() -> None:
    owners = {o["phone"] for o in wtd.cohort_owners(2026, 36, 50)}
    customers = {c["phone"] for c in wtd.cohort_customers(2026, 36, 50)}
    assert not owners & customers
    assert len(owners) == 50
    assert len(customers) == 50


def test_cohorts_from_different_weeks_never_share_a_number() -> None:
    week36 = {o["phone"] for o in wtd.cohort_owners(2026, 36, 10)}
    week37 = {o["phone"] for o in wtd.cohort_owners(2026, 37, 10)}
    assert not week36 & week37


def test_cohort_is_stable_across_runs() -> None:
    """Re-running inside the same week must reuse accounts, not create new ones."""
    first = wtd.cohort_owners(2026, 36, 5)
    second = wtd.cohort_owners(2026, 36, 5)
    assert first == second
    assert wtd.cohort_customers(2026, 36, 10) == wtd.cohort_customers(2026, 36, 10)


def test_cohort_tag_encodes_two_digit_year_and_week() -> None:
    assert wtd.cohort_tag(2026, 36) == "W2636"
    assert wtd.cohort_tag(2026, 1) == "W2601"
    assert wtd.cohort_tag(2030, 53) == "W3053"


def test_phone_rejects_an_index_that_would_overflow_ten_digits() -> None:
    with pytest.raises(SystemExit):
        wtd._phone("7", 2026, 36, 100_000)


def test_owners_are_spread_across_cities() -> None:
    owners = wtd.cohort_owners(2026, 36, 5)
    assert len({o["city"]["city"] for o in owners}) == 5


# ------------------------------------------------------------------ week arithmetic


def test_resolve_week_parses_an_explicit_iso_week() -> None:
    assert wtd.resolve_week("2026-W40") == (2026, 40)
    assert wtd.resolve_week("2026-w40") == (2026, 40)


def test_resolve_week_defaults_to_today() -> None:
    assert wtd.resolve_week(None) == dt.date.today().isocalendar()[:2]


@pytest.mark.parametrize("spec", ["2026", "nonsense", "2026-W99", "2026-W0"])
def test_resolve_week_rejects_bad_specs(spec: str) -> None:
    with pytest.raises(SystemExit):
        wtd.resolve_week(spec)


def test_previous_week_steps_back_one_week() -> None:
    assert wtd.previous_week(2026, 36) == (2026, 35)


def test_previous_week_crosses_the_year_boundary() -> None:
    """Week 1 must fall back into the previous ISO year, which may have 52 or 53 weeks."""
    prev = wtd.previous_week(2026, 1)
    assert prev is not None
    year, week = prev
    assert year == 2025
    assert week in (52, 53)


def test_previous_week_returns_none_for_a_week_that_does_not_exist() -> None:
    # 2026 has 53 ISO weeks only if the calendar says so; 2027-W53 does not exist.
    assert wtd.previous_week(2027, 53) is None


# --------------------------------------------------------------------- diner mix


def _diners(prefix: str, n: int) -> list[dict]:
    return [{"phone": f"{prefix}{i}", "name": f"{prefix} {i}"} for i in range(n)]


def test_order_roster_mixes_new_and_returning_diners() -> None:
    new = _diners("new", 10)
    repeat = _diners("old", 10)
    roster = wtd.order_roster(new, repeat, offset=0)[:10]
    phones = {d["phone"] for d in roster}
    assert any(p.startswith("new") for p in phones)
    assert any(p.startswith("old") for p in phones), "returning diners must appear"


def test_order_roster_rotates_per_kitchen() -> None:
    """Different kitchens should not all serve the same faces in the same order."""
    new, repeat = _diners("new", 10), _diners("old", 10)
    first = [d["phone"] for d in wtd.order_roster(new, repeat, offset=0)[:10]]
    second = [d["phone"] for d in wtd.order_roster(new, repeat, offset=3)[:10]]
    assert first != second


def test_order_roster_works_without_a_returning_cohort() -> None:
    """Week one has no previous cohort — orders must still be placeable."""
    roster = wtd.order_roster(_diners("new", 10), [], offset=0)
    assert roster
    assert all(d["phone"].startswith("new") for d in roster)


def test_order_roster_is_empty_when_no_diner_signed_in() -> None:
    assert wtd.order_roster([], [], offset=0) == []


def test_week_fill_covers_seven_days_at_three_orders_per_day() -> None:
    assert wtd.WEEK_FILL_DAYS == 7
    assert wtd.week_fill_target() == 21
    slots = wtd.week_fill_slots(21, days=7, seed=1)
    assert len(slots) == 21
    assert {slot.day_offset for slot in slots} == set(range(7))
