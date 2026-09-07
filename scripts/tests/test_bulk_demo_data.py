"""Bulk seed kitchens and customers must cover every platform presence city.

Dry-run uses CKAC_BULK_KITCHENS=1 — that path must stay a single Pune kitchen
so GCP parity smoke does not mint a kitchen per city.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ckac_common.validators import normalize_india_phone

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from bulk_demo_data import (  # noqa: E402
    SEED_CITIES,
    bulk_kitchen_specs,
    city_customer_phone,
    city_customer_specs,
    owner_kitchen_specs,
)
from demo_data import DEMO_CUSTOMERS, DEMO_OWNERS  # noqa: E402

PRESENCE_CITIES = {
    "Pune",
    "Mumbai",
    "Delhi",
    "Gurugram",
    "Noida",
    "Lucknow",
    "Kanpur",
    "Prayagraj",
    "Varanasi",
    "Jhansi",
    "Dehradun",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Kolkata",
}


def test_seed_cities_match_platform_presence() -> None:
    names = [c["name"] for c in SEED_CITIES]
    assert names[0] == "Pune"
    assert set(names) == PRESENCE_CITIES
    assert len(names) == len(set(names))
    for city in SEED_CITIES:
        assert city["areas"], city["name"]
        assert city["latitude"] and city["longitude"]
        assert city["state"] and city["pincode"]


def test_default_bulk_kitchens_cover_every_city() -> None:
    specs = bulk_kitchen_specs(30)
    assert len(specs) == 30
    cities = {s["city"] for s in specs}
    assert PRESENCE_CITIES <= cities
    for spec in specs:
        assert spec["latitude"] != 0
        assert spec["city"] in PRESENCE_CITIES


def test_smoke_count_stays_in_pune_only() -> None:
    specs = bulk_kitchen_specs(1)
    assert len(specs) == 1
    assert specs[0]["city"] == "Pune"


def test_first_kitchen_stays_pune_for_ckpnq_code() -> None:
    assert owner_kitchen_specs(0, 1)[0]["city"] == "Pune"


def test_kitchen_coords_stay_near_city_center() -> None:
    by_name = {c["name"]: c for c in SEED_CITIES}
    for spec in bulk_kitchen_specs(len(SEED_CITIES)):
        center = by_name[spec["city"]]
        assert abs(spec["latitude"] - center["latitude"]) < 0.5
        assert abs(spec["longitude"] - center["longitude"]) < 0.5


def test_city_customers_cover_every_location() -> None:
    specs = city_customer_specs(3)
    assert len(specs) == len(SEED_CITIES) * 3
    cities = {s["city"] for s in specs}
    assert cities == PRESENCE_CITIES
    phones = [s["phone"] for s in specs]
    assert len(phones) == len(set(phones))
    for spec in specs:
        assert normalize_india_phone(spec["phone"]) == spec["phone_e164"]
        assert spec["address_line"]
        assert spec["latitude"] and spec["longitude"]


def test_city_customer_phones_do_not_collide_with_demo_logins() -> None:
    reserved = {o["phone"] for o in DEMO_OWNERS} | {c["phone"] for c in DEMO_CUSTOMERS}
    bulk = {s["phone"] for s in city_customer_specs(5)}
    assert not bulk & reserved
    for phone in bulk:
        assert not phone.startswith("7")
        assert not phone.startswith("8")


def test_city_customer_phone_is_stable() -> None:
    assert city_customer_phone(1, 1) == city_customer_phone(1, 1)
    assert city_customer_phone(1, 1) != city_customer_phone(2, 1)
